# API v1 module
from fastapi import APIRouter
from . import analysis
from . import stocks
from . import watchlist
from . import user
from . import reviews
from . import records

api_router = APIRouter()

# 注册路由
api_router.include_router(analysis.router, prefix="/analysis", tags=["分析"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["股票"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["观察列表"])
api_router.include_router(user.router, prefix="/user", tags=["用户"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["复盘"])
api_router.include_router(records.router, prefix="/records", tags=["记录"])
