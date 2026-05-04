"""Prepare the dedicated E2E database.

This script is intentionally destructive for one test user only. It refuses to
run unless the environment is clearly non-production and the database name looks
like a test/e2e database.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_settings  # noqa: E402
from src.db.session import Base, SessionLocal, engine, ensure_database_exists  # noqa: E402
from src.models.analysis import Analysis, AnalysisReason, ReviewTask  # noqa: E402
from src.models.analysis_task import AnalysisTask  # noqa: E402
from src.models.analysis_result import AnalysisResult  # noqa: E402
from src.models.behavior_intervention import BehaviorIntervention  # noqa: E402
from src.models.emotion_history import EmotionHistory  # noqa: E402
from src.models.judgment_history import JudgmentHistory  # noqa: E402
from src.models.stock import Stock  # noqa: E402
from src.models.user import (  # noqa: E402
    BehaviorTag,
    ExperienceLevel,
    HoldingHorizon,
    RiskTolerance,
    User,
    UserProfile,
)
from src.models.user_action import UserAction  # noqa: E402
from src.models.watchlist import FocusReason, WatchlistItem  # noqa: E402
from src.models.watchlist_v2 import Watchlist  # noqa: E402

E2E_STOCKS = [
    {"stock_id": "SH600519", "stock_name": "贵州茅台", "market": "SH", "industry": "白酒", "pe_ratio": 20.97, "pb_ratio": 6.40},
    {"stock_id": "SZ002594", "stock_name": "比亚迪", "market": "SZ", "industry": "汽车", "pe_ratio": 28.30, "pb_ratio": 5.10},
    {"stock_id": "SZ300750", "stock_name": "宁德时代", "market": "SZ", "industry": "电池", "pe_ratio": 24.80, "pb_ratio": 4.20},
    {"stock_id": "SH600036", "stock_name": "招商银行", "market": "SH", "industry": "银行", "pe_ratio": 6.50, "pb_ratio": 0.95},
    {"stock_id": "SZ000001", "stock_name": "平安银行", "market": "SZ", "industry": "银行", "pe_ratio": 5.80, "pb_ratio": 0.72},
    {"stock_id": "SH601012", "stock_name": "隆基绿能", "market": "SH", "industry": "光伏", "pe_ratio": 18.60, "pb_ratio": 1.45},
    {"stock_id": "SH600900", "stock_name": "长江电力", "market": "SH", "industry": "电力", "pe_ratio": 22.10, "pb_ratio": 3.10},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset and seed the E2E test user data.")
    parser.add_argument("--username", default="testuser")
    parser.add_argument("--password", default="testpassword123")
    parser.add_argument("--skip-reset", action="store_true", help="Only seed user/stocks; do not delete existing E2E state.")
    return parser.parse_args()


def assert_safe_environment() -> None:
    settings = get_settings()
    url = make_url(settings.DATABASE_URL)
    db_name = (url.database or "").lower()
    env = settings.ENVIRONMENT.lower()

    safe_env = env in {"development", "dev", "test", "testing", "e2e"}
    safe_db = "test" in db_name or "e2e" in db_name

    if not settings.DEBUG or not safe_env or not safe_db:
        raise SystemExit(
            "[E2E DB GUARD] Refusing to prepare database. "
            f"DEBUG={settings.DEBUG}, ENVIRONMENT={settings.ENVIRONMENT}, database={url.database!r}. "
            "Use a dedicated test/e2e database, for example investment_e2e."
        )


def ensure_schema(*, reset_schema: bool) -> None:
    ensure_database_exists()

    if reset_schema:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))

    # E2E validates the current application contract, not historical migration
    # replay. The migration chain contains legacy enum names that are not safe
    # to replay from an empty DB, so use the current SQLAlchemy model schema.
    Base.metadata.create_all(bind=engine)


def get_or_create_user(db, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    email_username = "".join(ch if ch.isalnum() else "." for ch in username.lower()).strip(".") or "user"
    if user is None:
        user = User(username=username)
        db.add(user)
    user.email = f"{email_username}.e2e@investment-e2e.com"
    user.set_password(password)
    user.is_active = True
    db.flush()

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    profile.experience_level = ExperienceLevel.NOVICE
    profile.holding_horizon = HoldingHorizon.MEDIUM
    profile.risk_tolerance = RiskTolerance.MEDIUM
    profile.behavior_tags = []
    db.flush()
    return user


def reset_user_state(db, user: User) -> None:
    task_ids = [row[0] for row in db.query(AnalysisTask.id).filter(AnalysisTask.user_id == user.id).all()]
    legacy_analysis_ids = [row[0] for row in db.query(Analysis.id).filter(Analysis.user_id == user.id).all()]

    db.query(EmotionHistory).filter(EmotionHistory.user_id == user.id).delete(synchronize_session=False)
    db.query(JudgmentHistory).filter(JudgmentHistory.user_id == user.id).delete(synchronize_session=False)
    db.query(ReviewTask).filter(ReviewTask.user_id == user.id).delete(synchronize_session=False)
    db.query(Watchlist).filter(Watchlist.user_id == user.id).delete(synchronize_session=False)
    db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).delete(synchronize_session=False)
    db.query(FocusReason).filter(FocusReason.user_id == user.id).delete(synchronize_session=False)
    db.query(UserAction).filter(UserAction.user_id == user.id).delete(synchronize_session=False)
    db.query(BehaviorIntervention).filter(BehaviorIntervention.user_id == user.id).delete(synchronize_session=False)

    if task_ids:
        db.query(AnalysisResult).filter(AnalysisResult.analysis_task_id.in_(task_ids)).delete(synchronize_session=False)
        db.query(AnalysisTask).filter(AnalysisTask.id.in_(task_ids)).delete(synchronize_session=False)

    if legacy_analysis_ids:
        db.query(AnalysisReason).filter(AnalysisReason.analysis_id.in_(legacy_analysis_ids)).delete(synchronize_session=False)
        db.query(Analysis).filter(Analysis.id.in_(legacy_analysis_ids)).delete(synchronize_session=False)

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is not None:
        profile.experience_level = ExperienceLevel.NOVICE
        profile.holding_horizon = HoldingHorizon.MEDIUM
        profile.risk_tolerance = RiskTolerance.MEDIUM
        profile.behavior_tags = []


def seed_stocks(db) -> None:
    for data in E2E_STOCKS:
        stock = db.query(Stock).filter(Stock.stock_id == data["stock_id"]).first()
        if stock is None:
            stock = Stock(stock_id=data["stock_id"])
            db.add(stock)
        stock.stock_name = data["stock_name"]
        stock.market = data["market"]
        stock.industry = data["industry"]
        stock.pe_ratio = data["pe_ratio"]
        stock.pb_ratio = data["pb_ratio"]


def main() -> None:
    args = parse_args()
    assert_safe_environment()
    ensure_schema(reset_schema=not args.skip_reset)

    db = SessionLocal()
    try:
        user = get_or_create_user(db, args.username, args.password)
        if not args.skip_reset:
            reset_user_state(db, user)
        seed_stocks(db)
        db.commit()
        print(
            f"E2E database prepared: user={args.username}, "
            f"stocks={len(E2E_STOCKS)}, reset={not args.skip_reset}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
