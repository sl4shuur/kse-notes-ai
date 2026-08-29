"""Notes API endpoints."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi import status as http_status

from notes_ai.api.tags import load_tags, save_tags
from notes_ai.adapters.storage.json_store import JsonNoteStore
from notes_ai.adapters.storage.markdown import MarkdownNoteStore
from notes_ai.models import Note

app = FastAPI()

BASE_DIR = str(Path(__file__).resolve().parents[3])
OUTPUT_PATH = os.path.join(BASE_DIR, "output")
METADATA_PATH = os.path.join(BASE_DIR, "data", "note_data")
TAGS_PATH = os.path.join(BASE_DIR, "data", "tags.json")


def _note_path(note_id: str) -> Path:
    return Path(METADATA_PATH) / f"{note_id}.json"


def _sync_tag_counts(old_tags: list[str], new_tags: list[str]) -> None:
    """Adjust _tags.json counts for tags added/removed on a note."""
    old_set, new_set = set(old_tags), set(new_tags)
    added = new_set - old_set
    removed = old_set - new_set
    if not added and not removed:
        return

    data = load_tags()
    for t in added:
        data[t] = data.get(t, 0) + 1
    for t in removed:
        if t in data:
            data[t] = max(0, data[t] - 1)
    save_tags(data)
    return


@app.get("/notes")
async def list_notes(
    q: str | None = Query(default=None, min_length=1),
    source_type: str | None = None,
    tag: str | None = None,
    status: str | None = None,
):
    try:
        results = []
        os.makedirs(METADATA_PATH, exist_ok=True)
        for fname in os.listdir(METADATA_PATH):
            file_path = Path(METADATA_PATH) / fname
            if file_path.suffix != ".json":
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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes/{note_id}")
async def get_note(note_id: str):
    file_path = _note_path(note_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notes", status_code=http_status.HTTP_201_CREATED)
async def post_note(note: Note):
    try:
        store = JsonNoteStore(Path(METADATA_PATH))
        md_store = MarkdownNoteStore(Path(OUTPUT_PATH))
        await md_store.save(note)
        new_title = await store.save(note)

        if new_title != note.title:
            note = note.model_copy(update={"title": new_title})
            
        return note
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/notes/{note_id}")
async def put_note(note_id: str, note: Note, status: str = "draft", tags: list[str] = []):
    file_path = _note_path(note_id)
    if not file_path.exists():
            raise HTTPException(status_code=404, detail="Note not found(json)")
    
    md_path = Path(OUTPUT_PATH + f"/{note_id}.md")
    if not md_path.exists():
            raise HTTPException(status_code=404, detail="Note not found(md)")
    
    try:
        old_data = json.loads(file_path.read_text(encoding="utf-8"))
        old_tags = old_data.get("tags", [])
        data = json.loads(note.model_dump_json())
        data["status"] = status
        data["tags"] = tags
        data["date_modified"] = datetime.now(timezone.utc).isoformat()
        os.remove(md_path)
        md_path.write_text(data["content"])
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        _sync_tag_counts(old_tags, tags)

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/notes/{note_id}")
async def patch_note(
    note_id: str,
    content: str | None = None,
    status: str | None = None,
    tags: list[str] | None = Query(default=None),
    title: str | None = None,
):
    file_path = _note_path(note_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found(json)")
    
    md_path = Path(OUTPUT_PATH + f"/{note_id}.md")
    if not md_path.exists():
            raise HTTPException(status_code=404, detail="Note not found(md)")
    
    try:
        note_data = json.loads(file_path.read_text(encoding="utf-8"))
        
        if content is not None:
            note_data["content"] = content
            os.remove(md_path)
            md_path.write_text(content)

        if status is not None:
            note_data["status"] = status

        if title is not None:
            note_data["title"] = title

        if tags is not None:
            old_tags = note_data.get("tags", [])
            new_tags = list(dict.fromkeys(tags))  # dedupe, preserve order
            note_data["tags"] = new_tags
            _sync_tag_counts(old_tags, new_tags)

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
            raise HTTPException(status_code=404, detail="Note not found(json)")
    
    md_path = Path(OUTPUT_PATH + f"/{note_id}.md")
    if not md_path.exists():
                raise HTTPException(status_code=404, detail="Note not found(md)")
    
    try:
        note_data = json.loads(file_path.read_text(encoding="utf-8"))
        old_tags = note_data.get("tags", [])

        os.remove(md_path)
        os.remove(file_path)
       

        if old_tags:
            _sync_tag_counts(old_tags, [])

        return Response(status_code=http_status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))