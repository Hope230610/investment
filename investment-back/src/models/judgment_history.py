"""判断质量历史记录模型

对应 judgment_history 表，记录用户每次复盘选择的判断质量选项，
用于聚合计算判断质量百分比和趋势。
"""
from datetime import datetime, date
from typing import Optional
import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db.session import Base


class JudgmentHistory(Base):
    """用户判断质量历史记录

    每日一条记录，upsert 模式（同一 user_id + judgment_date 覆盖）。
    "难以区分"选项不写入 judgment_score，但记录 is_hard_to_tall = True。
    """
    __tablename__ = "judgment_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    analysis_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 判断日期
    judgment_date = Column(Date, nullable=False)

    # 判断得分：0/50/100（"难以区分"不写此字段，写 is_hard_to_tell）
    judgment_score = Column(Integer, nullable=False)

    # 判断标签原文
    judgment_label = Column(String(50), nullable=False)

    # 是否选择了"难以区分"
    is_hard_to_tell = Column(Boolean, default=False, nullable=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="judgment_history")

    __table_args__ = (
        Index("ix_judgment_history_judgment_date", "judgment_date"),
        Index("ix_judgment_history_user_date", "user_id", "judgment_date", unique=True),
    )
