from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.core.init_app import get_blockchain_service, get_ai_service
import logging


router = APIRouter()
logger = logging.getLogger("defi_risk.api.market")


@router.get("/data/{asset}")
async def get_market_data(
    asset: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取市场数据

    - **asset**: 资产名称（例如：ETH, BTC, USDC等）
    """
    try:
        logger.info(f"收到市场数据请求: {asset}")

        # 获取资产价格
        price = await blockchain_service.get_token_price(asset)

        # 获取资产历史数据
        historical_data = await blockchain_service.get_asset_historical_data(asset)

        # 计算24小时价格变化
        price_change_24h = 0
        volume_24h = 0
        market_cap = 0

        if historical_data is not None:
            # 这里应该从历史数据中提取相关信息
            # 简化处理，使用模拟数据
            price_change_24h = 2.5  # 百分比
            volume_24h = 1500000000  # 美元
            market_cap = 200000000000  # 美元

        return {
            "asset": asset,
            "price": price,
            "price_change_24h": price_change_24h,
            "volume_24h": volume_24h,
            "market_cap": market_cap,
        }
    except Exception as e:
        logger.error(f"获取市场数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取市场数据失败: {str(e)}")


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


@router.get("/alerts")
async def get_market_alerts(
    wallet_address: Optional[str] = None,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取市场警报

    - **wallet_address**: 钱包地址（可选）
    """
    try:
        logger.info(f"收到市场警报请求: {wallet_address or '无钱包地址'}")

        # 获取市场警报
        alerts = await blockchain_service.get_market_alerts(wallet_address)

        return {
            "wallet_address": wallet_address,
            "alerts": alerts,
            "alert_count": len(alerts),
        }
    except Exception as e:
        logger.error(f"获取市场警报时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取市场警报失败: {str(e)}")


@router.get("/gas-price")
async def get_gas_price(
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取当前gas价格
    """
    try:
        logger.info("收到gas价格请求")

        # 获取gas价格
        gas_price = await blockchain_service.get_gas_price()

        return {
            "gas_price": gas_price,
            "unit": "Gwei",
        }
    except Exception as e:
        logger.error(f"获取gas价格时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取gas价格失败: {str(e)}")
