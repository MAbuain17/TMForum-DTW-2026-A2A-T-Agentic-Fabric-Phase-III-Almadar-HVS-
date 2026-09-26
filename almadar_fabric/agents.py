"""Deterministic adapters for separate business, access and transport domains."""

from dataclasses import replace
from .models import AgentCard


class Registry:
    def __init__(self, cards):
        self.cards = tuple(cards)
        ids = [card.agent_id for card in self.cards]
        if len(set(ids)) != len(ids):
            raise ValueError("Agent IDs must be unique")

    def discover(self, skill, minimum_trust=0.8):
        eligible = [c for c in self.cards if skill in c.skills and c.onboarded and c.trust_score >= minimum_trust]
        if not eligible:
            raise LookupError(f"No authorised agent available for {skill}")
        return sorted(eligible, key=lambda c: (-c.trust_score, c.agent_id))[0]


def default_registry(scenario="ready"):
    cards = [
        AgentCard("identity", "Identity verifier", "Business", "Partner sandbox", ("identity.verify",), 0.96),
        AgentCard("access", "Access planner", "Access", "Access adapter A", ("access.qualify",), 0.94),
        AgentCard("transport", "Transport planner", "Transport", "Transport adapter B", ("transport.qualify",), 0.93),
        AgentCard("provision", "Service provisioner", "Service", "Almadar sandbox", ("service.provision", "service.rollback"), 0.97),
        AgentCard("assurance", "Service validator", "Assurance", "Assurance adapter C", ("service.validate",), 0.95),
    ]
    if scenario == "untrusted-agent":
        cards[3] = replace(cards[3], trust_score=0.42)
    return Registry(cards)


class SandboxAdapters:
    """Every method is simulated. No OSS calls or network commands are issued."""

    def __init__(self, scenario):
        self.scenario = scenario
        self.active = False

    def execute(self, skill, order):
        if skill == "identity.verify":
            return {"verified": self.scenario != "identity-rejected", "evidence": "synthetic/enterprise-register"}
        if skill == "access.qualify":
            return {"ready": self.scenario != "access-build", "capacity_mbps": 1000, "cost_lyd": 800,
                    "medium": "fibre", "evidence": "synthetic/access-inventory"}
        if skill == "transport.qualify":
            return {"capacity_mbps": 100 if self.scenario == "capacity-shortfall" else 1000,
                    "expected_latency_ms": 12, "cost_lyd": 500, "evidence": "synthetic/transport-inventory"}
        if skill == "service.provision":
            self.active = True
            return {"service_id": f"SVC-{order.order_id}", "configured": True,
                    "evidence": "synthetic/provisioning-receipt"}
        if skill == "service.validate":
            return {"throughput_mbps": order.bandwidth_mbps,
                    "latency_ms": 45 if self.scenario == "validation-failed" else 12,
                    "evidence": "synthetic/activation-test"}
        if skill == "service.rollback":
            self.active = False
            return {"rolled_back": True, "evidence": "synthetic/rollback-receipt"}
        raise ValueError(f"Unsupported skill: {skill}")
