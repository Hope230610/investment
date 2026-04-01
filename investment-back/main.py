from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.v1 import api_router
from src.core.config import get_settings
from src.core.logging import setup_logging
from src.db.session import Base, SessionLocal, engine, ensure_database_exists
from src.models.user import (
    ExperienceLevel,
    HoldingHorizon,
    RiskTolerance,
    User,
    UserProfile,
)

settings = get_settings()
logger = setup_logging(debug=settings.DEBUG)


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


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend service for the AI investment assistant.",
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

app.add_middleware(SecurityHeadersMiddleware)
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
    """Initialize database and seed a test user on startup."""
    logger.info("app_starting", version=settings.APP_VERSION)

    try:
        ensure_database_exists()
        Base.metadata.create_all(bind=engine)
    except UnicodeDecodeError as exc:
        logger.error(
            "database_connection_encoding_error",
            error=str(exc),
            database_url=settings.DATABASE_URL,
        )
        raise RuntimeError(
            "Database connection failed. Please verify DATABASE_URL and confirm the target PostgreSQL database exists."
        ) from exc

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            logger.info("creating_test_user")
            test_user = User(
                username="testuser",
                email="test@example.com",
            )
            test_user.set_password("testpassword123")
            db.add(test_user)
            db.commit()
            db.refresh(test_user)

            test_profile = UserProfile(
                user_id=test_user.id,
                experience_level=ExperienceLevel.NOVICE,
                holding_horizon=HoldingHorizon.MEDIUM,
                risk_tolerance=RiskTolerance.MEDIUM,
                behavior_tags=[],
            )
            db.add(test_profile)
            db.commit()

    except Exception as exc:  # pragma: no cover - seed failure should not crash startup
        logger.error("init_error", error=str(exc))
        db.rollback()
    finally:
        db.close()

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
