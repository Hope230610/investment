from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.user import User
from src.schemas.common import ErrorDetail, ErrorResponse, Message
from src.schemas.portfolio import (
    HoldingCreate,
    HoldingItem,
    HoldingUpdate,
    PortfolioOverview,
    PortfolioSummary,
    TransactionCreate,
    TransactionItem,
    TransactionUpdate,
)
from src.services.portfolio_service import PortfolioService


router = APIRouter()


def api_error(status_code: int, code: str, message: str, request: Optional[Request] = None) -> JSONResponse:
    request_id = request.headers.get("x-request-id") if request else None
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, request_id=request_id))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _parse_uuid(value: str, code: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(code) from exc


@router.get("/holdings", response_model=list[HoldingItem])
async def list_holdings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PortfolioService(db).list_holdings(current_user.id)


@router.post("/holdings", response_model=HoldingItem)
async def create_holding(
    payload: HoldingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PortfolioService(db).create_holding(current_user.id, payload)


@router.put("/holdings/{holding_id}", response_model=HoldingItem)
async def update_holding(
    holding_id: str,
    payload: HoldingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_id = _parse_uuid(holding_id, "INVALID_HOLDING_ID")
    except ValueError:
        return api_error(400, "INVALID_HOLDING_ID", "无效的持仓 ID", request)
    item = PortfolioService(db).update_holding(current_user.id, parsed_id, payload)
    if not item:
        return api_error(404, "HOLDING_NOT_FOUND", "持仓记录未找到", request)
    return item


@router.delete("/holdings/{holding_id}", response_model=Message)
async def delete_holding(
    holding_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_id = _parse_uuid(holding_id, "INVALID_HOLDING_ID")
    except ValueError:
        return api_error(400, "INVALID_HOLDING_ID", "无效的持仓 ID", request)
    if not PortfolioService(db).delete_holding(current_user.id, parsed_id):
        return api_error(404, "HOLDING_NOT_FOUND", "持仓记录未找到", request)
    return Message(message="持仓记录已删除")


@router.get("/transactions", response_model=list[TransactionItem])
async def list_transactions(
    stock_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PortfolioService(db).list_transactions(current_user.id, stock_id=stock_id, limit=limit)


@router.post("/transactions", response_model=TransactionItem)
async def create_transaction(
    payload: TransactionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return PortfolioService(db).create_transaction(current_user.id, payload)
    except ValueError as exc:
        if str(exc) == "TRANSACTION_REFERENCE_NOT_FOUND":
            return api_error(404, "TRANSACTION_REFERENCE_NOT_FOUND", "Transaction reference not found", request)
        raise


@router.put("/transactions/{transaction_id}", response_model=TransactionItem)
async def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_id = _parse_uuid(transaction_id, "INVALID_TRANSACTION_ID")
    except ValueError:
        return api_error(400, "INVALID_TRANSACTION_ID", "无效的交易记录 ID", request)
    try:
        item = PortfolioService(db).update_transaction(current_user.id, parsed_id, payload)
    except ValueError as exc:
        if str(exc) == "TRANSACTION_REFERENCE_NOT_FOUND":
            return api_error(404, "TRANSACTION_REFERENCE_NOT_FOUND", "Transaction reference not found", request)
        raise
    if not item:
        return api_error(404, "TRANSACTION_NOT_FOUND", "交易记录未找到", request)
    return item


@router.delete("/transactions/{transaction_id}", response_model=Message)
async def delete_transaction(
    transaction_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_id = _parse_uuid(transaction_id, "INVALID_TRANSACTION_ID")
    except ValueError:
        return api_error(400, "INVALID_TRANSACTION_ID", "无效的交易记录 ID", request)
    if not PortfolioService(db).delete_transaction(current_user.id, parsed_id):
        return api_error(404, "TRANSACTION_NOT_FOUND", "交易记录未找到", request)
    return Message(message="交易记录已删除")


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PortfolioService(db).get_overview(current_user.id).summary


@router.get("/overview", response_model=PortfolioOverview)
async def get_portfolio_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PortfolioService(db).get_overview(current_user.id)
