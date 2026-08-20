"""Uploads API endpoints."""
import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile

app = FastAPI()

current_path = os.path.abspath(__file__)
BASE_DIR = current_path[: -len("/api/uploads.py")]
UPLOAD_PATH = os.path.join(BASE_DIR, "data", "uploads")


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
    if not os.path.exists(UPLOAD_PATH):
        raise HTTPException(status_code=404, detail="Upload not found")

    import glob
    matches = glob.glob(os.path.join(UPLOAD_PATH, f"{file_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Upload not found")

    for f in matches:
        os.remove(f)

    return {"status": "deleted"}
