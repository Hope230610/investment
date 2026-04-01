from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from src.db.session import get_db
from src.schemas.analysis import AnalysisRecord
from src.api.deps import get_current_user
import structlog
from src.services.analysis_service import AnalysisService

router = APIRouter()
logger = structlog.get_logger()

# 初始化服务
def get_analysis_service(db: Session = Depends(get_db)):
    return AnalysisService(db)

@router.get("", response_model=List[AnalysisRecord])
async def get_analysis_records(
    scenario: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取分析记录"""
    logger.info("get_analysis_records", user_id=current_user.id)

    analysis_service = AnalysisService(db)
    analyses = analysis_service.get_user_analyses(
        current_user.id, scenario, limit
    )

    records = []
    for analysis in analyses:
        stock_name = "未知股票"
        from src.models.stock import Stock as StockModel
        stock = db.query(StockModel).filter(StockModel.stock_id == analysis.stock_id).first()
        if stock:
            stock_name = stock.stock_name

        records.append(AnalysisRecord(
            id=analysis.id,
            scenario=analysis.scenario.value,
            stock_id=analysis.stock_id,
            stock_name=stock_name,
            created_at=analysis.created_at,
            status=analysis.status,
            headline=analysis.headline
        ))

    logger.debug("records_count", count=len(records))
    return records
