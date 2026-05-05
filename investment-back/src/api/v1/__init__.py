from fastapi import APIRouter

from . import analysis, notifications, p3, portfolio, records, reviews, stocks, user, watchlist


api_router = APIRouter()

api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(records.router, prefix="/records", tags=["records"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(p3.router, prefix="/p3", tags=["p3"])
