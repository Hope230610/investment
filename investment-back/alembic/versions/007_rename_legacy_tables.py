"""Phase 3: 将旧表重命名为 *_legacy 后缀

Revision ID: 007
Revises: 006
Create Date: 2026-04-07 00:00:00.000000

对应 task 2.17：
- analyses           -> analyses_legacy
- analysis_reasons   -> analysis_reasons_legacy
- watchlist_items    -> watchlist_items_legacy
- focus_reasons      -> focus_reasons_legacy

重命名后，原接口在找不到表时应返回空结果（或友好提示），不报 500 错误。
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 按依赖顺序重命名（先叶子节点，再主表）

    # 1. watchlist_items（无外键依赖）
    op.execute("ALTER TABLE watchlist_items RENAME TO watchlist_items_legacy")

    # 2. focus_reasons（无外键依赖）
    op.execute("ALTER TABLE focus_reasons RENAME TO focus_reasons_legacy")

    # 3. analysis_reasons（FK 到 analyses_legacy，重命名前先清理约束）
    # FK 已在迁移 002 数据迁移完成后不再被查询，此处直接重命名表
    op.execute("ALTER TABLE analysis_reasons RENAME TO analysis_reasons_legacy")

    # 4. analyses（最后重命名）
    op.execute("ALTER TABLE analyses RENAME TO analyses_legacy")


def downgrade() -> None:
    # 按依赖顺序逆序恢复
    op.execute("ALTER TABLE analyses_legacy RENAME TO analyses")
    op.execute("ALTER TABLE analysis_reasons_legacy RENAME TO analysis_reasons")
    op.execute("ALTER TABLE focus_reasons_legacy RENAME TO focus_reasons")
    op.execute("ALTER TABLE watchlist_items_legacy RENAME TO watchlist_items")
