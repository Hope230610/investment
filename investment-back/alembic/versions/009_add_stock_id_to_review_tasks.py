"""009: 添加 stock_id 到 review_tasks 表

Revision ID: 009
Revises: 008
Create Date: 2026-04-14 00:00:00.000000

用于复盘表单预填股票信息。
原有 review_tasks 记录通过 JOIN analysis_tasks 回填 stock_id。
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 新增 nullable 列
    op.execute("""
        ALTER TABLE review_tasks ADD COLUMN stock_id VARCHAR(20);
    """)
    # 回填已有记录
    op.execute("""
        UPDATE review_tasks rt
        SET stock_id = at.stock_id
        FROM analysis_tasks at
        WHERE rt.analysis_task_id = at.id
          AND rt.stock_id IS NULL
    """)


def downgrade() -> None:
    op.drop_column("review_tasks", "stock_id")
