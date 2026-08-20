"""Sources API endpoints."""
import json
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

current_path = os.path.abspath(__file__)
BASE_DIR = current_path[: -len("/api/sources.py")]
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


@app.post("/sources", status_code=202)
async def create_source(body: SourceCreate):
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

    # TODO: enqueue a pipeline job here and return its job_id
    return {"job_id": f"job_{uuid4().hex[:4]}", "source": source_record}


@app.get("/sources")
async def list_sources():
    return _read_sources()


@app.get("/sources/{source_id}")
async def get_source(source_id: str):
    for s in _read_sources():
        if s["id"] == source_id:
            return s
    raise HTTPException(status_code=404, detail="Source not found")
