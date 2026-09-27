"""Capability discovery and synthetic RAN, transport, core and assurance adapters."""

from copy import deepcopy
from .models import DispatchDenied

ALIASES = {
    "root-cause-analysis": "fault.diagnose",
    "customer-impact": "subscriber.impact",
}
ROLES = [
    ("anomaly", "CX anomaly agent", "Assurance", "RADCOM", "event.detect"),
    (
        "diagnostics",
        "Topology and RCA agent",
        "Digital Twin",
        "Amdocs",
        "fault.diagnose",
    ),
    (
        "impact",
        "Subscriber impact agent",
        "Digital Twin",
        "RADCOM / Amdocs",
        "subscriber.impact",
    ),
    (
        "prioritise",
        "Prioritisation agent",
        "Digital Twin",
        "Amdocs",
        "fault.prioritize",
    ),
    (
        "recommend",
        "Problem resolution agent",
        "Complaint Management",
        "Amdocs",
        "fault.recommend",
    ),
    (
        "coordinate",
        "Domain coordination agent",
        "Network Operations",
        "Amdocs / domain agents",
        "fault.coordinate",
    ),
    ("ran", "RAN assurance agent", "RAN", "Huawei", "ran.check"),
    (
        "transport",
        "IP / transport remediation agent",
        "Transport",
        "Infosys",
        "transport.remediate",
    ),
    ("core", "Core assurance agent", "Core", "Local operator adapter", "core.check"),
    (
        "verify",
        "Service restoration agent",
        "Network Operations",
        "CX and domain verification",
        "service.verify",
    ),
]


class Registry:
    def __init__(self):
        self.cards = {
            row[0]: {
                "agent_id": row[0],
                "name": row[1],
                "domain": row[2],
                "reference_role": row[3],
                "skills": [row[4]],
                "onboarded": True,
                "implementation": "local simulated adapter",
            }
            for row in ROLES
        }

    def discover(self, skill):
        skill = ALIASES.get(skill, skill)
        for card in self.cards.values():
            if card["onboarded"] and skill in card["skills"]:
                return deepcopy(card)
        raise DispatchDenied(f"No onboarded agent for {skill}")


def explain(summary, evidence):
    return {
        "summary": summary,
        "evidence_refs": evidence,
        "confidence": "fixture-derived; not calibrated",
    }


class MobileTwin:
    def __init__(self, incident, scenario):
        self.incident, self.scenario, self.changed = incident, scenario, False
        self.actions = []

    def execute(self, skill, evidence):
        i = self.incident
        if skill == "fault.diagnose":
            if self.scenario == "missing-topology":
                raise DispatchDenied(
                    "Topology evidence missing: cannot isolate the shared fault"
                )
            return {
                "root_cause": "Optical interface degradation on shared backhaul",
                "domain": "Transport",
                "target": i.transport_id,
                "alarms": ["RX_POWER_LOW", "INTERFACE_ERRORS"],
                "explain": explain(
                    "Three cells share the degraded transport path; no primary core fault.",
                    ["topology", "optical-alarms"],
                ),
            }
        if skill == "subscriber.impact":
            return {
                "affected_subscribers": i.affected_subscribers,
                "cells": list(i.cell_ids),
                "service": i.service,
                "explain": explain(
                    "Aggregate subscriber impact joins affected cells to the shared backhaul.",
                    ["cell-kpis", "aggregate-session-count"],
                ),
            }
        if skill == "fault.prioritize":
            return {
                "priority": "HIGH",
                "owner_domain": evidence["Task_RCA"]["domain"],
                "explain": explain(
                    "Prioritisation combines root cause and subscriber impact.",
                    ["Task_RCA", "Task_CEAndImpact"],
                ),
            }
        if skill == "fault.recommend":
            return {
                "action": "reroute_backhaul",
                "target": i.transport_id,
                "requires": "feasibility and incident-scoped authority",
                "explain": explain(
                    "Use a healthy backup path while an optical inspection is scheduled.",
                    ["Task_RCA", "Task_Prioritize"],
                ),
            }
        if skill == "fault.coordinate":
            return {
                "domains": ["RAN", "Transport", "Core"],
                "action": "reroute_backhaul",
            }
        if skill in ("ran.check", "core.check", "transport.remediate"):
            domain = {
                "ran.check": "RAN",
                "core.check": "Core",
                "transport.remediate": "Transport",
            }[skill]
            if skill == "transport.remediate":
                self.changed = True
            action = {
                "domain": domain,
                "changed": skill == "transport.remediate",
                "action": (
                    "reroute backhaul"
                    if domain == "Transport"
                    else "validate; no configuration change"
                ),
            }
            self.actions.append(action)
            return action
        if skill == "service.verify":
            throughput = (
                24.6
                if self.changed and self.scenario != "persistent-degradation"
                else i.throughput_mbps
            )
            loss = (
                0.3
                if self.changed and self.scenario != "persistent-degradation"
                else i.packet_loss_pct
            )
            restored = (
                throughput >= i.min_throughput_mbps and loss <= i.max_packet_loss_pct
            )
            return {
                "restored": restored,
                "throughput_mbps": throughput,
                "packet_loss_pct": loss,
                "explain": explain(
                    "Closure requires both throughput and packet-loss thresholds.",
                    ["post-change-kpis", "domain-results"],
                ),
            }
        raise DispatchDenied(f"Unsupported skill {skill}")
