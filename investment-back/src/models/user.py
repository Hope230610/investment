import enum

from passlib.context import CryptContext
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from src.db.session import Base
from src.models.base import TimestampMixin


class ExperienceLevel(enum.Enum):
    """User experience level."""

    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class HoldingHorizon(enum.Enum):
    """Investment holding horizon."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class RiskTolerance(enum.Enum):
    """Risk tolerance level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BehaviorTag(enum.Enum):
    """Behavior tags inferred from user actions."""

    CHASING_RISE = "chasing_rise"
    PANIC_SELL = "panic_sell"
    FREQUENT_TRADING = "frequent_trading"
    STABLE_DISCIPLINE = "stable_discipline"


# Use PBKDF2 to avoid Windows bcrypt compatibility issues during local setup.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class User(TimestampMixin, Base):
    """Application user model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

    def set_password(self, password: str):
        """Hash and store the user's password."""
        self.hashed_password = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return pwd_context.verify(password, self.hashed_password)

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    analyses = relationship("Analysis", back_populates="user")
    watchlist = relationship("WatchlistItem", back_populates="user")
    reviews = relationship("ReviewTask", back_populates="user")


class UserProfile(TimestampMixin, Base):
    """User profile model."""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    experience_level = Column(
        Enum(ExperienceLevel),
        default=ExperienceLevel.NOVICE,
        nullable=False,
    )
    holding_horizon = Column(
        Enum(HoldingHorizon),
        default=HoldingHorizon.MEDIUM,
        nullable=False,
    )
    risk_tolerance = Column(
        Enum(RiskTolerance),
        default=RiskTolerance.MEDIUM,
        nullable=False,
    )
    behavior_tags = Column(JSON, default=list)

    user = relationship("User", back_populates="profile")
