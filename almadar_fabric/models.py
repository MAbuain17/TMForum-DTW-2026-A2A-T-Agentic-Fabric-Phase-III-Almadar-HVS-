"""Local task contracts; these are illustrative, not normative A2A-T schemas."""

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class Order:
    order_id: str
    customer: str
    site: str
    bandwidth_mbps: int
    max_latency_ms: float
    budget_lyd: int

    @classmethod
    def from_dict(cls, data):
        expected = set(cls.__dataclass_fields__)
        if not isinstance(data, dict) or set(data) != expected:
            raise ValueError("Order must contain exactly the six documented fields")
        for key in ("order_id", "customer", "site"):
            if not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 120:
                raise ValueError(f"{key} must be a non-empty string of at most 120 characters")
        for key in ("bandwidth_mbps", "budget_lyd"):
            if type(data[key]) is not int or not 1 <= data[key] <= 1_000_000:
                raise ValueError(f"{key} must be a positive integer up to 1,000,000")
        latency = data["max_latency_ms"]
        if type(latency) not in (int, float) or not math.isfinite(latency) or not 0 < latency <= 10000:
            raise ValueError("max_latency_ms must be finite and between 0 and 10,000")
        return cls(**data)


@dataclass(frozen=True)
class AgentCard:
    agent_id: str
    name: str
    domain: str
    provider: str
    skills: tuple[str, ...]
    trust_score: float
    onboarded: bool = True

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Task:
    context_id: str
    task_id: str
    skill: str
    target: str
    intent: str
    constraints: dict

    def to_dict(self):
        return {**asdict(self), "profile": "almadar-demo/task-t/0.1", "hvs": "HVS3"}
