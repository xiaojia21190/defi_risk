from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.models.schemas.portfolio import PortfolioAnalysisResponse
from app.core.init_app import get_blockchain_service, get_ai_service, get_risk_engine
import logging

from app.services.risk_engine import RiskEngine


router = APIRouter()
logger = logging.getLogger("defi_risk.api.wallet")


@router.get("/{wallet_address}/positions")
async def get_wallet_positions(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取钱包在所有协议中的头寸

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包头寸请求: {wallet_address}")

        # 获取所有协议头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        # 计算总价值
        total_value = sum(position.get("usd_value", 0) for position in positions)

        return {
            "wallet_address": wallet_address,
            "positions": positions,
            "total_value_usd": total_value,
            "position_count": len(positions),
        }
    except Exception as e:
        logger.error(f"获取钱包头寸时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取钱包头寸失败: {str(e)}")


@router.get("/{wallet_address}/risk")
async def analyze_wallet_risk(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    risk_engine: RiskEngine = Depends(get_risk_engine),
    ai_service: AiService = Depends(get_ai_service),
):
    """
    分析钱包整体风险

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包风险分析请求: {wallet_address}")

        # 检查AI服务是否可用
        ai_available = await ai_service.is_available()
        logger.info(f"AI服务可用性: {ai_available}")

        # 获取钱包头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        if not positions:
            return {
                "wallet_address": wallet_address,
                "risk_level": "LOW",
                "risk_score": 0,
                "message": "钱包中没有发现任何头寸",
                "recommendations": ["添加资产以获取风险分析"],
                "ai_available": ai_available,
            }

        # 分析风险
        risk_assessment = await risk_engine.analyze_portfolio(positions)

        # 获取AI洞察
        ai_insights = []
        ai_recommendations = []

        if ai_available:
            try:
                # 准备AI分析的上下文数据
                ai_context = {
                    "portfolio_summary": risk_assessment.detailed_analysis[
                        "portfolio_summary"
                    ],
                    "risk_level": risk_assessment.risk_level.value,
                    "risk_score": risk_assessment.total_score,
                    "top_assets": risk_assessment.detailed_analysis[
                        "portfolio_summary"
                    ].get("top_assets", []),
                }

                # 调用AI服务进行分析
                ai_analysis = await ai_service.analyze("portfolio_insights", ai_context)
                ai_insights = ai_analysis.insights

                # 如果AI分析中包含建议，添加到建议列表
                if ai_analysis.recommendations:
                    ai_recommendations = ai_analysis.recommendations
            except Exception as ai_error:
                logger.error(f"AI分析失败: {str(ai_error)}")
                ai_insights = [f"AI分析过程中出错: {str(ai_error)}"]

        # 构建响应
        response = {
            "wallet_address": wallet_address,
            "report_id": risk_assessment.id,
            "timestamp": risk_assessment.timestamp,
            "portfolio_summary": risk_assessment.detailed_analysis["portfolio_summary"],
            "risk_assessment": {
                "total_score": risk_assessment.total_score,
                "risk_level": risk_assessment.risk_level.value,
                "risk_by_type": risk_assessment.detailed_analysis["risk_by_type"],
                "warnings": risk_assessment.warnings,
                "recommendations": risk_assessment.recommendations + ai_recommendations,
                "mitigation_strategies": risk_assessment.mitigation_strategies,
                "monitoring_points": risk_assessment.monitoring_points,
            },
            "ai_insights": ai_insights,
            "ai_available": ai_available,
        }

        return response
    except Exception as e:
        logger.error(f"分析钱包风险时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析钱包风险失败: {str(e)}")


@router.get("/{wallet_address}/market-risk")
async def analyze_wallet_market_risk(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    risk_engine: RiskEngine = Depends(get_risk_engine),
    ai_service: AiService = Depends(get_ai_service),
):
    """
    分析钱包的市场风险

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包市场风险分析请求: {wallet_address}")

        # 检查AI服务是否可用
        ai_available = await ai_service.is_available()
        logger.info(f"AI服务可用性: {ai_available}")

        # 获取钱包头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        if not positions:
            return {
                "wallet_address": wallet_address,
                "risk_level": "LOW",
                "risk_score": 0,
                "message": "钱包中没有发现任何头寸",
                "recommendations": ["添加资产以获取市场风险分析"],
                "ai_available": ai_available,
            }

        # 分析市场风险
        market_risk_result = await risk_engine.analyze_market_risk(positions)

        # 获取AI洞察和建议
        ai_insights = []
        ai_recommendations = []
        ai_monitoring_points = []

        if ai_available and market_risk_result.factors:
            try:
                # 准备AI分析的数据
                risk_data = {
                    "risk_factors": [
                        {
                            "factor_name": factor.factor_name,
                            "score": factor.score,
                            "description": factor.description,
                            "trend": factor.trend,
                            "data_points": factor.data_points,
                        }
                        for factor in market_risk_result.factors
                    ],
                    "analysis_type": "market_risk_recommendations",
                }

                # 获取AI建议
                ai_rec_result = await ai_service.analyze_with_predictor(
                    analysis_type="market_risk_recommendations", data=risk_data
                )

                if (
                    hasattr(ai_rec_result, "recommendations")
                    and ai_rec_result.recommendations
                ):
                    ai_recommendations = ai_rec_result.recommendations

                # 获取AI监控点
                ai_mon_result = await ai_service.analyze_with_predictor(
                    analysis_type="market_risk_monitoring_points", data=risk_data
                )

                if (
                    hasattr(ai_mon_result, "monitoring_points")
                    and ai_mon_result.monitoring_points
                ):
                    ai_monitoring_points = ai_mon_result.monitoring_points

            except Exception as ai_error:
                logger.error(f"AI市场风险分析失败: {str(ai_error)}")
                ai_insights = [f"AI市场风险分析过程中出错: {str(ai_error)}"]

        # 构建响应
        response = {
            "wallet_address": wallet_address,
            "risk_type": market_risk_result.risk_type,
            "target": market_risk_result.target,
            "score": market_risk_result.score,
            "risk_level": (
                "HIGH"
                if market_risk_result.score > 70
                else "MEDIUM" if market_risk_result.score > 40 else "LOW"
            ),
            "factors": [
                {
                    "name": factor.factor_name,
                    "score": factor.score,
                    "weight": factor.weight,
                    "description": factor.description,
                    "trend": factor.trend,
                    "data_points": factor.data_points,
                }
                for factor in market_risk_result.factors
            ],
            "recommendations": market_risk_result.recommendations + ai_recommendations,
            "monitoring_points": market_risk_result.monitoring_points
            + ai_monitoring_points,
            "ai_insights": ai_insights,
            "ai_available": ai_available,
        }

        return response
    except Exception as e:
        logger.error(f"分析钱包市场风险时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析钱包市场风险失败: {str(e)}")


@router.get("/{wallet_address}/alerts")
async def get_wallet_alerts(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取钱包相关的市场警报

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包警报请求: {wallet_address}")

        # 获取市场警报
        alerts = await blockchain_service.get_market_alerts(wallet_address)

        return {
            "wallet_address": wallet_address,
            "alerts": alerts,
            "alert_count": len(alerts),
        }
    except Exception as e:
        logger.error(f"获取钱包警报时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取钱包警报失败: {str(e)}")
