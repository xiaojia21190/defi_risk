from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class PositionSchema(BaseModel):
    """投资头寸模型"""

    protocol: str
    asset: str
    amount: float
    apy: Optional[float] = None
    invest_type: Optional[int] = None
    invest_type_name: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "protocol": "Aave",
                "asset": "ETH",
                "amount": 2.5,
                "apy": 3.2,
                "invest_type": 6,
                "invest_type_name": "借贷",
            }
        }


class PortfolioRequest(BaseModel):
    """投资组合请求模型"""

    wallet_address: Optional[str] = None
    positions: Optional[List[PositionSchema]] = None

    class Config:
        schema_extra = {
            "example": {
                "wallet_address": "0x1234...",
                "positions": [
                    {
                        "protocol": "Aave",
                        "asset": "ETH",
                        "amount": 2.5,
                        "apy": 3.2,
                        "invest_type": 6,
                        "invest_type_name": "借贷",
                    }
                ],
            }
        }


class RiskFactorResponse(BaseModel):
    """风险因子响应模型"""

    name: str
    score: float
    description: str
    trend: str


class RiskTypeResponse(BaseModel):
    """风险类型响应模型"""

    type_name: str
    score: float
    level: str
    factors: List[RiskFactorResponse]


class PortfolioSummaryResponse(BaseModel):
    """投资组合摘要响应模型"""

    total_value: float
    position_count: int
    protocol_count: int
    asset_count: int
    top_protocols: List[Dict[str, Any]]
    top_assets: List[Dict[str, Any]]


class RiskAssessmentResponse(BaseModel):
    """风险评估响应模型"""

    total_score: float
    risk_level: str
    risk_by_type: Dict[str, RiskTypeResponse]
    warnings: List[str]
    recommendations: List[str]
    mitigation_strategies: List[str]
    monitoring_points: List[str]


class PortfolioAnalysisResponse(BaseModel):
    """投资组合分析响应模型"""

    report_id: str
    timestamp: datetime
    portfolio_summary: PortfolioSummaryResponse
    risk_assessment: RiskAssessmentResponse
    detailed_analysis: Dict[str, Any]
    ai_insights: Optional[List[str]] = None
