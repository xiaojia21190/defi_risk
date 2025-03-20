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


def _convert_timestamp(timestamp_obj):
    """转换单个时间戳对象为ISO格式字符串"""
    if isinstance(timestamp_obj, pd.Timestamp):
        return timestamp_obj.isoformat()
    elif isinstance(timestamp_obj, datetime):
        return timestamp_obj.isoformat()
    return timestamp_obj


@router.get("/predict/{asset}")
async def predict_market(
    asset: str,
    time_frame: str = Query("24h", description="预测时间范围: 24h, 7d, 30d"),
    days: Optional[int] = Query(30, description="历史数据的天数"),
    ai_service: AiService = Depends(get_ai_service),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取市场数据、历史数据并预测市场趋势

    - **asset**: 资产名称（例如：ETH, BTC, USDC等）
    - **time_frame**: 预测时间范围（24h, 7d, 30d）
    - **days**: 历史数据的天数，默认30天
    """
    try:
        logger.info(
            f"收到综合市场数据和预测请求: {asset}, 时间范围: {time_frame}, 历史天数: {days}"
        )

        # 获取资产历史数据用于AI分析
        historical_data = await blockchain_service.get_coingecko_historical_data(
            asset, days
        )

        # 构建AI分析上下文
        if historical_data is not None:
            # 先将DataFrame转换为字典列表
            history_dict = []
            for _, row in historical_data.iterrows():
                history_dict.append(
                    {
                        "timestamp": _convert_timestamp(row["timestamp"]),
                        "price": float(row["price"]),
                        "volume": (
                            float(row["volume"])
                            if "volume" in row and row["volume"] is not None
                            else None
                        ),
                        "market_cap": (
                            float(row["market_cap"])
                            if "market_cap" in row and row["market_cap"] is not None
                            else None
                        ),
                        "source": row["source"] if "source" in row else None,
                    }
                )
        else:
            history_dict = {}

        context = {
            "asset": asset,
            "time_frame": time_frame,
            "historical_data": history_dict,
        }

        # 调用AI服务进行分析
        analysis = await ai_service.analyze("market_prediction", context)

        # 确保analysis中的所有数据都被正确转换
        analysis_dict = {
            "predictions": analysis.predictions,
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
            "confidence": analysis.confidence,
        }

        # 转换所有时间戳为ISO格式
        converted_analysis = {
            "predictions": [
                _convert_timestamp(p) for p in analysis_dict["predictions"]
            ],
            "insights": analysis_dict["insights"],
            "recommendations": analysis_dict["recommendations"],
            "confidence": analysis_dict["confidence"],
        }

        # 合并所有数据到一个结果中
        result = {
            "asset": asset,
            "time_frame": time_frame,
            "price_history": historical_data,
            "predictions": converted_analysis["predictions"],
            "insights": converted_analysis["insights"],
            "recommendations": converted_analysis["recommendations"],
            "confidence": converted_analysis["confidence"],
            "timestamp": _convert_timestamp(datetime.now()),
        }

        return result
    except Exception as e:
        logger.error(f"获取市场数据和预测时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取市场数据和预测失败: {str(e)}")


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
