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
from app.core.utility import create_standard_response, safe_get, ensure_list

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

            return create_standard_response(
                {
                    "positions": wallet_data.get("positions", []),
                    "total_value_usd": wallet_data.get("total_value_usd", 0),
                    "position_count": len(wallet_data.get("positions", [])),
                    "protocols": protocols_used,
                    "protocol_count": len(protocols_used),
                },
                wallet_address=wallet_address,
                is_demo=True,
            )

        # 获取所有协议头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        # 计算总价值
        total_value = 0
        for position in positions:
            if "total_assets" in position:
                total_value += float(position.get("total_assets", 0))
            elif "amount" in position:
                total_value += float(position.get("amount", 0))

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
                                "chain", position.get("chain", "Ethereum")
                            ),
                            "tvl": protocol_info.get("tvl", 0),
                            "supported_assets": protocol_info.get(
                                "supported_assets", ["ETH", "USDC"]
                            ),
                            "features": protocol_info.get("coingecko", {}).get(
                                "categories", ["借贷", "流动性挖矿"]
                            ),
                            "description": protocol_info.get("coingecko", {}).get(
                                "description", f"{protocol_name}是一个DeFi协议"
                            ),
                            "contract_addresses": protocol_info.get("coingecko", {})
                            .get("contract_addresses", {})
                            .get("ethereum", ""),
                        }
                    )
                except Exception:
                    # 如果获取协议信息失败，使用基本信息
                    protocols_used.append(
                        {
                            "name": protocol_name,
                            "chain": position.get("chain", "Unknown"),
                            "tvl": 0,
                            "supported_assets": [position.get("asset", "Unknown")],
                            "features": ["质押", "流动性挖矿"],
                            "description": f"{protocol_name}是一个DeFi协议",
                        }
                    )

        # 构建响应
        response = create_standard_response(
            {
                "positions": positions,
                "total_value_usd": total_value,
                "position_count": len(positions),
                "protocols": protocols_used,
                "protocol_count": len(protocols_used),
            },
            wallet_address=wallet_address,
        )

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

        # 检查区块链服务是否可用，不可用时使用演示数据
        if not blockchain_service or not hasattr(
            blockchain_service, "get_all_positions"
        ):
            logger.warning("区块链服务不可用，使用演示数据")
            if settings.DEMO_MODE:
                return demo_service.analyze_wallet_risk(wallet_address)
            else:
                raise HTTPException(status_code=503, detail="区块链服务暂时不可用")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 钱包风险 {wallet_address}")
            demo_risk_data = demo_service.analyze_wallet_risk(wallet_address)

            # 确保演示数据中的assets是完整的
            if not demo_risk_data.get("positions_summary", {}).get("assets"):
                wallet_data = demo_service.get_wallet_positions(wallet_address)
                positions = wallet_data.get("positions", [])

                # 使用优化后的逻辑收集所有资产
                assets = set()
                for p in positions:
                    # 直接从positions获取asset
                    if "asset" in p:
                        assets.add(p["asset"])
                    # 从嵌套的positions子数组获取asset
                    if "positions" in p:
                        for sub_p in p["positions"]:
                            if "asset" in sub_p and sub_p["asset"]:
                                assets.add(sub_p["asset"])
                            # 从tokenList中获取资产
                            if "tokenList" in sub_p:
                                for token in sub_p["tokenList"]:
                                    if "tokenSymbol" in token and token["tokenSymbol"]:
                                        assets.add(token["tokenSymbol"])

                # 过滤掉空值并更新demo_risk_data
                assets = list(filter(None, assets))
                if assets and "positions_summary" in demo_risk_data:
                    demo_risk_data["positions_summary"]["assets"] = assets

            return demo_risk_data

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
        result = create_standard_response(
            {
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
                        safe_get_position_value(position) for position in positions
                    ),
                    "position_count": len(positions),
                    "protocols": list(
                        filter(
                            None, set(safe_get(p, "protocol", "") for p in positions)
                        )
                    ),
                    "assets": list(
                        filter(
                            None,
                            {
                                # 直接从positions对象中提取asset字段
                                safe_get(p, "asset", "")
                                for p in positions
                            }
                            .union(
                                {
                                    # 从嵌套的positions子数组中提取asset字段
                                    safe_get(sub_p, "asset", "")
                                    for p in positions
                                    if has_positions(p)
                                    for sub_p in ensure_list(
                                        safe_get(p, "positions", [])
                                    )
                                }
                            )
                            .union(
                                {
                                    # 考虑tokenList中可能的资产
                                    safe_get(token, "tokenSymbol", "")
                                    for p in positions
                                    if has_positions(p)
                                    for sub_p in ensure_list(
                                        safe_get(p, "positions", [])
                                    )
                                    if has_token_list(sub_p)
                                    for token in ensure_list(
                                        safe_get(sub_p, "tokenList", [])
                                    )
                                }
                            ),
                        )
                    ),
                },
                "ai_enhanced": ai_insights.get("recommendations", []) != [],
            },
            wallet_address=wallet_address,
        )

        return result
    except Exception as e:
        logger.error(f"分析钱包风险时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: 钱包风险 {wallet_address}")
            demo_risk_data = demo_service.analyze_wallet_risk(wallet_address)

            # 确保演示数据中的assets是完整的
            if not demo_risk_data.get("positions_summary", {}).get("assets"):
                wallet_data = demo_service.get_wallet_positions(wallet_address)
                positions = wallet_data.get("positions", [])

                # 使用优化后的逻辑收集所有资产
                assets = set()
                for p in positions:
                    # 直接从positions获取asset
                    if "asset" in p:
                        assets.add(p["asset"])
                    # 从嵌套的positions子数组获取asset
                    if "positions" in p:
                        for sub_p in p["positions"]:
                            if "asset" in sub_p and sub_p["asset"]:
                                assets.add(sub_p["asset"])
                            # 从tokenList中获取资产
                            if "tokenList" in sub_p:
                                for token in sub_p["tokenList"]:
                                    if "tokenSymbol" in token and token["tokenSymbol"]:
                                        assets.add(token["tokenSymbol"])

                # 过滤掉空值并更新demo_risk_data
                assets = list(filter(None, assets))
                if assets and "positions_summary" in demo_risk_data:
                    demo_risk_data["positions_summary"]["assets"] = assets

            return demo_risk_data

        raise HTTPException(status_code=500, detail=f"分析钱包风险失败: {str(e)}")


def safe_get_position_value(position):
    """
    安全获取头寸的价值，处理不同类型的头寸对象

    Args:
        position: 头寸对象，可能是字典或PlatformAsset类型

    Returns:
        float: 头寸价值
    """
    # 尝试获取total_assets
    total_assets = safe_get(position, "total_assets", None)
    if total_assets is not None:
        try:
            return float(total_assets)
        except (ValueError, TypeError):
            pass

    # 尝试获取amount
    amount = safe_get(position, "amount", 0)
    try:
        return float(amount)
    except (ValueError, TypeError):
        return 0


def has_positions(obj):
    """
    检查对象是否有positions属性或键

    Args:
        obj: 要检查的对象

    Returns:
        bool: 是否有positions
    """
    if isinstance(obj, dict):
        return "positions" in obj
    return hasattr(obj, "positions") and getattr(obj, "positions") is not None


def has_token_list(obj):
    """
    检查对象是否有tokenList属性或键

    Args:
        obj: 要检查的对象

    Returns:
        bool: 是否有tokenList
    """
    if isinstance(obj, dict):
        return "tokenList" in obj
    return hasattr(obj, "tokenList") and getattr(obj, "tokenList") is not None


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
        response = create_standard_response(
            {
                "alerts": alerts,
                "alert_count": len(alerts),
            },
            wallet_address=wallet_address,
        )

        return response
    except Exception as e:
        logger.error(f"获取钱包警报时出错: {str(e)}")
        # 如果是演示模式，尝试返回演示数据
        if settings.DEMO_MODE:
            try:
                logger.info(f"出错时使用演示数据: 钱包警报 {wallet_address}")
                return demo_service.get_wallet_alerts(wallet_address)
            except Exception as demo_err:
                logger.warning(f"使用演示数据也失败: {str(demo_err)}")
        # 统一使用HTTPException
        raise HTTPException(status_code=500, detail=f"获取钱包警报失败: {str(e)}")


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

        # 确保响应格式一致 - 使用safe_get处理不同类型的结果对象
        if not safe_get(simulation_result, "timestamp"):
            if isinstance(simulation_result, dict):
                simulation_result["timestamp"] = datetime.now().isoformat()

        if not safe_get(simulation_result, "is_demo_data"):
            if isinstance(simulation_result, dict):
                simulation_result["is_demo_data"] = False

        return create_standard_response(
            simulation_result, wallet_address=wallet_address
        )
    except Exception as e:
        logger.error(f"模拟市场情景时出错: {str(e)}")
        # 如果是演示模式，尝试返回演示数据
        if settings.DEMO_MODE:
            try:
                logger.info(
                    f"出错时使用演示数据: 市场情景模拟 {wallet_address}, 情景: {scenario}"
                )
                return demo_service.get_market_scenario_simulation(
                    wallet_address, scenario
                )
            except Exception as demo_err:
                logger.warning(f"使用演示数据也失败: {str(demo_err)}")
        # 统一使用HTTPException
