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
    分析钱包风险 - 重定向到投资组合分析
    """
    try:
        # 获取钱包头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        # 分析风险
        risk_assessment = await risk_engine.analyze_portfolio(positions)

        # 获取AI洞察
        ai_context = {
            "portfolio_summary": risk_assessment.detailed_analysis["portfolio_summary"],
            "risk_level": risk_assessment.risk_level.value,
            "risk_score": risk_assessment.total_score,
            "top_assets": risk_assessment.detailed_analysis["portfolio_summary"][
                "top_assets"
            ],
        }

        ai_analysis = await ai_service.analyze("portfolio_insights", ai_context)

        # 构建响应
        response = PortfolioAnalysisResponse(
            report_id=risk_assessment.id,
            timestamp=risk_assessment.timestamp,
            portfolio_summary=risk_assessment.detailed_analysis["portfolio_summary"],
            risk_assessment={
                "total_score": risk_assessment.total_score,
                "risk_level": risk_assessment.risk_level.value,
                "risk_by_type": risk_assessment.detailed_analysis["risk_by_type"],
                "warnings": risk_assessment.warnings,
                "recommendations": risk_assessment.recommendations,
                "mitigation_strategies": risk_assessment.mitigation_strategies,
                "monitoring_points": risk_assessment.monitoring_points,
            },
            detailed_analysis=risk_assessment.detailed_analysis,
            ai_insights=ai_analysis.insights,
        )
        return response
    except Exception as e:
        logger.error(f"分析钱包风险时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析钱包风险失败: {str(e)}")


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
