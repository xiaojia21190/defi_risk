import logging

from app.core.logging import setup_logging
from app.core.config import settings

# 设置日志
logger = setup_logging()
logger.info(f"启动应用 {settings.APP_NAME} v{settings.APP_VERSION}")


def create_app():
    """创建FastAPI应用"""
    from fastapi import FastAPI
    from app.api.router import api_router
    from app.core.config import settings
    from app.core.init_app import register_extensions, setup_middlewares, init_services
    from app.core.exception_handlers import register_exception_handlers

    # 创建FastAPI实例
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 注册API路由
    app.include_router(api_router)

    # 注册异常处理器
    register_exception_handlers(app)

    # 设置中间件
    setup_middlewares(app)

    # 注册扩展
    register_extensions(app)

    # 初始化服务
    init_services(app)

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

    return app


# 创建应用实例
app = create_app()
