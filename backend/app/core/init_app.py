"""
应用初始化模块 - 用于初始化应用组件
"""

import logging
from fastapi import FastAPI
from app.services.risk_engine import RiskEngine
from app.services.ai_service import AiService
from app.services.blockchain import BlockchainService
from app.risk_modules.market_risk import MarketRiskAnalyzer
from app.risk_modules.protocol_risk import ProtocolRiskAnalyzer
from app.risk_modules.liquidity_risk import LiquidityRiskAnalyzer
from app.risk_modules.correlation_risk import CorrelationRiskAnalyzer
from app.risk_modules.smart_contract_risk import SmartContractRiskAnalyzer
from app.core.config import settings


logger = logging.getLogger("defi_risk.init_app")


def init_risk_engine() -> RiskEngine:
    """
    初始化风险引擎

    Returns:
        风险引擎实例
    """
    logger.info("初始化风险引擎")

    # 创建风险引擎
    risk_engine = RiskEngine()

    # 创建AI服务
    ai_service = AiService()

    # 创建区块链服务
    blockchain_service = BlockchainService()

    # 创建并注册风险分析器
    market_risk_analyzer = MarketRiskAnalyzer(
        ai_predictor=ai_service, blockchain_service=blockchain_service
    )
    protocol_risk_analyzer = ProtocolRiskAnalyzer(
        ai_predictor=ai_service, blockchain_service=blockchain_service
    )
    liquidity_risk_analyzer = LiquidityRiskAnalyzer(
        ai_predictor=ai_service, blockchain_service=blockchain_service
    )
    correlation_risk_analyzer = CorrelationRiskAnalyzer(
        ai_predictor=ai_service, blockchain_service=blockchain_service
    )
    smart_contract_risk_analyzer = SmartContractRiskAnalyzer(
        ai_predictor=ai_service, blockchain_service=blockchain_service
    )

    # 注册风险分析器
    risk_engine.register_analyzer("MARKET", market_risk_analyzer)
    risk_engine.register_analyzer("PROTOCOL", protocol_risk_analyzer)
    risk_engine.register_analyzer("LIQUIDITY", liquidity_risk_analyzer)
    risk_engine.register_analyzer("CORRELATION", correlation_risk_analyzer)
    risk_engine.register_analyzer("SMART_CONTRACT", smart_contract_risk_analyzer)

    logger.info("风险引擎初始化完成")

    return risk_engine


def init_app(app: FastAPI) -> None:
    """
    初始化应用

    Args:
        app: FastAPI应用实例
    """
    logger.info(f"初始化应用: {settings.APP_NAME} v{settings.APP_VERSION}")

    # 初始化风险引擎
    risk_engine = init_risk_engine()

    # 将风险引擎添加到应用状态
    app.state.risk_engine = risk_engine

    # 创建AI服务
    ai_service = AiService()

    # 将AI服务添加到应用状态
    app.state.ai_service = ai_service

    # 创建区块链服务
    blockchain_service = BlockchainService()

    # 将区块链服务添加到应用状态
    app.state.blockchain_service = blockchain_service

    logger.info("应用初始化完成")


def get_risk_engine() -> RiskEngine:
    """
    获取风险引擎实例

    Returns:
        风险引擎实例
    """
    # 如果没有初始化，则初始化
    if not hasattr(get_risk_engine, "_instance"):
        get_risk_engine._instance = init_risk_engine()

    return get_risk_engine._instance


def get_ai_service() -> AiService:
    """
    获取AI服务实例

    Returns:
        AI服务实例
    """
    # 如果没有初始化，则初始化
    if not hasattr(get_ai_service, "_instance"):
        get_ai_service._instance = AiService()

    return get_ai_service._instance


def get_blockchain_service() -> BlockchainService:
    """
    获取区块链服务实例

    Returns:
        区块链服务实例
    """
    # 如果没有初始化，则初始化
    if not hasattr(get_blockchain_service, "_instance"):
        get_blockchain_service._instance = BlockchainService()

    return get_blockchain_service._instance
