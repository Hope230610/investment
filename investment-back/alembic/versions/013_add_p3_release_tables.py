"""013: add p3 release candidate tables

Revision ID: 013
Revises: 012
Create Date: 2026-05-05 00:00:00.000000
"""
from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    if context.is_offline_mode():
        return False
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    if context.is_offline_mode():
        return False
    return any(index["name"] == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def _create_index_once(index_name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _assert_columns(table_name: str, required_columns: set[str]) -> None:
    if context.is_offline_mode():
        return
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}
    missing = sorted(required_columns - existing)
    if missing:
        raise RuntimeError(f"{table_name} exists but is missing required columns: {', '.join(missing)}")


def upgrade() -> None:
    plan_code = postgresql.ENUM("free", "pro", name="plancodeenum")
    plan_code.create(op.get_bind(), checkfirst=True)
    privacy_level = postgresql.ENUM("public", "unlisted", name="shareprivacylevelenum")
    privacy_level.create(op.get_bind(), checkfirst=True)

    if not _table_exists("share_snapshots"):
        op.create_table(
            "share_snapshots",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("share_id", sa.String(length=32), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("source_type", sa.String(length=40), nullable=False),
            sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("support_evidence", sa.JSON(), nullable=False),
            sa.Column("counter_evidence", sa.JSON(), nullable=False),
            sa.Column("risks", sa.JSON(), nullable=False),
            sa.Column("invalidation_conditions", sa.JSON(), nullable=False),
            sa.Column("confidence_level", sa.String(length=20), nullable=False),
            sa.Column("data_timestamp", sa.DateTime(), nullable=True),
            sa.Column("disclaimer", sa.Text(), nullable=False),
            sa.Column("privacy_level", postgresql.ENUM("public", "unlisted", name="shareprivacylevelenum", create_type=False), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("sanitizer_version", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _assert_columns(
        "share_snapshots",
        {
            "id",
            "share_id",
            "user_id",
            "source_type",
            "source_id",
            "title",
            "summary",
            "support_evidence",
            "counter_evidence",
            "risks",
            "invalidation_conditions",
            "confidence_level",
            "data_timestamp",
            "disclaimer",
            "privacy_level",
            "expires_at",
            "revoked_at",
            "sanitizer_version",
            "created_at",
            "updated_at",
        },
    )
    _create_index_once("ix_share_snapshots_share_id", "share_snapshots", ["share_id"], unique=True)
    _create_index_once("ix_share_snapshots_user_id", "share_snapshots", ["user_id"])
    _create_index_once("ix_share_snapshots_user_source", "share_snapshots", ["user_id", "source_type", "source_id"])
    _create_index_once("ix_share_snapshots_expires_at", "share_snapshots", ["expires_at"])

    if not _table_exists("user_entitlements"):
        op.create_table(
            "user_entitlements",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("plan_code", postgresql.ENUM("free", "pro", name="plancodeenum", create_type=False), nullable=False),
            sa.Column("feature_flags", sa.JSON(), nullable=False),
            sa.Column("valid_until", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _assert_columns(
        "user_entitlements",
        {"id", "user_id", "plan_code", "feature_flags", "valid_until", "created_at", "updated_at"},
    )
    _create_index_once("ix_user_entitlements_user_id", "user_entitlements", ["user_id"], unique=True)

    if not _table_exists("usage_counters"):
        op.create_table(
            "usage_counters",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("usage_key", sa.String(length=60), nullable=False),
            sa.Column("usage_date", sa.Date(), nullable=False),
            sa.Column("count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _assert_columns(
        "usage_counters",
        {"id", "user_id", "usage_key", "usage_date", "count", "created_at", "updated_at"},
    )
    _create_index_once("ix_usage_counters_user_id", "usage_counters", ["user_id"])
    _create_index_once("ix_usage_counters_user_key_date", "usage_counters", ["user_id", "usage_key", "usage_date"], unique=True)


def downgrade() -> None:
    if _table_exists("usage_counters"):
        for index_name in ["ix_usage_counters_user_key_date", "ix_usage_counters_user_id"]:
            if _index_exists("usage_counters", index_name):
                op.drop_index(index_name, table_name="usage_counters")
        op.drop_table("usage_counters")
    if _table_exists("user_entitlements"):
        if _index_exists("user_entitlements", "ix_user_entitlements_user_id"):
            op.drop_index("ix_user_entitlements_user_id", table_name="user_entitlements")
        op.drop_table("user_entitlements")
    if _table_exists("share_snapshots"):
        for index_name in [
            "ix_share_snapshots_expires_at",
            "ix_share_snapshots_user_source",
            "ix_share_snapshots_user_id",
            "ix_share_snapshots_share_id",
        ]:
            if _index_exists("share_snapshots", index_name):
                op.drop_index(index_name, table_name="share_snapshots")
        op.drop_table("share_snapshots")
    postgresql.ENUM(name="shareprivacylevelenum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="plancodeenum").drop(op.get_bind(), checkfirst=True)
