"""Local FastAPI backend. No external networking or real sensor transports.

The optional offline AI assistant (ai_engine) runs only on this computer and is
DEMO-only: it is not medically validated."""
from __future__ import annotations
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .database import Database
from .service import MonitoringService
from .playbooks import get_playbook
from .clinical import all_protocols, get_protocol, resources
from .incidents import IncidentError, IncidentConflict
from .sources import SCENARIOS, ZONES
from .rules import SYMPTOM_LABELS
from .ai_engine import AIEngine, JobManager, MAX_RECORDS
from .nasa import NasaReference

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("ASTRO_DB_PATH", str(ROOT / "data" / "telemetry.sqlite3"))


class ScenarioRequest(BaseModel):
    scenario: str


class LinkRequest(BaseModel):
    available: bool


class SymptomsRequest(BaseModel):
    symptoms: list[str] = Field(default_factory=list, max_length=8)


class IncidentCreateRequest(BaseModel):
    protocol_id: str = Field(min_length=1, max_length=80)
    crew_ids: list[str] = Field(default_factory=list, max_length=12)
    zone_ids: list[str] = Field(default_factory=list, max_length=2)
    origin_code: str = Field(default="MANUAL_REPORT", max_length=100)
    note: str = Field(default="", max_length=1000)
    actor_id: str = Field(min_length=1, max_length=30)


class IncidentStepRequest(BaseModel):
    status: str
    actor_id: str
    note: str = Field(default="", max_length=500)


class IncidentReviewRequest(BaseModel):
    actor_id: str
    note: str = Field(default="", max_length=500)


class AIAnalyzeRequest(BaseModel):
    records: dict[str, str] = Field(min_length=1, max_length=MAX_RECORDS)


class CrewRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    zone_id: str


def create_app(db_path: str | Path | None = None, background: bool = True, ai_engine=None, nasa_fetcher=None) -> FastAPI:
    service = MonitoringService(Database(db_path or DB_PATH))
    nasa = NasaReference(str(db_path or DB_PATH), fetcher=nasa_fetcher)
    engine = ai_engine or AIEngine()
    jobs = JobManager(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if background:
            async def loop():
                while True:
                    await asyncio.sleep(2)
                    service.step()
            task = asyncio.create_task(loop())
        try:
            yield
        finally:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(title="AstroMed Offline Multi-Crew Demo", version="0.4.0", lifespan=lifespan)
    app.state.monitor = service
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

    @app.get("/")
    def homepage():
        return FileResponse(ROOT / "static" / "index.html")

    @app.get("/api/health")
    def health():
        return {"ok": True, "mode": "SIMULATION_ONLY", "ai_model_enabled": engine.available,
                "medical_approval": "NOT_VALIDATED", "clinical_workflow": "DEMO_ONLY"}

    @app.get("/api/nasa/status")
    def nasa_status():
        # Cache only: works fully offline and never touches the network.
        return nasa.status()

    @app.post("/api/nasa/refresh")
    def nasa_refresh():
        # Sync endpoint runs in a worker thread, so monitoring keeps running.
        outcome = nasa.refresh()
        return {"result": outcome, **nasa.status()}

    @app.get("/api/status")
    def status():
        return service.status()

    @app.get("/api/crew")
    def crew():
        data = service.status()
        return {"items": data["crew"], "capacity": data["crew_capacity"]}

    @app.post("/api/crew")
    def add_crew(payload: CrewRequest):
        if payload.zone_id not in ZONES:
            raise HTTPException(422, "Unknown zone_id")
        if not payload.name.strip():
            raise HTTPException(422, "Crew name cannot be blank")
        try:
            return service.add_crew(payload.name, payload.zone_id)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.delete("/api/crew/{crew_id}")
    def remove_crew(crew_id: str):
        try:
            return service.remove_crew(crew_id)
        except KeyError:
            raise HTTPException(404, "Crew member not found")
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/crew/{crew_id}/history")
    def crew_history(crew_id: str, limit: int = Query(60, ge=1, le=300)):
        if crew_id not in {person["crew_id"] for person in service.status()["crew"]}:
            raise HTTPException(404, "Crew member not found")
        return {"crew_id": crew_id, "items": service.db.get_crew_history(crew_id, limit)}

    @app.get("/api/history")
    def history(limit: int = Query(60, ge=1, le=300)):
        return {"items": service.db.get_history(limit)}

    @app.get("/api/events")
    def events(limit: int = Query(40, ge=1, le=200), subject_id: str | None = None):
        return {"items": service.db.get_events(limit, subject_id)}

    @app.get("/api/findings")
    def findings():
        return {"items": service.status()["shared_findings"]}

    @app.get("/api/playbooks/{protocol_id}")
    def playbook(protocol_id: str):
        result = get_playbook(protocol_id)
        if not result:
            raise HTTPException(404, "Unknown protocol")
        return result

    @app.get("/api/protocols")
    def protocols():
        return {"items": all_protocols(), "mode": "DEMO", "clinical_use": False}

    @app.get("/api/protocols/{protocol_id}")
    def protocol(protocol_id: str):
        found = get_protocol(protocol_id)
        if not found:
            raise HTTPException(404, "Protocol not found")
        return found

    @app.get("/api/resources")
    def available_resources():
        return {"items": resources(), "source": "SYNTHETIC_INVENTORY"}

    @app.get("/api/incidents")
    def incidents(limit: int = Query(50, ge=1, le=200)):
        return {"items": service.incidents.list(limit)}

    @app.get("/api/incidents/{incident_id}")
    def incident(incident_id: str):
        try:
            return service.incidents.get(incident_id)
        except KeyError:
            raise HTTPException(404, "Incident not found")

    @app.post("/api/incidents", status_code=201)
    def incident_create(payload: IncidentCreateRequest):
        try:
            return service.create_incident(payload.protocol_id, payload.crew_ids, payload.zone_ids,
                                           payload.origin_code, payload.note, payload.actor_id)
        except KeyError:
            raise HTTPException(404, "Crew member not found")
        except IncidentError as exc:
            raise HTTPException(422, str(exc))

    @app.patch("/api/incidents/{incident_id}/steps/{index}")
    def incident_step(incident_id: str, index: int, payload: IncidentStepRequest):
        try:
            return service.update_incident_step(incident_id, index, payload.status,
                                                payload.actor_id, payload.note)
        except KeyError:
            raise HTTPException(404, "Incident, step or actor not found")
        except IncidentConflict as exc:
            raise HTTPException(409, str(exc))
        except IncidentError as exc:
            raise HTTPException(422, str(exc))

    @app.post("/api/incidents/{incident_id}/review")
    def incident_review(incident_id: str, payload: IncidentReviewRequest):
        try:
            return service.review_incident(incident_id, payload.actor_id, payload.note)
        except KeyError:
            raise HTTPException(404, "Incident or actor not found")
        except IncidentConflict as exc:
            raise HTTPException(409, str(exc))
        except IncidentError as exc:
            raise HTTPException(422, str(exc))

    @app.post("/api/scenario")
    def scenario(payload: ScenarioRequest):
        if payload.scenario not in SCENARIOS:
            raise HTTPException(422, "Unknown scenario")
        return service.set_scenario(payload.scenario)

    @app.post("/api/link")
    def link(payload: LinkRequest):
        return service.set_link(payload.available)

    @app.post("/api/crew/{crew_id}/symptoms")
    def person_symptoms(crew_id: str, payload: SymptomsRequest):
        if any(s not in SYMPTOM_LABELS for s in payload.symptoms):
            raise HTTPException(422, "Unknown symptom")
        try:
            return service.set_symptoms(payload.symptoms, crew_id)
        except KeyError:
            raise HTTPException(404, "Crew member not found")

    @app.post("/api/symptoms")
    def legacy_symptoms(payload: SymptomsRequest):
        if any(s not in SYMPTOM_LABELS for s in payload.symptoms):
            raise HTTPException(422, "Unknown symptom")
        return service.set_symptoms(payload.symptoms)

    @app.post("/api/step")
    def step():
        return service.step()

    # ---- Offline AI assistant (DEMO) ---------------------------------
    @app.get("/api/ai/status")
    def ai_status():
        return engine.status()

    @app.post("/api/ai/load", status_code=202)
    def ai_load():
        if not engine.available:
            raise HTTPException(409, "AI modeli o'rnatilmagan. README dagi 'AI yordamchi' bo'limiga qarang.")
        if not engine.loaded and not engine.loading:
            import threading
            threading.Thread(target=lambda: _quiet(engine.load), daemon=True).start()
        return engine.status()

    @app.post("/api/ai/analyze", status_code=202)
    def ai_analyze(payload: AIAnalyzeRequest):
        if not engine.available:
            raise HTTPException(409, "AI modeli o'rnatilmagan. README dagi 'AI yordamchi' bo'limiga qarang.")
        try:
            return jobs.submit(payload.records)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/ai/jobs/{job_id}")
    def ai_job(job_id: str):
        try:
            return jobs.get(job_id)
        except KeyError:
            raise HTTPException(404, "AI vazifasi topilmadi")

    @app.get("/api/ai/demo")
    def ai_demo():
        from .ai_engine import DEMO_RECORDS
        return {"records": DEMO_RECORDS}

    return app


def _quiet(fn):
    try:
        fn()
    except Exception:
        pass  # error is kept in engine.status()


app = create_app()
