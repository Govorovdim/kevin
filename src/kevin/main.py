import time
from collections import defaultdict
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from kevin.api.v1.router import router as v1_router
from kevin.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

_cors_kwargs: dict = dict(
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
)

if settings.debug:
    # Allow any local-network address during development
    _cors_kwargs["allow_origin_regex"] = (
        r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?"
    )

app.add_middleware(CORSMiddleware, **_cors_kwargs)


# ── Simple in-memory rate limiter for auth endpoints ──────────────────────────

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # per window


@app.middleware("http")
async def rate_limit_auth(request: Request, call_next):
    if request.url.path.startswith("/api/v1/auth/"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        # Purge old entries
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
        ]
        if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
            )
        _rate_limit_store[client_ip].append(now)
    return await call_next(request)


app.include_router(v1_router, prefix="/api/v1")


def main() -> None:
    uvicorn.run(
        "kevin.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
