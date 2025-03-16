from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.services.demo_data import DemoDataService, get_demo_data_service
from app.core.init_app import get_blockchain_service, get_ai_service
from app.core.config import settings
import logging


router = APIRouter()
logger = logging.getLogger("defi_risk.api.protocol")


@router.get("/list")
async def get_protocols(
    wallet_address: Optional[str] = None,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取协议列表

    - **wallet_address**: 可选的钱包地址，如果提供，则只返回该钱包使用的协议
    """
    try:
        if wallet_address:
            logger.info(f"收到钱包协议列表请求: {wallet_address}")
        else:
            logger.info("收到支持协议列表请求")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            if wallet_address:
                logger.info(f"使用演示数据: 钱包协议列表 {wallet_address}")
                # 获取钱包头寸
                wallet_data = demo_service.get_wallet_positions(wallet_address)

                # 直接使用钱包数据中的协议列表
                if "protocols" in wallet_data:
                    return {
                        "protocols": wallet_data["protocols"],
                        "count": len(wallet_data["protocols"]),
                        "wallet_address": wallet_address,
                    }

                # 如果没有协议列表，则提取协议列表（兼容旧版本）
                protocols_used = []
                protocols_set = set()

                for position in wallet_data.get("positions", []):
                    protocol_name = position.get("protocol", "")
                    if protocol_name and protocol_name not in protocols_set:
                        protocols_set.add(protocol_name)
                        # 获取协议详细信息
                        protocol_info = demo_service.get_protocol_info(protocol_name)
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

                return {
                    "protocols": protocols_used,
                    "count": len(protocols_used),
                    "wallet_address": wallet_address,
                }
            else:
                logger.info("使用演示数据: 所有协议列表")
                return demo_service.get_protocols()

        # 如果提供了钱包地址，获取该钱包使用的协议
        if wallet_address:
            # 获取钱包头寸
            positions = await blockchain_service.get_all_positions(wallet_address)

            # 提取协议列表
            protocols_used = []
            protocols_set = set()

            for position in positions:
                protocol_name = position.get("protocol", "")
                if protocol_name and protocol_name not in protocols_set:
                    protocols_set.add(protocol_name)
                    # 获取协议详细信息
                    try:
                        protocol_info = await blockchain_service.get_protocol_info(
                            protocol_name
                        )
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

            return {
                "protocols": protocols_used,
                "count": len(protocols_used),
                "wallet_address": wallet_address,
            }

        # 否则返回所有支持的协议列表
        # 这里应该从区块链服务获取支持的协议列表
        # 简化处理，使用模拟数据
        protocols = [
            {
                "name": "Aave",
                "chain": "Ethereum",
                "tvl": 5000000000,
                "supported_assets": ["ETH", "USDC", "DAI", "USDT", "WBTC", "LINK"],
                "features": ["借贷", "流动性挖矿", "闪电贷"],
                "description": "Aave是一个去中心化借贷平台，允许用户存款赚取利息或借款。",
            },
            {
                "name": "Compound",
                "chain": "Ethereum",
                "tvl": 3000000000,
                "supported_assets": ["ETH", "USDC", "DAI", "USDT", "WBTC"],
                "features": ["借贷", "治理"],
                "description": "Compound是一个算法性的、自主性的利率协议，为开发者建立在以太坊上的金融应用程序而设计。",
            },
            {
                "name": "Uniswap",
                "chain": "Ethereum",
                "tvl": 8000000000,
                "supported_assets": ["ETH", "USDC", "DAI", "USDT", "WBTC", "UNI"],
                "features": ["交易", "流动性提供", "收费分享"],
                "description": "Uniswap是一个去中心化交易协议，为自动化代币交易提供流动性。",
            },
            {
                "name": "Curve",
                "chain": "Ethereum",
                "tvl": 4000000000,
                "supported_assets": ["USDC", "DAI", "USDT"],
                "features": ["稳定币交换", "流动性挖矿"],
                "description": "Curve是一个为稳定币设计的交易所，提供低滑点、低费用的交易。",
            },
            {
                "name": "MakerDAO",
                "chain": "Ethereum",
                "tvl": 7000000000,
                "supported_assets": ["ETH", "WBTC"],
                "features": ["抵押", "稳定币铸造"],
                "description": "MakerDAO是一个去中心化自治组织，创建并维护DAI稳定币。",
            },
            {
                "name": "SushiSwap",
                "chain": "Ethereum",
                "tvl": 2000000000,
                "supported_assets": ["ETH", "USDC", "DAI", "SUSHI"],
                "features": ["交易", "流动性挖矿", "收益农场"],
                "description": "SushiSwap是一个去中心化交易所，提供代币交换和流动性挖矿服务。",
            },
            {
                "name": "Balancer",
                "chain": "Ethereum",
                "tvl": 1500000000,
                "supported_assets": ["ETH", "USDC", "DAI", "BAL"],
                "features": ["多资产池", "流动性挖矿"],
                "description": "Balancer是一个自动化投资组合管理器和交易平台。",
            },
            {
                "name": "Yearn",
                "chain": "Ethereum",
                "tvl": 1000000000,
                "supported_assets": ["ETH", "USDC", "DAI", "YFI"],
                "features": ["收益聚合", "自动复投"],
                "description": "Yearn是一个收益聚合器，自动优化用户的DeFi收益。",
            },
            {
                "name": "PancakeSwap",
                "chain": "BSC",
                "tvl": 6000000000,
                "supported_assets": ["BNB", "BUSD", "CAKE"],
                "features": ["交易", "流动性挖矿", "彩票"],
                "description": "PancakeSwap是币安智能链上的去中心化交易所。",
            },
            {
                "name": "dYdX",
                "chain": "Ethereum",
                "tvl": 900000000,
                "supported_assets": ["ETH", "USDC"],
                "features": ["杠杆交易", "永续合约"],
                "description": "dYdX是一个去中心化交易平台，提供杠杆和衍生品交易。",
            },
        ]

        return {"protocols": protocols, "count": len(protocols)}
    except Exception as e:
        logger.error(f"获取协议列表时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info("出错时使用演示数据: 协议列表")
            return demo_service.get_protocols()
        raise HTTPException(status_code=500, detail=f"获取协议列表失败: {str(e)}")


@router.get("/{protocol_name}")
async def get_protocol_info(
    protocol_name: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取协议信息

    - **protocol_name**: 协议名称
    """
    try:
        logger.info(f"收到协议信息请求: {protocol_name}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 协议信息 {protocol_name}")
            return demo_service.get_protocol_info(protocol_name)

        # 获取协议信息
        protocol_info = await blockchain_service.get_protocol_info(protocol_name)
        return protocol_info
    except Exception as e:
        logger.error(f"获取协议信息时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: 协议信息 {protocol_name}")
            return demo_service.get_protocol_info(protocol_name)
        raise HTTPException(status_code=500, detail=f"获取协议信息失败: {str(e)}")


@router.get("/risk/{protocol_name}")
async def analyze_protocol_risk(
    protocol_name: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    ai_service: AiService = Depends(get_ai_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    分析协议风险

    - **protocol_name**: 协议名称
    """
    try:
        logger.info(f"收到协议风险分析请求: {protocol_name}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 协议风险 {protocol_name}")
            protocol_info = demo_service.get_protocol_info(protocol_name)
            risk_score = protocol_info.get("risk_score", 80)

            # 根据风险分数生成风险评估
            risk_level = "低"
            if risk_score < 75:
                risk_level = "高"
            elif risk_score < 85:
                risk_level = "中等"

            return {
                "protocol": protocol_name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": [
                    {
                        "factor": "智能合约风险",
                        "score": risk_score + 5 if risk_score + 5 <= 100 else 100,
                        "description": "协议经过多次审计，但仍存在潜在漏洞风险。",
                    },
                    {
                        "factor": "经济模型风险",
                        "score": risk_score - 5 if risk_score - 5 >= 0 else 0,
                        "description": "协议经济模型相对稳定，但在极端市场条件下可能面临挑战。",
                    },
                    {
                        "factor": "治理风险",
                        "score": risk_score,
                        "description": "协议治理机制较为完善，但决策过程可能存在中心化风险。",
                    },
                ],
                "recommendations": [
                    "关注协议安全更新和审计报告",
                    "分散投资，避免将大量资金集中在单一协议",
                    "了解协议治理机制和决策流程",
                ],
                "is_demo_data": True,
            }

        # 获取协议信息
        protocol_info = await blockchain_service.get_protocol_info(protocol_name)

        # 分析协议风险
        risk_analysis = await ai_service.analyze_protocol_risk(
            protocol_name, protocol_info
        )
        return risk_analysis
    except Exception as e:
        logger.error(f"分析协议风险时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: 协议风险 {protocol_name}")
            protocol_info = demo_service.get_protocol_info(protocol_name)
            risk_score = protocol_info.get("risk_score", 80)

            # 根据风险分数生成风险评估
            risk_level = "低"
            if risk_score < 75:
                risk_level = "高"
            elif risk_score < 85:
                risk_level = "中等"

            return {
                "protocol": protocol_name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": [
                    {
                        "factor": "智能合约风险",
                        "score": risk_score + 5 if risk_score + 5 <= 100 else 100,
                        "description": "协议经过多次审计，但仍存在潜在漏洞风险。",
                    },
                    {
                        "factor": "经济模型风险",
                        "score": risk_score - 5 if risk_score - 5 >= 0 else 0,
                        "description": "协议经济模型相对稳定，但在极端市场条件下可能面临挑战。",
                    },
                    {
                        "factor": "治理风险",
                        "score": risk_score,
                        "description": "协议治理机制较为完善，但决策过程可能存在中心化风险。",
                    },
                ],
                "recommendations": [
                    "关注协议安全更新和审计报告",
                    "分散投资，避免将大量资金集中在单一协议",
                    "了解协议治理机制和决策流程",
                ],
                "is_demo_data": True,
            }
        raise HTTPException(status_code=500, detail=f"分析协议风险失败: {str(e)}")
