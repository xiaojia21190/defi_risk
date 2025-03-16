"""
应用初始化模块 - 用于初始化应用组件
"""

import logging
from fastapi import FastAPI
from app.services.risk_engine import RiskEngine
from app.services.ai_service import AiService
from app.services.blockchain import BlockchainService
from app.services.demo_data import DemoDataService, get_demo_data_service
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

    # 设置风险引擎的AI服务
    risk_engine.ai_service = ai_service

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
    risk_engine.register_analyzer("market", market_risk_analyzer)
    risk_engine.register_analyzer("protocol", protocol_risk_analyzer)
    risk_engine.register_analyzer("liquidity", liquidity_risk_analyzer)
    risk_engine.register_analyzer("correlation", correlation_risk_analyzer)
    risk_engine.register_analyzer("smart_contract", smart_contract_risk_analyzer)

    # 设置风险权重
    risk_engine.set_weights(settings.RISK_WEIGHTS)

    logger.info("风险引擎初始化完成")

    return risk_engine


def init_demo_data_service() -> DemoDataService:
    """
    初始化演示数据服务

    Returns:
        演示数据服务实例
    """
    logger.info("初始化演示数据服务")
    return DemoDataService()


def init_app(app: FastAPI) -> None:
    """
    初始化应用

    Args:
        app: FastAPI应用实例
    """
    logger.info(f"初始化应用: {settings.APP_NAME} v{settings.APP_VERSION}")

    # 初始化风险引擎
    risk_engine = init_risk_engine()

    # 初始化AI服务
    ai_service = AiService()

    # 初始化区块链服务
    blockchain_service = BlockchainService()

    # 初始化演示数据服务
    demo_data_service = init_demo_data_service()

    # 设置应用状态
    app.state.risk_engine = risk_engine
    app.state.ai_service = ai_service
    app.state.blockchain_service = blockchain_service
    app.state.demo_data_service = demo_data_service

    # 记录初始化完成
    logger.info(
        f"应用初始化完成: 风险引擎={risk_engine}, AI服务={ai_service}, 区块链服务={blockchain_service}, 演示数据服务={demo_data_service}"
    )


def get_risk_engine() -> RiskEngine:
    """
    获取风险引擎实例

    Returns:
        风险引擎实例
    """
    # 这里应该从应用状态中获取风险引擎实例
    # 但为了简化，直接创建一个新实例
    return init_risk_engine()


def get_ai_service() -> AiService:
    """
    获取AI服务实例

    Returns:
        AI服务实例
    """
    # 这里应该从应用状态中获取AI服务实例
    # 但为了简化，直接创建一个新实例
    return AiService()


def get_blockchain_service() -> BlockchainService:
    """
    获取区块链服务实例

    Returns:
        区块链服务实例
    """
    # 这里应该从应用状态中获取区块链服务实例
    # 但为了简化，直接创建一个新实例
    return BlockchainService()
