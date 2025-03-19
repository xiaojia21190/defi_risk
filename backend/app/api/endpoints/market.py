from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.services.demo_data import DemoDataService, get_demo_data_service
from app.core.init_app import get_blockchain_service, get_ai_service
from app.core.config import settings
import logging
import pandas as pd
from datetime import datetime


router = APIRouter()
logger = logging.getLogger("defi_risk.api.market")


@router.get("/data/{asset}")
async def get_market_data(
    asset: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取资产市场数据

    - **asset**: 资产符号，如ETH、BTC等
    """
    try:
        logger.info(f"收到市场数据请求: {asset}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 市场数据 {asset}")
            return demo_service.get_market_data(asset)

        # 实际环境下从区块链服务获取数据
        market_data = await blockchain_service.get_asset_data(asset)
        return market_data
    except Exception as e:
        logger.error(f"获取市场数据时出错: {str(e)}")
        return {"error": f"获取市场数据失败: {str(e)}"}


@router.get("/data/{asset}/history")
async def get_asset_price_history(
    asset: str,
    days: Optional[int] = 30,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取资产价格历史数据

    - **asset**: 资产符号，如ETH、BTC等
    - **days**: 历史数据的天数，默认30天
    """
    try:
        logger.info(f"收到资产价格历史数据请求: {asset}，天数: {days}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 资产价格历史 {asset}")
            return demo_service.get_asset_price_history(asset, days)

        # 实际环境下从区块链服务获取数据
        history_data = await blockchain_service.get_asset_historical_data(asset, days)
        return {
            "asset": asset,
            "days": days,
            "data_points": history_data,
            "is_demo_data": False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取资产价格历史数据时出错: {str(e)}")
        return {"error": f"获取资产价格历史数据失败: {str(e)}"}


@router.get("/predict/{asset}")
async def predict_market(
    asset: str,
    time_frame: str = Query("24h", description="预测时间范围: 24h, 7d, 30d"),
    ai_service: AiService = Depends(get_ai_service),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    预测市场趋势

    - **asset**: 资产名称（例如：ETH, BTC, USDC等）
    - **time_frame**: 预测时间范围（24h, 7d, 30d）
    """
    try:
        logger.info(f"收到市场预测请求: {asset}, 时间范围: {time_frame}")

        # 获取资产历史数据
        historical_data = await blockchain_service.get_asset_historical_data(asset)

        # 构建AI分析上下文
        context = {
            "asset": asset,
            "time_frame": time_frame,
            "historical_data": (
                historical_data.to_dict() if historical_data is not None else {}
            ),
        }

        # 调用AI服务进行分析
        analysis = await ai_service.analyze("market_prediction", context)

        return {
            "asset": asset,
            "time_frame": time_frame,
            "predictions": analysis.predictions,
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
            "confidence": analysis.confidence,
        }
    except Exception as e:
        logger.error(f"预测市场趋势时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预测市场趋势失败: {str(e)}")


# 注意: 市场警报功能已移至钱包API
# 要获取市场警报，请使用以下端点:
# GET /api/wallet/{wallet_address}/alerts


@router.get("/gas")
async def get_gas_price(
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取当前gas价格
    """
    try:
        logger.info("收到gas价格请求")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info("使用演示数据: gas价格")
            return demo_service.get_gas_price()

        # 获取gas价格
        gas_price = await blockchain_service.get_gas_price()
        return gas_price
    except Exception as e:
        logger.error(f"获取gas价格时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info("出错时使用演示数据: gas价格")
            return demo_service.get_gas_price()
        raise HTTPException(status_code=500, detail=f"获取gas价格失败: {str(e)}")
