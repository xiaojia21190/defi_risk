from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.services.demo_data import DemoDataService, get_demo_data_service
from app.core.init_app import get_blockchain_service, get_ai_service
from app.core.config import settings
import logging


router = APIRouter()
logger = logging.getLogger("defi_risk.api.market")


@router.get("/data/{asset}")
async def get_market_data(
    asset: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取市场数据

    - **asset**: 资产名称（例如：ETH, BTC, USDC等）
    """
    try:
        logger.info(f"收到市场数据请求: {asset}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: {asset}")
            return demo_service.get_market_data(asset)

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
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: {asset}")
            return demo_service.get_market_data(asset)
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


@router.post("/predict/{asset}")
async def predict_market_trend(
    asset: str,
    days: int = Query(7, description="预测天数"),
    ai_service: AiService = Depends(get_ai_service),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    预测资产市场趋势

    - **asset**: 资产名称（例如：ETH, BTC, USDC等）
    - **days**: 预测天数
    """
    try:
        logger.info(f"收到市场预测请求: {asset}, 天数: {days}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 市场预测 {asset}")
            # 这里可以添加市场预测的演示数据
            return {
                "asset": asset,
                "trend": "上涨",
                "confidence": 0.75,
                "prediction_days": days,
                "price_prediction": [
                    {"day": i, "price": 3000 + i * 50, "change": i * 1.5}
                    for i in range(1, days + 1)
                ],
                "is_demo_data": True,
            }

        # 获取历史数据
        historical_data = await blockchain_service.get_asset_historical_data(asset)

        # 使用AI服务预测趋势
        prediction = await ai_service.predict_market_trend(asset, historical_data, days)
        return prediction
    except Exception as e:
        logger.error(f"预测市场趋势时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: 市场预测 {asset}")
            return {
                "asset": asset,
                "trend": "上涨",
                "confidence": 0.75,
                "prediction_days": days,
                "price_prediction": [
                    {"day": i, "price": 3000 + i * 50, "change": i * 1.5}
                    for i in range(1, days + 1)
                ],
                "is_demo_data": True,
            }
        raise HTTPException(status_code=500, detail=f"预测市场趋势失败: {str(e)}")
