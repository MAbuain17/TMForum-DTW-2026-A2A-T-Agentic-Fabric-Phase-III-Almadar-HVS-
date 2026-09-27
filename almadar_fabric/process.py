"""Compile the supported HVS1 BPMN subset into graph and pinned Task-T templates."""

from pathlib import Path
import xml.etree.ElementTree as ET
from .audit import digest

DATA = Path(__file__).parent / "data"
FIELDS = (
    "Task Description",
    "Task Type",
    "Target Object",
    "Task Context",
    "Constraints",
    "Expected Output",
)
SKILLS = {
    "Task_RCA": "fault.diagnose",
    "Task_CEAndImpact": "subscriber.impact",
    "Task_Prioritize": "fault.prioritize",
    "Task_HandleAndRemediate": "fault.recommend",
    "Task_CrossDomainRemediation": "fault.coordinate",
    "Task_ConfirmRestoration": "service.verify",
}


def compile_process(path=None):
    root = ET.parse(path or DATA / "mobile-assurance.bpmn").getroot()
    ns = {"b": "http://www.omg.org/spec/BPMN/20100524/MODEL"}
    process = root.find("b:process", ns)
    if process is None:
        raise ValueError("Missing BPMN process")
    allowed = {
        "laneSet",
        "documentation",
        "startEvent",
        "endEvent",
        "parallelGateway",
        "task",
        "sequenceFlow",
    }
    if any(x.tag.split("}")[-1] not in allowed for x in process):
        raise ValueError("Unsupported BPMN element")
    nodes = [
        {
            "id": x.attrib["id"],
            "name": x.attrib.get("name", x.attrib["id"]),
            "type": x.tag.split("}")[-1],
        }
        for x in process
        if x.tag.split("}")[-1] in {"startEvent", "endEvent", "parallelGateway", "task"}
    ]
    ids = {x["id"] for x in nodes}
    if len(ids) != len(nodes):
        raise ValueError("Duplicate BPMN node")
    edges = [
        {
            "id": x.attrib["id"],
            "from": x.attrib["sourceRef"],
            "to": x.attrib["targetRef"],
        }
        for x in process.findall("b:sequenceFlow", ns)
    ]
    if any(x["from"] not in ids or x["to"] not in ids for x in edges):
        raise ValueError("Dangling BPMN edge")
    tasks = {x["id"]: x for x in nodes if x["type"] == "task"}
    if set(tasks) != set(SKILLS):
        raise ValueError("Expected the six HVS1 activities")
    lanes = {}
    for lane in process.findall("b:laneSet/b:lane", ns):
        for ref in lane.findall("b:flowNodeRef", ns):
            if ref.text in lanes:
                raise ValueError("Ambiguous activity lane")
            lanes[ref.text] = lane.attrib["name"]

    def predecessors(node, visited=frozenset()):
        if node in visited:
            raise ValueError("Cyclic BPMN is unsupported")
        result = set()
        for edge in edges:
            if edge["to"] == node:
                parent = edge["from"]
                result |= (
                    {parent}
                    if parent in tasks
                    else set(predecessors(parent, visited | {node}))
                )
        return sorted(result)

    templates = {}
    for task_id, task in tasks.items():
        if task_id not in lanes:
            raise ValueError("Task has no lane")
        template = {
            "id": task_id,
            "version": "1.0",
            "hvs": "HVS1",
            "domain": "Assurance",
            "description": task["name"],
            "lane": lanes[task_id],
            "skill": SKILLS[task_id],
            "required_evidence": predecessors(task_id),
            "allowed_initiators": {
                "Task_RCA": ["anomaly"],
                "Task_CEAndImpact": ["anomaly"],
                "Task_Prioritize": ["diagnostics"],
                "Task_HandleAndRemediate": ["prioritise"],
                "Task_CrossDomainRemediation": ["recommend"],
                "Task_ConfirmRestoration": ["coordinate"],
            }[task_id],
            "fields": list(FIELDS),
        }
        templates[task_id] = template | {"template_hash": digest(template)}
    graph = {"id": process.attrib["id"], "nodes": nodes, "edges": edges}
    return {
        "graph": graph,
        "process_hash": digest(graph),
        "templates": templates,
        "lane_playbooks": {
            lane: [t for t in tasks if lanes[t] == lane]
            for lane in sorted(set(lanes.values()))
        },
    }


def render_prompt(template, incident, evidence):
    return dict(
        zip(
            FIELDS,
            [
                template["description"],
                "FAULT_MANAGEMENT / HVS1",
                {
                    "transport_id": incident.transport_id,
                    "cell_ids": list(incident.cell_ids),
                },
                {
                    "incident_id": incident.incident_id,
                    "service": incident.service,
                    "evidence_ids": sorted(evidence),
                },
                {
                    "scope": "incident-only",
                    "bulk_reset_allowed": False,
                    "min_throughput_mbps": incident.min_throughput_mbps,
                    "max_packet_loss_pct": incident.max_packet_loss_pct,
                },
                {
                    "format": "structured evidence and explanation",
                    "closure_requires": "measured service restoration",
                },
            ],
        )
    )
