from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.init_app import init_app


# 设置日志
logger = setup_logging()

# 创建应用
app = FastAPI(
    title=settings.APP_NAME, version=settings.APP_VERSION, debug=settings.DEBUG
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)

# 初始化应用
init_app(app)


@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "DeFi风险分析API",
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}
