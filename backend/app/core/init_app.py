"""
应用初始化模块 - 用于初始化应用组件
"""

import logging
from fastapi import FastAPI, Request, Depends
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


def create_services():
    """
    创建所有服务实例

    Returns:
        tuple: 包含所有服务实例的元组
    """
    logger.info("创建服务实例")

    # 创建基础服务
    ai_service = AiService()
    blockchain_service = BlockchainService()

    # 创建风险引擎并注入依赖
    risk_engine = RiskEngine(
        blockchain_service=blockchain_service, ai_service=ai_service
    )

    # 创建演示数据服务
    demo_data_service = DemoDataService()

    return ai_service, blockchain_service, risk_engine, demo_data_service


def setup_risk_analyzers(risk_engine, ai_service, blockchain_service):
    """
    设置风险分析器

    Args:
        risk_engine: 风险引擎实例
        ai_service: AI服务实例
        blockchain_service: 区块链服务实例
    """
    logger.info("设置风险分析器")

    # 创建风险分析器
    analyzers = {
        "market": MarketRiskAnalyzer(
            ai_predictor=ai_service, blockchain_service=blockchain_service
        ),
        "protocol": ProtocolRiskAnalyzer(
            ai_predictor=ai_service, blockchain_service=blockchain_service
        ),
        "liquidity": LiquidityRiskAnalyzer(
            ai_predictor=ai_service, blockchain_service=blockchain_service
        ),
        "correlation": CorrelationRiskAnalyzer(
            ai_predictor=ai_service, blockchain_service=blockchain_service
        ),
        "smart_contract": SmartContractRiskAnalyzer(
            ai_predictor=ai_service, blockchain_service=blockchain_service
        ),
    }

    # 注册风险分析器
    for risk_type, analyzer in analyzers.items():
        risk_engine.register_analyzer(risk_type, analyzer)

    # 设置风险权重
    risk_engine.set_weights(settings.RISK_WEIGHTS)


def init_app(app: FastAPI) -> None:
    """
    初始化应用

    Args:
        app: FastAPI应用实例
    """
    logger.info(f"初始化应用: {settings.APP_NAME} v{settings.APP_VERSION}")

    # 创建所有服务实例
    ai_service, blockchain_service, risk_engine, demo_data_service = create_services()

    # 设置风险分析器
    setup_risk_analyzers(risk_engine, ai_service, blockchain_service)

    # 设置应用状态
    app.state.risk_engine = risk_engine
    app.state.ai_service = ai_service
    app.state.blockchain_service = blockchain_service
    app.state.demo_data_service = demo_data_service

    # 添加启动和关闭事件处理
    setup_lifecycle_events(app)

    logger.info(
        f"应用初始化完成: 风险引擎={risk_engine}, AI服务={ai_service}, 区块链服务={blockchain_service}, 演示数据服务={demo_data_service}"
    )


def setup_lifecycle_events(app: FastAPI):
    """
    设置应用生命周期事件处理

    Args:
        app: FastAPI应用实例
    """

    @app.on_event("startup")
    async def startup_event():
        """应用启动时执行的事件处理"""
        logger.info("应用启动事件触发")
        # 可以在这里添加启动时需要执行的异步初始化操作

    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时执行的事件处理"""
        logger.info("应用关闭事件触发")
        # 可以在这里添加关闭时需要执行的资源释放操作

        # 关闭各服务
        if hasattr(app.state, "ai_service") and hasattr(app.state.ai_service, "close"):
            await app.state.ai_service.close()

        if hasattr(app.state, "blockchain_service") and hasattr(
            app.state.blockchain_service, "close"
        ):
            await app.state.blockchain_service.close()


def get_risk_engine(request: Request) -> RiskEngine:
    """
    获取风险引擎实例

    Args:
        request: FastAPI请求对象

    Returns:
        风险引擎实例
    """
    return request.app.state.risk_engine


def get_ai_service(request: Request) -> AiService:
    """
    获取AI服务实例

    Args:
        request: FastAPI请求对象

    Returns:
        AI服务实例
    """
    return request.app.state.ai_service


def get_blockchain_service(request: Request) -> BlockchainService:
    """
    获取区块链服务实例

    Args:
        request: FastAPI请求对象

    Returns:
        区块链服务实例
    """
    return request.app.state.blockchain_service


def get_demo_data_service(request: Request) -> DemoDataService:
    """
    获取演示数据服务实例

    Args:
        request: FastAPI请求对象

    Returns:
        演示数据服务实例
    """
    return request.app.state.demo_data_service
