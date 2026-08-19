"""Tags API endpoints."""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, status

app = FastAPI()

current_path = os.path.abspath(__file__)
BASE_DIR = current_path[: -len("/api/sources.py")]
OUTPUT_PATH = os.path.join(BASE_DIR, "output")
METADATA_PATH = os.path.join(BASE_DIR, "data", "note_data")

TAGS_PATH = Path(METADATA_PATH) / "_tags.json"


def load_tags() -> dict:
    if not TAGS_PATH.exists():
        return {}
    return json.loads(TAGS_PATH.read_text(encoding="utf-8"))


def save_tags(data: dict) -> None:
    TAGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def rename_tag_in_notes(old: str, new: str) -> None:
    for fname in os.listdir(METADATA_PATH):
        file_path = Path(METADATA_PATH) / fname
        if file_path.suffix != ".json" or file_path.stem.startswith("_"):
            continue
        note = json.loads(file_path.read_text(encoding="utf-8"))
        note["tags"] = [new if x == old else x for x in note.get("tags", [])]
        note["tags"] = list(dict.fromkeys(note["tags"]))  # dedupe, preserve order
        file_path.write_text(json.dumps(note, indent=2), encoding="utf-8")


def remove_tag_from_notes(tag: str) -> None:
    for fname in os.listdir(METADATA_PATH):
        file_path = Path(METADATA_PATH) / fname
        if file_path.suffix != ".json" or file_path.stem.startswith("_"):
            continue
        note = json.loads(file_path.read_text(encoding="utf-8"))
        note["tags"] = [x for x in note.get("tags", []) if x != tag]
        file_path.write_text(json.dumps(note, indent=2), encoding="utf-8")


@app.post("/tags", status_code=status.HTTP_201_CREATED)
async def post_tag(tag: str):
    data = load_tags()
    if tag in data:
        return Response(status_code=status.HTTP_200_OK)
    data[tag] = 0
    save_tags(data)
    return Response(status_code=status.HTTP_201_CREATED)


@app.get("/tags")
async def list_tags():
    return load_tags()


@app.patch("/tags/{tag}")
async def patch_tag(tag: str, new_tag: str):
    data = load_tags()
    if tag not in data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    count = data.pop(tag)
    # merge counts if new_tag already exists
    data[new_tag] = data.get(new_tag, 0) + count
    save_tags(data)

    rename_tag_in_notes(tag, new_tag)
    return Response(status_code=status.HTTP_200_OK)


@app.delete("/tags/{tag}")
async def delete_tag(tag: str):
    data = load_tags()
    if tag not in data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    data.pop(tag)
    save_tags(data)

    remove_tag_from_notes(tag)
    return Response(status_code=status.HTTP_200_OK)