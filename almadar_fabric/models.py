"""Operator-scoped incident inputs; all sample values are synthetic."""

from dataclasses import dataclass, asdict
import math


@dataclass(frozen=True)
class Incident:
    incident_id: str = "ALM-FLT-001"
    service: str = "Mobile broadband"
    area: str = "Tripoli demo cluster"
    cell_ids: tuple = ("ALM-CELL-01", "ALM-CELL-02", "ALM-CELL-03")
    transport_id: str = "ALM-BH-01"
    affected_subscribers: int = 840
    throughput_mbps: float = 2.4
    packet_loss_pct: float = 8.2
    min_throughput_mbps: float = 15.0
    max_packet_loss_pct: float = 1.0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ValueError("Unknown incident field")
        values = cls().to_dict() | data
        for key in ("incident_id", "service", "area", "transport_id"):
            if (
                not isinstance(values[key], str)
                or not 1 <= len(values[key].strip()) <= 120
            ):
                raise ValueError(f"Invalid {key}")
        cells = values["cell_ids"]
        if (
            not isinstance(cells, (list, tuple))
            or not 1 <= len(cells) <= 20
            or any(not isinstance(x, str) or not 1 <= len(x) <= 80 for x in cells)
            or len(set(cells)) != len(cells)
        ):
            raise ValueError("Expected 1–20 unique cell IDs")
        values["cell_ids"] = tuple(cells)
        n = values["affected_subscribers"]
        if type(n) is not int or not 0 <= n <= 1000000:
            raise ValueError("Invalid affected subscriber count")
        for key in (
            "throughput_mbps",
            "packet_loss_pct",
            "min_throughput_mbps",
            "max_packet_loss_pct",
        ):
            v = values[key]
            maximum = 100 if "pct" in key else 10000
            if (
                type(v) not in (int, float)
                or not math.isfinite(v)
                or not 0 <= v <= maximum
            ):
                raise ValueError(f"Invalid {key}")
        return cls(**values)


class DispatchDenied(ValueError):
    pass
