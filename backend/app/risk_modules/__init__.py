"""
风险模块包 - 包含各种风险评估模块
"""

from app.risk_modules.base import RiskAnalyzerBase
from app.risk_modules.market_risk import MarketRiskAnalyzer
from app.risk_modules.protocol_risk import ProtocolRiskAnalyzer
from app.risk_modules.liquidity_risk import LiquidityRiskAnalyzer
from app.risk_modules.correlation_risk import CorrelationRiskAnalyzer
from app.risk_modules.smart_contract_risk import SmartContractRiskAnalyzer
from app.services.ai_predictor import AiPredictor
from app.services.ai_service import AiService
from app.services.blockchain import BlockchainService
from app.services.risk_engine import RiskEngine

__all__ = [
    "RiskAnalyzerBase",
    "MarketRiskAnalyzer",
    "ProtocolRiskAnalyzer",
    "LiquidityRiskAnalyzer",
    "CorrelationRiskAnalyzer",
    "SmartContractRiskAnalyzer",
    "create_risk_analyzers",
]


def create_risk_analyzers(
    blockchain_service=None, ai_service=None, ai_predictor=None, risk_engine=None
):
    """
    创建所有风险分析器实例

    Args:
        blockchain_service: 区块链服务实例
        ai_service: AI服务实例
        ai_predictor: AI预测器实例
        risk_engine: 风险引擎实例

    Returns:
        Dict: 包含所有风险分析器实例的字典
    """

    if ai_predictor is None:
        ai_predictor = AiPredictor()

    if ai_service is None:
        ai_service = AiService()

    # 如果没有提供区块链服务，创建一个
    if blockchain_service is None:
        blockchain_service = BlockchainService()

    # 如果没有提供风险引擎，创建一个并设置区块链服务引用
    if risk_engine is None:
        risk_engine = RiskEngine(
            blockchain_service=blockchain_service, ai_service=ai_service
        )
        # 设置区块链服务的风险引擎引用，解决循环依赖
        blockchain_service.risk_engine = risk_engine

    # 创建各风险分析器实例
    market_risk = MarketRiskAnalyzer(
        blockchain_service=blockchain_service,
        ai_service=ai_service,
        ai_predictor=ai_predictor,
        risk_engine=risk_engine,
    )

    protocol_risk = ProtocolRiskAnalyzer(
        blockchain_service=blockchain_service,
        ai_service=ai_service,
        ai_predictor=ai_predictor,
        risk_engine=risk_engine,
    )

    liquidity_risk = LiquidityRiskAnalyzer(
        blockchain_service=blockchain_service,
        ai_service=ai_service,
        ai_predictor=ai_predictor,
        risk_engine=risk_engine,
    )

    correlation_risk = CorrelationRiskAnalyzer(
        blockchain_service=blockchain_service,
        ai_service=ai_service,
        ai_predictor=ai_predictor,
        risk_engine=risk_engine,
    )

    smart_contract_risk = SmartContractRiskAnalyzer(
        blockchain_service=blockchain_service,
        ai_service=ai_service,
        ai_predictor=ai_predictor,
        risk_engine=risk_engine,
    )

    return {
        "market_risk": market_risk,
        "protocol_risk": protocol_risk,
        "liquidity_risk": liquidity_risk,
        "correlation_risk": correlation_risk,
        "smart_contract_risk": smart_contract_risk,
    }
