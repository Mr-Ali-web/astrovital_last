"""Stage 3 offline SIMULATION-ONLY investigation workflows.

No diagnosis, treatment recommendation, or autonomous actuation. All catalogs are
unvalidated DEMO data and must not be promoted to clinical instructions.
"""
from __future__ import annotations
from copy import deepcopy
from .playbooks import PLAYBOOKS, NOTICE

VERSION = "0.3-demo.1"
# Deliberately no medication, dose, invasive procedures or instructions to operate
# life-support equipment. Resource state is only a fake inventory for UI testing.
RESOURCES = [
    {"id": "tablet", "name": "Bort plansheti / offline terminal", "category": "communication", "available": True},
    {"id": "backup_sensor", "name": "Zaxira tibbiy sensor (DEMO)", "category": "diagnostic", "available": True},
    {"id": "environment_panel", "name": "Kabina monitoring paneli (DEMO)", "category": "environment", "available": True},
    {"id": "medical_kit", "name": "Tibbiy to‘plam (DEMO)", "category": "equipment", "available": True},
    {"id": "dosimeter", "name": "Dozimetr (DEMO)", "category": "environment", "available": False},
    {"id": "crew_comms", "name": "Ekipaj ichki aloqasi (DEMO)", "category": "communication", "available": True},
]

PROTOCOL_META = {
    "sensor-check": ("individual", ["backup_sensor"], ["signal_quality"], "O‘lchov sifatini tekshirish"),
    "vitals-check": ("individual", ["backup_sensor", "tablet"], ["vital_change"], "Individual alomatlarni qayd etish"),
    "breathing": ("individual", ["backup_sensor", "environment_panel"], ["breathing_change"], "Nafas olish signallarini tekshirish"),
    "trauma": ("individual", ["medical_kit", "crew_comms"], ["injury_report"], "Jarohat xabarini hujjatlashtirish"),
    "urgent-medical": ("individual", ["medical_kit", "crew_comms"], ["urgent_symptoms"], "Shoshilinch holat xabarini qayd etish"),
    "crew-investigation": ("crew", ["environment_panel", "backup_sensor"], ["crew_cluster"], "Ekipajlararo bog‘liqlikni o‘rganish"),
    "cabin-atmosphere": ("zone", ["environment_panel", "crew_comms"], ["cabin_anomaly"], "Kabina atmosferasi signali"),
    "engineering-check": ("zone", ["environment_panel"], ["equipment_signal"], "Muhandislik signali"),
    "space-environment": ("mission", ["dosimeter", "environment_panel"], ["radiation_signal"], "Kosmik muhit signali"),
}


def get_protocol(protocol_id: str) -> dict | None:
    source = PLAYBOOKS.get(protocol_id)
    meta = PROTOCOL_META.get(protocol_id)
    if source is None or meta is None:
        return None
    scope, resources, tags, description = meta
    return {
        "id": protocol_id,
        "version": VERSION,
        "title": source["title"],
        "description": description,
        "scope": scope,
        "approval_status": "DEMO",
        "approver": None,
        "approved_at": None,
        "applicable_tags": tags,
        "required_resources": resources,
        "steps": [{"index": i, "title": step} for i, step in enumerate(source["steps"])],
        "notice": NOTICE,
        "allow_clinical_use": False,
    }


def all_protocols() -> list[dict]:
    return [get_protocol(pid) for pid in PROTOCOL_META]


def resources() -> list[dict]:
    return deepcopy(RESOURCES)


def missing_resources(protocol_id: str) -> list[str]:
    p = get_protocol(protocol_id)
    if not p:
        raise KeyError(protocol_id)
    available = {r["id"] for r in RESOURCES if r["available"]}
    return [resource for resource in p["required_resources"] if resource not in available]
