from functools import lru_cache
from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# 已知的不安全默认值，生产环境禁止使用
_UNSAFE_DEFAULTS = {
    "SECRET_KEY": {
        "your-secret-key-here-change-in-production",
        "changeme",
        "secret",
        "test-secret",
    },
    "AI_API_KEY": {
        "a37cc339-b87a-45a1-bd09-035010baf1ef",
        "sk-test",
        "sk-placeholder",
        "",
    },
}


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "AI投资决策助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development | production
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:123456@localhost:5432/investment_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # JWT
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    # AI
    AI_API_KEY: Optional[str] = "a37cc339-b87a-45a1-bd09-035010baf1ef"
    AI_MODEL: str = "glm-4-7-251222"
    AI_API_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    AI_API_TIMEOUT: int = 30

    # Market data
    STOCK_DATA_TIMEOUT: float = 8.0
    STOCK_DATA_CACHE_SECONDS: int = 180
    STOCK_NOTICE_LOOKBACK_DAYS: int = 30

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        """Accept common deployment-style DEBUG values."""
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    @model_validator(mode="after")
    def validate_production_config(self):
        """生产与真实内测环境禁止默认安全配置和 debug 能力，硬失败。"""
        is_production = (
            self.ENVIRONMENT.lower() in ("production", "prod", "staging")
            or not self.DEBUG
        )
        if not is_production:
            return self

        violations: list[str] = []

        unsafe_secret = _UNSAFE_DEFAULTS["SECRET_KEY"]
        if self.SECRET_KEY.lower() in {v.lower() for v in unsafe_secret}:
            violations.append(
                f"SECRET_KEY has default/placeholder value '{self.SECRET_KEY}' — "
                "must be set explicitly in production"
            )

        unsafe_ai = _UNSAFE_DEFAULTS["AI_API_KEY"]
        if (self.AI_API_KEY or "").strip().lower() in {v.lower() for v in unsafe_ai}:
            violations.append(
                f"AI_API_KEY has default/placeholder value — "
                "must be set explicitly in production"
            )

        if violations:
            joined = "; ".join(violations)
            raise ValueError(
                f"[PRODUCTION CONFIG VIOLATION] {joined}. "
                "Application refuses to start in production with insecure defaults. "
                "Set explicit values via environment variables or .env file."
            )

        return self


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
