"""011: 为 analysis_results 新增证据结构字段

Revision ID: 011
Revises: 010
Create Date: 2026-04-24 00:00:00.000000

对应 p2-evidence-card 变更：
- DecisionCardV2 新增 4 个结构化字段：
  supporting_evidence, counter_evidence, invalidation_conditions, confidence_level
- 字段在服务层构造，不依赖 LLM；旧路径（DecisionCard）不受影响
"""
from alembic import op
import sqlalchemy as sa


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 为 analysis_results 新增 4 个证据结构字段
    # 已有数据：设置合理默认值（空列表 + medium 置信度），不影响旧分析结果展示
    op.add_column(
        "analysis_results",
        sa.Column("supporting_evidence", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "analysis_results",
        sa.Column("counter_evidence", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "analysis_results",
        sa.Column("invalidation_conditions", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "analysis_results",
        sa.Column("confidence_level", sa.String(length=20), nullable=False, server_default="medium"),
    )


def downgrade() -> None:
    op.drop_column("analysis_results", "confidence_level")
    op.drop_column("analysis_results", "invalidation_conditions")
    op.drop_column("analysis_results", "counter_evidence")
    op.drop_column("analysis_results", "supporting_evidence")
