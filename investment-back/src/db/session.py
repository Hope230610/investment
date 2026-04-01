import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.config import get_settings

settings = get_settings()


def ensure_database_exists():
    """Create the configured PostgreSQL database if it does not exist yet."""
    url = make_url(settings.DATABASE_URL)
    if not url.drivername.startswith("postgresql") or not url.database:
        return

    connect_kwargs = {
        "dbname": "postgres",
        "user": url.username,
        "password": url.password,
        "host": url.host or "localhost",
        "port": url.port or 5432,
    }

    conn = psycopg2.connect(**connect_kwargs)
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (url.database,),
            )
            exists = cursor.fetchone() is not None
            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database))
                )
    finally:
        conn.close()


engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
