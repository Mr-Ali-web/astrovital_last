"""SQLite-only local persistence and simulated outbox; NO real Earth transmission."""
from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .models import MissionTelemetry, utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_at TEXT NOT NULL,
 scenario TEXT NOT NULL,
 source TEXT NOT NULL,
 payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_at TEXT NOT NULL,
 event_type TEXT NOT NULL,
 severity TEXT NOT NULL,
 code TEXT NOT NULL,
 message TEXT NOT NULL,
 scope TEXT DEFAULT 'mission',
 subject_id TEXT DEFAULT 'mission',
 subject_name TEXT,
 affected_crew TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS outbox (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 event_id INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'queued',
 created_at TEXT NOT NULL,
 delivered_at TEXT,
 FOREIGN KEY(event_id) REFERENCES events(id)
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_telemetry_id ON telemetry(id);
CREATE INDEX IF NOT EXISTS idx_events_id ON events(id);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            # Safe additive migration for optional reuse of a v0.1 database.
            cols = {col[1] for col in conn.execute("PRAGMA table_info(events)")}
            for name in ("scope", "subject_id"):
                if name not in cols:
                    conn.execute(f"ALTER TABLE events ADD COLUMN {name} TEXT DEFAULT 'mission'")
            # Keep the name snapshot on the event, independent of the current roster.
            if "subject_name" not in cols:
                conn.execute("ALTER TABLE events ADD COLUMN subject_name TEXT")
            if "affected_crew" not in cols:
                conn.execute("ALTER TABLE events ADD COLUMN affected_crew TEXT NOT NULL DEFAULT '[]'")
            self._backfill_event_names(conn)

    @staticmethod
    def _backfill_event_names(conn: sqlite3.Connection) -> None:
        """Recover names from old snapshots ONLY for unambiguous legacy crew IDs.

        Older events did not capture an identity snapshot; if one ID was reused
        for different names, leave it unknown rather than show a wrong person.
        """
        missing = conn.execute("SELECT DISTINCT subject_id FROM events "
                               "WHERE scope='crew' AND subject_name IS NULL").fetchall()
        if not missing:
            return
        targets = {r[0] for r in missing}
        names = {cid: set() for cid in targets}
        for row in conn.execute("SELECT payload FROM telemetry ORDER BY id"):
            try:
                crew = json.loads(row[0]).get("crew", {})
                for cid in targets.intersection(crew):
                    name = crew[cid].get("name")
                    if name:
                        names[cid].add(str(name))
            except (ValueError, AttributeError, TypeError):
                continue
        for cid, choices in names.items():
            if len(choices) == 1:
                conn.execute("UPDATE events SET subject_name=? WHERE subject_id=? "
                             "AND scope='crew' AND subject_name IS NULL",
                             (next(iter(choices)), cid))

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save_telemetry(self, mission: MissionTelemetry) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO telemetry(created_at,scenario,source,payload) VALUES (?,?,?,?)",
                         (mission.timestamp, mission.scenario, mission.source,
                          json.dumps(mission.as_dict(), ensure_ascii=False)))

    def get_history(self, limit: int = 60) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM telemetry ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row["payload"]) for row in reversed(rows)]

    def get_crew_history(self, crew_id: str, limit: int = 60) -> list[dict]:
        # Filter AFTER limiting to stored snapshots; safe even if legacy v0.1 data exists.
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM telemetry ORDER BY id DESC LIMIT ?", (min(limit * 10, 2000),)).fetchall()
        result = []
        for row in rows:
            data = json.loads(row["payload"])
            person = data.get("crew", {}).get(crew_id)
            if person:
                result.append({"timestamp": data["timestamp"], "scenario": data["scenario"],
                               "crew_id": crew_id, "zone_id": person["zone_id"],
                               "vitals": person["vitals"], "symptoms": person["symptoms"]})
            if len(result) >= limit:
                break
        return list(reversed(result))

    def add_event(self, event_type: str, severity: str, code: str, message: str,
                  scope: str = "mission", subject_id: str = "mission",
                  subject_name: str | None = None,
                  affected_crew: list[dict[str, str]] | None = None) -> int:
        """Save event identity at occurrence time; keep it after roster changes."""
        crew_json = json.dumps(affected_crew or [], ensure_ascii=False)
        with self._connect() as conn:
            cursor = conn.execute("INSERT INTO events(created_at,event_type,severity,code,message,scope,"
                                  "subject_id,subject_name,affected_crew) VALUES (?,?,?,?,?,?,?,?,?)",
                                  (utc_now(), event_type, severity, code, message, scope,
                                   subject_id, subject_name, crew_json))
            event_id = int(cursor.lastrowid)
            conn.execute("INSERT INTO outbox(event_id,created_at) VALUES (?,?)", (event_id, utc_now()))
            return event_id

    def get_events(self, limit: int = 40, subject_id: str | None = None) -> list[dict]:
        with self._connect() as conn:
            if subject_id:
                rows = conn.execute("SELECT * FROM events WHERE subject_id=? ORDER BY id DESC LIMIT ?",
                                    (subject_id, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for row in rows:
            event = dict(row)
            try:
                event["affected_crew"] = json.loads(event["affected_crew"] or "[]")
            except (TypeError, ValueError):
                event["affected_crew"] = []
            result.append(event)
        return result

    def pending_count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT count(*) FROM outbox WHERE status='queued'").fetchone()[0])

    def simulate_delivery(self) -> int:
        """Mark local delivery simulation. NO network or real mission controller exists."""
        with self._connect() as conn:
            cursor = conn.execute("UPDATE outbox SET status='simulated_delivered', delivered_at=? "
                                  "WHERE status='queued'", (utc_now(),))
            return int(cursor.rowcount)

    def set_setting(self, key: str, value) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO settings(key,value) VALUES (?,?) "
                         "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         (key, json.dumps(value, ensure_ascii=False)))

    def get_setting(self, key: str, default=None):
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default
