"""Uploads API endpoints."""
import os
import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile

app = FastAPI()

BASE_DIR = str(Path(__file__).resolve().parents[3])
UPLOAD_PATH = os.path.join(BASE_DIR, "data", "uploads")
FILE_ID_PATTERN = re.compile(r"file_[0-9a-f]{8}")


def get_upload_path(file_id: str) -> Path:
    """Resolve an upload ID to its stored file."""
    if not FILE_ID_PATTERN.fullmatch(file_id):
        raise HTTPException(status_code=400, detail="Invalid file ID format")
    if not os.path.exists(UPLOAD_PATH):
        raise HTTPException(status_code=404, detail="Upload not found")

    matches = [
        Path(UPLOAD_PATH) / filename
        for filename in os.listdir(UPLOAD_PATH)
        if filename == file_id or filename.startswith(file_id + ".")
    ]
    if not matches:
        raise HTTPException(status_code=404, detail="Upload not found")
    return matches[0]


@app.post("/uploads")
async def upload_file(file: UploadFile):
    file_id = f"file_{uuid4().hex[:8]}"
    os.makedirs(UPLOAD_PATH, exist_ok=True)

    suffix = Path(file.filename).suffix if file.filename else ""
    dest = os.path.join(UPLOAD_PATH, f"{file_id}{suffix}")

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"file_id": file_id, "filename": file.filename}


@app.delete("/uploads/{file_id}")
async def delete_upload(file_id: str):
    os.remove(get_upload_path(file_id))

    return {"status": "deleted"}
