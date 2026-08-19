"""Tags API endpoints."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response, status

from notes_ai.adapters.storage.json_store import JsonNoteStore
from notes_ai.models import Note

app = FastAPI()

current_path = os.path.abspath(__file__)
BASE_DIR = current_path[: -len("/api/sources.py")]
OUTPUT_PATH = os.path.join(BASE_DIR, "output")
METADATA_PATH = os.path.join(BASE_DIR, "data", "note_data")


@app.post("/tags")
async def post_tag(tag:str):
    tag_path = METADATA_PATH + "/_tags.json"
    data = json.load(tag_path)
    if tag in data:
        return Response(status_code=200)
    else:
        data["tag"] = 1
    Path(tag_path).write_text(json.dumps(data,indent= 2))    
    return Response(status_code=200)

@app.get("/tags")
async def list_tags(tag:str):
    tag_path = METADATA_PATH + "/_tags.json"
    data = json.load(tag_path)
    return data


@app.patch("/tags/{tag}")
async def patch_tag(tag:str, new_tag):
    tag_path = METADATA_PATH + "/_tags.json"
    data = json.load(tag_path)
    if tag in data:
        c = data[tag]
        data.pop(tag)
        data["new_tag"] = c
        Path(tag_path).write_text(json.dumps(data,indent= 2))  

    for fname in os.listdir(METADATA_PATH):
                file_path = Path(METADATA_PATH) / fname
                if file_path.suffix != ".json":
                    continue
                if file_path.stem[0] == "_":
                    continue
                note = json.loads(file_path.read_text(encoding="utf-8"))
                tags = [new_tag if x == tag else x for x in note["tags"]]
                note["tags"] = tags
                note_json = json.dumps(note, indent = 2)
                file_path.write_text(note_json, encoding="utf-8")
    return Response(status_code=200)

@app.delete("/tags/{tag}")
async def list_tags(tag:str):
    tag_path = METADATA_PATH + "/_tags.json"
    data = json.load(tag_path)
    if tag in data:
            data.pop(tag)
            Path(tag_path).write_text(json.dumps(data,indent= 2))  
    for fname in os.listdir(METADATA_PATH):
                    file_path = Path(METADATA_PATH) / fname
                    if file_path.suffix != ".json":
                        continue
                    if file_path.stem[0] == "_":
                        continue
                    note = json.loads(file_path.read_text(encoding="utf-8"))
                    tags = [x for x in note["tags"] if x != tag]
                    note["tags"] = tags
                    note_json = json.dumps(note, indent = 2)
                    file_path.write_text(note_json, encoding="utf-8")
    return Response(status_code=200)