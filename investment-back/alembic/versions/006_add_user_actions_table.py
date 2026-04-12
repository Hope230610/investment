"""Phase 3: 创建 user_actions 表

Revision ID: 006
Revises: 005
Create Date: 2026-04-07 00:00:00.000000

对应 task 2.15：
- 创建 user_actions 表（UUID 主键）
- 记录用户关键操作埋点（scenario_selected / analysis_submitted / ...）
- 为 Phase 3 后端 API 提供用户行为追溯能力
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


# 枚举类型
USER_ACTION_TYPE_ENUM = "useractiontypeenum"


def upgrade() -> None:
    # === 1. 创建枚举类型 ===
    op.execute(
        f"CREATE TYPE {USER_ACTION_TYPE_ENUM} AS ENUM "
        "('scenario_selected', 'analysis_submitted', "
        "'behavior_intervention_shown', 'cooldown_started', 'review_task_completed')"
    )

    # === 2. 创建 user_actions 表 ===
    op.create_table(
        "user_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "action_type",
            sa.Enum(
                "scenario_selected",
                "analysis_submitted",
                "behavior_intervention_shown",
                "cooldown_started",
                "review_task_completed",
                name=USER_ACTION_TYPE_ENUM,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("action_payload", JSON, nullable=True),
        sa.Column("stock_id", sa.String(length=20), nullable=True),
        sa.Column("analysis_task_id", UUID(as_uuid=True), nullable=True),
        sa.Column("page_path", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index("ix_user_actions_user_id", "user_actions", ["user_id"])
    op.create_index("ix_user_actions_action_type", "user_actions", ["action_type"])
    op.create_index("ix_user_actions_created_at", "user_actions", ["created_at"])
    op.create_index("ix_user_actions_stock_id", "user_actions", ["stock_id"])
    op.create_index("ix_user_actions_analysis_task_id", "user_actions", ["analysis_task_id"])


def downgrade() -> None:
    op.drop_table("user_actions")
    op.execute(f"DROP TYPE IF EXISTS {USER_ACTION_TYPE_ENUM}")
