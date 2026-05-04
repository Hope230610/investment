from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid as uuid_lib

import structlog
from sqlalchemy.orm import Session

from src.models.stock import Stock as StockModel
from src.schemas.analysis import AnalysisCreate, AnalysisUpdate, AnalysisResult


logger = structlog.get_logger()


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
    ) -> Any:
        """创建分析任务记录（仅写入 analysis_tasks 表）。

        ANALYSIS_ROUTING["analysis"] 已废弃，旧路径（analyses 表）已停止使用。
        """
        self.logger.info("creating_analysis", user_id=user_id, routing="new")

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

        return self._create_analysis_task(user_id, analysis_data)

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
        # 但如果携带了 pending_review_task_id，说明是从 ReviewsPage 入口来的，
        # 原始 reminder 已在 ResultPage 被完成，不创建新 ReviewTask
        scenario_payload = analysis_data.scenario_payload or {}
        skip_review_task = scenario_payload.get("pending_review_task_id")
        if analysis_data.scenario.value == "post_trade_review" and not skip_review_task:
            stock_name = ""
            stock = self.db.query(StockModel).filter(
                StockModel.stock_id == analysis_data.stock_id
            ).first()
            if stock:
                stock_name = stock.stock_name

            review_task = ReviewTaskModel(
                user_id=user_id,
                analysis_task_id=task.id,
                stock_id=analysis_data.stock_id,
                stock_name=stock_name or analysis_data.stock_id,
                scenario="post_trade_review",
                review_at=datetime.utcnow(),
                status=ReviewTaskStatus.PENDING,
            )
            self.db.add(review_task)
            self.db.commit()
            self.logger.info("review_task_created_sync", task_id=str(task.id))

        return task

    def get_analysis(self, analysis_id: int, user_id: int) -> None:
        """Legacy stub — not used. get_analysis in API uses _get_analysis_from_new_tables."""
        return None

    def get_user_analyses(
        self, user_id: int, scenario: Optional[str] = None, limit: int = 100
    ) -> List[Any]:
        """Legacy stub — returns empty. Records page uses _get_analysis_records_from_new_tables."""
        return []

    def mark_analysis_completed(
        self, analysis_id: int, user_id: int, result: AnalysisResult
    ) -> bool:
        """Legacy stub — result is written by tasks.py::run_analysis_job."""
        return True

    def save_analysis_reasons(
        self, analysis_id: int, reasons: List[Dict[str, Any]]
    ) -> List[Any]:
        """Legacy stub — reason summary is written by tasks.py::run_analysis_job."""
        return []

    def has_expired(self, analysis: Any) -> bool:
        """Legacy stub."""
        return False

    def get_recent_analyses(self, user_id: int, days: int = 30) -> List[Any]:
        """返回用户近 N 天最新分析记录（用于行为干预判断）。

        新路径：从 analysis_tasks + analysis_results 查询，
        仅取 headline_judgement 用于情绪/意图关键词判断。
        """
        from src.models.analysis_task import AnalysisTask, AnalysisStatusEnum
        from src.models.analysis_result import AnalysisResult

        since_date = datetime.utcnow() - timedelta(days=days)
        tasks = (
            self.db.query(AnalysisTask)
            .filter(
                AnalysisTask.user_id == user_id,
                AnalysisTask.created_at >= since_date,
                AnalysisTask.status.in_([
                    AnalysisStatusEnum.READY,
                    AnalysisStatusEnum.PARTIAL_READY,
                ]),
            )
            .order_by(AnalysisTask.created_at.desc())
            .limit(10)
            .all()
        )
        results = []
        for task in tasks:
            r = self.db.query(AnalysisResult).filter(
                AnalysisResult.analysis_task_id == task.id
            ).first()
            # intervention_service checks item.get("headline") so use dict shape
            results.append({"headline": r.headline_judgement if r else ""})
        return results
