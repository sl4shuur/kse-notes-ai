"""FastAPI application entry point."""

from fastapi import FastAPI

from notes_ai.api.sources import app as sources_app
from notes_ai.api.uploads import app as uploads_app
from notes_ai.api.jobs import app as jobs_app
from notes_ai.api.stats import app as stats_app

app = FastAPI(title="Notes AI", version="0.1.0")

app.mount("/api", sources_app)
app.mount("/api", uploads_app)
app.mount("/api", jobs_app)
app.mount("/api", stats_app)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
