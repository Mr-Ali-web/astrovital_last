"""Synthetic multi-person mission source and future hardware boundary.

NO synthetic measurement may be silently presented as a real hardware reading.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from random import Random
from .models import CrewSample, Measurement, MissionTelemetry, Telemetry, utc_now

DEFAULT_ROSTER = [
    {"crew_id": "C01", "name": "Kosmonavt 01", "zone_id": "HAB"},
    {"crew_id": "C02", "name": "Kosmonavt 02", "zone_id": "HAB"},
    {"crew_id": "C03", "name": "Kosmonavt 03", "zone_id": "LAB"},
    {"crew_id": "C04", "name": "Kosmonavt 04", "zone_id": "LAB"},
]
ZONES = {"HAB": "Yashash moduli", "LAB": "Laboratoriya moduli"}
SCENARIOS = {
    "normal": "Barqaror ekipaj",
    "single_low_spo2": "Faqat bir kosmonavtda SpO₂ pasayishi",
    "shared_co2": "Ikki modulda CO₂ va ekipaj ko‘rsatkichlari o‘zgarishi",
    "zone_ventilation_fault": "HAB modulida ventilyatsiya nosozligi",
    "shared_low_o2": "Ikki modulda O₂ pasayishi",
    "crew_cluster_only": "Bir nechta kosmonavtda o‘zgarish; muhit normal",
    "radiation_event": "Radiatsiya ko‘tarilishi (kosmik muhit demo)",
    "sensor_fault": "Bir kosmonavtda sensor uzilishi",
    "multi_sensor_fault": "Bir nechta sensorlar uzilishi",
    "combined": "Bir vaqtning o‘zida turli xavflar",
    # Older names accepted so v0.1 workflows remain convenient.
    "low_spo2": "Bir kosmonavtda SpO₂ pasayishi (eski nom)",
    "high_pulse": "Bir kosmonavtda puls tezlashishi",
    "high_co2": "Umumiy CO₂ oshishi (eski nom)",
    "low_cabin_o2": "Umumiy O₂ pasayishi (eski nom)",
}


class MissionTelemetrySource(ABC):
    @abstractmethod
    def read(self) -> MissionTelemetry:
        """One synchronous mission snapshot with explicit crew/zone assignments."""


# Earlier hardware adapter name kept for existing integrations.
TelemetrySource = MissionTelemetrySource


class DemoSimulator(MissionTelemetrySource):
    """Deterministic synthetic signals. Scenario implies no validated cause."""

    def __init__(self, seed: int = 42, roster: list[dict] | None = None):
        self.random = Random(seed)
        self.roster = [dict(x) for x in (roster if roster is not None else DEFAULT_ROSTER)]
        self.scenario = "normal"
        self.sample_index = 0
        self.symptoms: dict[str, list[str]] = {}

    def set_scenario(self, scenario: str) -> None:
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")
        self.scenario = scenario
        self.sample_index = 0

    def read(self) -> MissionTelemetry:
        self.sample_index += 1
        r = self.random
        time = utc_now()
        progress = min(self.sample_index, 8) / 8
        cohort = self.roster
        first_id = cohort[0]["crew_id"] if cohort else None
        by_zone = {z: [p["crew_id"] for p in cohort if p["zone_id"] == z] for z in ZONES}

        zones = {}
        for zone_id in ZONES:
            base = {
                "o2_partial": (21.1 + r.uniform(-.10, .10), "kPa"),
                "co2_partial": (.09 + r.uniform(-.015, .015), "kPa"),
                "pressure": (101.3 + r.uniform(-.15, .15), "kPa"),
                "temperature": (22.4 + r.uniform(-.25, .25), "°C"),
                "humidity": (48 + r.uniform(-1.5, 1.5), "%"),
                "radiation": (.4 + r.uniform(-.06, .06), "µSv/h"),
            }
            values = {key: Measurement(round(v, 3), unit, sensor_id=f"SIM-{zone_id}-{key}", captured_at=time)
                      for key, (v, unit) in base.items()}
            if self.scenario in ("shared_co2", "high_co2", "combined") or (self.scenario == "zone_ventilation_fault" and zone_id == "HAB"):
                values["co2_partial"].value = round(.15 + .72 * progress, 3)
            if self.scenario in ("shared_low_o2", "low_cabin_o2"):
                values["o2_partial"].value = round(20.7 - 4.3 * progress, 3)
            if self.scenario == "radiation_event":
                values["radiation"].value = round(.5 + 10 * progress, 3)
            zones[zone_id] = values

        systems = {
            "scrubber_ok": Measurement(0 if self.scenario in ("shared_co2", "high_co2", "combined") else 1,
                                       "boolean", sensor_id="SIM-SCRUBBER", captured_at=time),
            "hab_fan_ok": Measurement(0 if self.scenario == "zone_ventilation_fault" else 1,
                                      "boolean", sensor_id="SIM-HAB-FAN", captured_at=time),
        }
        crew = {}
        for pos, person in enumerate(cohort):
            crew_id, zone_id = person["crew_id"], person["zone_id"]
            vital = {
                "heart_rate": Measurement(round(75 + r.uniform(-4, 4) + pos*1.5, 1), "bpm"),
                "spo2": Measurement(round(98 + r.uniform(-.5, .5), 1), "%"),
                "systolic_bp": Measurement(round(117 + r.uniform(-4, 4), 1), "mmHg"),
                "diastolic_bp": Measurement(round(76 + r.uniform(-3, 3), 1), "mmHg"),
                "body_temp": Measurement(round(36.7 + r.uniform(-.12, .12), 2), "°C"),
                "resp_rate": Measurement(round(15 + r.uniform(-1, 1), 1), "/min"),
            }
            if self.scenario in ("single_low_spo2", "low_spo2", "combined") and crew_id == first_id:
                vital["spo2"].value = round(98 - 11 * progress, 1)
            if self.scenario in ("high_pulse", "combined") and crew_id == first_id:
                vital["heart_rate"].value = round(95 + 50 * progress, 1)
            affected = (
                self.scenario in ("shared_co2", "high_co2", "shared_low_o2", "low_cabin_o2", "crew_cluster_only")
                or (self.scenario == "zone_ventilation_fault" and zone_id == "HAB")
            )
            if affected:
                vital["spo2"].value = round(98 - 11 * progress, 1)
                vital["resp_rate"].value = round(15 + 15 * progress, 1)
            if self.scenario in ("sensor_fault", "multi_sensor_fault") and (crew_id == first_id or self.scenario == "multi_sensor_fault"):
                vital["spo2"].value = None
                vital["spo2"].quality = "missing"
            for key, point in vital.items():
                point.sensor_id = f"SIM-{crew_id}-{key}"
                point.captured_at = time
            crew[crew_id] = CrewSample(crew_id, person["name"], zone_id, vital, list(self.symptoms.get(crew_id, [])))
        return MissionTelemetry(time, "synthetic-simulator", self.scenario, crew, zones, systems)


class HardwareSource(MissionTelemetrySource):
    """Future: implement read() with real authenticated sensor IDs, freshness and quality."""
    def __init__(self, device_config: dict | None = None):
        self.device_config = device_config or {}

    def read(self) -> MissionTelemetry:
        raise NotImplementedError("Real hardware adapters are not installed. Do not replace missing measurements with simulated values.")
