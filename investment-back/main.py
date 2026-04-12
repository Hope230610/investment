import uuid
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from src.api.v1 import api_router
from src.core.config import get_settings
from src.core.logging import setup_logging
from src.db.session import Base, engine, ensure_database_exists

settings = get_settings()
logger = setup_logging(debug=settings.DEBUG)

# Request ID context variable — 可在任意位置通过 log.bind(request_id=...) 访问
_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add a minimal set of security headers."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
        )
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Generate or forward request_id and bind to structlog context."""

    async def dispatch(self, request: Request, call_next):
        # Use incoming x-request-id header, or generate a new UUID
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        _request_id_var.set(req_id)

        # Bind to structlog context so all log entries in this request include it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=req_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend service for the AI investment assistant.",
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Record request logs."""
    log = logger.bind(
        method=request.method,
        path=request.url.path,
        query=dict(request.query_params),
    )
    log.info("incoming_request")

    try:
        response = await call_next(request)
        log.bind(status_code=response.status_code).info("request_complete")
        return response
    except Exception as exc:  # pragma: no cover - defensive logging
        log.bind(error=str(exc)).error("request_error")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})


app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/ready")
async def readiness_check():
    """Readiness probe for load balancer / k8s.

    Checks that the database is reachable.
    Returns 200 + {status: ready} when healthy.
    Returns 503 + {status: not ready} when unhealthy.
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "reason": "database unreachable",
                "detail": str(exc),
            },
        )
    return {"status": "ready", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_PREFIX}/docs",
    }


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("app_starting", version=settings.APP_VERSION)

    try:
        ensure_database_exists()
        Base.metadata.create_all(bind=engine)
    except UnicodeDecodeError as exc:
        logger.error(
            "database_connection_encoding_error",
            error=str(exc),
        )
        raise RuntimeError(
            "Database connection failed. Please verify DATABASE_URL and confirm the target PostgreSQL database exists."
        ) from exc

    logger.info("app_started")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown hook."""
    logger.info("app_shutting_down")
    logger.info("app_shutdown")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
