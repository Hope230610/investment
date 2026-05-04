import uuid
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.v1 import api_router
from src.core.config import get_settings
from src.core.logging import setup_logging
from src.db.session import Base, engine, ensure_database_exists
from src.schemas.common import ErrorDetail, ErrorResponse

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
    response = await call_next(request)
    log.bind(status_code=response.status_code).info("request_complete")
    return response


app.include_router(api_router, prefix=settings.API_PREFIX)


# ─── Global exception handlers ─────────────────────────────────────────────────

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Convert all HTTPException (including FastAPI's) to unified error structure."""
    request_id = _request_id_var.get()
    body = ErrorResponse(error=ErrorDetail(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail) if exc.detail else f"HTTP {exc.status_code}",
        request_id=request_id,
        retryable=exc.status_code >= 500,
    ))
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(),
        headers=dict(exc.headers) if exc.headers else {},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert request validation failures to the unified API error contract."""
    request_id = _request_id_var.get()
    body = ErrorResponse(error=ErrorDetail(
        code="REQUEST_VALIDATION_ERROR",
        message=_format_validation_error(exc),
        request_id=request_id,
        retryable=False,
    ))
    return JSONResponse(status_code=422, content=body.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all: convert unexpected exceptions to unified error structure."""
    request_id = _request_id_var.get()
    body = ErrorResponse(error=ErrorDetail(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        request_id=request_id,
        retryable=True,
    ))
    return JSONResponse(status_code=500, content=body.model_dump())


def _format_validation_error(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "请求参数校验失败"

    messages: list[str] = []
    for error in errors[:3]:
        loc = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        detail = str(error.get("msg") or "字段不合法")
        messages.append(f"{loc}: {detail}" if loc else detail)

    if len(errors) > 3:
        messages.append(f"另有 {len(errors) - 3} 个字段需要检查")

    return "请求参数校验失败：" + "；".join(messages)


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
