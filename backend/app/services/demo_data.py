"""
演示数据服务
提供各种API端点的演示数据
"""

from typing import Dict, List, Any, Optional
import random
from datetime import datetime, timedelta
import logging
import math

from app.core.config import Settings

logger = logging.getLogger("defi_risk.services.demo_data")


class DemoDataService:
    """演示数据服务"""

    def __init__(self):
        """初始化演示数据服务"""
        logger.info("初始化演示数据服务")
        # 缓存一些演示数据，避免每次请求都生成新的随机数据
        self._demo_data_cache = {}
        self._last_refresh = datetime.now()

    def refresh_data(self) -> Dict[str, Any]:
        """刷新演示数据"""
        logger.info("刷新演示数据")
        self._demo_data_cache = {}
        self._last_refresh = datetime.now()
        return {
            "status": "success",
            "message": "演示数据已刷新",
            "timestamp": self._last_refresh.isoformat(),
        }

    def get_demo_status(self, demo_accounts: List[Dict[str, str]]) -> Dict[str, Any]:
        """获取演示模式状态"""
        return {
            "demo_mode": True,
            "api_version": "1.0.0",
            "last_refresh": self._last_refresh.isoformat(),
            "demo_accounts": demo_accounts,
        }

    def get_market_data(self, asset: str) -> Dict[str, Any]:
        """获取资产市场数据"""
        cache_key = f"market_data_{asset}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 为不同资产生成不同的演示数据
        price_map = {
            "ETH": random.uniform(2800, 3200),
            "BTC": random.uniform(58000, 62000),
            "USDC": 1.0,
            "USDT": 1.0,
            "DAI": 1.0,
            "AAVE": random.uniform(80, 120),
            "UNI": random.uniform(5, 15),
            "COMP": random.uniform(40, 60),
            "MKR": random.uniform(1200, 1800),
            "SNX": random.uniform(2, 5),
        }

        price = price_map.get(asset.upper(), random.uniform(10, 1000))
        price_change = random.uniform(-5, 8)
        volume = random.uniform(500000000, 2000000000)
        market_cap = price * random.uniform(10000000, 100000000)

        data = {
            "asset": asset,
            "price": round(price, 2),
            "price_change_24h": round(price_change, 2),
            "volume_24h": round(volume, 2),
            "market_cap": round(market_cap, 2),
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = data
        return data

    def get_gas_price(self) -> Dict[str, Any]:
        """获取Gas价格"""
        cache_key = "gas_price"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        base_fee = random.uniform(15, 25)
        priority_fee = random.uniform(1, 3)

        data = {
            "base_fee_gwei": round(base_fee, 2),
            "priority_fee_gwei": round(priority_fee, 2),
            "total_gwei": round(base_fee + priority_fee, 2),
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = data
        return data

    def get_protocols(self) -> Dict[str, Any]:
        """获取协议列表"""
        cache_key = "protocols"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        protocols = [
            {"name": "Aave", "chain": "Ethereum", "tvl": 5000000000, "risk_score": 85},
            {
                "name": "Compound",
                "chain": "Ethereum",
                "tvl": 3000000000,
                "risk_score": 82,
            },
            {
                "name": "Uniswap",
                "chain": "Ethereum",
                "tvl": 8000000000,
                "risk_score": 88,
            },
            {"name": "Curve", "chain": "Ethereum", "tvl": 4000000000, "risk_score": 80},
            {
                "name": "MakerDAO",
                "chain": "Ethereum",
                "tvl": 7000000000,
                "risk_score": 90,
            },
            {
                "name": "SushiSwap",
                "chain": "Ethereum",
                "tvl": 2000000000,
                "risk_score": 75,
            },
            {
                "name": "Balancer",
                "chain": "Ethereum",
                "tvl": 1500000000,
                "risk_score": 78,
            },
            {"name": "Yearn", "chain": "Ethereum", "tvl": 1000000000, "risk_score": 76},
            {
                "name": "PancakeSwap",
                "chain": "BSC",
                "tvl": 6000000000,
                "risk_score": 72,
            },
            {"name": "dYdX", "chain": "Ethereum", "tvl": 900000000, "risk_score": 79},
        ]

        data = {
            "protocols": protocols,
            "count": len(protocols),
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = data
        return data

    def get_protocol_info(self, protocol_name: str) -> Dict[str, Any]:
        """获取协议信息"""
        cache_key = f"protocol_info_{protocol_name.lower()}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 为不同协议生成不同的演示数据
        protocol_info = {
            "aave": {
                "name": "Aave",
                "description": "Aave是一个去中心化借贷平台，允许用户存款赚取利息或借款。",
                "website": "https://aave.com",
                "tvl": 5000000000,
                "supported_assets": ["ETH", "USDC", "DAI", "USDT", "WBTC", "LINK"],
                "features": ["借贷", "流动性挖矿", "闪电贷"],
                "risk_score": 85,
                "audit_reports": [
                    "https://example.com/aave-audit1",
                    "https://example.com/aave-audit2",
                ],
            },
            "compound": {
                "name": "Compound",
                "description": "Compound是一个算法性的、自主性的利率协议，为开发者建立在以太坊上的金融应用程序而设计。",
                "website": "https://compound.finance",
                "tvl": 3000000000,
                "supported_assets": ["ETH", "USDC", "DAI", "USDT", "WBTC"],
                "features": ["借贷", "治理"],
                "risk_score": 82,
                "audit_reports": ["https://example.com/compound-audit1"],
            },
            "uniswap": {
                "name": "Uniswap",
                "description": "Uniswap是一个去中心化交易协议，为自动化代币交易提供流动性。",
                "website": "https://uniswap.org",
                "tvl": 8000000000,
                "supported_assets": ["ETH", "USDC", "DAI", "USDT", "WBTC", "UNI"],
                "features": ["交易", "流动性提供", "收费分享"],
                "risk_score": 88,
                "audit_reports": [
                    "https://example.com/uniswap-audit1",
                    "https://example.com/uniswap-audit2",
                ],
            },
        }

        # 如果没有特定协议的信息，生成通用信息
        if protocol_name.lower() not in protocol_info:
            data = {
                "name": protocol_name,
                "description": f"{protocol_name}是一个DeFi协议。",
                "website": f"https://{protocol_name.lower()}.io",
                "tvl": random.uniform(500000000, 5000000000),
                "supported_assets": ["ETH", "USDC", "DAI"],
                "features": ["借贷", "交易"],
                "risk_score": random.randint(70, 90),
                "audit_reports": [
                    f"https://example.com/{protocol_name.lower()}-audit1"
                ],
                "is_demo_data": True,
            }
        else:
            data = protocol_info[protocol_name.lower()]
            data["is_demo_data"] = True

        self._demo_data_cache[cache_key] = data
        return data

    def get_wallet_positions(self, wallet_address: str) -> Dict[str, Any]:
        """获取钱包头寸"""
        cache_key = f"wallet_positions_{wallet_address}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 获取协议信息，用于丰富头寸数据
        protocols_data = self.get_protocols()
        protocols_map = {p["name"]: p for p in protocols_data["protocols"]}

        # 为指定的测试钱包地址生成特定头寸数据
        if wallet_address == "0x881896A2E1D65f5dfA4d23Bf6b917cE703ed068b":
            # 特定的协议数据
            positions = [
                {
                    "protocol": "Aethir",
                    "total_assets": 24.853047218058176,
                    "total_debts": 0,
                    "leverage": 1,
                    "positions": [
                        {
                            "protocol": "Aethir",
                            "asset": "ATH",
                            "amount": 24.853047218058176,
                            "invest_type": 5,
                            "apy": None,
                            "tokenList": [
                                {
                                    "tokenSymbol": "ATH",
                                    "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/1-0xbe0ed4138121ecfc5c0e56b40517da27e6c5226b-97.png/type=default_350_0",
                                    "coinAmount": "700",
                                    "currencyAmount": "20.6723120784516392",
                                    "tokenPrecision": 18,
                                    "tokenAddress": "0xbe0ed4138121ecfc5c0e56b40517da27e6c5226b",
                                    "network": "ETH",
                                },
                                {
                                    "tokenSymbol": "ATH",
                                    "tokenType": "reward",
                                    "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/1-0xbe0ed4138121ecfc5c0e56b40517da27e6c5226b-97.png/type=default_350_0",
                                    "coinAmount": "141.566873923846617599",
                                    "currencyAmount": "4.180735139606535478423888582881597544",
                                    "tokenPrecision": 18,
                                    "tokenAddress": "0xbe0ed4138121ecfc5c0e56b40517da27e6c5226b",
                                    "network": "ETH",
                                },
                                {
                                    "tokenSymbol": "$MICRO",
                                    "tokenType": "reward",
                                    "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/1-0x8cedb0680531d26e62abdbd0f4c5428b7fdc26d5-97.png/type=default_350_0?v=1737438768635",
                                    "coinAmount": "0",
                                    "currencyAmount": "0",
                                    "tokenPrecision": 18,
                                    "tokenAddress": "0x8cedb0680531d26e62abdbd0f4c5428b7fdc26d5",
                                    "network": "ETH",
                                },
                            ],
                        }
                    ],
                },
                {
                    "protocol": "Data Ownership Protocol",
                    "total_assets": 7.873041229406134,
                    "total_debts": 0,
                    "leverage": 1,
                    "positions": [
                        {
                            "protocol": "Data Ownership Protocol",
                            "asset": "DOP",
                            "amount": 7.873041229406134,
                            "invest_type": 5,
                            "apy": None,
                            "tokenList": [
                                {
                                    "tokenSymbol": "DOP",
                                    "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/1-0x97a9a15168c22b3c137e6381037e1499c8ad0978.png/type=default_350_0",
                                    "coinAmount": "18823.556555002779517212",
                                    "currencyAmount": "7.348927005958289431130504714770158588",
                                    "tokenPrecision": 18,
                                    "tokenAddress": "0x97a9a15168c22b3c137e6381037e1499c8ad0978",
                                    "network": "ETH",
                                },
                                {
                                    "tokenSymbol": "DOP",
                                    "tokenType": "reward",
                                    "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/1-0x97a9a15168c22b3c137e6381037e1499c8ad0978.png/type=default_350_0",
                                    "coinAmount": "1342.46723614931240325",
                                    "currencyAmount": "0.52411422344784457827242483007770925",
                                    "tokenPrecision": 18,
                                    "tokenAddress": "0x97a9a15168c22b3c137e6381037e1499c8ad0978",
                                    "network": "ETH",
                                },
                            ],
                        }
                    ],
                },
                {
                    "protocol": "sophon",
                    "total_assets": 0,
                    "total_debts": 0,
                    "leverage": 0,
                    "positions": [],
                },
            ]

            # 自定义的协议信息
            protocols_used = [
                {
                    "name": "Aethir",
                    "chain": "Ethereum",
                    "tvl": [],
                    "supported_assets": ["ETH", "USDC"],
                    "features": ["借贷", "流动性挖矿"],
                    "description": "Powerful GPU compute solutions on-demand.",
                },
                {
                    "name": "Data Ownership Protocol",
                    "chain": "Unknown",
                    "tvl": 0,
                    "supported_assets": ["ETH", "USDC"],
                    "features": ["借贷", "流动性挖矿"],
                    "description": "Data Ownership Protocol是一个DeFi协议",
                },
                {
                    "name": "sophon",
                    "chain": "Unknown",
                    "tvl": 0,
                    "supported_assets": ["ETH", "USDC"],
                    "features": ["借贷", "流动性挖矿"],
                    "description": "sophon是一个DeFi协议",
                },
            ]

            data = {
                "wallet_address": wallet_address,
                "positions": positions,
                "total_value_usd": 32.726088447464306,
                "position_count": len(positions),
                "protocols": protocols_used,
                "protocol_count": len(protocols_used),
                "timestamp": datetime.now().isoformat(),
                "is_demo_data": True,
            }

            self._demo_data_cache[cache_key] = data
            return data

        # 为演示账户1生成特定的头寸数据
        elif wallet_address == "0xdemo1234567890abcdef1234567890abcdef123456":
            positions = [
                {
                    "protocol": "Aave",
                    "type": "lending",
                    "asset": "ETH",
                    "amount": 5.0,
                    "usd_value": 15000.0,
                    "apy": 2.5,
                    "chain": "Ethereum",
                },
                {
                    "protocol": "Compound",
                    "type": "lending",
                    "asset": "USDC",
                    "amount": 10000.0,
                    "usd_value": 10000.0,
                    "apy": 3.2,
                    "chain": "Ethereum",
                },
                {
                    "protocol": "Uniswap",
                    "type": "liquidity",
                    "asset": "ETH-USDC",
                    "amount": 2.0,
                    "usd_value": 8000.0,
                    "apy": 15.5,
                    "chain": "Ethereum",
                },
                {
                    "protocol": "MakerDAO",
                    "type": "cdp",
                    "asset": "ETH",
                    "amount": 10.0,
                    "usd_value": 30000.0,
                    "leverage": 2.0,
                    "chain": "Ethereum",
                },
            ]
        # 为演示账户2生成高风险头寸数据
        elif wallet_address == "0xdemo2234567890abcdef1234567890abcdef123456":
            positions = [
                {
                    "protocol": "dYdX",
                    "type": "margin",
                    "asset": "ETH",
                    "amount": 10.0,
                    "usd_value": 30000.0,
                    "leverage": 5.0,
                    "chain": "Ethereum",
                },
                {
                    "protocol": "Aave",
                    "type": "borrowing",
                    "asset": "USDC",
                    "amount": 20000.0,
                    "usd_value": 20000.0,
                    "apy": 4.5,
                    "chain": "Ethereum",
                },
                {
                    "protocol": "SushiSwap",
                    "type": "farming",
                    "asset": "SUSHI-ETH",
                    "amount": 5.0,
                    "usd_value": 15000.0,
                    "apy": 45.0,
                    "chain": "Ethereum",
                },
            ]
        # 为其他钱包生成随机头寸数据
        else:
            positions = [
                {
                    "protocol": "Aave",
                    "type": "lending",
                    "asset": "ETH",
                    "amount": random.uniform(1, 10),
                    "usd_value": random.uniform(3000, 30000),
                    "apy": random.uniform(1, 5),
                    "chain": "Ethereum",
                },
                {
                    "protocol": "Compound",
                    "type": "lending",
                    "asset": "USDC",
                    "amount": random.uniform(1000, 20000),
                    "usd_value": random.uniform(1000, 20000),
                    "apy": random.uniform(2, 6),
                    "chain": "Ethereum",
                },
            ]

        # 丰富头寸数据，添加协议详细信息
        for position in positions:
            protocol_name = position["protocol"]
            if protocol_name in protocols_map:
                protocol_info = protocols_map[protocol_name]
                position["protocol_info"] = {
                    "name": protocol_name,
                    "chain": protocol_info.get("chain", "Ethereum"),
                    "tvl": protocol_info.get("tvl", 0),
                    "risk_score": protocol_info.get("risk_score", 80),
                }
            else:
                # 如果找不到协议信息，提供默认值
                position["protocol_info"] = {
                    "name": protocol_name,
                    "chain": position.get("chain", "Ethereum"),
                    "tvl": 0,
                    "risk_score": 80,
                }

        total_value = sum(position.get("usd_value", 0) for position in positions)

        # 提取协议列表，确保包含前端需要的字段
        protocols_used = []
        protocols_set = set()

        for position in positions:
            protocol_name = position.get("protocol", "")
            if protocol_name and protocol_name not in protocols_set:
                protocols_set.add(protocol_name)
                # 获取协议详细信息
                protocol_info = self.get_protocol_info(protocol_name)
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
                        "features": protocol_info.get(
                            "features", ["借贷", "流动性挖矿"]
                        ),
                        "description": protocol_info.get(
                            "description", f"{protocol_name}是一个DeFi协议"
                        ),
                    }
                )

        data = {
            "wallet_address": wallet_address,
            "positions": positions,
            "total_value_usd": total_value,
            "position_count": len(positions),
            "protocols": protocols_used,  # 添加协议列表
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = data
        return data

    def analyze_wallet_risk(self, wallet_address: str) -> Dict[str, Any]:
        """分析钱包风险"""
        cache_key = f"wallet_risk_{wallet_address}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 获取钱包头寸数据
        positions_data = self.get_wallet_positions(wallet_address)
        positions = positions_data.get("positions", [])
        position_count = positions_data.get("position_count", 0)

        # 为指定的测试钱包地址生成特定风险分析
        if wallet_address == "0x881896A2E1D65f5dfA4d23Bf6b917cE703ed068b":
            risk_score = 35  # 较低风险
            risk_level = "低风险"

            risk_factors = [
                {
                    "factor": "资产集中度",
                    "score": 50,
                    "weight": 0.25,
                    "description": "投资组合中Aethir占比较高(约76%)，增加了单一协议风险。",
                },
                {
                    "factor": "质押协议风险",
                    "score": 40,
                    "weight": 0.2,
                    "description": "Aethir是一个新兴协议，可能面临验证者风险和智能合约风险。",
                },
                {
                    "factor": "总资产规模",
                    "score": 20,
                    "weight": 0.15,
                    "description": "总资产价值较小($32.73)，总体风险敞口有限。",
                },
                {
                    "factor": "杠杆风险",
                    "score": 10,
                    "weight": 0.15,
                    "description": "无杠杆头寸，降低了市场波动带来的风险。",
                },
                {
                    "factor": "协议安全性",
                    "score": 35,
                    "weight": 0.15,
                    "description": "所持有的协议已经过安全审计，但仍存在智能合约风险。",
                },
                {
                    "factor": "质押流动性风险",
                    "score": 40,
                    "weight": 0.1,
                    "description": "质押资产存在一定的解除质押期，可能影响流动性。",
                },
            ]

            recommendations = [
                "考虑分散投资到不同类型的质押协议",
                "关注Aethir和Data Ownership Protocol的安全更新和审计报告",
                "定期检查质押资产的解质押期和流动性状况",
                "考虑增加Aave等成熟DeFi协议的资产配置以平衡风险",
            ]

            data = {
                "wallet_address": wallet_address,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
                "risk_metrics": {
                    "market_risk_score": 30,
                    "protocol_risk_score": 40,
                    "liquidity_risk_score": 35,
                    "concentration_risk_score": 50,
                    "smart_contract_risk_score": 38,  # 新增：智能合约风险评分
                    "token_economics_risk_score": 42,  # 新增：代币经济模型风险评分
                },
                "positions_summary": {
                    "total_value": positions_data["total_value_usd"],
                    "position_count": position_count,
                    "protocols": ["Aethir", "Data Ownership Protocol", "sophon"],
                    "assets": ["ATH", "DOP"],
                },
                "warnings": [
                    "投资组合中质押协议占比较高，建议多样化",
                    "ATH代币的流动性较低，可能面临退出困难",  # 新增：流动性风险警告
                ],
                "monitoring_points": [
                    "关注Aethir协议的开发和安全状况",
                    "关注DOP稳定币的锚定状态",
                    "监控ATH代币的交易量变化",  # 新增：监控点
                    "关注新兴协议的安全审计报告更新",  # 新增：监控点
                ],
                "detailed_analysis": {  # 新增：详细分析部分
                    "liquidity_analysis": {
                        "ATH": {
                            "daily_volume": "$245,000",
                            "market_depth": "低",
                            "slippage_risk": "高",
                            "exchange_listings": ["DEX只有Uniswap V3"],
                            "risk_level": "高",
                        },
                        "DOP": {
                            "daily_volume": "$1,250,000",
                            "market_depth": "中",
                            "slippage_risk": "中",
                            "exchange_listings": ["Uniswap V3", "Balancer"],
                            "risk_level": "中",
                        },
                    },
                    "smart_contract_security": {
                        "Aethir": {
                            "audit_count": 1,
                            "last_audit_date": "2023-12-15",
                            "audit_firms": ["BlockSec"],
                            "known_issues": 2,
                            "risk_level": "中高",
                        },
                        "Data Ownership Protocol": {
                            "audit_count": 2,
                            "last_audit_date": "2024-01-10",
                            "audit_firms": ["CertiK", "PeckShield"],
                            "known_issues": 1,
                            "risk_level": "中",
                        },
                        "sophon": {
                            "audit_count": 0,
                            "last_audit_date": null,
                            "audit_firms": [],
                            "known_issues": 0,
                            "risk_level": "未知",
                        },
                    },
                    "token_economics": {
                        "ATH": {
                            "total_supply": "100,000,000",
                            "circulating_supply": "12,500,000",
                            "inflation_rate": "15% 年通胀",
                            "token_utility": "平台治理和手续费折扣",
                            "vesting_schedule": "团队解锁期为4年",
                            "risk_level": "中高",
                        },
                        "DOP": {
                            "total_supply": "1,000,000,000",
                            "circulating_supply": "150,000,000",
                            "inflation_rate": "8% 年通胀",
                            "token_utility": "质押奖励和协议治理",
                            "vesting_schedule": "早期投资者锁定期为2年",
                            "risk_level": "中",
                        },
                    },
                },
                "timestamp": datetime.now().isoformat(),
                "is_demo_data": True,
            }

            self._demo_data_cache[cache_key] = data
            return data

        # 为演示账户1生成低风险分析
        elif wallet_address == "0xdemo1234567890abcdef1234567890abcdef123456":
            risk_score = 65
            risk_level = "中等"
            risk_factors = [
                {
                    "factor": "市场风险",
                    "score": 60,
                    "weight": 0.3,
                    "description": "投资组合中ETH占比较高，市场波动风险中等。",
                },
                {
                    "factor": "协议风险",
                    "score": 85,
                    "weight": 0.15,
                    "description": "使用的协议安全性较高，但仍有一定风险。",
                },
                {
                    "factor": "流动性风险",
                    "score": 70,
                    "weight": 0.2,
                    "description": "部分资产流动性较好，但Uniswap流动性池存在无常损失风险。",
                },
                {
                    "factor": "智能合约风险",
                    "score": 80,
                    "weight": 0.2,
                    "description": "使用的协议经过多次审计，但仍存在潜在漏洞风险。",
                },
                {
                    "factor": "相关性风险",
                    "score": 50,
                    "weight": 0.1,
                    "description": "资产之间相关性较高，市场下跌时可能同时受影响。",
                },
                {
                    "factor": "监管风险",
                    "score": 60,
                    "weight": 0.05,
                    "description": "DeFi领域监管不确定性较高。",
                },
            ]
            recommendations = [
                "考虑分散投资，减少ETH集中度",
                "关注MakerDAO的抵押率，避免清算风险",
                "定期检查协议安全更新",
                "考虑增加稳定币比例以降低波动风险",
            ]
        # 为演示账户2生成高风险分析
        elif wallet_address == "0xdemo2234567890abcdef1234567890abcdef123456":
            risk_score = 85
            risk_level = "高"
            risk_factors = [
                {
                    "factor": "市场风险",
                    "score": 90,
                    "weight": 0.3,
                    "description": "高杠杆交易风险极高，市场波动可能导致强制清算。",
                },
                {
                    "factor": "协议风险",
                    "score": 75,
                    "weight": 0.15,
                    "description": "使用的部分协议安全性有待验证。",
                },
                {
                    "factor": "流动性风险",
                    "score": 80,
                    "weight": 0.2,
                    "description": "高收益农场流动性较低，退出可能面临滑点。",
                },
                {
                    "factor": "智能合约风险",
                    "score": 85,
                    "weight": 0.2,
                    "description": "部分协议代码未经全面审计，存在漏洞风险。",
                },
                {
                    "factor": "相关性风险",
                    "score": 90,
                    "weight": 0.1,
                    "description": "资产高度相关，市场下跌时风险集中。",
                },
                {
                    "factor": "监管风险",
                    "score": 80,
                    "weight": 0.05,
                    "description": "部分协议可能面临监管压力。",
                },
            ]
            recommendations = [
                "降低杠杆率，减少强制清算风险",
                "减少借贷比例，增加安全边际",
                "分散投资到更多经过审计的协议",
                "设置止损策略，控制下行风险",
                "考虑将部分高风险资产转换为稳定币",
            ]
        # 为其他钱包生成随机风险分析
        else:
            risk_score = random.randint(50, 80)
            risk_levels = {
                (0, 50): "低",
                (50, 70): "中等",
                (70, 85): "高",
                (85, 100): "极高",
            }
            risk_level = next(
                (
                    level
                    for (lower, upper), level in risk_levels.items()
                    if lower <= risk_score < upper
                ),
                "中等",
            )
            risk_factors = [
                {
                    "factor": "市场风险",
                    "score": random.randint(50, 90),
                    "weight": 0.3,
                    "description": "市场波动可能影响投资组合价值。",
                },
                {
                    "factor": "协议风险",
                    "score": random.randint(60, 90),
                    "weight": 0.15,
                    "description": "协议安全性和稳定性存在一定风险。",
                },
                {
                    "factor": "流动性风险",
                    "score": random.randint(50, 85),
                    "weight": 0.2,
                    "description": "部分资产流动性有限，可能面临退出困难。",
                },
                {
                    "factor": "智能合约风险",
                    "score": random.randint(60, 90),
                    "weight": 0.2,
                    "description": "智能合约可能存在漏洞或安全隐患。",
                },
                {
                    "factor": "相关性风险",
                    "score": random.randint(50, 85),
                    "weight": 0.1,
                    "description": "资产相关性可能导致风险集中。",
                },
                {
                    "factor": "监管风险",
                    "score": random.randint(60, 90),
                    "weight": 0.05,
                    "description": "监管政策变化可能影响投资。",
                },
            ]
            recommendations = [
                "分散投资到不同类型的资产",
                "关注协议安全更新和审计报告",
                "设置适当的风险控制策略",
                "定期重新平衡投资组合",
            ]

        data = {
            "wallet_address": wallet_address,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "positions_summary": {
                "total_value": positions_data["total_value_usd"],
                "position_count": position_count,
                "protocols": list(set(p["protocol"] for p in positions)),
                "assets": list(set(p["asset"] for p in positions)),
            },
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = data
        return data

    def get_wallet_alerts(self, wallet_address: str) -> Dict[str, Any]:
        """获取钱包警报"""
        cache_key = f"wallet_alerts_{wallet_address}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 为特定的测试钱包地址生成定制警报
        if wallet_address == "0x881896A2E1D65f5dfA4d23Bf6b917cE703ed068b":
            alerts = [
                {
                    "id": f"concentration-{int(datetime.now().timestamp())}",
                    "type": "concentration",
                    "severity": "warning",
                    "protocol": "Aethir",
                    "asset": "ATH",
                    "message": "Aethir协议占比过高(76%)，增加了单一协议风险",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "percentage": 76,
                        "threshold": 50,
                        "recommendation": "考虑分散投资到其他成熟DeFi协议以降低集中度风险",
                    },
                },
                {
                    "id": f"emerging-token-{int(datetime.now().timestamp())}",
                    "type": "emerging_risk",
                    "severity": "info",
                    "protocol": "",
                    "asset": "ATH,DOP",
                    "message": "投资组合中包含新兴代币，可能存在较高波动性",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "tokens": ["ATH", "DOP"],
                        "recommendation": "密切关注新兴代币的市场动态和项目发展",
                    },
                },
                {
                    "id": f"total-value-{int(datetime.now().timestamp())}",
                    "type": "tvl",
                    "severity": "info",
                    "protocol": "",
                    "asset": "",
                    "message": "投资组合总值较小($32.73)，风险敞口有限",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "total_value": 32.73,
                        "recommendation": "可以考虑这是试验性质的投资组合，适合尝试新的DeFi策略",
                    },
                },
            ]

            data = {
                "wallet_address": wallet_address,
                "alerts": alerts,
                "alert_count": len(alerts),
                "timestamp": datetime.now().isoformat(),
                "is_demo_data": True,
            }

            self._demo_data_cache[cache_key] = data
            return data

        # 为演示账户1生成特定警报
        elif wallet_address == "0xdemo1234567890abcdef1234567890abcdef123456":
            alerts = [
                {
                    "id": "alert-001",
                    "type": "collateral_ratio",
                    "severity": "warning",
                    "protocol": "MakerDAO",
                    "asset": "ETH",
                    "message": "抵押率接近清算阈值，建议增加抵押或减少借贷",
                    "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "details": {
                        "value": 150.0,  # 数值类型而非字符串
                        "threshold": 130.0,  # 数值类型而非字符串
                        "leverage": 2.0,
                        "recommendation": "建议增加抵押或减少借贷以降低清算风险",
                    },
                },
                {
                    "id": "alert-002",
                    "type": "price_drop",
                    "severity": "info",
                    "protocol": "",
                    "asset": "ETH",
                    "message": "ETH价格在过去24小时下跌了5%",
                    "timestamp": (datetime.now() - timedelta(hours=12)).isoformat(),
                    "details": {
                        "current_price": 3000.0,  # 数值类型
                        "previous_price": 3150.0,  # 数值类型
                        "price_change_24h": -5.0,  # 负值表示下跌
                        "volatility": 5.0,
                    },
                },
            ]
        # 为演示账户2生成高风险警报
        elif wallet_address == "0xdemo2234567890abcdef1234567890abcdef123456":
            alerts = [
                {
                    "id": "alert-003",
                    "type": "liquidation_risk",
                    "severity": "critical",
                    "protocol": "dYdX",
                    "asset": "ETH",
                    "message": "杠杆头寸接近清算价格，极高风险",
                    "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
                    "details": {
                        "current_price": 3000.0,
                        "liquidation_price": 2800.0,
                        "leverage": 5.0,
                        "safe_leverage": 3.0,
                        "risk_ratio": 0.93,  # 当前价格与清算价格的比率
                        "recommendation": "建议降低杠杆或增加抵押以避免清算",
                    },
                },
                {
                    "id": "alert-004",
                    "type": "high_utilization",
                    "severity": "warning",
                    "protocol": "Aave",
                    "asset": "USDC",
                    "message": "借贷资产利用率超过90%，利率可能上升",
                    "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
                    "details": {
                        "value": 92.0,
                        "threshold": 90.0,
                        "current_apy": 4.5,
                        "previous_apy": 3.8,
                        "apy_change": 0.7,
                    },
                },
                {
                    "id": "alert-005",
                    "type": "protocol_risk",
                    "severity": "warning",
                    "protocol": "SushiSwap",
                    "asset": "",
                    "message": "协议最近发现安全漏洞，建议关注更新",
                    "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                    "details": {
                        "recommendation": "建议减少在该协议的敞口，直到安全更新发布",
                        "analysis": "该漏洞影响流动性池合约，但尚未被利用",
                    },
                },
            ]
        # 为其他钱包生成随机警报
        else:
            alert_types = [
                "price_drop",
                "collateral_ratio",
                "protocol_risk",
                "high_utilization",
            ]
            severities = ["info", "warning", "critical"]
            protocols = ["Aave", "Compound", "Uniswap", "MakerDAO"]
            assets = ["ETH", "USDC", "DAI", "WBTC"]

            alerts = []
            for i in range(random.randint(0, 3)):
                alert_type = random.choice(alert_types)
                severity = random.choice(severities)
                protocol = random.choice(protocols)
                asset = random.choice(assets)

                # 基本警报结构
                alert = {
                    "id": f"alert-{random.randint(100, 999)}",
                    "type": alert_type,
                    "severity": severity,
                    "protocol": protocol,
                    "asset": asset,
                    "message": f"{protocol}上的{asset}存在{alert_type}风险",
                    "timestamp": (
                        datetime.now() - timedelta(hours=random.randint(1, 24))
                    ).isoformat(),
                    "details": {},
                }

                # 根据警报类型添加详细信息
                if alert_type == "price_drop":
                    price_change = random.uniform(-15, -2)
                    current_price = random.uniform(100, 3000)
                    previous_price = current_price * (1 - price_change / 100)
                    alert["details"] = {
                        "current_price": round(current_price, 2),
                        "previous_price": round(previous_price, 2),
                        "price_change_24h": round(price_change, 2),
                        "volatility": round(abs(price_change), 2),
                    }
                elif alert_type == "collateral_ratio":
                    value = random.uniform(130, 170)
                    threshold = random.uniform(110, 130)
                    alert["details"] = {
                        "value": round(value, 2),
                        "threshold": round(threshold, 2),
                        "leverage": round(100 / value * 100, 2),
                        "recommendation": "建议增加抵押或减少借贷",
                    }
                elif alert_type == "protocol_risk":
                    alert["details"] = {
                        "recommendation": "建议关注协议更新和安全公告",
                        "analysis": "该协议最近出现了一些异常活动",
                    }
                elif alert_type == "high_utilization":
                    value = random.uniform(85, 95)
                    threshold = 80
                    current_apy = random.uniform(3, 8)
                    previous_apy = random.uniform(2, 5)
                    alert["details"] = {
                        "value": round(value, 2),
                        "threshold": threshold,
                        "current_apy": round(current_apy, 2),
                        "previous_apy": round(previous_apy, 2),
                        "apy_change": round(current_apy - previous_apy, 2),
                    }

                alerts.append(alert)

        data = {
            "wallet_address": wallet_address,
            "alerts": alerts,
            "alert_count": len(alerts),
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = data
        return data

    def get_asset_price_history(self, asset: str, days: int = 30) -> Dict[str, Any]:
        """获取资产价格历史数据，用于图表展示

        参数:
            asset: 资产名称
            days: 历史天数

        返回:
            包含时间序列价格数据的字典
        """
        cache_key = f"price_history_{asset}_{days}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 生成模拟价格数据
        base_price = self.get_market_data(asset)["price"]
        price_series = []

        # 根据资产类型设定不同的波动模式
        volatility = 0.02  # 默认波动性
        if asset.upper() in ["BTC", "ETH"]:
            volatility = 0.04  # 大型资产波动性较大
        elif asset.upper() in ["USDC", "USDT", "DAI"]:
            volatility = 0.002  # 稳定币波动性很小

        # 生成历史数据点
        for i in range(days):
            date = datetime.now() - timedelta(days=days - i - 1)
            # 创建市场趋势模式，而不是纯随机
            trend_factor = 0.7 * math.sin(i / 10) + 0.3 * random.uniform(-1, 1)
            change = trend_factor * volatility
            price = base_price * (1 + change)
            base_price = price  # 让下一个价格基于当前价格

            price_series.append(
                {
                    "date": date.isoformat(),
                    "price": round(price, 2),
                    "volume": round(random.uniform(500000000, 2000000000), 2),
                }
            )

        data = {
            "asset": asset,
            "days": days,
            "data_points": price_series,
            "is_demo_data": True,
            "timestamp": datetime.now().isoformat(),
        }

        self._demo_data_cache[cache_key] = data
        return data

    def get_detailed_risk_report(self, wallet_address: str) -> Dict[str, Any]:
        """获取钱包的详细风险分析报告

        参数:
            wallet_address: 钱包地址

        返回:
            包含详细风险分析的字典
        """
        cache_key = f"risk_report_{wallet_address}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 提取钱包地址对应的演示账户类型
        risk_level = "medium"  # 默认风险级别
        for account in Settings.DEMO_ACCOUNTS:
            if account["address"] == wallet_address:
                risk_level = account.get("risk_level", "medium")
                break

        # 根据风险级别生成不同的数据
        if risk_level == "low":
            risk_score = random.randint(20, 40)
            risk_trend = "稳定"
            portfolio_concentration = "低"
            protocol_diversity = "中"
            security_score = random.randint(80, 95)
        elif risk_level == "medium":
            risk_score = random.randint(41, 70)
            risk_trend = "轻微上升"
            portfolio_concentration = "中"
            protocol_diversity = "中"
            security_score = random.randint(65, 85)
        elif risk_level == "medium-high":
            risk_score = random.randint(71, 80)
            risk_trend = "上升"
            portfolio_concentration = "高"
            protocol_diversity = "高"
            security_score = random.randint(55, 70)
        else:  # high
            risk_score = random.randint(81, 95)
            risk_trend = "急剧上升"
            portfolio_concentration = "极高"
            protocol_diversity = "低"
            security_score = random.randint(40, 60)

        # 获取钱包头寸数据
        positions_data = self.get_wallet_positions(wallet_address)

        # 生成风险历史数据（过去30天）
        risk_history = []
        base_risk = risk_score
        for i in range(30):
            date = datetime.now() - timedelta(days=30 - i - 1)
            if risk_level == "low":
                change = random.uniform(-2, 2)
            elif risk_level == "medium":
                change = random.uniform(-3, 4)
            elif risk_level == "medium-high":
                change = random.uniform(-3, 5)
            else:  # high
                change = random.uniform(-5, 8)

            day_risk = max(min(base_risk + change, 100), 0)
            risk_history.append({"date": date.isoformat(), "score": round(day_risk, 1)})
            # 逐渐恢复到目标风险值，模拟风险的自然变化
            base_risk = 0.9 * base_risk + 0.1 * risk_score

        # 生成详细的风险报告
        report = {
            "wallet_address": wallet_address,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_trend": risk_trend,
            "risk_history": risk_history,
            "portfolio_analysis": {
                "total_value": positions_data.get("total_value_usd", 0),
                "asset_count": len(positions_data.get("positions", [])),
                "concentration": portfolio_concentration,
                "diversity_score": random.randint(1, 100),
                "protocol_diversity": protocol_diversity,
                "chain_diversity": "中" if risk_level == "medium-high" else "低",
            },
            "security_analysis": {
                "smart_contract_security": {
                    "score": security_score,
                    "audit_status": (
                        "大部分已审计" if security_score > 70 else "部分未审计"
                    ),
                    "vulnerabilities": {
                        "high": random.randint(0, 3) if security_score < 70 else 0,
                        "medium": (
                            random.randint(0, 5)
                            if security_score < 85
                            else random.randint(0, 2)
                        ),
                        "low": random.randint(1, 10),
                    },
                },
                "historical_incidents": self._generate_security_incidents(risk_level),
            },
            "market_conditions": {
                "current_market": "牛市" if random.random() > 0.5 else "熊市",
                "volatility": "高" if risk_level in ["high", "medium-high"] else "中",
                "liquidity": "中等",
                "correlation_risk": "高" if risk_level == "high" else "中",
            },
            "ai_insights": self._generate_ai_insights(wallet_address, risk_level),
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = report
        return report

    def _generate_security_incidents(self, risk_level: str) -> List[Dict[str, Any]]:
        """生成安全事件历史"""
        incidents = []
        incident_count = 0

        if risk_level == "low":
            incident_count = random.randint(0, 1)
        elif risk_level == "medium":
            incident_count = random.randint(0, 2)
        elif risk_level == "medium-high":
            incident_count = random.randint(1, 3)
        else:  # high
            incident_count = random.randint(2, 5)

        incident_types = [
            "闪电贷攻击",
            "重入攻击",
            "预言机操纵",
            "治理攻击",
            "前端劫持",
            "私钥泄露",
        ]
        protocols = [
            "Uniswap",
            "Aave",
            "Compound",
            "Curve",
            "MakerDAO",
            "dYdX",
            "Yearn",
            "SushiSwap",
        ]

        for i in range(incident_count):
            incident_type = random.choice(incident_types)
            protocol = random.choice(protocols)
            severity = random.choice(["高", "中", "低"])
            date = datetime.now() - timedelta(days=random.randint(30, 365))

            incidents.append(
                {
                    "id": f"INC-{random.randint(1000, 9999)}",
                    "date": date.isoformat(),
                    "type": incident_type,
                    "protocol": protocol,
                    "severity": severity,
                    "description": f"{protocol}遭受{incident_type}，影响程度{severity}",
                    "status": "已解决" if random.random() > 0.3 else "部分解决",
                }
            )

        return incidents

    def _generate_ai_insights(
        self, wallet_address: str, risk_level: str
    ) -> List[Dict[str, Any]]:
        """生成AI洞察"""
        insights = []

        # 基于风险级别生成不同的洞察
        if risk_level == "low":
            insights = [
                {
                    "title": "稳健的资产配置",
                    "content": "您的投资组合以稳定币和蓝筹资产为主，风险较低。建议继续保持稳健的投资策略，可以适当考虑增加部分收益型产品提高整体收益率。",
                    "confidence": 0.9,
                },
                {
                    "title": "稳定币多样化",
                    "content": "您的投资组合中稳定币占比较高，但集中在USDC。建议考虑分散到不同的稳定币中，降低单一稳定币的风险。",
                    "confidence": 0.85,
                },
            ]
        elif risk_level == "medium":
            insights = [
                {
                    "title": "适度的风险暴露",
                    "content": "您的投资组合在风险和收益之间取得了较好的平衡。ETH和BTC的配置适中，DeFi协议的使用也较为多样化。",
                    "confidence": 0.87,
                },
                {
                    "title": "协议分散建议",
                    "content": "您的资产主要集中在2-3个主流协议中，建议适度分散到更多协议以降低协议风险，但注意不要过度分散导致Gas成本提高。",
                    "confidence": 0.82,
                },
                {
                    "title": "市场波动风险提示",
                    "content": "当前市场波动较大，建议关注借贷头寸的健康因子，避免因市场下跌导致清算风险。",
                    "confidence": 0.75,
                },
            ]
        elif risk_level == "medium-high":
            insights = [
                {
                    "title": "跨链风险分析",
                    "content": "您的资产分布在多个区块链上，增加了资产多样性，但也带来了跨链桥和不同链上安全风险。建议关注各链上的安全更新。",
                    "confidence": 0.8,
                },
                {
                    "title": "高收益协议风险",
                    "content": "部分高收益协议存在较高的智能合约风险和流动性风险，建议将这些协议的资产控制在总资产的20%以内。",
                    "confidence": 0.85,
                },
                {
                    "title": "链间资产平衡",
                    "content": "您在Arbitrum上的资产占比较高，如果该L2出现问题，影响会较大。建议在不同链之间更均衡地配置资产。",
                    "confidence": 0.78,
                },
            ]
        else:  # high
            insights = [
                {
                    "title": "高杠杆风险警告",
                    "content": "您的投资组合使用了较高杠杆，在市场波动时面临较大的清算风险。建议降低杠杆率或增加抵押品以提高安全边际。",
                    "confidence": 0.92,
                },
                {
                    "title": "新兴协议风险",
                    "content": "您使用了多个新兴协议，这些协议尚未经过充分的市场验证和安全审计。建议将这类协议的配置控制在较低比例。",
                    "confidence": 0.88,
                },
                {
                    "title": "NFT流动性风险",
                    "content": "您的资产中包含较高比例的NFT，这类资产在市场下跌时流动性可能急剧下降。建议考虑分散部分到更具流动性的资产中。",
                    "confidence": 0.85,
                },
                {
                    "title": "紧急风险缓解策略",
                    "content": "根据当前市场情况和您的头寸，建议立即增加抵押品或减少部分借款，将健康因子提高到至少1.5以上，以防范潜在的市场波动。",
                    "confidence": 0.9,
                },
            ]

        return insights

    def get_market_scenario_simulation(
        self, wallet_address: str, scenario: str = "market_crash"
    ) -> Dict[str, Any]:
        """获取市场情景模拟

        参数:
            wallet_address: 钱包地址
            scenario: 市场情景类型

        返回:
            市场情景模拟结果
        """
        cache_key = f"market_scenario_{wallet_address}_{scenario}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 场景数据
        scenario_data = {
            "market_crash": {
                "title": "市场崩盘",
                "description": "加密市场整体下跌50%的极端情景",
                "impact_level": "严重",
                "duration": "短期至中期",
                "asset_impacts": {
                    "ATH": -0.65,  # ATH下跌65%
                    "DOP": -0.60,  # DOP下跌60%
                    "ETH": -0.50,
                    "BTC": -0.45,
                    "USDC": 0,
                    "USDT": 0,
                    "DAI": -0.01,
                    "AAVE": -0.55,
                    "UNI": -0.60,
                    "COMP": -0.58,
                    "MKR": -0.52,
                    "SNX": -0.65,
                },
            },
            "bull_run": {
                "title": "牛市行情",
                "description": "加密市场整体上涨100%的乐观情景",
                "impact_level": "积极",
                "duration": "中期至长期",
                "asset_impacts": {
                    "ATH": 1.8,  # ATH上涨180%
                    "DOP": 2.0,  # DOP上涨200%
                    "ETH": 1.2,
                    "BTC": 0.8,
                    "USDC": 0,
                    "USDT": 0,
                    "DAI": 0.01,
                    "AAVE": 1.5,
                    "UNI": 1.8,
                    "COMP": 1.6,
                    "MKR": 1.3,
                    "SNX": 2.2,
                },
            },
            "defi_hack": {
                "title": "DeFi黑客事件",
                "description": "主要DeFi协议遭遇安全漏洞攻击的情景",
                "impact_level": "中度至严重",
                "duration": "短期",
                "asset_impacts": {
                    "ATH": -0.3,  # ATH下跌30%
                    "DOP": -0.25,  # DOP下跌25%
                    "ETH": -0.15,
                    "BTC": -0.05,
                    "USDC": -0.02,
                    "USDT": -0.02,
                    "DAI": -0.03,
                    "AAVE": -0.4,
                    "UNI": -0.35,
                    "COMP": -0.38,
                    "MKR": -0.3,
                    "SNX": -0.42,
                },
            },
            "regulatory_crackdown": {
                "title": "监管打击",
                "description": "全球主要国家加强加密资产监管的情景",
                "impact_level": "中度",
                "duration": "中期至长期",
                "asset_impacts": {
                    "ATH": -0.4,  # ATH下跌40%
                    "DOP": -0.45,  # DOP下跌45%
                    "ETH": -0.3,
                    "BTC": -0.25,
                    "USDC": -0.05,
                    "USDT": -0.05,
                    "DAI": -0.04,
                    "AAVE": -0.38,
                    "UNI": -0.42,
                    "COMP": -0.4,
                    "MKR": -0.35,
                    "SNX": -0.48,
                },
            },
        }

        # 获取钱包数据
        positions_data = self.get_wallet_positions(wallet_address)
        positions = positions_data.get("positions", [])

        # 获取风险数据
        risk_data = self.analyze_wallet_risk(wallet_address)
        original_risk_score = risk_data.get("risk_score", 50)

        # 为指定的测试钱包地址生成特定场景模拟
        if wallet_address == "0x881896A2E1D65f5dfA4d23Bf6b917cE703ed068b":
            # 获取所选场景数据
            selected_scenario = scenario_data.get(
                scenario, scenario_data["market_crash"]
            )
            asset_impacts = selected_scenario["asset_impacts"]

            # 计算场景前的总值
            total_value_before = positions_data.get("total_value_usd", 32.73)

            # 模拟场景对每个头寸的影响
            impacted_positions = []
            total_value_after = 0

            for position in positions:
                if "positions" in position and position["positions"]:
                    # 处理嵌套的positions结构
                    for sub_position in position["positions"]:
                        asset = sub_position.get("asset", "")
                        amount_before = sub_position.get("amount", 0)

                        # 应用资产影响率，没有特定的资产影响则使用默认值
                        impact_rate = asset_impacts.get(
                            asset, -0.5 if scenario == "market_crash" else 0.8
                        )
                        amount_after = amount_before * (1 + impact_rate)

                        impacted_positions.append(
                            {
                                "protocol": sub_position.get("protocol", ""),
                                "asset": asset,
                                "amount_before": amount_before,
                                "amount_after": amount_after,
                                "change_percentage": impact_rate * 100,
                            }
                        )

                        total_value_after += amount_after
                else:
                    # 简单结构，直接处理头寸本身
                    protocol = position.get("protocol", "")
                    total_assets = position.get("total_assets", 0)

                    # 假设协议中主要持有的代币是该协议的原生代币
                    asset = protocol
                    impact_rate = asset_impacts.get(
                        asset, -0.5 if scenario == "market_crash" else 0.8
                    )
                    assets_after = total_assets * (1 + impact_rate)

                    # 只添加非空头寸
                    if total_assets > 0:
                        impacted_positions.append(
                            {
                                "protocol": protocol,
                                "asset": asset,
                                "amount_before": total_assets,
                                "amount_after": assets_after,
                                "change_percentage": impact_rate * 100,
                            }
                        )

                        total_value_after += assets_after

            # 调整风险分数
            if scenario == "market_crash":
                # 市场崩盘会增加风险
                new_risk_score = min(original_risk_score + 20, 100)
            elif scenario == "bull_run":
                # 牛市可能降低某些风险
                new_risk_score = max(original_risk_score - 10, 0)
            elif scenario == "defi_hack":
                # DeFi黑客事件增加风险
                new_risk_score = min(original_risk_score + 15, 100)
            else:  # regulatory_crackdown
                # 监管风险增加
                new_risk_score = min(original_risk_score + 12, 100)

            # 构建结果
            result = {
                "wallet_address": wallet_address,
                "scenario": scenario,
                "scenario_info": {
                    "title": selected_scenario["title"],
                    "description": selected_scenario["description"],
                    "impact_level": selected_scenario["impact_level"],
                    "duration": selected_scenario["duration"],
                    "probability": "中",  # 新增：事件发生概率
                    "leading_indicators": (
                        [  # 新增：先行指标
                            "市场恐慧指数低于20",
                            "主要国家央行加息",
                            "主流交易所交易量下降30%以上",
                        ]
                        if scenario == "market_crash"
                        else (
                            [
                                "市场恐慧指数高于80",
                                "机构资金大量流入",
                                "链上活动明显增加",
                            ]
                            if scenario == "bull_run"
                            else (
                                ["社交媒体上DeFi黑客事件讨论增加", "闪电贷交易量激增"]
                                if scenario == "defi_hack"
                                else [
                                    "主要国家发布加密监管政策草案",
                                    "交易所合规性要求提高",
                                ]
                            )
                        )
                    ),
                },
                "portfolio_impact": {
                    "total_value_before": total_value_before,
                    "total_value_after": total_value_after,
                    "change_amount": total_value_after - total_value_before,
                    "change_percentage": (
                        (
                            (total_value_after - total_value_before)
                            / total_value_before
                            * 100
                        )
                        if total_value_before > 0
                        else 0
                    ),
                    "positions": impacted_positions,
                    "liquidity_impact": {  # 新增：流动性影响
                        "slippage_increase": (
                            "高" if scenario == "market_crash" else "低"
                        ),
                        "exit_difficulty": (
                            "ATH代币可能面临无法及时退出的风险"
                            if scenario in ["market_crash", "defi_hack"]
                            else "正常"
                        ),
                        "swap_options": (
                            ["Curve", "Uniswap"]
                            if scenario != "defi_hack"
                            else ["仅Uniswap"]
                        ),
                    },
                    "protocol_specific_impacts": [  # 新增：协议特定影响
                        {
                            "protocol": "Aethir",
                            "impact_details": (
                                "在市场崩盘情景下，Aethir协议的ATH代币可能面临较大抛售压力，流动性池可能枯竭"
                                if scenario == "market_crash"
                                else (
                                    "随着市场升温，Aethir的用户增长和需求可能提高代币价值"
                                    if scenario == "bull_run"
                                    else (
                                        "如果安全漏洞影响Aethir，可能导致资产损失或临时冻结"
                                        if scenario == "defi_hack"
                                        else "监管打击可能导致Aethir必须调整业务模式，影响代币实用性"
                                    )
                                )
                            ),
                            "risk_level": (
                                "高"
                                if scenario in ["market_crash", "defi_hack"]
                                else "中"
                            ),
                        },
                        {
                            "protocol": "Data Ownership Protocol",
                            "impact_details": (
                                "作为一个相对新兴的协议，市场下跌可能严重影响DOP代币价格和流动性"
                                if scenario == "market_crash"
                                else (
                                    "DOP可能受益于增长的市场关注度和采用率"
                                    if scenario == "bull_run"
                                    else (
                                        "智能合约漏洞可能导致数据或资金损失"
                                        if scenario == "defi_hack"
                                        else "数据隐私监管可能对协议的核心功能产生特殊影响"
                                    )
                                )
                            ),
                            "risk_level": (
                                "中高"
                                if scenario in ["market_crash", "regulatory_crackdown"]
                                else "中"
                            ),
                        },
                    ],
                },
                "risk_impact": {
                    "risk_score_before": original_risk_score,
                    "risk_score_after": new_risk_score,
                    "change": new_risk_score - original_risk_score,
                    "risk_factors_impact": [  # 新增：风险因素影响细节
                        {
                            "factor": "资产集中度风险",
                            "before": 50,
                            "after": (
                                65
                                if scenario == "market_crash"
                                else (45 if scenario == "bull_run" else 55)
                            ),
                            "impact": (
                                "市场下跌会放大单一资产集中风险"
                                if scenario == "market_crash"
                                else (
                                    "牛市可能暂时掩盖集中度风险，但长期风险仍存在"
                                    if scenario == "bull_run"
                                    else "安全事件/监管变化突显多样化的重要性"
                                )
                            ),
                        },
                        {
                            "factor": "流动性风险",
                            "before": 35,
                            "after": (
                                70
                                if scenario == "market_crash"
                                else (30 if scenario == "bull_run" else 50)
                            ),
                            "impact": (
                                "极端市场环境下小币种流动性可能完全枯竭"
                                if scenario == "market_crash"
                                else (
                                    "市场活跃度提高，流动性风险降低"
                                    if scenario == "bull_run"
                                    else "安全事件/监管变化可能导致交易所下架或限制交易"
                                )
                            ),
                        },
                    ],
                },
                "action_plan": {  # 新增：行动计划部分
                    "immediate_actions": [
                        (
                            "设置止损单，限制下行风险"
                            if scenario == "market_crash"
                            else (
                                "考虑获利了结一部分头寸"
                                if scenario == "bull_run"
                                else "暂停在涉事协议的额外投资"
                            )
                        ),
                        (
                            "增加稳定币比例，准备抄底机会"
                            if scenario == "market_crash"
                            else (
                                "重新平衡投资组合，确保风险可控"
                                if scenario == "bull_run"
                                else "检查协议的安全更新和公告"
                            )
                        ),
                    ],
                    "mid_term_strategy": [
                        "在市场稳定后，分散投资到不同资产类别和协议",
                        "增加非相关资产配置，提高投资组合韧性",
                    ],
                    "technical_adjustments": [
                        "调整Aethir的仓位，降低ATH代币比例至30%以下",
                        "考虑添加Aave或Compound等成熟协议以分散风险",
                    ],
                },
                "recommendations": self._generate_scenario_recommendations(scenario),
                "timestamp": datetime.now().isoformat(),
                "is_demo_data": True,
            }

            self._demo_data_cache[cache_key] = result
            return result

        # 对于其他钱包，使用通用逻辑
        # 获取场景信息
        if scenario not in scenario_data:
            scenario = "market_crash"  # 默认使用市场崩盘场景
        selected_scenario = scenario_data[scenario]

        # 获取钱包头寸
        positions = positions_data.get("positions", [])
        original_risk = self.analyze_wallet_risk(wallet_address)

        # 计算情景对投资组合的影响
        asset_impacts = selected_scenario["asset_impacts"]
        impacted_positions = []
        total_value_before = 0
        total_value_after = 0

        for position in positions:
            protocol = position.get("protocol", "Unknown")
            asset = position.get("asset", "ETH")
            usd_value = position.get("usd_value", position.get("amount", 0))
            total_value_before += usd_value

            # 计算变化
            change_ratio = asset_impacts.get(asset, -0.2)  # 默认-20%
            new_value = usd_value * (1 + change_ratio)
            total_value_after += new_value

            impacted_positions.append(
                {
                    "protocol": protocol,
                    "asset": asset,
                    "value_before": usd_value,
                    "value_after": new_value,
                    "change_percentage": change_ratio * 100,
                }
            )

        # 计算风险变化
        original_risk_score = original_risk["risk_score"]
        # 根据场景调整风险分数
        if scenario == "market_crash":
            risk_change = 35
        elif scenario == "bull_run":
            risk_change = -10
        elif scenario == "defi_hack":
            risk_change = 25
        else:  # regulatory_crackdown
            risk_change = 20

        new_risk_score = min(100, max(10, original_risk_score + risk_change))

        # 生成场景特定建议
        recommendations = self._generate_scenario_recommendations(scenario)

        result = {
            "wallet_address": wallet_address,
            "scenario": scenario,
            "scenario_info": {
                "title": selected_scenario["title"],
                "description": selected_scenario["description"],
                "impact_level": selected_scenario["impact_level"],
                "duration": selected_scenario["duration"],
            },
            "portfolio_impact": {
                "total_value_before": total_value_before,
                "total_value_after": total_value_after,
                "change_amount": total_value_after - total_value_before,
                "change_percentage": (
                    (total_value_after - total_value_before) / total_value_before * 100
                    if total_value_before > 0
                    else 0
                ),
                "positions": impacted_positions,
            },
            "risk_impact": {
                "risk_score_before": original_risk_score,
                "risk_score_after": new_risk_score,
                "change": new_risk_score - original_risk_score,
            },
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = result
        return result

    def get_wallet_market_risk(self, wallet_address: str) -> Dict[str, Any]:
        """获取钱包市场风险分析

        参数:
            wallet_address: 钱包地址

        返回:
            市场风险分析结果
        """
        cache_key = f"market_risk_{wallet_address}"
        if cache_key in self._demo_data_cache:
            return self._demo_data_cache[cache_key]

        # 为指定的测试钱包地址生成特定市场风险分析
        if wallet_address == "0x881896A2E1D65f5dfA4d23Bf6b917cE703ed068b":
            factors = [
                {
                    "name": "资产集中度风险",
                    "score": 50,
                    "weight": 0.4,
                    "description": "投资组合中Aethir占比约76%，增加了单一资产风险",
                    "trend": "稳定",
                    "data_points": [
                        {"asset": "ATH", "percentage": 0.76},
                        {"asset": "DOP", "percentage": 0.24},
                    ],
                },
                {
                    "name": "质押与稳定币相关性风险",
                    "score": 30,
                    "weight": 0.3,
                    "description": "质押资产(ATH)与稳定币(DOP)相关性低，有较好的多样化效果",
                    "trend": "稳定",
                    "data_points": [
                        {"asset_pair": "ATH-DOP", "correlation": 0.2},
                    ],
                },
                {
                    "name": "质押市场风险",
                    "score": 45,
                    "weight": 0.3,
                    "description": "质押资产在验证者减少或网络问题时可能面临价格波动",
                    "trend": "稳定",
                    "data_points": [{"volatility_index": 45}],
                },
            ]

            data = {
                "risk_type": "MARKET",
                "target": "portfolio",
                "score": 42,
                "risk_level": "MEDIUM-LOW",
                "factors": factors,
                "recommendations": [
                    "考虑增加稳定币比例以平衡质押资产风险",
                    "减少Aethir在投资组合中的占比",
                    "关注ETH 2.0相关的网络更新和变化",
                    "考虑引入一些Aave等成熟DeFi协议的资产",
                ],
                "monitoring_points": [
                    "监控Aethir代币的价格波动",
                    "关注DOP稳定币的锚定状态",
                    "定期检查质押资产的解质押期和流动性状况",
                ],
                "ai_insights": [],
                "ai_available": True,
                "timestamp": datetime.now().isoformat(),
                "is_demo_data": True,
            }

            self._demo_data_cache[cache_key] = data
            return data

        # 为其他钱包生成随机市场风险数据
        risk_score = random.randint(40, 70)

        risk_levels = {
            (0, 50): "低",
            (50, 70): "中等",
            (70, 85): "高",
            (85, 100): "极高",
        }
        risk_level = next(
            (
                level
                for (lower, upper), level in risk_levels.items()
                if lower <= risk_score < upper
            ),
            "中等",
        )
        risk_factors = [
            {
                "name": "资产集中度风险",
                "score": random.randint(30, 80),
                "weight": 0.4,
                "description": "投资组合中ETH占比较高，增加了单一资产风险",
                "trend": random.choice(["上升", "稳定", "下降"]),
                "data_points": [
                    {"asset": "ETH", "percentage": random.uniform(0.5, 0.7)},
                    {"asset": "USDC", "percentage": random.uniform(0.1, 0.2)},
                    {"asset": "其他", "percentage": random.uniform(0.1, 0.3)},
                ],
            },
            {
                "name": "资产相关性风险",
                "score": random.randint(40, 70),
                "weight": 0.3,
                "description": "投资组合中资产相关性较高，多样化效果有限",
                "trend": random.choice(["上升", "稳定", "下降"]),
                "data_points": [
                    {"asset_pair": "ETH-BTC", "correlation": random.uniform(0.7, 0.9)},
                    {"asset_pair": "ETH-Alts", "correlation": random.uniform(0.6, 0.8)},
                ],
            },
            {
                "name": "市场波动风险",
                "score": random.randint(40, 80),
                "weight": 0.3,
                "description": f"当前市场波动性{random.choice(['较高', '中等', '较低'])}",
                "trend": random.choice(["上升", "稳定", "下降"]),
                "data_points": [{"volatility_index": random.randint(40, 80)}],
            },
        ]

        # 生成市场风险建议
        recommendations = [
            "将ETH持仓比例从当前的65%降低至40%以下，减少单一资产风险",
            "增加稳定币比例至少20%，作为市场波动的缓冲",
            "考虑在当前价格区间设置分批止盈点，锁定部分收益",
            "对于高波动性资产，设置15%的止损位，控制下行风险",
            "增加低相关性资产，提高投资组合的多样性",
            "关注市场整体趋势变化，避免在下跌趋势中追加投资",
        ]
        random.shuffle(recommendations)
        recommendations = recommendations[: random.randint(3, 5)]

        # 生成市场风险监控点
        monitoring_points = [
            "每日监控ETH价格变动，如单日下跌超过10%，考虑减仓",
            "关注投资组合中最大资产ETH的市值占比，保持在40%以下",
            "监控市场恐惧与贪婪指数，当指数低于20或高于80时重新评估仓位",
            "追踪主要资产间的相关性变化，特别是ETH-BTC对的相关系数",
            "关注主要持仓资产的交易量变化，交易量突增可能预示价格波动",
            "定期评估投资组合的整体波动率，与市场基准进行比较",
        ]
        random.shuffle(monitoring_points)
        monitoring_points = monitoring_points[: random.randint(3, 5)]

        # 构建结果
        result = {
            "wallet_address": wallet_address,
            "risk_type": "MARKET",
            "target": "portfolio",
            "score": risk_score,
            "risk_level": risk_level,
            "factors": risk_factors,
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
            "ai_insights": ["AI分析显示当前市场处于波动阶段，建议保持谨慎并设置止损"],
            "ai_available": True,
            "timestamp": datetime.now().isoformat(),
            "is_demo_data": True,
        }

        self._demo_data_cache[cache_key] = result
        return result

    def _generate_scenario_recommendations(self, scenario: str) -> List[str]:
        """生成不同情景下的建议"""
        recommendations = {
            "market_crash": [
                "减少借贷头寸，降低杠杆率",
                "增加稳定币储备，准备在市场低点买入",
                "设置止损点，防止进一步下跌",
                "增加抵押品，防止清算",
                "分散资产到不同类型的加密货币",
                "暂时减少流动性挖矿敞口",
                "关注市场底部信号，为反弹做准备",
            ],
            "bull_run": [
                "定期获利了结，锁定部分盈利",
                "调整资产配置，防止过度集中",
                "关注市场情绪指标，警惕市场过热",
                "考虑对冲策略，防范突然回调",
                "重新平衡投资组合，确保风险可控",
                "为可能的回调准备现金储备",
                "设置不同价格区间的获利目标",
            ],
            "defi_hack": [
                "分散资产到多个协议，降低单一协议风险",
                "优先使用经过多次审计的成熟协议",
                "关注协议安全更新和公告",
                "考虑使用去中心化保险产品",
                "保持一部分资产在非托管钱包中",
                "定期审核智能合约的安全状况",
                "关注社区对协议安全性的讨论",
            ],
            "regulatory_crackdown": [
                "关注各国监管动态，适时调整投资策略",
                "增加合规性高的资产比例",
                "考虑分散到不同司法管辖区的协议",
                "准备应急撤离计划，确保资金安全",
                "关注交易所的合规状况",
                "减少匿名币种的敞口",
                "关注监管友好型的DeFi协议发展",
            ],
        }

        # 获取对应场景的建议列表
        scenario_recs = recommendations.get(scenario, recommendations["market_crash"])

        # 随机选择4-6条建议
        random.shuffle(scenario_recs)
        return scenario_recs[: random.randint(4, 6)]


# 创建全局演示数据服务实例
demo_data_service = DemoDataService()


def get_demo_data_service() -> DemoDataService:
    """获取演示数据服务实例"""
    return demo_data_service
