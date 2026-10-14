import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import COOKIE_NAME
from app.api.routes import analytics, auth, conversations, documents, organization, public_chat, tickets
from app.core.config import settings
from app.db.session import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="AI Support Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def csrf_origin_check(request: Request, call_next):
    """Defence in depth on top of SameSite cookies: in production, state-changing requests that
    carry the auth cookie must come from our own frontend origin."""
    if (
        settings.app_env == "production"
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.cookies.get(COOKIE_NAME)
    ):
        origin = request.headers.get("origin")
        if origin and origin != settings.frontend_origin:
            return JSONResponse({"detail": "Cross-origin request blocked"}, status_code=403)
    return await call_next(request)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db():
    with engine.connect() as conn:
        version = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")).scalar()
    return {"database": "connected", "pgvector_version": version}


for module in (auth, organization, documents, public_chat, conversations, tickets, analytics):
    app.include_router(module.router)
