"""Phase 2: 新建 emotion_history 和 judgment_history 表

Revision ID: 008
Revises: 007
Create Date: 2026-04-12 00:00:00.000000

对应 Phase 2 后端接入：
- emotion_history: 用户每日情绪评分记录（1-5），用于 sparkline
- judgment_history: 用户每次复盘的判断质量记录，用于聚合百分比和趋势
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. emotion_history 表
    op.execute("""
        CREATE TABLE emotion_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            analysis_task_id UUID REFERENCES analysis_tasks(id) ON DELETE SET NULL,
            recorded_date DATE NOT NULL,
            emotion_level INTEGER NOT NULL,
            intent VARCHAR(50),
            trigger_reason VARCHAR(100),
            created_at TIMESTAMP DEFAULT now() NOT NULL,
            UNIQUE (user_id, recorded_date)
        )
    """)
    op.execute("CREATE INDEX ix_emotion_history_user_id ON emotion_history(user_id)")
    op.execute("CREATE INDEX ix_emotion_history_recorded_date ON emotion_history(recorded_date)")

    # 2. judgment_history 表
    op.execute("""
        CREATE TABLE judgment_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            analysis_task_id UUID REFERENCES analysis_tasks(id) ON DELETE SET NULL,
            judgment_date DATE NOT NULL,
            judgment_score INTEGER NOT NULL,
            judgment_label VARCHAR(50) NOT NULL,
            is_hard_to_tell BOOLEAN DEFAULT false NOT NULL,
            created_at TIMESTAMP DEFAULT now() NOT NULL,
            UNIQUE (user_id, judgment_date)
        )
    """)
    op.execute("CREATE INDEX ix_judgment_history_user_id ON judgment_history(user_id)")
    op.execute("CREATE INDEX ix_judgment_history_judgment_date ON judgment_history(judgment_date)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS judgment_history")
    op.execute("DROP TABLE IF EXISTS emotion_history")
