"""Sources API endpoints."""
import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from notes_ai.api.jobs import _read_jobs, _write_jobs
from notes_ai.api.uploads import get_upload_path
from notes_ai.main import generate_notes

app = FastAPI()

BASE_DIR = str(Path(__file__).resolve().parents[3])
SOURCES_PATH = os.path.join(BASE_DIR, "data", "sources.json")


def _read_sources() -> list[dict]:
    if not os.path.exists(SOURCES_PATH):
        return []
    return json.loads(Path(SOURCES_PATH).read_text(encoding="utf-8"))


def _write_sources(sources: list[dict]) -> None:
    os.makedirs(os.path.dirname(SOURCES_PATH), exist_ok=True)
    Path(SOURCES_PATH).write_text(json.dumps(sources, indent=2), encoding="utf-8")


class SourceCreate(BaseModel):
    input_type: str
    location: str
    note_focus: str | None = None


def run_job(job_id: str, location: str, note_focus: str | None = None):
    jobs = _read_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j["status"] = "running"
            break
    _write_jobs(jobs)

    try:
        notes = asyncio.run(generate_notes([location], note_focus=note_focus))
        if not notes:
            raise RuntimeError("The pipeline did not generate a note")
        note_id = notes[0].title

        jobs = _read_jobs()
        for j in jobs:
            if j["id"] == job_id:
                j["status"] = "done"
                j["note_id"] = note_id
                break
        _write_jobs(jobs)
    except Exception as error:
        jobs = _read_jobs()
        for j in jobs:
            if j["id"] == job_id:
                j["status"] = "failed"
                j["error"] = str(error)
                break
        _write_jobs(jobs)

@app.post("/sources", status_code=202)
async def create_source(body: SourceCreate, background_tasks: BackgroundTasks):
    processing_location = body.location
    if body.input_type in {"pdf", "image", "audio"}:
        processing_location = str(get_upload_path(body.location))

    source_id = f"src_{uuid4().hex[:8]}"
    source_record = {
        "id": source_id,
        "input_type": body.input_type,
        "location": body.location,
        "note_focus": body.note_focus,
    }

    sources = _read_sources()
    sources.append(source_record)
    _write_sources(sources)

    job_id = f"job_{uuid4().hex[:4]}"
    
    jobs = _read_jobs()
    jobs.append({
        "id": job_id,
        "status": "pending",
        "type": "generate_note",
        "source_id": source_id,
    })
    _write_jobs(jobs)

    # Enqueue pipeline job
    background_tasks.add_task(run_job, job_id, processing_location, body.note_focus)

    return {"job_id": job_id, "source": source_record}


@app.get("/sources")
async def list_sources():
    return _read_sources()


@app.get("/sources/{source_id}")
async def get_source(source_id: str):
    for s in _read_sources():
        if s["id"] == source_id:
            return s
    raise HTTPException(status_code=404, detail="Source not found")
