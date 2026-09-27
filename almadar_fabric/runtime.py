"""Agent-owned HVS1 handoffs against a compiled operator playbook."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from .agents import Registry, MobileTwin
from .audit import AuditLog, verify_chain
from .gateway import GovernanceObserver, TrustGateway
from .models import Incident, DispatchDenied
from .process import compile_process, render_prompt

SCENARIOS = {
    "transport-fault": "Shared backhaul degradation",
    "missing-topology": "Missing topology evidence",
    "unsafe-action": "Bulk reset rejected",
    "prompt-tampered": "Altered signed request rejected",
    "privacy-redaction": "Subscriber identifiers redacted",
    "persistent-degradation": "Service remains degraded",
    "unregistered-agent": "Transport agent not onboarded",
}


def sample_incident():
    return Incident()


class AssuranceSession:
    def __init__(self, incident, scenario):
        self.incident = Incident.from_dict(incident.to_dict())
        self.scenario, self.design = scenario, compile_process()
        self.registry, self.audit, self.observer = (
            Registry(),
            AuditLog(),
            GovernanceObserver(),
        )
        self.gateway = TrustGateway(self.audit, self.observer)
        self.twin, self.results, self.messages = (
            MobileTwin(self.incident, scenario),
            {},
            [],
        )
        if scenario == "unregistered-agent":
            self.registry.cards["transport"]["onboarded"] = False

    def dispatch(self, initiator, activity, evidence, skill=None):
        template = deepcopy(self.design["templates"][activity])
        if skill:
            template.update(
                id=activity + "/" + skill,
                skill=skill,
                required_evidence=["Task_CrossDomainRemediation"],
                allowed_initiators=["coordinate"],
            )
            from .audit import digest

            template["template_hash"] = digest(
                {k: v for k, v in template.items() if k != "template_hash"}
            )
        card = self.registry.discover(template["skill"])
        self.audit.append(
            "discover",
            initiator,
            "Capability discovered",
            skill=template["skill"],
            executor=card["agent_id"],
        )
        payload = {
            "initiator": initiator,
            "executor": card["agent_id"],
            "activity": template["id"],
            "skill": template["skill"],
            "template_hash": template["template_hash"],
            "structured_prompt": render_prompt(template, self.incident, evidence),
            "evidence": deepcopy(evidence),
        }
        if self.scenario == "privacy-redaction" and activity == "Task_CEAndImpact":
            payload["subscriber_ids"] = ["synthetic-subscriber-001"]
        if self.scenario == "unsafe-action" and skill == "transport.remediate":
            payload["structured_prompt"]["Constraints"]["bulk_reset_allowed"] = True
        envelope = self.gateway.sign(payload, template, self.incident, self.registry)
        if self.scenario == "prompt-tampered" and activity == "Task_Prioritize":
            envelope["payload"]["structured_prompt"]["Target Object"][
                "transport_id"
            ] = "OUT-OF-SCOPE"
        checked = self.gateway.verify(envelope, card["agent_id"])
        wire = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {"message": {"metadata": {"local_a2at_profile": envelope}}},
        }
        self.messages.append(wire)
        result = self.twin.execute(checked["skill"], checked["evidence"])
        self.audit.append(
            "execute",
            card["agent_id"],
            template["description"],
            activity=template["id"],
            result=result,
            passport_id=envelope["passport"]["id"],
        )
        return result, card["agent_id"]

    def handoff(self, owner, activity):
        result, receiver = self.dispatch(owner, activity, self.results)
        self.results[activity] = result
        if activity == "Task_Prioritize":
            return self.handoff(receiver, "Task_HandleAndRemediate")
        if activity == "Task_HandleAndRemediate":
            return self.handoff(receiver, "Task_CrossDomainRemediation")
        if activity == "Task_CrossDomainRemediation":
            # Domain actions are ordered so an unavailable domain cannot cause a partial change.
            for skill in ("ran.check", "core.check", "transport.remediate"):
                self.registry.discover(skill)
            self.audit.append(
                "negotiate",
                receiver,
                "TARGET → FEASIBILITY → INFORMATION accepted in local domain policy",
                target=self.incident.transport_id,
                backup_path_available=True,
                scope="incident-only",
            )
            for skill in ("ran.check", "core.check", "transport.remediate"):
                result, _ = self.dispatch(receiver, activity, self.results, skill)
                self.results[skill] = result
            return self.handoff(receiver, "Task_ConfirmRestoration")
        return result

    def start(self):
        self.audit.append(
            "event",
            "anomaly",
            "Domain-scoped anomaly subscription matched",
            domain="Assurance",
            incident_id=self.incident.incident_id,
            profile="local Event-T representation",
        )
        status, reason = (
            "restored",
            "Throughput and packet loss meet the incident closure thresholds",
        )
        try:
            # Both branches complete before the prioritisation agent receives a task.
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = {
                    activity: pool.submit(self.dispatch, "anomaly", activity, {})
                    for activity in ("Task_RCA", "Task_CEAndImpact")
                }
                errors = []
                for activity, future in pending.items():
                    try:
                        self.results[activity] = future.result()[0]
                    except DispatchDenied as exc:
                        errors.append(exc)
                if errors:
                    raise errors[0]
            self.audit.append(
                "join",
                "diagnostics",
                "Both root-cause and subscriber-impact evidence available",
            )
            self.handoff("diagnostics", "Task_Prioritize")
            if not self.results["Task_ConfirmRestoration"]["restored"]:
                status, reason = (
                    "escalated",
                    "Post-change service measurements remain outside closure thresholds",
                )
        except DispatchDenied as exc:
            status, reason = "awaiting-operator", str(exc)
            self.audit.append("escalate", "operator", reason)
        audit = self.audit.records
        return {
            "operator": "Almadar Aljadid",
            "hvs": "HVS1",
            "incident": self.incident.to_dict(),
            "scenario": self.scenario,
            "status": status,
            "reason": reason,
            "network_changed": self.twin.changed,
            "domain_actions": self.twin.actions,
            "results": self.results,
            "design": self.design,
            "registry": list(self.registry.cards.values()),
            "governance": {
                "scores": self.observer.scores,
                "events": self.observer.events,
                "mode": "advisory",
            },
            "messages": self.messages,
            "audit": audit,
            "audit_valid": verify_chain(audit),
        }


def run(incident=None, scenario="transport-fault"):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario")
    return AssuranceSession(incident or sample_incident(), scenario).start()
