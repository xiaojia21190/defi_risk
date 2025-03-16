"""
演示数据服务
提供各种API端点的演示数据
"""

from typing import Dict, List, Any, Optional
import random
from datetime import datetime, timedelta
import logging

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

        # 为演示账户1生成特定的头寸数据
        if wallet_address == "0xdemo1234567890abcdef1234567890abcdef123456":
            positions = [
                {
                    "protocol": "Aave",
                    "type": "lending",
                    "asset": "ETH",
                    "amount": 5.0,
                    "usd_value": 15000.0,
                    "apy": 2.5,
                },
                {
                    "protocol": "Compound",
                    "type": "lending",
                    "asset": "USDC",
                    "amount": 10000.0,
                    "usd_value": 10000.0,
                    "apy": 3.2,
                },
                {
                    "protocol": "Uniswap",
                    "type": "liquidity",
                    "asset": "ETH-USDC",
                    "amount": 2.0,
                    "usd_value": 8000.0,
                    "apy": 15.5,
                },
                {
                    "protocol": "MakerDAO",
                    "type": "cdp",
                    "asset": "ETH",
                    "amount": 10.0,
                    "usd_value": 30000.0,
                    "borrowed": 15000.0,
                    "collateral_ratio": 200.0,
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
                },
                {
                    "protocol": "Aave",
                    "type": "borrowing",
                    "asset": "USDC",
                    "amount": 20000.0,
                    "usd_value": 20000.0,
                    "interest_rate": 4.5,
                },
                {
                    "protocol": "SushiSwap",
                    "type": "farming",
                    "asset": "SUSHI-ETH",
                    "amount": 5.0,
                    "usd_value": 15000.0,
                    "apy": 45.0,
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
                },
                {
                    "protocol": "Compound",
                    "type": "lending",
                    "asset": "USDC",
                    "amount": random.uniform(1000, 20000),
                    "usd_value": random.uniform(1000, 20000),
                    "apy": random.uniform(2, 6),
                },
            ]

        total_value = sum(position.get("usd_value", 0) for position in positions)

        data = {
            "wallet_address": wallet_address,
            "positions": positions,
            "total_value_usd": total_value,
            "position_count": len(positions),
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

        # 获取钱包头寸
        positions_data = self.get_wallet_positions(wallet_address)
        positions = positions_data["positions"]

        # 为演示账户1生成中等风险分析
        if wallet_address == "0xdemo1234567890abcdef1234567890abcdef123456":
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
                "position_count": positions_data["position_count"],
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

        # 为演示账户1生成特定警报
        if wallet_address == "0xdemo1234567890abcdef1234567890abcdef123456":
            alerts = [
                {
                    "id": "alert-001",
                    "type": "collateral_ratio",
                    "severity": "warning",
                    "protocol": "MakerDAO",
                    "asset": "ETH",
                    "message": "抵押率接近清算阈值，建议增加抵押或减少借贷",
                    "current_value": "150%",
                    "threshold": "130%",
                    "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                },
                {
                    "id": "alert-002",
                    "type": "price_drop",
                    "severity": "info",
                    "asset": "ETH",
                    "message": "ETH价格在过去24小时下跌了5%",
                    "current_value": "$3000",
                    "previous_value": "$3150",
                    "timestamp": (datetime.now() - timedelta(hours=12)).isoformat(),
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
                    "current_price": "$3000",
                    "liquidation_price": "$2800",
                    "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
                },
                {
                    "id": "alert-004",
                    "type": "high_utilization",
                    "severity": "warning",
                    "protocol": "Aave",
                    "asset": "USDC",
                    "message": "借贷资产利用率超过90%，利率可能上升",
                    "current_value": "92%",
                    "threshold": "90%",
                    "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
                },
                {
                    "id": "alert-005",
                    "type": "protocol_risk",
                    "severity": "warning",
                    "protocol": "SushiSwap",
                    "message": "协议最近发现安全漏洞，建议关注更新",
                    "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
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


# 创建全局演示数据服务实例
demo_data_service = DemoDataService()


def get_demo_data_service() -> DemoDataService:
    """获取演示数据服务实例"""
    return demo_data_service
