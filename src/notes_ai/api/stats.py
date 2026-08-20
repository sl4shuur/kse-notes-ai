"""Stats API endpoint."""
import json
import os
from pathlib import Path

from fastapi import FastAPI

app = FastAPI()

BASE_DIR = str(Path(__file__).resolve().parents[3])
NOTE_DATA_PATH = os.path.join(BASE_DIR, "data", "note_data")
SOURCES_PATH = os.path.join(BASE_DIR, "data", "sources.json")


@app.get("/stats")
async def get_stats():
    notes_total = 0
    if os.path.exists(NOTE_DATA_PATH):
        notes_total = len([
            f for f in os.listdir(NOTE_DATA_PATH)
            if f.endswith(".json") and not f.startswith("_")
        ])

    sources_count = 0
    if os.path.exists(SOURCES_PATH):
        sources = json.loads(Path(SOURCES_PATH).read_text(encoding="utf-8"))
        sources_count = len(sources)

    return {
        "notes_total": notes_total,
        "sources_count": sources_count,
        "source_types_supported": 5,
    }
