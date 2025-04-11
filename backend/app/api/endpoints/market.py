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
    from_timestamp: Optional[int] = Query(
        None, description="开始时间的UNIX时间戳（秒）"
    ),
    to_timestamp: Optional[int] = Query(None, description="结束时间的UNIX时间戳（秒）"),
    ai_service: AiService = Depends(get_ai_service),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取市场数据、历史数据并预测市场趋势

    - **asset**: 资产名称（例如：ETH, BTC, USDC等）
    - **time_frame**: 预测时间范围（24h, 7d, 30d）
    - **days**: 历史数据的天数，默认30天
    - **from_timestamp**: (可选) 开始时间的UNIX时间戳（秒），如果提供则忽略days参数
    - **to_timestamp**: (可选) 结束时间的UNIX时间戳（秒），如果提供则必须同时提供from_timestamp
    """
    try:
        logger.info(
            f"收到综合市场数据和预测请求: {asset}, 时间范围: {time_frame}, "
            f"历史天数: {days if not from_timestamp else '未使用'}, "
            f"从时间戳: {from_timestamp if from_timestamp else '未指定'}, "
            f"到时间戳: {to_timestamp if to_timestamp else '未指定'}"
        )

        # 获取资产历史数据用于AI分析
        historical_data = await blockchain_service.get_coingecko_historical_data(
            asset, days, from_timestamp, to_timestamp
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


@router.get("/sentiment/{asset}")
async def get_asset_sentiment(
    asset: str,
    days: Optional[int] = Query(7, description="获取情绪数据的天数"),
    ai_service: AiService = Depends(get_ai_service),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取特定资产的市场情绪分析数据

    - **asset**: 资产名称（例如：ETH, BTC, USDC等）
    - **days**: 分析数据的天数，默认7天
    """
    try:
        logger.info(f"收到市场情绪分析请求: {asset}, 天数: {days}")

        # 获取情绪分析服务
        sentiment_service = ai_service.get_sentiment_service()
        if not sentiment_service:
            return {
                "error": "情绪分析服务不可用",
                "message": "系统未配置或未启用情绪分析服务",
                "asset": asset,
                "timestamp": _convert_timestamp(datetime.now()),
            }

        # 获取情绪分析结果
        sentiment_summary = await sentiment_service.get_asset_sentiment_summary(
            asset=asset, days=days
        )

        if not sentiment_summary:
            return {
                "error": "无法获取情绪数据",
                "message": f"未能获取到{asset}的市场情绪数据",
                "asset": asset,
                "timestamp": _convert_timestamp(datetime.now()),
            }

        # 处理时间序列数据，使其可序列化
        time_series_data = {}
        for source, series in sentiment_summary.time_series.items():
            time_series_data[source] = {
                "asset": series.asset,
                "source": series.source,
                "resolution": series.resolution,
                "data": [
                    {
                        "timestamp": _convert_timestamp(point.timestamp),
                        "sentiment_score": point.sentiment_score,
                        "volume": point.volume,
                        "source": point.source,
                        "metadata": point.metadata,
                    }
                    for point in series.data
                ],
            }

        # 处理风险因子，使其可序列化
        risk_factors = []
        for factor in sentiment_summary.risk_factors:
            risk_factors.append(
                {
                    "id": factor.id,
                    "name": factor.name,
                    "description": factor.description,
                    "score": factor.score,
                    "weight": factor.weight,
                    "trend": factor.trend,
                    "recommendations": factor.recommendations,
                    "monitoring_points": factor.monitoring_points,
                }
            )

        # 构建响应
        result = {
            "asset": sentiment_summary.asset,
            "timestamp": _convert_timestamp(sentiment_summary.timestamp),
            "overall_sentiment": sentiment_summary.overall_sentiment,
            "sentiment_change_24h": sentiment_summary.sentiment_change_24h,
            "sentiment_change_7d": sentiment_summary.sentiment_change_7d,
            "social_sentiment": sentiment_summary.social_sentiment,
            "news_sentiment": sentiment_summary.news_sentiment,
            "total_mentions": sentiment_summary.total_mentions,
            "sentiment_breakdown": {
                "bullish": sentiment_summary.bullish_percentage,
                "bearish": sentiment_summary.bearish_percentage,
                "neutral": sentiment_summary.neutral_percentage,
            },
            "top_topics": sentiment_summary.top_topics,
            "risk_factors": risk_factors,
            "recommendations": sentiment_summary.recommendations,
            "time_series": time_series_data,
        }

        return result
    except Exception as e:
        logger.error(f"获取市场情绪分析时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取市场情绪分析失败: {str(e)}")


@router.get("/sentiment/portfolio")
async def get_portfolio_sentiment(
    wallet_address: str = Query(..., description="钱包地址"),
    days: Optional[int] = Query(7, description="获取情绪数据的天数"),
    ai_service: AiService = Depends(get_ai_service),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取投资组合的市场情绪分析

    - **wallet_address**: 钱包地址
    - **days**: 分析数据的天数，默认7天
    """
    try:
        logger.info(f"收到投资组合情绪分析请求: {wallet_address}, 天数: {days}")

        # 获取情绪分析服务
        sentiment_service = ai_service.get_sentiment_service()
        if not sentiment_service:
            return {
                "error": "情绪分析服务不可用",
                "message": "系统未配置或未启用情绪分析服务",
                "wallet_address": wallet_address,
                "timestamp": _convert_timestamp(datetime.now()),
            }

        # 获取钱包头寸
        if settings.DEMO_MODE:
            wallet_data = demo_service.get_wallet_positions(wallet_address)
            positions = wallet_data.get("positions", [])
        else:
            positions = await blockchain_service.get_all_positions(wallet_address)

        if not positions:
            return {
                "error": "无投资组合数据",
                "message": "未找到该钱包地址的投资组合数据",
                "wallet_address": wallet_address,
                "timestamp": _convert_timestamp(datetime.now()),
            }

        # 提取主要资产
        assets = {}
        total_value = 0

        # 处理嵌套的positions结构
        for protocol_position in positions:
            inner_positions = []

            # 处理不同的数据结构
            if "positions" in protocol_position:
                inner_positions = protocol_position["positions"]
            elif isinstance(protocol_position, dict):
                inner_positions = [protocol_position]

            # 遍历每个协议中的具体资产positions
            for pos in inner_positions:
                position_amount = pos.get("amount", 0)
                total_value += position_amount

                # 获取资产信息
                if "tokenList" in pos and pos["tokenList"]:
                    for token in pos["tokenList"]:
                        token_symbol = token.get("tokenSymbol", "")
                        if not token_symbol:
                            continue

                        # 计算代币价值
                        if "currencyAmount" in token:
                            token_value = float(token.get("currencyAmount", "0"))
                        else:
                            token_value = (
                                position_amount / len(pos["tokenList"])
                                if pos["tokenList"]
                                else 0
                            )

                        # 累加到资产映射中
                        if token_symbol not in assets:
                            assets[token_symbol] = 0
                        assets[token_symbol] += token_value
                else:
                    # 如果没有tokenList，使用资产名称
                    asset = pos.get("asset", "Unknown").split("/")[
                        0
                    ]  # 处理流动性池资产格式

                    if asset not in assets:
                        assets[asset] = 0
                    assets[asset] += position_amount

        # 对资产按价值排序
        sorted_assets = sorted(
            [(asset, value) for asset, value in assets.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        # 只分析前5个最大资产
        top_assets = [asset for asset, _ in sorted_assets[:5]]

        # 获取每个资产的情绪数据
        asset_sentiments = {}
        for asset in top_assets:
            sentiment_summary = await sentiment_service.get_asset_sentiment_summary(
                asset=asset, days=days
            )

            if sentiment_summary:
                weight = assets[asset] / total_value if total_value > 0 else 0
                asset_sentiments[asset] = {
                    "overall_sentiment": sentiment_summary.overall_sentiment,
                    "sentiment_change_24h": sentiment_summary.sentiment_change_24h,
                    "social_sentiment": sentiment_summary.social_sentiment,
                    "news_sentiment": sentiment_summary.news_sentiment,
                    "top_topics": sentiment_summary.top_topics[:3],
                    "weight": weight,
                    "value": assets[asset],
                }

        # 计算投资组合的加权情绪指标
        if asset_sentiments:
            weighted_sentiment = sum(
                data["overall_sentiment"] * data["weight"]
                for asset, data in asset_sentiments.items()
            )

            weighted_change = sum(
                data["sentiment_change_24h"] * data["weight"]
                for asset, data in asset_sentiments.items()
            )

            # 提取所有资产的共同热门话题
            all_topics = []
            for asset, data in asset_sentiments.items():
                for topic in data.get("top_topics", []):
                    if isinstance(topic, dict) and "topic" in topic:
                        all_topics.append(topic["topic"])
                    else:
                        all_topics.append(topic)

            from collections import Counter

            topic_counter = Counter(all_topics)
            portfolio_topics = [
                {"topic": topic, "count": count}
                for topic, count in topic_counter.most_common(5)
            ]

            # 生成投资组合级别的建议
            recommendations = (
                await sentiment_service.generate_portfolio_recommendations(
                    asset_sentiments=asset_sentiments,
                    weighted_sentiment=weighted_sentiment,
                    weighted_change=weighted_change,
                )
            )
        else:
            weighted_sentiment = 0
            weighted_change = 0
            portfolio_topics = []
            recommendations = ["无法获取足够的市场情绪数据，无法提供建议"]

        # 构建响应
        result = {
            "wallet_address": wallet_address,
            "timestamp": _convert_timestamp(datetime.now()),
            "portfolio_sentiment": weighted_sentiment,
            "sentiment_change_24h": weighted_change,
            "asset_sentiments": asset_sentiments,
            "top_topics": portfolio_topics,
            "recommendations": recommendations,
            "assets_analyzed": len(asset_sentiments),
            "total_assets": len(assets),
        }

        return result
    except Exception as e:
        logger.error(f"获取投资组合情绪分析时出错: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"获取投资组合情绪分析失败: {str(e)}"
        )
