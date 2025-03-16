from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.services.demo_data import DemoDataService, get_demo_data_service
from app.core.config import settings
import logging


router = APIRouter()
logger = logging.getLogger("defi_risk.api.demo")


@router.get("/status")
async def get_demo_status(
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取演示模式状态

    返回当前API的演示模式状态和可用的演示账户
    """
    try:
        logger.info("收到演示模式状态请求")
        return demo_service.get_demo_status(settings.DEMO_ACCOUNTS)
    except Exception as e:
        logger.error(f"获取演示模式状态时出错: {str(e)}")
        return {
            "demo_mode": settings.DEMO_MODE,
            "error": str(e),
            "demo_accounts": settings.DEMO_ACCOUNTS,
        }


@router.get("/refresh")
async def refresh_demo_data(
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    刷新演示数据

    清除演示数据缓存，生成新的随机数据
    """
    try:
        logger.info("收到刷新演示数据请求")
        return demo_service.refresh_data()
    except Exception as e:
        logger.error(f"刷新演示数据时出错: {str(e)}")
        return {"status": "error", "message": f"刷新演示数据失败: {str(e)}"}


@router.get("/accounts")
async def get_demo_accounts():
    """
    获取演示账户列表

    返回可用于演示的钱包账户列表
    """
    try:
        logger.info("收到演示账户列表请求")
        return {
            "accounts": settings.DEMO_ACCOUNTS,
            "count": len(settings.DEMO_ACCOUNTS),
        }
    except Exception as e:
        logger.error(f"获取演示账户列表时出错: {str(e)}")
        return {"accounts": [], "error": str(e)}
