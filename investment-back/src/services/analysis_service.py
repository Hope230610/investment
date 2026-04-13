from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import uuid as uuid_lib

import structlog
from sqlalchemy.orm import Session

from src.models.analysis import Analysis as AnalysisModel
from src.models.analysis import AnalysisReason, AnalysisStatus
from src.models.stock import Stock as StockModel
from src.schemas.analysis import AnalysisCreate, AnalysisUpdate, AnalysisResult


logger = structlog.get_logger()

# 表路由清单：控制 API 走新表还是旧表
# beta 阶段：全量切换到新表
ANALYSIS_ROUTING = {"analysis": "new"}


def _is_valid_uuid(value: str) -> bool:
    """判断字符串是否为合法 UUID"""
    try:
        uuid_lib.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def _parse_analysis_id(analysis_id: str) -> tuple[str, Optional[int]]:
    """解析 analysis_id：返回 (id_type, id_value)

    迁移期兼容：同时接受 UUID 和 Integer。
    返回 (uuid, None) 表示 UUID 格式，(int_str, int_value) 表示 Integer 格式。
    """
    if _is_valid_uuid(analysis_id):
        return ("uuid", None)
    try:
        int_val = int(analysis_id)
        return ("int", int_val)
    except (ValueError, TypeError):
        return ("unknown", None)


class AnalysisService:
    """Persistence helpers for analysis records."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger.bind(service="analysis")

    def create_analysis(
        self, user_id: int, analysis_data: AnalysisCreate
    ) -> Union[AnalysisModel, Any]:
        """创建分析任务记录。

        根据 ANALYSIS_ROUTING["analysis"] 决定写入新表还是旧表：
        - "new": 写入 analysis_tasks（新路径），返回 AnalysisTask
        - "old": 写入 analyses（旧路径），返回 Analysis（旧路径兼容）
        """
        self.logger.info("creating_analysis", user_id=user_id, routing=ANALYSIS_ROUTING["analysis"])

        # 确保 stock 记录存在
        stock = self.db.query(StockModel).filter(
            StockModel.stock_id == analysis_data.stock_id
        ).first()
        if not stock:
            market = analysis_data.stock_id[:2].upper() if len(analysis_data.stock_id) >= 2 else "SZ"
            stock = StockModel(
                stock_id=analysis_data.stock_id,
                stock_name=analysis_data.stock_id,
                market=market,
            )
            self.db.add(stock)
            self.db.commit()

        if ANALYSIS_ROUTING.get("analysis") == "new":
            return self._create_analysis_task(user_id, analysis_data)
        return self._create_analysis_legacy(user_id, analysis_data)

    def _create_analysis_legacy(self, user_id: int, analysis_data: AnalysisCreate) -> AnalysisModel:
        """旧路径：写入 analyses_legacy 表"""
        analysis = AnalysisModel(
            user_id=user_id,
            stock_id=analysis_data.stock_id,
            scenario=analysis_data.scenario,
            status=AnalysisStatus.PROCESSING,
            scenario_payload=analysis_data.scenario_payload,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        self.logger.debug("analysis_created", analysis_id=analysis.id)
        return analysis

    def _create_analysis_task(self, user_id: int, analysis_data: AnalysisCreate) -> Any:
        """新路径：写入 analysis_tasks 表"""
        from src.models.analysis_task import AnalysisTask, AnalysisScenarioEnum, AnalysisStatusEnum
        from src.models.analysis import ReviewTask as ReviewTaskModel, ReviewTaskStatus

        task = AnalysisTask(
            id=uuid_lib.uuid4(),
            user_id=user_id,
            stock_id=analysis_data.stock_id,
            scenario=AnalysisScenarioEnum(analysis_data.scenario.value),
            status=AnalysisStatusEnum.PROCESSING,
            scenario_payload=analysis_data.scenario_payload,
            started_at=datetime.utcnow(),
            expired_at=datetime.utcnow() + timedelta(days=7),
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self.logger.debug("analysis_task_created", task_id=str(task.id))

        # 对于 post_trade_review，同步创建 ReviewTask，
        # 让用户提交后能在复盘记录页立即看到这条记录（Fix 3）
        if analysis_data.scenario.value == "post_trade_review":
            stock_name = ""
            stock = self.db.query(StockModel).filter(
                StockModel.stock_id == analysis_data.stock_id
            ).first()
            if stock:
                stock_name = stock.stock_name

            review_task = ReviewTaskModel(
                user_id=user_id,
                analysis_task_id=task.id,
                stock_name=stock_name or analysis_data.stock_id,
                scenario="post_trade_review",
                review_at=datetime.utcnow(),
                status=ReviewTaskStatus.PENDING,
            )
            self.db.add(review_task)
            self.db.commit()
            self.logger.info("review_task_created_sync", task_id=str(task.id))

        return task

    def update_analysis(
        self, analysis_id: int, user_id: int, update_data: AnalysisUpdate
    ) -> Optional[AnalysisModel]:
        analysis = self.db.query(AnalysisModel).filter(
            AnalysisModel.id == analysis_id,
            AnalysisModel.user_id == user_id,
        ).first()
        if not analysis:
            return None

        update_fields = update_data.dict(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(analysis, field, value)

        self.db.commit()
        self.db.refresh(analysis)
        self.logger.debug("analysis_updated", analysis_id=analysis.id)
        return analysis

    def get_analysis(self, analysis_id: int, user_id: int) -> Optional[AnalysisModel]:
        return self.db.query(AnalysisModel).filter(
            AnalysisModel.id == analysis_id,
            AnalysisModel.user_id == user_id,
        ).first()

    def get_user_analyses(
        self, user_id: int, scenario: Optional[str] = None, limit: int = 100
    ) -> List[AnalysisModel]:
        query = self.db.query(AnalysisModel).filter(AnalysisModel.user_id == user_id)
        if scenario:
            query = query.filter(AnalysisModel.scenario == scenario)
        return query.order_by(AnalysisModel.created_at.desc()).limit(limit).all()

    def mark_analysis_completed(
        self, analysis_id: int, user_id: int, result: AnalysisResult
    ) -> bool:
        analysis = self.get_analysis(analysis_id, user_id)
        if not analysis:
            self.logger.error("analysis_not_found", analysis_id=analysis_id)
            return False

        analysis.status = AnalysisStatus.READY
        analysis.headline = result.decision_card.headline_judgement
        analysis.decision_card = result.decision_card.model_dump(mode="json")
        analysis.fit_summary = result.fit_summary
        analysis.market_context = result.market_context.model_dump(mode="json")
        analysis.explanation_layer = result.explanation_layer.model_dump(mode="json")
        analysis.intervention = (
            result.intervention.model_dump(mode="json")
            if result.intervention
            else None
        )
        analysis.review_at = result.decision_card.review_at
        analysis.valid_until = result.decision_card.valid_until

        self.db.commit()
        self.logger.info("analysis_completed", analysis_id=analysis_id)
        return True

    def save_analysis_reasons(
        self, analysis_id: int, reasons: List[Dict[str, Any]]
    ) -> List[AnalysisReason]:
        saved: List[AnalysisReason] = []
        for reason_data in reasons:
            reason = AnalysisReason(
                analysis_id=analysis_id,
                text=reason_data["text"],
                order=reason_data.get("order", 0),
                mark_type=reason_data["mark_type"],
            )
            self.db.add(reason)
            saved.append(reason)

        self.db.commit()
        for reason in saved:
            self.db.refresh(reason)

        self.logger.debug("reasons_saved", count=len(saved), analysis_id=analysis_id)
        return saved

    def has_expired(self, analysis: AnalysisModel) -> bool:
        if analysis.valid_until:
            return datetime.now() > analysis.valid_until
        return False

    def get_recent_analyses(self, user_id: int, days: int = 30) -> List[AnalysisModel]:
        since_date = datetime.now() - timedelta(days=days)
        return (
            self.db.query(AnalysisModel)
            .filter(
                AnalysisModel.user_id == user_id,
                AnalysisModel.created_at >= since_date,
            )
            .order_by(AnalysisModel.created_at.desc())
            .all()
        )
