"""FastAPI application entry point."""

from fastapi import FastAPI

from notes_ai.api.sources import app as sources_app
from notes_ai.api.uploads import app as uploads_app
from notes_ai.api.jobs import app as jobs_app
from notes_ai.api.notes import app as notes_app
from notes_ai.api.tags import app as tags_app
from notes_ai.api.stats import app as stats_app

app = FastAPI(title="Notes AI", version="0.1.0")

app.include_router(sources_app.router, prefix="/api")
app.include_router(uploads_app.router, prefix="/api")
app.include_router(jobs_app.router, prefix="/api")
app.include_router(notes_app.router, prefix="/api")
app.include_router(tags_app.router, prefix="/api")
app.include_router(stats_app.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
