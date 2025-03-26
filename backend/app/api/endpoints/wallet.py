from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.services.demo_data import DemoDataService, get_demo_data_service
from app.models.schemas.portfolio import PortfolioAnalysisResponse
from app.core.init_app import get_blockchain_service, get_ai_service, get_risk_engine
from app.core.config import settings
import logging
from datetime import datetime

from app.services.risk_engine import RiskEngine


router = APIRouter()
logger = logging.getLogger("defi_risk.api.wallet")


@router.get("/{wallet_address}/positions")
async def get_wallet_positions(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取钱包在所有协议中的头寸和协议信息

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包头寸和协议信息请求: {wallet_address}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 钱包头寸和协议信息 {wallet_address}")
            # 获取钱包头寸
            wallet_data = demo_service.get_wallet_positions(wallet_address)
            # 获取协议信息
            protocols = demo_service.get_protocols()

            # 提取使用的协议信息
            protocols_used = []
            protocols_set = set()

            for position in wallet_data.get("positions", []):
                protocol_name = position.get("protocol", "")
                if protocol_name and protocol_name not in protocols_set:
                    protocols_set.add(protocol_name)
                    # 从协议列表中查找协议信息
                    protocol_info = next(
                        (
                            p
                            for p in protocols.get("protocols", [])
                            if p["name"] == protocol_name
                        ),
                        None,
                    )
                    if protocol_info:
                        protocols_used.append(protocol_info)
                    else:
                        # 如果没有找到协议信息，使用基本信息
                        protocols_used.append(
                            {
                                "name": protocol_name,
                                "chain": position.get("chain", "Unknown"),
                                "tvl": 0,
                                "supported_assets": ["ETH", "USDC"],
                                "features": ["借贷", "流动性挖矿"],
                                "description": f"{protocol_name}是一个DeFi协议",
                            }
                        )

            return {
                "wallet_address": wallet_address,
                "positions": wallet_data.get("positions", []),
                "total_value_usd": wallet_data.get("total_value_usd", 0),
                "position_count": len(wallet_data.get("positions", [])),
                "protocols": protocols_used,
                "protocol_count": len(protocols_used),
                "timestamp": datetime.now().isoformat(),
                "is_demo_data": True,
            }

        # 获取所有协议头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        # 计算总价值
        total_value = 0
        for position in positions:
            if "total_assets" in position:
                total_value += position.get("total_assets", 0)
            elif "amount" in position:
                total_value += position.get("amount", 0)

        # 提取协议列表并获取协议信息
        protocols_used = []
        protocols_set = set()

        for position in positions:
            protocol_name = position.get("protocol", "")
            if protocol_name and protocol_name not in protocols_set:
                protocols_set.add(protocol_name)
                try:
                    # 获取协议详细信息
                    protocol_info = await blockchain_service.get_protocol(protocol_name)
                    protocols_used.append(
                        {
                            "name": protocol_name,
                            "chain": protocol_info.get(
                                "chain", position.get("chain", "Unknown")
                            ),
                            "tvl": protocol_info.get("tvl", 0),
                            "supported_assets": protocol_info.get(
                                "supported_assets", ["ETH", "USDC"]
                            ),
                            "features": protocol_info.get(
                                "features", ["借贷", "流动性挖矿"]
                            ),
                            "description": protocol_info.get(
                                "description", f"{protocol_name}是一个DeFi协议"
                            ),
                        }
                    )
                except Exception:
                    # 如果获取协议信息失败，使用基本信息
                    protocols_used.append(
                        {
                            "name": protocol_name,
                            "chain": position.get("chain", "Unknown"),
                            "tvl": 0,
                            "supported_assets": ["ETH", "USDC"],
                            "features": ["借贷", "流动性挖矿"],
                            "description": f"{protocol_name}是一个DeFi协议",
                        }
                    )

        # 构建响应
        response = {
            "wallet_address": wallet_address,
            "positions": positions,
            "total_value_usd": total_value,
            "position_count": len(positions),
            "protocols": protocols_used,
            "protocol_count": len(protocols_used),
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": False,
        }

        return response
    except Exception as e:
        logger.error(f"获取钱包头寸和协议信息时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: 钱包头寸和协议信息 {wallet_address}")
            return demo_service.get_wallet_positions(wallet_address)
        raise HTTPException(
            status_code=500, detail=f"获取钱包头寸和协议信息失败: {str(e)}"
        )


@router.get("/{wallet_address}/risk")
async def analyze_wallet_risk(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    risk_engine: RiskEngine = Depends(get_risk_engine),
    ai_service: AiService = Depends(get_ai_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    分析钱包风险

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包风险分析请求: {wallet_address}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 钱包风险 {wallet_address}")
            return demo_service.analyze_wallet_risk(wallet_address)

        # 获取钱包头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        # 使用风险引擎分析投资组合风险
        risk_analysis = await risk_engine.analyze_portfolio_risk(
            positions, wallet_address
        )

        # 获取AI洞察
        ai_insights = await ai_service.get_portfolio_insights(
            wallet_address, positions, risk_analysis
        )

        # 构建响应
        result = {
            "wallet_address": wallet_address,
            "risk_score": risk_analysis.get("risk_score", 0),
            "risk_level": risk_analysis.get("risk_level", "未知"),
            "risk_factors": risk_analysis.get("risk_factors", []),
            "risk_metrics": risk_analysis.get("risk_metrics", {}),
            "recommendations": ai_insights.get("recommendations", [])
            or risk_analysis.get("recommendations", []),
            "warnings": risk_analysis.get("warnings", []),
            "monitoring_points": risk_analysis.get("monitoring_points", []),
            "analysis_timestamp": risk_analysis.get(
                "analysis_timestamp", datetime.now().isoformat()
            ),
            "positions_summary": {
                "total_value": sum(
                    position.get("usd_value", 0) for position in positions
                ),
                "position_count": len(positions),
                "protocols": list(set(p.get("protocol", "") for p in positions)),
                "assets": list(set(p.get("asset", "") for p in positions)),
            },
            "ai_enhanced": ai_insights.get("recommendations", []) != [],
        }

        return result
    except Exception as e:
        logger.error(f"分析钱包风险时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: 钱包风险 {wallet_address}")
            return demo_service.analyze_wallet_risk(wallet_address)
        raise HTTPException(status_code=500, detail=f"分析钱包风险失败: {str(e)}")


@router.get("/{wallet_address}/market-risk")
async def analyze_wallet_market_risk(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    risk_engine: RiskEngine = Depends(get_risk_engine),
    ai_service: AiService = Depends(get_ai_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    分析钱包的市场风险

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包市场风险分析请求: {wallet_address}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 钱包市场风险分析 {wallet_address}")
            # 尝试从demo_service获取市场风险数据
            # 如果demo_service没有专门的市场风险方法，可以复用风险分析数据
            try:
                return demo_service.get_wallet_market_risk(wallet_address)
            except (AttributeError, NotImplementedError):
                logger.info("演示服务中没有专门的市场风险方法，使用通用风险数据")
                risk_data = demo_service.analyze_wallet_risk(wallet_address)
                # 从通用风险数据中提取市场风险相关数据
                return {
                    "wallet_address": wallet_address,
                    "risk_type": "MARKET",
                    "target": "portfolio",
                    "score": risk_data.get("risk_metrics", {}).get("market_risk_score", 50),
                    "risk_level": "HIGH" if risk_data.get("risk_score", 50) > 70 else
                                 "MEDIUM" if risk_data.get("risk_score", 50) > 40 else "LOW",
                    "factors": risk_data.get("risk_factors", []),
                    "recommendations": risk_data.get("recommendations", []),
                    "monitoring_points": risk_data.get("monitoring_points", []),
                    "ai_insights": [],
                    "ai_available": True,
                    "is_demo_data": True,
                }

        # 检查AI服务是否可用
        ai_available = False
        try:
            ai_available = await ai_service.is_available()
            logger.info(f"AI服务可用性: {ai_available}")
        except Exception as ai_error:
            logger.warning(f"检查AI服务可用性时出错: {str(ai_error)}")

        # 获取钱包头寸
        try:
            positions = await blockchain_service.get_all_positions(wallet_address)
        except Exception as pos_error:
            logger.error(f"获取钱包头寸时出错: {str(pos_error)}")
            raise HTTPException(status_code=500, detail=f"获取钱包头寸失败: {str(pos_error)}")

        if not positions:
            logger.info(f"钱包 {wallet_address} 没有头寸")
            return {
                "wallet_address": wallet_address,
                "risk_type": "MARKET",
                "target": "portfolio",
                "score": 0,
                "risk_level": "LOW",
                "factors": [],
                "recommendations": ["添加资产以获取市场风险分析"],
                "monitoring_points": [],
                "ai_insights": [],
                "ai_available": ai_available,
                "timestamp": datetime.now().isoformat(),
            }

        # 分析市场风险
        try:
            market_risk_result = await risk_engine.analyze_market_risk(positions)
        except Exception as risk_error:
            logger.error(f"分析市场风险时出错: {str(risk_error)}")
            # 返回一个基本的风险结果
            return {
                "wallet_address": wallet_address,
                "risk_type": "MARKET",
                "target": "portfolio",
                "score": 50,  # 默认中等风险
                "risk_level": "MEDIUM",
                "factors": [],
                "recommendations": ["风险分析过程中出错，请稍后重试"],
                "monitoring_points": ["监控市场整体波动"],
                "ai_insights": [f"分析过程中出错: {str(risk_error)}"],
                "ai_available": ai_available,
                "error": str(risk_error),
                "timestamp": datetime.now().isoformat(),
            }

        # 获取AI洞察和建议
        ai_insights = []
        ai_recommendations = []
        ai_monitoring_points = []

        if ai_available and hasattr(market_risk_result, 'factors') and market_risk_result.factors:
            try:
                # 准备AI分析的数据
                risk_data = {
                    "risk_factors": [
                        {
                            "factor_name": getattr(factor, "factor_name", "未知因素"),
                            "score": getattr(factor, "score", 50),
                            "description": getattr(factor, "description", ""),
                            "trend": getattr(factor, "trend", "稳定"),
                            "data_points": getattr(factor, "data_points", []),
                        }
                        for factor in market_risk_result.factors
                    ],
                    "analysis_type": "market_risk_recommendations",
                }

                # 获取AI建议
                ai_rec_result = await ai_service.analyze_with_predictor(
                    analysis_type="market_risk_recommendations", data=risk_data
                )

                # 确保使用字典访问方式获取推荐
                if isinstance(ai_rec_result, dict) and "recommendations" in ai_rec_result:
                    ai_recommendations = ai_rec_result["recommendations"]

                # 获取AI监控点
                ai_mon_result = await ai_service.analyze_with_predictor(
                    analysis_type="market_risk_monitoring_points", data=risk_data
                )

                # 确保使用字典访问方式获取监控点
                if isinstance(ai_mon_result, dict) and "monitoring_points" in ai_mon_result:
                    ai_monitoring_points = ai_mon_result["monitoring_points"]

            except Exception as ai_error:
                logger.error(f"AI市场风险分析失败: {str(ai_error)}")
                ai_insights = [f"AI市场风险分析过程中出错: {str(ai_error)}"]

        # 构建响应
        # 安全地访问market_risk_result的属性
        risk_type = getattr(market_risk_result, "risk_type", "MARKET")
        target = getattr(market_risk_result, "target", "portfolio")
        score = getattr(market_risk_result, "score", 50.0)
        recommendations = getattr(market_risk_result, "recommendations", [])
        monitoring_points = getattr(market_risk_result, "monitoring_points", [])

        # 确定风险等级
        risk_level = "HIGH" if score > 70 else "MEDIUM" if score > 40 else "LOW"

        # 安全地处理factors
        factors = []
        if hasattr(market_risk_result, "factors"):
            for factor in market_risk_result.factors:
                factors.append({
                    "name": getattr(factor, "factor_name", "未知因素"),
                    "score": getattr(factor, "score", 50.0),
                    "weight": getattr(factor, "weight", 1.0),
                    "description": getattr(factor, "description", ""),
                    "trend": getattr(factor, "trend", "稳定"),
                    "data_points": getattr(factor, "data_points", []),
                })

        response = {
            "wallet_address": wallet_address,
            "risk_type": risk_type,
            "target": target,
            "score": score,
            "risk_level": risk_level,
            "factors": factors,
            "recommendations": recommendations + ai_recommendations,
            "monitoring_points": monitoring_points + ai_monitoring_points,
            "ai_insights": ai_insights,
            "ai_available": ai_available,
            "timestamp": datetime.now().isoformat(),
        }

        return response
    except Exception as e:
        logger.error(f"分析钱包市场风险时出错: {str(e)}")
        # 如果是演示模式，尝试返回演示数据
        if settings.DEMO_MODE:
            try:
                logger.info(f"出错时使用演示数据: 钱包市场风险分析 {wallet_address}")
                return demo_service.get_wallet_market_risk(wallet_address)
            except:
                pass
        # 如果无法使用演示数据，返回错误信息
        raise HTTPException(status_code=500, detail=f"分析钱包市场风险失败: {str(e)}")


@router.get("/{wallet_address}/alerts")
async def get_wallet_alerts(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取钱包的风险警报

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包警报请求: {wallet_address}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 钱包警报 {wallet_address}")
            return demo_service.get_wallet_alerts(wallet_address)

        # 获取钱包警报
        alerts = await blockchain_service.get_wallet_alerts(wallet_address)

        # 构建响应
        response = {
            "wallet_address": wallet_address,
            "alerts": alerts,
            "alert_count": len(alerts),
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": False,
        }

        return response
    except Exception as e:
        logger.error(f"获取钱包警报时出错: {str(e)}")
        return {"error": f"获取钱包警报失败: {str(e)}"}


@router.get("/{wallet_address}/scenario-simulation")
async def simulate_market_scenario(
    wallet_address: str,
    scenario: str = "market_crash",
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
    risk_engine: RiskEngine = Depends(get_risk_engine),
):
    """
    模拟极端市场情景下的投资组合表现

    - **wallet_address**: 钱包地址
    - **scenario**: 市场情景类型
      - market_crash: 市场崩盘
      - bull_run: 牛市
      - defi_hack: DeFi黑客事件
      - regulatory_crackdown: 监管打击
    """
    try:
        logger.info(f"收到市场情景模拟请求: {wallet_address}, 情景: {scenario}")

        # 验证情景类型
        valid_scenarios = [
            "market_crash",
            "bull_run",
            "defi_hack",
            "regulatory_crackdown",
        ]
        if scenario not in valid_scenarios:
            logger.warning(f"无效的情景类型: {scenario}, 使用默认值: market_crash")
            scenario = "market_crash"

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(
                f"使用演示数据: 市场情景模拟 {wallet_address}, 情景: {scenario}"
            )
            return demo_service.get_market_scenario_simulation(wallet_address, scenario)

        # 模拟市场情景
        simulation_result = await risk_engine.simulate_market_scenario(
            wallet_address, scenario, blockchain_service
        )

        return simulation_result
    except Exception as e:
        logger.error(f"模拟市场情景时出错: {str(e)}")
        return {"error": f"模拟市场情景失败: {str(e)}"}
