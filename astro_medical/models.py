"""Device-independent, JSON-serializable telemetry contracts for multiple crewmembers."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

Severity = Literal["normal", "attention", "critical", "unknown"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Measurement:
    value: float | None
    unit: str
    quality: Literal["good", "invalid", "missing", "stale", "uncalibrated"] = "good"
    sensor_id: str | None = None
    captured_at: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Telemetry:
    """Individual projection for compatibility with the original single-crew rules."""
    timestamp: str
    source: str
    scenario: str
    vitals: dict[str, Measurement]
    cabin: dict[str, Measurement]
    symptoms: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"timestamp": self.timestamp, "source": self.source, "scenario": self.scenario,
                "vitals": {k: v.as_dict() for k, v in self.vitals.items()},
                "cabin": {k: v.as_dict() for k, v in self.cabin.items()},
                "symptoms": list(self.symptoms)}


@dataclass
class CrewSample:
    crew_id: str
    name: str
    zone_id: str
    vitals: dict[str, Measurement]
    symptoms: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"crew_id": self.crew_id, "name": self.name, "zone_id": self.zone_id,
                "vitals": {k: v.as_dict() for k, v in self.vitals.items()},
                "symptoms": list(self.symptoms)}


@dataclass
class MissionTelemetry:
    timestamp: str
    source: str
    scenario: str
    crew: dict[str, CrewSample]
    zones: dict[str, dict[str, Measurement]]
    systems: dict[str, Measurement] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"timestamp": self.timestamp, "source": self.source, "scenario": self.scenario,
                "crew": {key: val.as_dict() for key, val in self.crew.items()},
                "zones": {zone: {key: val.as_dict() for key, val in items.items()}
                          for zone, items in self.zones.items()},
                "systems": {key: val.as_dict() for key, val in self.systems.items()}}


@dataclass(frozen=True)
class Alert:
    code: str
    severity: Severity
    title: str
    description: str
    protocol_id: str
    origin: str
    scope: Literal["crew", "zone", "mission"] = "mission"
    subject_id: str = "mission"
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Finding:
    code: str
    level: Severity
    category: str
    title: str
    interpretation: str
    affected_crew: tuple[str, ...]
    affected_zones: tuple[str, ...]
    evidence: tuple[str, ...]
    uncertainties: tuple[str, ...]
    suggested_checks: tuple[str, ...]
    protocol_id: str

    def as_dict(self) -> dict:
        return asdict(self)
