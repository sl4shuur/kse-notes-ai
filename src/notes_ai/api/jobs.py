"""Jobs API endpoints."""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI()

current_path = os.path.abspath(__file__)
BASE_DIR = current_path[: -len("/api/jobs.py")]
JOBS_PATH = os.path.join(BASE_DIR, "data", "jobs.json")
LOGS_PATH = os.path.join(BASE_DIR, "data", "logs")


def _read_jobs() -> list[dict]:
    if not os.path.exists(JOBS_PATH):
        return []
    return json.loads(Path(JOBS_PATH).read_text(encoding="utf-8"))


def _write_jobs(jobs: list[dict]) -> None:
    os.makedirs(os.path.dirname(JOBS_PATH), exist_ok=True)
    Path(JOBS_PATH).write_text(json.dumps(jobs, indent=2), encoding="utf-8")


@app.get("/jobs")
async def list_jobs():
    return _read_jobs()


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    for j in _read_jobs():
        if j["id"] == job_id:
            return j
    raise HTTPException(status_code=404, detail="Job not found")


@app.get("/jobs/{job_id}/log")
async def get_job_log(job_id: str, since: str | None = None):
    log_file = os.path.join(LOGS_PATH, f"{job_id}.log")
    if not os.path.exists(log_file):
        return []
    lines = Path(log_file).read_text(encoding="utf-8").splitlines()
    return lines


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    jobs = _read_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j["status"] = "cancelled"
            _write_jobs(jobs)
            return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Job not found")
