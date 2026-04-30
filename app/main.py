from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import access, cycles, feedback, ideas, logs, signals, trends

app = FastAPI(title="Analytic Crew API", version="2.0")

app.include_router(cycles.router, prefix="/api")
app.include_router(ideas.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(access.router, prefix="/api")
app.include_router(logs.router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
