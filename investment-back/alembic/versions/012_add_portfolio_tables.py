"""012: add portfolio holdings and transactions

Revision ID: 012
Revises: 011
Create Date: 2026-05-04 00:00:00.000000
"""
from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "012"
down_revision = "011"
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
    transaction_side = postgresql.ENUM("buy", "sell", name="transactionside")
    transaction_side.create(op.get_bind(), checkfirst=True)
    transaction_side_column = postgresql.ENUM("buy", "sell", name="transactionside", create_type=False)

    if not _table_exists("holdings"):
        op.create_table(
            "holdings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("stock_id", sa.String(length=20), nullable=False),
            sa.Column("stock_name", sa.String(length=100), nullable=False),
            sa.Column("market", sa.String(length=10), nullable=False),
            sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("cost_price", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("current_price", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("position_updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["stock_id"], ["stocks.stock_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _assert_columns(
        "holdings",
        {
            "id",
            "user_id",
            "stock_id",
            "stock_name",
            "market",
            "quantity",
            "cost_price",
            "current_price",
            "note",
            "position_updated_at",
            "created_at",
            "updated_at",
        },
    )
    _create_index_once("ix_holdings_user_id", "holdings", ["user_id"])
    _create_index_once("ix_holdings_stock_id", "holdings", ["stock_id"])
    _create_index_once("ix_holdings_user_stock", "holdings", ["user_id", "stock_id"], unique=True)

    if not _table_exists("transactions"):
        op.create_table(
            "transactions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("stock_id", sa.String(length=20), nullable=False),
            sa.Column("stock_name", sa.String(length=100), nullable=False),
            sa.Column("market", sa.String(length=10), nullable=False),
            sa.Column("side", transaction_side_column, nullable=False),
            sa.Column("price", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("traded_at", sa.DateTime(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("analysis_task_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("pre_trade_check_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("review_task_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["analysis_task_id"], ["analysis_tasks.id"]),
            sa.ForeignKeyConstraint(["pre_trade_check_id"], ["analysis_tasks.id"]),
            sa.ForeignKeyConstraint(["review_task_id"], ["review_tasks.id"]),
            sa.ForeignKeyConstraint(["stock_id"], ["stocks.stock_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _assert_columns(
        "transactions",
        {
            "id",
            "user_id",
            "stock_id",
            "stock_name",
            "market",
            "side",
            "price",
            "quantity",
            "traded_at",
            "reason",
            "analysis_task_id",
            "pre_trade_check_id",
            "review_task_id",
            "created_at",
            "updated_at",
        },
    )
    _create_index_once("ix_transactions_user_id", "transactions", ["user_id"])
    _create_index_once("ix_transactions_stock_id", "transactions", ["stock_id"])
    _create_index_once("ix_transactions_user_stock", "transactions", ["user_id", "stock_id"])
    _create_index_once("ix_transactions_user_traded_at", "transactions", ["user_id", "traded_at"])


def downgrade() -> None:
    if _table_exists("transactions"):
        for index_name in [
            "ix_transactions_user_traded_at",
            "ix_transactions_user_stock",
            "ix_transactions_stock_id",
            "ix_transactions_user_id",
        ]:
            if _index_exists("transactions", index_name):
                op.drop_index(index_name, table_name="transactions")
        op.drop_table("transactions")
    if _table_exists("holdings"):
        for index_name in [
            "ix_holdings_user_stock",
            "ix_holdings_stock_id",
            "ix_holdings_user_id",
        ]:
            if _index_exists("holdings", index_name):
                op.drop_index(index_name, table_name="holdings")
        op.drop_table("holdings")
    postgresql.ENUM(name="transactionside").drop(op.get_bind(), checkfirst=True)
