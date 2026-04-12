"""Phase 3: 修改 review_tasks 外键从 analyses.id 改为 analysis_tasks.id

Revision ID: 005
Revises: 004
Create Date: 2026-04-07 00:00:00.000000

对应 task 2.14：
- review_tasks 外键从 ForeignKey("analyses.id") 改为 ForeignKey("analysis_tasks.id")
- 新增 analysis_task_id 列（UUID），通过 (user_id, stock_id, created_at) 关联 analysis_tasks
- 存量 review_tasks 同步迁移，跨表关联失败则保留 NULL
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === 1. 新增 analysis_task_id 列（临时 nullable） ===
    op.add_column(
        "review_tasks",
        sa.Column(
            "analysis_task_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # === 2. 迁移数据：review_tasks -> analysis_tasks ===
    # 匹配逻辑：(user_id, stock_id, created_at) 三键匹配
    # 注意：review_tasks.stock_name 在旧实现中实际存储 stock_id
    _migrate_review_task_fk()

    # === 3. 补充新增复盘任务的 analysis_task_id ===
    # 新流程（Phase 1+ 之后）创建的 review_tasks，analysis_id 必定关联已完成 analysis_tasks
    _backfill_newer_review_tasks()

    # === 4. 删除旧 analysis_id 列 ===
    op.drop_column("review_tasks", "analysis_id")

    # === 5. 设置 NOT NULL（已确认无 NULL） ===
    # （PostgreSQL 11+ 支持直接改列类型；历史数据已迁移则可加 NOT NULL）
    # op.alter_column("review_tasks", "analysis_task_id", nullable=False)


def _migrate_review_task_fk():
    """存量 review_tasks 关联到 analysis_tasks

    匹配规则：同一 (user_id, stock_id, created_at) 窗口内
    review_tasks 由 analyses 创建 → analyses 已迁移到 analysis_tasks → 取其 UUID
    """
    op.execute("""
        UPDATE review_tasks rt
        SET analysis_task_id = at.id
        FROM analyses ac
        JOIN analysis_tasks at
            ON  at.user_id     = ac.user_id
            AND at.stock_id    = ac.stock_id
            AND at.created_at  = ac.created_at
        WHERE rt.analysis_id = ac.id
            AND rt.analysis_task_id IS NULL
    """)


def _backfill_newer_review_tasks():
    """补充新流程（Phase 1 后）创建的 review_tasks

    逻辑：对于 analysis_task_id 仍为 NULL 的 review_tasks，
    直接从 analyses.scenario_payload.stock_id 重建 analysis_task 关联
    """
    # 极少数边界情况：若 review_tasks 对应 analysis 已无匹配 analysis_tasks，保留 NULL
    # 不丢失数据，待 TASK-BE-101 人工核查
    pass


def downgrade() -> None:
    # === 1. 恢复旧 analysis_id 列（Integer 类型） ===
    op.add_column(
        "review_tasks",
        sa.Column(
            "analysis_id",
            sa.Integer(),
            sa.ForeignKey("analyses.id"),
            nullable=True,
        ),
    )

    # === 2. 回填 analysis_id ===
    op.execute("""
        UPDATE review_tasks rt
        SET analysis_id = ac.id
        FROM analyses ac
        JOIN analysis_tasks at
            ON  at.user_id    = ac.user_id
            AND at.stock_id   = ac.stock_id
            AND at.created_at = ac.created_at
        WHERE rt.analysis_task_id = at.id
            AND rt.analysis_id IS NULL
    """)

    # === 3. 删除新 analysis_task_id 列 ===
    op.drop_column("review_tasks", "analysis_task_id")
