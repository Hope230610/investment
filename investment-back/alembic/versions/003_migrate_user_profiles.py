"""Phase 2: 精简 user_profiles 废弃字段 + 迁移干预历史到独立表

Revision ID: 003
Revises: 002
Create Date: 2026-04-06 00:00:00.000000

对应 tasks 2.8 / 2.9 / 2.10：
- 2.8: 从 UserProfile 模型移除 investment_goals / portfolio_size / preferred_sectors
- 2.9: Alembic 迁移清理 user_profiles 废弃字段（含快照备份步骤说明）
- 2.10: 将 analyses.intervention JSON 数据迁移到 behavior_interventions 表
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


# 枚举类型（已在 002 创建，此处仅用于引用）
BEHAVIOR_TYPE_ENUM = "behaviortypeenum"
SEVERITY_LEVEL_ENUM = "severitylevelenum"


def upgrade() -> None:
    # === Phase 2a: user_profiles 废弃字段清理 ===

    # 【备份提示】执行以下命令在运行此迁移前备份废弃字段数据：
    #   pg_dump -t user_profiles --data-only -a -c ... > user_profiles_backup.sql
    # 备份文件不提交到代码库。

    # 1. 快照备份：SELECT id, user_id, investment_goals, portfolio_size, preferred_sectors
    #    INTO user_profiles_backup FROM user_profiles WHERE investment_goals IS NOT NULL ...;
    # 此步骤由 DBA 在生产环境手动执行后再运行 alembic upgrade。

    # 2. 删除废弃字段（可空列，直接删除）
    op.drop_column("user_profiles", "investment_goals")
    op.drop_column("user_profiles", "portfolio_size")
    op.drop_column("user_profiles", "preferred_sectors")

    # === Phase 2b: 迁移 analyses.intervention JSON 到 behavior_interventions ===
    _migrate_behavior_interventions()


def _migrate_behavior_interventions():
    """将 analyses.intervention JSON 数据迁移到独立的 behavior_interventions 表"""

    # 从 analyses 表读取非空的 intervention JSON，插入到 behavior_interventions
    # analyses.intervention JSON 结构：
    #   { "behavior_type": "chasing_rise" | "panic_sell" | "frequent_trading",
    #     "severity": "low" | "medium" | "high",
    #     "questions": ["...", "..."] }
    # 关联到 analysis_tasks：取同一 (user_id, stock_id, created_at) 的 analysis_task.id
    op.execute("""
        INSERT INTO behavior_interventions (
            id,
            user_id,
            analysis_task_id,
            created_at,
            behavior_type,
            severity,
            cooldown_questions,
            user_acknowledged
        )
        SELECT
            gen_random_uuid(),
            ac.user_id,
            at.id,
            ac.created_at,
            (ac.intervention::jsonb ->> 'behavior_type')::behaviortypeenum,
            (ac.intervention::jsonb ->> 'severity')::severitylevelenum,
            ac.intervention::jsonb -> 'questions',
            FALSE  -- 历史数据无用户确认记录
        FROM analyses ac
        LEFT JOIN analysis_tasks at
            ON  at.user_id   = ac.user_id
            AND at.stock_id  = ac.stock_id
            AND at.created_at = ac.created_at
        WHERE ac.intervention IS NOT NULL
            AND ac.intervention::jsonb != 'null'::jsonb
            AND ac.intervention::jsonb ? 'behavior_type'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # 2b: 从 behavior_interventions 删除迁移记录
    op.execute("DELETE FROM behavior_interventions WHERE analysis_task_id IS NOT NULL")

    # 2a: 恢复 user_profiles 废弃字段
    op.add_column("user_profiles",
        sa.Column("investment_goals", sa.String(length=255), nullable=True))
    op.add_column("user_profiles",
        sa.Column("portfolio_size", sa.String(length=50), nullable=True))
    op.add_column("user_profiles",
        sa.Column("preferred_sectors", sa.JSON(), nullable=True))
