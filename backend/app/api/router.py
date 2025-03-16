from fastapi import APIRouter
from app.api.endpoints import portfolio, market, protocol, wallet, demo
from app.core.config import settings


api_router = APIRouter(prefix=settings.API_PREFIX)

# 注册路由
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(protocol.router, prefix="/protocol", tags=["protocol"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])

# 在这里添加更多路由
# api_router.include_router(
#     market.router,
#     prefix="/market",
#     tags=["market"]
# )
