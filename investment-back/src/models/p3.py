from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db.session import Base
from src.models.base import TimestampMixin


class PlanCodeEnum(str, enum.Enum):
    FREE = "free"
    PRO = "pro"


class SharePrivacyLevelEnum(str, enum.Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"


class ShareSnapshot(TimestampMixin, Base):
    """Sanitized, revocable public snapshot of an analysis result."""

    __tablename__ = "share_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    share_id = Column(String(32), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    source_type = Column(String(40), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    support_evidence = Column(JSON, nullable=False, default=list)
    counter_evidence = Column(JSON, nullable=False, default=list)
    risks = Column(JSON, nullable=False, default=list)
    invalidation_conditions = Column(JSON, nullable=False, default=list)
    confidence_level = Column(String(20), nullable=False)
    data_timestamp = Column(DateTime, nullable=True)
    disclaimer = Column(Text, nullable=False)
    privacy_level = Column(
        Enum(
            SharePrivacyLevelEnum,
            name="shareprivacylevelenum",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
        default=SharePrivacyLevelEnum.UNLISTED,
    )
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    sanitizer_version = Column(String(40), nullable=False, default="share-sanitizer-v1")

    user = relationship("User", backref="share_snapshots")

    __table_args__ = (
        Index("ix_share_snapshots_user_source", "user_id", "source_type", "source_id"),
        Index("ix_share_snapshots_expires_at", "expires_at"),
    )


class UserEntitlement(TimestampMixin, Base):
    """Current commercial plan and feature flags for a user."""

    __tablename__ = "user_entitlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    plan_code = Column(
        Enum(
            PlanCodeEnum,
            name="plancodeenum",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
        default=PlanCodeEnum.FREE,
    )
    feature_flags = Column(JSON, nullable=False, default=dict)
    valid_until = Column(DateTime, nullable=True)

    user = relationship("User", backref="entitlement")


class UsageCounter(TimestampMixin, Base):
    """Daily per-user usage counter for entitlement checks."""

    __tablename__ = "usage_counters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    usage_key = Column(String(60), nullable=False)
    usage_date = Column(Date, nullable=False)
    count = Column(Integer, nullable=False, default=0)

    user = relationship("User", backref="usage_counters")

    __table_args__ = (
        Index("ix_usage_counters_user_key_date", "user_id", "usage_key", "usage_date", unique=True),
    )
