"""010: normalize watchlists.added_from_scenario enum values

Revision ID: 010
Revises: 009
Create Date: 2026-04-21 00:00:00.000000
"""

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            current_labels text[];
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'addedfromscenarioenum'
            ) THEN
                CREATE TYPE addedfromscenarioenum AS ENUM (
                    'single_stock_check',
                    'pre_trade_check',
                    'post_trade_review'
                );
                RETURN;
            END IF;

            SELECT array_agg(e.enumlabel ORDER BY e.enumsortorder)
            INTO current_labels
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'addedfromscenarioenum';

            IF current_labels = ARRAY[
                'single_stock_check',
                'pre_trade_check',
                'post_trade_review'
            ] THEN
                RETURN;
            END IF;

            CREATE TYPE addedfromscenarioenum_new AS ENUM (
                'single_stock_check',
                'pre_trade_check',
                'post_trade_review'
            );

            ALTER TABLE watchlists
            ALTER COLUMN added_from_scenario
            TYPE addedfromscenarioenum_new
            USING (
                CASE added_from_scenario::text
                    WHEN 'single_stock_check' THEN 'single_stock_check'
                    WHEN 'pre_trade_check' THEN 'pre_trade_check'
                    WHEN 'post_trade_review' THEN 'post_trade_review'
                    ELSE NULL
                END
            )::addedfromscenarioenum_new;

            DROP TYPE addedfromscenarioenum;
            ALTER TYPE addedfromscenarioenum_new RENAME TO addedfromscenarioenum;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'addedfromscenarioenum'
            ) THEN
                CREATE TYPE addedfromscenarioenum_old AS ENUM (
                    'analysis_result',
                    'manual',
                    'scenario'
                );

                ALTER TABLE watchlists
                ALTER COLUMN added_from_scenario
                TYPE addedfromscenarioenum_old
                USING (
                    CASE added_from_scenario::text
                        WHEN 'single_stock_check' THEN 'scenario'
                        WHEN 'pre_trade_check' THEN 'scenario'
                        WHEN 'post_trade_review' THEN 'scenario'
                        ELSE NULL
                    END
                )::addedfromscenarioenum_old;

                DROP TYPE addedfromscenarioenum;
                ALTER TYPE addedfromscenarioenum_old RENAME TO addedfromscenarioenum;
            END IF;
        END $$;
        """
    )
