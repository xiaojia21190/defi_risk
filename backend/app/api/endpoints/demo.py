from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.demo_data import DemoDataService, get_demo_data_service
from app.core.config import settings
from app.core.utility import create_standard_response
import logging
from datetime import datetime


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
        status_data = demo_service.get_demo_status(settings.DEMO_ACCOUNTS)
        return create_standard_response(status_data, is_demo=True)
    except Exception as e:
        logger.error(f"获取演示模式状态时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取演示模式状态失败: {str(e)}")


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
        refresh_result = demo_service.refresh_data()
        return create_standard_response(refresh_result, is_demo=True)
    except Exception as e:
        logger.error(f"刷新演示数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刷新演示数据失败: {str(e)}")


@router.get("/accounts")
async def get_demo_accounts():
    """
    获取演示账户列表

    返回可用于演示的钱包账户列表
    """
    try:
        logger.info("收到演示账户列表请求")
        accounts_data = {
            "accounts": settings.DEMO_ACCOUNTS,
            "count": len(settings.DEMO_ACCOUNTS),
        }
        return create_standard_response(accounts_data, is_demo=True)
    except Exception as e:
        logger.error(f"获取演示账户列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取演示账户列表失败: {str(e)}")
