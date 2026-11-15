"""NASA reference data: fetched when the Internet is available, cached in SQLite,
and served from the cache when the crew is offline.

Sources (all public NASA services):
  * NASA OSDR Search API  - https://osdr.nasa.gov/osdr/data/search  (no key)
  * NASA DONKI space weather - https://api.nasa.gov/DONKI/...        (api.nasa.gov key,
    DEMO_KEY works with strict limits; set NASA_API_KEY for your own key)
  * OSDR RadLab and Environmental Data Application (EDA) are linked as portals.

IMPORTANT SAFETY BOUNDARY: this data is REFERENCE ONLY. It never feeds the
medical rule engine, never changes risk levels and never produces advice. A
failed download never raises into the monitoring loop.
"""
from __future__ import annotations
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Callable

OSDR_SEARCH = "https://osdr.nasa.gov/osdr/data/search"
DONKI_BASE = "https://api.nasa.gov/DONKI"
PORTALS = [
    {"id": "radlab", "name": "OSDR RadLab", "url": "https://visualization.osdr.nasa.gov/",
     "note": "Kosmik agentliklarning radiatsiya dozimetriyasi ma’lumotlari"},
    {"id": "eda", "name": "OSDR Environmental Data Application (EDA)", "url": "https://visualization.osdr.nasa.gov/",
     "note": "ISS kabinasi va uskunalari telemetriyasi, missiyama-missiya taqqoslash"},
    {"id": "osdr", "name": "NASA Open Science Data Repository", "url": "https://osdr.nasa.gov/bio/repo/",
     "note": "Kosmik biologiya va GeneLab tadqiqotlari"},
]
SCHEMA = """
CREATE TABLE IF NOT EXISTS nasa_cache (
 key TEXT PRIMARY KEY,
 fetched_at TEXT,
 ok INTEGER NOT NULL DEFAULT 0,
 error TEXT,
 payload TEXT NOT NULL DEFAULT '{}'
);
"""
Fetcher = Callable[[str], object]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def http_get_json(url: str, timeout: float = 15.0):
    request = urllib.request.Request(url, headers={"User-Agent": "AstroMed-demo/0.4", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (fixed NASA hosts)
        return json.loads(response.read().decode("utf-8"))


def _pick(mapping: dict, *names):
    lowered = {str(k).lower(): v for k, v in mapping.items()}
    for name in names:
        if name.lower() in lowered and lowered[name.lower()] not in (None, ""):
            return lowered[name.lower()]
    return None


def parse_osdr(raw) -> dict:
    """Defensive parse of the OSDR search response (Elasticsearch-style hits)."""
    hits = raw.get("hits", {}) if isinstance(raw, dict) else {}
    total = hits.get("total") if isinstance(hits, dict) else None
    if isinstance(total, dict):
        total = total.get("value")
    rows = hits.get("hits", []) if isinstance(hits, dict) else []
    items = []
    for row in rows[:10]:
        source = row.get("_source") or row.get("source") or row
        if not isinstance(source, dict):
            continue
        accession = _pick(source, "Accession", "accession", "Study Identifier")
        title = _pick(source, "Study Title", "study_title", "title")
        if accession or title:
            items.append({
                "accession": str(accession or ""), "title": str(title or ""),
                "link": f"https://osdr.nasa.gov/bio/repo/data/studies/{accession}" if accession else None,
            })
    return {"total": total if isinstance(total, int) else len(items), "items": items}


def parse_donki(raw, id_keys: tuple[str, ...], time_keys: tuple[str, ...]) -> dict:
    events = raw if isinstance(raw, list) else []
    items = []
    for event in events[-10:]:
        if not isinstance(event, dict):
            continue
        items.append({
            "id": str(_pick(event, *id_keys) or ""),
            "time": str(_pick(event, *time_keys) or ""),
            "link": _pick(event, "link"),
        })
    items.reverse()
    return {"total": len(events), "items": items}


class NasaReference:
    """Offline-first NASA reference cache. All network use is explicit (refresh())."""

    def __init__(self, db_path: str, fetcher: Fetcher | None = None, api_key: str | None = None):
        self.db_path = str(db_path)
        self.fetcher = fetcher or http_get_json
        self.api_key = api_key or os.getenv("NASA_API_KEY", "DEMO_KEY")
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def sources(self) -> dict[str, dict]:
        end = _now().date()
        start = end - timedelta(days=30)
        window = f"startDate={start}&endDate={end}&api_key={urllib.parse.quote(self.api_key)}"

        def osdr(term: str) -> str:
            return f"{OSDR_SEARCH}?{urllib.parse.urlencode({'term': term, 'from': 0, 'size': 10, 'type': 'cgene'})}"

        return {
            "osdr_radiation": {"title": "Kosmik radiatsiya tadqiqotlari (OSDR)", "group": "radiation",
                               "url": osdr("radiation"), "parse": parse_osdr},
            "osdr_microgravity": {"title": "Mikrogravitatsiya ta’siri tadqiqotlari (OSDR)", "group": "biology",
                                  "url": osdr("microgravity"), "parse": parse_osdr},
            "osdr_cabin": {"title": "Kabina muhiti va CO₂ tadqiqotlari (OSDR)", "group": "environment",
                           "url": osdr("cabin carbon dioxide"), "parse": parse_osdr},
            "donki_sep": {"title": "Quyosh zarralari hodisalari, so‘nggi 30 kun (DONKI SEP)", "group": "space_weather",
                          "url": f"{DONKI_BASE}/SEP?{window}",
                          "parse": lambda raw: parse_donki(raw, ("sepID", "id"), ("eventTime", "time"))},
            "donki_flr": {"title": "Quyosh alangalari, so‘nggi 30 kun (DONKI FLR)", "group": "space_weather",
                          "url": f"{DONKI_BASE}/FLR?{window}",
                          "parse": lambda raw: parse_donki(raw, ("flrID", "id"), ("beginTime", "time"))},
        }

    def refresh(self) -> dict:
        """Try to download every source. Never raises; records per-source errors."""
        result = {}
        for key, spec in self.sources().items():
            stamp = _now().isoformat(timespec="seconds")
            try:
                payload = spec["parse"](self.fetcher(spec["url"]))
                self._store(key, stamp, True, None, payload)
                result[key] = "ok"
            except Exception as exc:  # network down is a normal offline condition
                self._store_error(key, stamp, f"{type(exc).__name__}: {exc}"[:200])
                result[key] = "error"
        return result

    def _store(self, key, stamp, ok, error, payload):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO nasa_cache(key,fetched_at,ok,error,payload) VALUES(?,?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET fetched_at=excluded.fetched_at, ok=excluded.ok, "
                "error=excluded.error, payload=excluded.payload", (key, stamp, int(ok), error, json.dumps(payload)))

    def _store_error(self, key, stamp, error):
        # Keep the last good payload; only record that the newest attempt failed.
        with self._connect() as conn:
            row = conn.execute("SELECT payload, ok FROM nasa_cache WHERE key=?", (key,)).fetchone()
            if row:
                conn.execute("UPDATE nasa_cache SET error=?, fetched_at=fetched_at WHERE key=?", (error, key))
            else:
                conn.execute("INSERT INTO nasa_cache(key,fetched_at,ok,error,payload) VALUES(?,?,?,?,?)",
                             (key, None, 0, error, "{}"))

    def status(self) -> dict:
        with self._connect() as conn:
            rows = {r["key"]: r for r in conn.execute("SELECT * FROM nasa_cache")}
        sources = []
        for key, spec in self.sources().items():
            row = rows.get(key)
            payload = json.loads(row["payload"]) if row else {}
            sources.append({
                "id": key, "title": spec["title"], "group": spec["group"],
                "cached": bool(row and row["fetched_at"]), "fetched_at": row["fetched_at"] if row else None,
                "last_error": row["error"] if row else None,
                "total": payload.get("total"), "items": payload.get("items", []),
            })
        return {"mode": "OFFLINE_CACHE", "reference_only": True, "api_key_type": "custom" if self.api_key != "DEMO_KEY" else "DEMO_KEY",
                "sources": sources, "portals": PORTALS, "advisory": self._advisory(sources)}

    @staticmethod
    def _advisory(sources: list[dict]) -> dict:
        """Informational only. Does NOT change risk levels or medical rules."""
        cutoff = _now() - timedelta(hours=72)
        recent = []
        for src in sources:
            if src["id"] not in ("donki_sep", "donki_flr"):
                continue
            for item in src["items"]:
                try:
                    when = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if when >= cutoff:
                    recent.append({"source": src["id"], "id": item["id"], "time": item["time"]})
        have_data = any(s["cached"] and s["group"] == "space_weather" for s in sources)
        if not have_data:
            return {"state": "unknown", "message": "Kosmik ob-havo ma’lumoti hali yuklanmagan (Internet kerak).", "events": []}
        if recent:
            return {"state": "recent_events",
                    "message": "So‘nggi 72 soatda NASA DONKI quyosh hodisalarini qayd etgan. Bu faqat ma’lumot; xavf darajasi o‘zgarmaydi.",
                    "events": recent}
        return {"state": "none_recent", "message": "Keshdagi ma’lumotga ko‘ra so‘nggi 72 soatda DONKI hodisasi yo‘q.", "events": []}
