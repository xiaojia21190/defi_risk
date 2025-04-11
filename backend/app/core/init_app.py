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
from app.services.ai_predictor import AiPredictor


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

    # 设置区块链服务的风险引擎引用，解决循环依赖
    blockchain_service.risk_engine = risk_engine

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

    # 确保AI服务有有效的预测器
    if not hasattr(ai_service, "_ai_predictor") or ai_service._ai_predictor is None:
        logger.info("风险分析器初始化时设置AI预测器")
        try:
            ai_predictor = ai_service.get_predictor()
            logger.info(f"风险分析器初始化获取AI预测器: {ai_predictor is not None}")
        except Exception as e:
            logger.error(f"风险分析器初始化时获取AI预测器失败: {str(e)}")

    # 创建风险分析器
    analyzers = {
        "market": MarketRiskAnalyzer(
            ai_service=ai_service,  # 修正：将ai_service传递给ai_service参数
            ai_predictor=ai_service.get_predictor(),  # 确保ai_predictor被正确初始化
            blockchain_service=blockchain_service,
            risk_engine=risk_engine,
        ),
        "protocol": ProtocolRiskAnalyzer(
            ai_service=ai_service,  # 修正：将ai_service传递给ai_service参数
            ai_predictor=ai_service.get_predictor(),  # 确保ai_predictor被正确初始化
            blockchain_service=blockchain_service,
            risk_engine=risk_engine,
        ),
        "liquidity": LiquidityRiskAnalyzer(
            ai_service=ai_service,  # 修正：将ai_service传递给ai_service参数
            ai_predictor=ai_service.get_predictor(),  # 确保ai_predictor被正确初始化
            blockchain_service=blockchain_service,
            risk_engine=risk_engine,
        ),
        "correlation": CorrelationRiskAnalyzer(
            ai_service=ai_service,  # 修正：将ai_service传递给ai_service参数
            ai_predictor=ai_service.get_predictor(),  # 确保ai_predictor被正确初始化
            blockchain_service=blockchain_service,
            risk_engine=risk_engine,
        ),
        "smart_contract": SmartContractRiskAnalyzer(
            ai_service=ai_service,  # 修正：将ai_service传递给ai_service参数
            ai_predictor=ai_service.get_predictor(),  # 确保ai_predictor被正确初始化
            blockchain_service=blockchain_service,
            risk_engine=risk_engine,
        ),
    }

    # 注册风险分析器
    for risk_type, analyzer in analyzers.items():
        risk_engine.register_analyzer(risk_type, analyzer)

    # 设置风险权重
    risk_engine.set_weights(settings.RISK_WEIGHTS)


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


def init_services(app: FastAPI) -> None:
    """初始化应用服务"""

    # 初始化区块链服务
    from app.services.blockchain import BlockchainService
    from app.services.risk_engine import RiskEngine
    from app.services.ai_predictor import AiPredictor
    from app.risk_modules import create_risk_analyzers

    # 临时存储服务实例，以便相互引用
    service_instances = {}

    # 创建AI预测器
    ai_predictor = AiPredictor()
    service_instances["ai_predictor"] = ai_predictor

    # 创建AI服务并设置AI预测器
    ai_service = AiService()
    service_instances["ai_service"] = ai_service

    # 先创建服务实例，但暂不相互引用
    blockchain_service = BlockchainService()
    service_instances["blockchain_service"] = blockchain_service

    # 使用 BlockchainService 创建 RiskEngine
    risk_engine = RiskEngine(
        blockchain_service=blockchain_service, ai_service=ai_service
    )
    service_instances["risk_engine"] = risk_engine

    # 补充相互引用
    blockchain_service.risk_engine = risk_engine

    # 将服务添加到 app.state
    app.state.blockchain_service = blockchain_service
    app.state.risk_engine = risk_engine
    app.state.ai_predictor = ai_predictor
    app.state.ai_service = ai_service

    # 注册风险分析器
    logger.info("注册风险分析器")
    risk_analyzers = create_risk_analyzers(
        blockchain_service=blockchain_service,
        ai_service=ai_service,
        ai_predictor=ai_predictor,
        risk_engine=risk_engine,
    )

    # 将分析器注册到风险引擎
    for risk_type, analyzer in risk_analyzers.items():
        risk_engine.register_analyzer(risk_type, analyzer)

    # 设置风险权重
    risk_engine.set_weights(settings.RISK_WEIGHTS)

    # 添加启动和关闭事件处理
    @app.on_event("startup")
    async def startup_event():
        """应用启动时执行的事件处理"""
        logger.info("应用启动事件触发")
        # 可以在这里添加启动时需要执行的异步初始化操作

        # 确保AI服务正确初始化AI预测器
        if hasattr(app.state, "ai_service"):
            logger.info("启动时初始化AI预测器")
            try:
                # 预初始化AI预测器，避免首次调用时延迟
                predictor = app.state.ai_service.get_predictor()
                logger.info(f"AI预测器初始化状态: {predictor is not None}")

                # 设置到ai_service._ai_predictor
                app.state.ai_service._ai_predictor = predictor

                # 设置到risk_engine中
                if hasattr(app.state, "risk_engine"):
                    app.state.risk_engine.ai_service = app.state.ai_service
                    logger.info("已将AI服务设置到风险引擎")
            except Exception as e:
                logger.error(f"启动时初始化AI预测器失败: {str(e)}")

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

    logger.info(f"风险分析器注册完成: {', '.join(risk_analyzers.keys())}")


def register_extensions(app: FastAPI) -> None:
    """
    注册应用扩展和插件

    Args:
        app: FastAPI应用实例
    """
    logger.info("注册应用扩展")
    # 目前没有需要注册的扩展
    # 可以在此添加数据库连接、缓存等扩展的初始化


def setup_middlewares(app: FastAPI) -> None:
    """
    设置应用中间件

    Args:
        app: FastAPI应用实例
    """
    from fastapi.middleware.cors import CORSMiddleware

    logger.info("设置应用中间件")

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 可以在此添加其他中间件，例如认证、日志等
