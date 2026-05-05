"""Phase 3: 合并 watchlist_items + focus_reasons 到 watchlists 表

Revision ID: 004
Revises: 003
Create Date: 2026-04-07 00:00:00.000000

对应 task 2.13：
- 新建 watchlists 表（UUID 主键，UNIQUE(user_id, stock_id)）
- 从 watchlist_items 迁移：id, user_id, stock_id, focus_reason
- 从 focus_reasons 补充 focus_reason（已有则保留）
- 标记 added_from_scenario / source_analysis_id（从 analyses 关联）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON, ENUM
import uuid

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


# 枚举类型
ADDED_FROM_SCENARIO_ENUM = "addedfromscenarioenum"


def upgrade() -> None:
    # === 1. 创建枚举类型 ===
    op.execute(
        f"CREATE TYPE {ADDED_FROM_SCENARIO_ENUM} AS ENUM "
        "('single_stock_check', 'pre_trade_check', 'post_trade_review')"
    )

    # === 2. 创建 watchlists 表 ===
    op.create_table(
        "watchlists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stock_id", sa.String(length=20), sa.ForeignKey("stocks.stock_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column(
            "focus_reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "added_from_scenario",
            ENUM("single_stock_check", "pre_trade_check", "post_trade_review", name=ADDED_FROM_SCENARIO_ENUM, create_type=False),
            nullable=True,
        ),
        sa.Column(
            "source_analysis_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "notify_on_events",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])
    op.create_index("ix_watchlists_stock_id", "watchlists", ["stock_id"])
    op.create_index("ix_watchlists_added_from_scenario", "watchlists", ["added_from_scenario"])
    op.create_index("ix_watchlists_source_analysis_id", "watchlists", ["source_analysis_id"])
    op.create_unique_constraint(
        "uq_watchlists_user_stock",
        "watchlists",
        ["user_id", "stock_id"],
    )

    # === 3. 数据迁移：watchlist_items -> watchlists ===
    _migrate_watchlist_items()

    # === 4. 数据迁移：focus_reasons 补充 focus_reason ===
    _migrate_focus_reasons()


def _migrate_watchlist_items():
    """将 watchlist_items 数据迁移到 watchlists"""

    op.execute("""
        INSERT INTO watchlists (
            id,
            user_id,
            stock_id,
            created_at,
            updated_at,
            focus_reason,
            notify_on_events
        )
        SELECT
            gen_random_uuid(),
            user_id,
            stock_id,
            created_at,
            updated_at,
            focus_reason,
            TRUE  -- 旧表无此字段，默认开启
        FROM watchlist_items wi
        ON CONFLICT (user_id, stock_id) DO NOTHING
    """)


def _migrate_focus_reasons():
    """从 focus_reasons 补充 focus_reason，更新 added_from_scenario / source_analysis_id

    逻辑：
    - 若 watchlists.focus_reason 为 NULL，用 focus_reasons.reason 填充
    - 通过 focus_reasons.analysis_id 关联 analyses -> analysis_tasks.id 获取 source_analysis_id
    - 通过 analyses.scenario 推断 added_from_scenario
    """

    # 步骤 1：用 focus_reasons.reason 填充 watchlists.focus_reason（已有则跳过）
    op.execute("""
        UPDATE watchlists w
        SET focus_reason = fr.reason,
            updated_at = NOW()
        FROM focus_reasons fr
        WHERE
            w.user_id = fr.user_id
            AND w.stock_id = fr.stock_id
            AND w.focus_reason IS NULL
    """)

    # 步骤 2：通过 analyses -> analysis_tasks 关联，补充 source_analysis_id 和 added_from_scenario
    # 注意：analyses 表在迁移 007 才会重命名为 *_legacy，此处仍用原名
    op.execute("""
        UPDATE watchlists w
        SET
            source_analysis_id = at.id,
            added_from_scenario = LOWER(ac.scenario::text)::addedfromscenarioenum,
            updated_at = NOW()
        FROM focus_reasons fr
        JOIN analyses ac
            ON ac.id = fr.analysis_id
        JOIN analysis_tasks at
            ON  at.user_id    = ac.user_id
            AND at.stock_id   = ac.stock_id
            AND at.created_at = ac.created_at
        WHERE
            w.user_id = fr.user_id
            AND w.stock_id = fr.stock_id
            AND w.source_analysis_id IS NULL
    """)


def downgrade() -> None:
    # 清理迁移的数据（仅删除 watchlists 表，保留旧表供回滚使用）
    op.drop_table("watchlists")
    op.execute(f"DROP TYPE IF EXISTS {ADDED_FROM_SCENARIO_ENUM}")
