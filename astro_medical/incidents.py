"""Local incident tracker for demo clinical checklists. No clinical treatment logic."""
from __future__ import annotations
import json
import uuid
from threading import RLock
from .clinical import get_protocol, missing_resources
from .models import utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('open','reviewed')),
  protocol_id TEXT NOT NULL,
  protocol_version TEXT NOT NULL,
  scope TEXT NOT NULL,
  crew_snapshot TEXT NOT NULL,
  zone_ids TEXT NOT NULL,
  origin_code TEXT NOT NULL,
  note TEXT NOT NULL,
  evidence_snapshot TEXT NOT NULL,
  steps_snapshot TEXT NOT NULL,
  missing_resources TEXT NOT NULL,
  approval_snapshot TEXT NOT NULL DEFAULT 'DEMO'
);
CREATE TABLE IF NOT EXISTS incident_steps (
  incident_id TEXT NOT NULL,
  step_index INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','acknowledged','completed','blocked')),
  updated_at TEXT,
  actor_id TEXT,
  actor_name TEXT,
  note TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (incident_id, step_index),
  FOREIGN KEY(incident_id) REFERENCES incidents(id)
);
CREATE TABLE IF NOT EXISTS incident_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  action TEXT NOT NULL,
  actor_id TEXT,
  actor_name TEXT,
  details TEXT NOT NULL,
  FOREIGN KEY(incident_id) REFERENCES incidents(id)
);
CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at);
CREATE INDEX IF NOT EXISTS idx_incident_audit ON incident_audit(incident_id,id);
"""


class IncidentError(ValueError):
    """Invalid workflow request; converted to API 422."""


class IncidentConflict(ValueError):
    """State changed or task is closed; converted to API 409."""


class IncidentStore:
    def __init__(self, db):
        self.db = db
        self._lock = RLock()
        with self.db._connect() as conn:
            conn.executescript(SCHEMA)

    @staticmethod
    def _decode(row):
        result = dict(row)
        for key in ("crew_snapshot", "zone_ids", "evidence_snapshot", "steps_snapshot", "missing_resources"):
            result[key] = json.loads(result[key])
        return result

    def _get(self, conn, incident_id):
        row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if row is None:
            raise KeyError(incident_id)
        result = self._decode(row)
        result["steps"] = [dict(r) for r in conn.execute(
            "SELECT * FROM incident_steps WHERE incident_id=? ORDER BY step_index", (incident_id,))]
        return result

    def list(self, limit=50):
        with self.db._connect() as conn:
            return [self._decode(row) for row in conn.execute(
                "SELECT * FROM incidents ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,))]

    def get(self, incident_id):
        with self.db._connect() as conn:
            result = self._get(conn, incident_id)
            result["audit"] = [dict(row) for row in conn.execute(
                "SELECT * FROM incident_audit WHERE incident_id=? ORDER BY id", (incident_id,))]
            return result

    def create(self, protocol_id, crew, zone_ids, origin_code, note, evidence, actor):
        protocol = get_protocol(protocol_id)
        if not protocol:
            raise IncidentError("Noma'lum protokol")
        if not crew and not zone_ids:
            raise IncidentError("Ekipaj a'zosi yoki modul tanlanishi kerak")
        if protocol["scope"] == "individual" and len(crew) != 1:
            raise IncidentError("Individual protokol uchun aynan bir kosmonavt tanlang")
        if protocol["scope"] == "crew" and len(crew) < 2:
            raise IncidentError("Ekipaj protokoli uchun kamida ikki kosmonavt tanlang")
        if protocol["scope"] == "zone" and not zone_ids:
            raise IncidentError("Modul protokoli uchun zona tanlang")
        if len(note) > 1000 or len(origin_code) > 100:
            raise IncidentError("Matn haddan tashqari uzun")
        incident_id = "INC-" + uuid.uuid4().hex[:12].upper()
        now = utc_now()
        missing = missing_resources(protocol_id)
        with self._lock, self.db._connect() as conn:
            conn.execute("""INSERT INTO incidents
              (id,created_at,updated_at,status,protocol_id,protocol_version,scope,
               crew_snapshot,zone_ids,origin_code,note,evidence_snapshot,steps_snapshot,missing_resources,approval_snapshot)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (incident_id, now, now, "open", protocol_id, protocol["version"], protocol["scope"],
                json.dumps(crew, ensure_ascii=False), json.dumps(zone_ids), origin_code, note,
                json.dumps(evidence, ensure_ascii=False), json.dumps(protocol["steps"], ensure_ascii=False),
                json.dumps(missing), protocol["approval_status"]))
            for step in protocol["steps"]:
                conn.execute("INSERT INTO incident_steps (incident_id,step_index,status) VALUES (?,?,?)",
                             (incident_id, step["index"], "pending"))
            self._audit(conn, incident_id, "CASE_CREATED", actor, {"protocol_id": protocol_id, "crew": crew,
                      "zones": zone_ids, "missing_resources": missing})
        return self.get(incident_id)

    @staticmethod
    def _audit(conn, incident_id, action, actor, details):
        conn.execute("INSERT INTO incident_audit (incident_id,created_at,action,actor_id,actor_name,details) "
                     "VALUES (?,?,?,?,?,?)", (incident_id, utc_now(), action, actor["crew_id"],
                                              actor["name"], json.dumps(details, ensure_ascii=False)))

    def update_step(self, incident_id, index, status, actor, note):
        if status not in ("pending", "acknowledged", "completed", "blocked"):
            raise IncidentError("Noto‘g‘ri qadam holati")
        if len(note) > 500:
            raise IncidentError("Izoh haddan tashqari uzun")
        with self._lock, self.db._connect() as conn:
            incident = self._get(conn, incident_id)
            if incident["status"] != "open":
                raise IncidentConflict("Yakunlangan holatni o‘zgartirib bo‘lmaydi")
            found = next((s for s in incident["steps"] if s["step_index"] == index), None)
            if found is None:
                raise KeyError("Unknown incident step")
            # The prototype records review status, never asserts real-world clinical success.
            if status == "completed" and incident["missing_resources"]:
                raise IncidentConflict("DEMO inventarda kerakli resurs yetishmaydi: 'completed' o‘rniga 'blocked' qo‘llang")
            if status == "completed" and found["status"] not in ("acknowledged", "completed"):
                raise IncidentConflict("Avval ko‘rib chiqilganini belgilang")
            now = utc_now()
            conn.execute("UPDATE incident_steps SET status=?,updated_at=?,actor_id=?,actor_name=?,note=? "
                         "WHERE incident_id=? AND step_index=?",
                         (status, now, actor["crew_id"], actor["name"], note, incident_id, index))
            conn.execute("UPDATE incidents SET updated_at=? WHERE id=?", (now, incident_id))
            self._audit(conn, incident_id, "STEP_" + status.upper(), actor,
                        {"step_index": index, "old_status": found["status"], "note": note})
        return self.get(incident_id)

    def mark_reviewed(self, incident_id, actor, note):
        if len(note) > 500:
            raise IncidentError("Izoh haddan tashqari uzun")
        with self._lock, self.db._connect() as conn:
            incident = self._get(conn, incident_id)
            if incident["status"] != "open":
                raise IncidentConflict("Bu holat allaqachon yakunlangan")
            if any(s["status"] not in ("completed", "blocked") for s in incident["steps"]):
                raise IncidentConflict("Barcha qadamlar completed yoki blocked bo‘lsin")
            conn.execute("UPDATE incidents SET status='reviewed',updated_at=? WHERE id=?", (utc_now(), incident_id))
            self._audit(conn, incident_id, "CASE_REVIEWED", actor, {"note": note})
        return self.get(incident_id)
