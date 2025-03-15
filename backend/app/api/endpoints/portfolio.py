from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.models.schemas.portfolio import PortfolioRequest, PortfolioAnalysisResponse
from app.services.risk_engine import RiskEngine
from app.services.ai_service import AiService
from app.core.init_app import get_risk_engine, get_ai_service
import logging
from app.models.domain.ai import AiRequest


router = APIRouter()
logger = logging.getLogger("defi_risk.api.portfolio")


@router.post("/analyze", response_model=PortfolioAnalysisResponse)
async def analyze_portfolio(
    request: PortfolioRequest,
    risk_engine: RiskEngine = Depends(get_risk_engine),
    ai_service: AiService = Depends(get_ai_service),
):
    """
    分析投资组合风险

    - **wallet_address**: 钱包地址（可选）
    - **positions**: 投资头寸列表（可选）

    至少需要提供钱包地址或头寸列表之一
    """
    try:
        logger.info(
            f"收到投资组合分析请求: {request.wallet_address or '自定义投资组合'}"
        )

        # 验证请求
        if not request.wallet_address and not request.positions:
            raise HTTPException(status_code=400, detail="必须提供钱包地址或头寸列表")

        # 准备投资组合数据
        if request.wallet_address:
            # TODO: 从区块链获取投资组合
            # 这里暂时使用模拟数据
            portfolio_data = {
                "wallet_address": request.wallet_address,
                "positions": [
                    {
                        "protocol": "Aave",
                        "asset": "ETH",
                        "amount": 2.5,
                        "apy": 3.2,
                        "invest_type": 6,
                        "invest_type_name": "借贷",
                    },
                    {
                        "protocol": "Uniswap",
                        "asset": "ETH/USDC",
                        "amount": 5000,
                        "apy": 15.8,
                        "invest_type": 2,
                        "invest_type_name": "流动性池",
                    },
                ],
            }
        else:
            # 使用提供的头寸
            portfolio_data = {"positions": [pos.dict() for pos in request.positions]}

        # 分析风险
        risk_assessment = await risk_engine.analyze_portfolio(portfolio_data)

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

        logger.info(f"投资组合分析完成: {request.wallet_address or '自定义投资组合'}")

        return response
    except Exception as e:
        logger.error(f"分析投资组合时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
