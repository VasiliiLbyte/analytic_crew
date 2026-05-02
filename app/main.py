from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import access, cycles, feedback, ideas, logs, signals, trends
from app.core.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)

        settings = get_settings()
        limiter = settings.get_rate_limiter()
        if not await limiter.acquire():
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        return await call_next(request)

app = FastAPI(title="Analytic Crew API", version="2.0")
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_origin_regex=r"https://.*\.v0\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
