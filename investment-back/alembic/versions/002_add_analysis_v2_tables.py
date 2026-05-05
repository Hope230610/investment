"""Phase 1: 新增 analysis_tasks / analysis_results / behavior_interventions 表

Revision ID: 002
Revises: 001
Create Date: 2026-04-06 00:00:00.000000

对应基线 database_design.md 定义的 analysis_tasks / analysis_results / behavior_interventions 表。
存量数据迁移：在 upgrade() 中将 analyses 表数据迁移到新表。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON, ENUM
import uuid

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


# 枚举类型
INTERACTION_SCENARIO = "interactionscenario"
ANALYSIS_STATUS_ENUM = "analysisstatusv2"
OUTPUT_MARK_TYPE = "outputmarktype"
VALID_PERIOD_ENUM = "validperiodenum"
OUTPUT_TAG_ENUM = "outputtagenum"
BEHAVIOR_TYPE_ENUM = "behaviortypeenum"
SEVERITY_LEVEL_ENUM = "severitylevelenum"
INTERVENTION_ACTION_TAKEN_ENUM = "interventionactiontakenenum"


def upgrade() -> None:
    # === 1. 创建枚举类型 ===
    # interactionscenario is created by 001 and reused here. This project has
    # not had a production release yet, so 001 owns the canonical lowercase
    # enum labels required by the current application models.
    op.execute(f"CREATE TYPE {ANALYSIS_STATUS_ENUM} AS ENUM ('processing', 'partial_ready', 'ready', 'expired', 'failed')")
    op.execute(f"CREATE TYPE {VALID_PERIOD_ENUM} AS ENUM ('short', 'medium', 'long')")
    op.execute(f"CREATE TYPE {OUTPUT_TAG_ENUM} AS ENUM ('data_fact', 'model_inference', 'uncertainty')")
    op.execute(f"CREATE TYPE {BEHAVIOR_TYPE_ENUM} AS ENUM ('chasing_rise', 'panic_sell', 'frequent_trading')")
    op.execute(f"CREATE TYPE {SEVERITY_LEVEL_ENUM} AS ENUM ('low', 'medium', 'high')")
    op.execute(f"CREATE TYPE {INTERVENTION_ACTION_TAKEN_ENUM} AS ENUM ('continued', 'delayed', 'cancelled', 'logged_only')")

    # === 2. 创建 analysis_tasks 表 ===
    op.create_table(
        "analysis_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stock_id", sa.String(20), sa.ForeignKey("stocks.stock_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("scenario", ENUM("single_stock_check", "pre_trade_check", "post_trade_review", name=INTERACTION_SCENARIO, create_type=False), nullable=False),
        sa.Column("status", ENUM("processing", "partial_ready", "ready", "expired", "failed", name=ANALYSIS_STATUS_ENUM, create_type=False), nullable=False, server_default="processing"),
        sa.Column("user_profile_snapshot", JSON, nullable=True),
        sa.Column("scenario_payload", JSON, nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("expired_at", sa.DateTime(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_analysis_tasks_user_id", "analysis_tasks", ["user_id"])
    op.create_index("ix_analysis_tasks_stock_id", "analysis_tasks", ["stock_id"])
    op.create_index("ix_analysis_tasks_scenario", "analysis_tasks", ["scenario"])
    op.create_index("ix_analysis_tasks_status", "analysis_tasks", ["status"])
    op.create_index("ix_analysis_tasks_expired_at", "analysis_tasks", ["expired_at"])

    # === 3. 创建 analysis_results 表 ===
    op.create_table(
        "analysis_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("analysis_task_id", UUID(as_uuid=True), sa.ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("headline_judgement", sa.Text(), nullable=False),
        sa.Column("key_reason_summary", JSON, nullable=False, server_default="[]"),
        sa.Column("user_fit_summary", JSON, nullable=False, server_default='{"fit":"","unfit":""}'),
        sa.Column("next_step_actions", JSON, nullable=False, server_default="[]"),
        sa.Column("primary_risks", sa.Text(), nullable=False),
        sa.Column("review_at", sa.DateTime(), nullable=False),
        sa.Column("intervention", JSON, nullable=True),
        sa.Column("fit_summary", sa.Text(), nullable=True),
        sa.Column("market_context", JSON, nullable=True),
        sa.Column("explanation_layer", JSON, nullable=True),
        sa.Column("detail_panels", JSON, nullable=True),
        sa.Column("output_tags", JSON, nullable=False, server_default="[]"),
        sa.Column("valid_period", ENUM("short", "medium", "long", name=VALID_PERIOD_ENUM, create_type=False), nullable=False, server_default="medium"),
    )
    op.create_index("ix_analysis_results_task_id", "analysis_results", ["analysis_task_id"], unique=True)

    # === 4. 创建 behavior_interventions 表 ===
    op.create_table(
        "behavior_interventions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("analysis_task_id", UUID(as_uuid=True), sa.ForeignKey("analysis_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("behavior_type", ENUM("chasing_rise", "panic_sell", "frequent_trading", name=BEHAVIOR_TYPE_ENUM, create_type=False), nullable=False),
        sa.Column("severity", ENUM("low", "medium", "high", name=SEVERITY_LEVEL_ENUM, create_type=False), nullable=False),
        sa.Column("cooldown_started_at", sa.DateTime(), nullable=True),
        sa.Column("cooldown_ended_at", sa.DateTime(), nullable=True),
        sa.Column("cooldown_questions", JSON, nullable=True),
        sa.Column("user_acknowledged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("action_taken", ENUM("continued", "delayed", "cancelled", "logged_only", name=INTERVENTION_ACTION_TAKEN_ENUM, create_type=False), nullable=True),
    )
    op.create_index("ix_behavior_interventions_user_id", "behavior_interventions", ["user_id"])
    op.create_index("ix_behavior_interventions_behavior_type", "behavior_interventions", ["behavior_type"])
    op.create_index("ix_behavior_interventions_created_at", "behavior_interventions", ["created_at"])

    # === 5. 存量数据迁移：analyses -> analysis_tasks + analysis_results ===
    # 从旧 analyses 表读取数据，插入到新表
    _migrate_analyses_data()


def _migrate_analyses_data():
    """将 analyses 表存量数据迁移到 analysis_tasks + analysis_results"""

    # 迁移 analyses -> analysis_tasks（处理 null expired_at）
    op.execute("""
        INSERT INTO analysis_tasks (
            id, user_id, stock_id, created_at, updated_at,
            scenario, status, user_profile_snapshot, scenario_payload,
            started_at, completed_at, expired_at, error_message
        )
        SELECT
            gen_random_uuid(),
            user_id,
            stock_id,
            created_at,
            updated_at,
            LOWER(scenario::text)::interactionscenario,
            LOWER(status::text)::analysisstatusv2,
            NULL,  -- user_profile_snapshot 历史数据不可用
            scenario_payload,
            CASE WHEN LOWER(status::text) IN ('ready', 'expired', 'failed') THEN updated_at ELSE NULL END,
            CASE WHEN LOWER(status::text) IN ('ready', 'expired') THEN updated_at ELSE NULL END,
            COALESCE(valid_until, created_at + INTERVAL '7 days'),  -- 兜底 7 天有效期
            NULL  -- error_message 历史数据不可用
        FROM analyses
        ON CONFLICT DO NOTHING
    """)

    # 迁移 analyses -> analysis_results（只迁移有 headline 的记录）
    op.execute("""
        INSERT INTO analysis_results (
            id, analysis_task_id, created_at,
            headline_judgement, key_reason_summary, user_fit_summary,
            next_step_actions, primary_risks, review_at,
            intervention, fit_summary, market_context,
            explanation_layer, detail_panels, output_tags, valid_period
        )
        SELECT
            gen_random_uuid(),
            at.id,
            ac.created_at,
            COALESCE(ac.headline, '（无结论）'),
            COALESCE(
                (SELECT jsonb_agg(jsonb_build_object('text', text, 'mark_type', LOWER(mark_type::text)))
                 FROM analysis_reasons ar2 WHERE ar2.analysis_id = ac.id),
                '[]'::jsonb
            ),  -- key_reason_summary from analysis_reasons
            jsonb_build_object('fit', COALESCE(ac.fit_summary, ''), 'unfit', ''),
            '[]'::jsonb,  -- next_step_actions 历史数据不可用
            '',  -- primary_risks 历史数据不可用
            COALESCE(ac.review_at, ac.valid_until, ac.created_at + INTERVAL '7 days'),
            ac.intervention,
            ac.fit_summary,
            ac.market_context,
            ac.explanation_layer,
            NULL,  -- detail_panels 历史数据不可用
            '[]'::jsonb,  -- output_tags 历史数据不可用
            'medium'::validperiodenum
        FROM analyses ac
        JOIN analysis_tasks at
            ON at.user_id = ac.user_id
            AND at.stock_id = ac.stock_id
            AND at.created_at = ac.created_at
        WHERE ac.headline IS NOT NULL
        ON CONFLICT (analysis_task_id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("behavior_interventions")
    op.drop_table("analysis_results")
    op.drop_table("analysis_tasks")
    op.execute(f"DROP TYPE IF EXISTS {INTERVENTION_ACTION_TAKEN_ENUM}")
    op.execute(f"DROP TYPE IF EXISTS {SEVERITY_LEVEL_ENUM}")
    op.execute(f"DROP TYPE IF EXISTS {BEHAVIOR_TYPE_ENUM}")
    op.execute(f"DROP TYPE IF EXISTS {OUTPUT_TAG_ENUM}")
    op.execute(f"DROP TYPE IF EXISTS {VALID_PERIOD_ENUM}")
    op.execute(f"DROP TYPE IF EXISTS {ANALYSIS_STATUS_ENUM}")
