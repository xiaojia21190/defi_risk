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

        # 计算24小时价格变化、交易量和市值
        price_change_24h = 0
        volume_24h = 0
        market_cap = 0

        if historical_data is not None and not historical_data.empty:
            logger.info(f"成功获取{asset}的历史数据，计算市场指标")

            # 确保数据按时间排序
            historical_data = historical_data.sort_values("timestamp")

            # 获取最近的数据点
            latest_data = historical_data.iloc[-1]

            # 如果有足够的数据点，计算24小时价格变化
            if len(historical_data) >= 2:
                # 获取24小时前的数据点（或最早的数据点，如果数据不足24小时）
                previous_data = historical_data.iloc[0]

                # 如果有多个数据点，尝试找到接近24小时前的数据点
                if len(historical_data) > 2:
                    # 计算24小时前的时间戳
                    target_time = latest_data["timestamp"] - pd.Timedelta(days=1)

                    # 找到最接近的数据点
                    historical_data["time_diff"] = abs(
                        historical_data["timestamp"] - target_time
                    )
                    previous_data = historical_data.loc[
                        historical_data["time_diff"].idxmin()
                    ]

                # 计算价格变化百分比
                if previous_data["price"] > 0:
                    price_change_24h = (
                        (latest_data["price"] - previous_data["price"])
                        / previous_data["price"]
                    ) * 100

            # 获取交易量（使用最近的数据点）
            volume_24h = latest_data.get("volume", 0)

            # 获取市值（如果有）
            market_cap = latest_data.get("market_cap", 0)

            # 如果市值为空，尝试估算（价格 * 流通供应量）
            # 注意：这需要额外的数据源来获取流通供应量
            if not market_cap or pd.isna(market_cap):
                # 简化处理，使用价格的倍数作为市值的估计
                # 这只是一个粗略的估计，实际应用中应该使用真实的流通供应量数据
                supply_estimates = {
                    "BTC": 19000000,  # 比特币大约1900万枚
                    "ETH": 120000000,  # 以太坊大约1.2亿枚
                    "USDC": 30000000000,  # USDC大约300亿枚
                    "USDT": 80000000000,  # USDT大约800亿枚
                }

                # 获取估计的供应量，如果没有预设值则使用一个默认值
                estimated_supply = supply_estimates.get(asset.upper(), 1000000)
                market_cap = price * estimated_supply
        else:
            logger.warning(f"未能获取{asset}的历史数据，使用默认值")
            # 如果没有历史数据，使用默认值
            price_change_24h = 0
            volume_24h = 0
            market_cap = price * 1000000  # 简单估算

        # 构建响应
        response = {
            "asset": asset,
            "price": price,
            "price_change_24h": round(price_change_24h, 2),
            "volume_24h": volume_24h,
            "market_cap": market_cap,
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": False,
        }

        logger.info(
            f"返回{asset}的市场数据: 价格={price}, 24h变化={price_change_24h}%, 交易量={volume_24h}, 市值={market_cap}"
        )
        return response
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
