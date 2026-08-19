"""Notes API endpoints."""
"""Notes API endpoints."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response, status
from notes_ai.api.tags import post_tag
from notes_ai.adapters.storage.json_store import JsonNoteStore
from notes_ai.models import Note

app = FastAPI()

current_path = os.path.abspath(__file__)
BASE_DIR = current_path[: -len("/api/sources.py")]
OUTPUT_PATH = os.path.join(BASE_DIR, "output")
METADATA_PATH = os.path.join(BASE_DIR, "data", "note_data")


def _note_path(note_id: str) -> Path:
    return Path(METADATA_PATH) / f"{note_id}.json"


@app.get("/notes")
async def list_notes(
    q: str | None = Query(default=None, min_length=1),
    source_type: str | None = None,
    tag: str | None = None,
    status: str | None = None,
):
    try:
        results = []
        for fname in os.listdir(METADATA_PATH):
            file_path = Path(METADATA_PATH) / fname
            if file_path.suffix != ".json":
                continue
            if file_path.stem[0] == "_":
                continue

            data = json.loads(file_path.read_text(encoding="utf-8"))

            if source_type and data.get("source", {}).get("input_type") != source_type:
                continue
            if tag and tag not in data.get("tags", []):
                continue
            if status and data.get("status") != status:
                continue
            if q and q.lower() not in json.dumps(data).lower():
                continue

            results.append(data)

        return results
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/notes/{note_id}")
async def get_note(note_id: str):
    file_path = _note_path(note_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notes", status_code=status.HTTP_201_CREATED)
async def post_note(note: Note):
    try:
        store = JsonNoteStore(METADATA_PATH)
        store.save(note)
        return note
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/notes/{note_id}")
async def put_note(note_id: str, note: Note, status, tags):
    file_path = _note_path(note_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        data = json.load(note.model_dump_json())
        data["status"] = status
        data["tags"] = tags
        json_data= json.dumps(data, indent = 2)
        file_path.write_text(json_data, encoding="utf-8")
        return json_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/notes/{note_id}")
async def patch_note(
    note_id: str,
    content: str | None = None,
    status: str | None = None,
    tags: str | list[str] | None = [],
    title: str | None = None,
):
    file_path = _note_path(note_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")

    try:
        note_data = json.loads(file_path.read_text(encoding="utf-8"))

        if content is not None:
            note_data["content"] = content
        if status is not None:
            note_data["status"] = status
        if title is not None:
            note_data["title"] = title
        if tags is not None:
            existing = note_data.get("tags", [])
            new_tags = tags if isinstance(tags, list) else [tags]
            note_data["tags"] = existing + [t for t in new_tags if t not in existing]
            data = json.load(METADATA_PATH + "/_tags.json")
            for t in [t for t in new_tags if t not in existing]:
                if t not in data:
                    data[t] = 1
                else:
                    data[t] += 1
            Path(METADATA_PATH + "/_tags.json").write_text(json.dumps(data, indent = 2))            

                
        note_data["date_modified"] = datetime.now(timezone.utc).isoformat()

        file_path.write_text(json.dumps(note_data, indent=2), encoding="utf-8")
        return note_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    file_path = _note_path(note_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        os.remove(file_path)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

                   


    

    
    