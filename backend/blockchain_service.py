from typing import List, Dict, Optional, Tuple
from web3 import Web3
import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import logging
import random
from collections import OrderedDict
import asyncio
import aiohttp
from cachetools import TTLCache, cached

# 设置日志记录器
logger = logging.getLogger("defi_risk.blockchain")

# 设置代理
proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

# 创建一个5分钟过期的缓存，最多存储100个项目
cache = TTLCache(maxsize=100, ttl=300)  # 300秒 = 5分钟


class HistoricalDataCache:
    def __init__(self):
        # 为不同时间周期创建独立的TTLCache
        # 缓存时间设置为数据周期的2倍，确保数据时效性
        self.cache_map = {
            "1m": TTLCache(maxsize=1000, ttl=120),  # 2分钟
            "5m": TTLCache(maxsize=1000, ttl=600),  # 10分钟
            "15m": TTLCache(maxsize=1000, ttl=1800),  # 30分钟
            "1h": TTLCache(maxsize=1000, ttl=7200),  # 2小时
            "4h": TTLCache(maxsize=500, ttl=28800),  # 8小时
            "1d": TTLCache(maxsize=500, ttl=172800),  # 48小时
        }
        self.logger = logging.getLogger("defi_risk.cache")

    def get_cache(self, interval: str) -> TTLCache:
        """获取对应时间周期的缓存"""
        # 确保 interval 是字符串类型
        interval_str = str(interval)

        # 打印调试信息
        self.logger.info(f"获取缓存：interval={interval_str}, 类型={type(interval)}")
        self.logger.info(f"可用的缓存键：{list(self.cache_map.keys())}")

        # 检查 interval 是否在 cache_map 中
        if interval_str not in self.cache_map:
            self.logger.warning(f"未找到间隔为 {interval_str} 的缓存")
            return None

        return self.cache_map[interval_str]

    def get(self, key: str, interval: str):
        """获取缓存数据"""
        try:
            # 确保 interval 是字符串类型
            interval_str = str(interval)

            # 打印调试信息
            self.logger.info(
                f"获取缓存：key={key}, interval={interval_str}, 类型={type(interval)}"
            )

            # 检查 interval 是否在 cache_map 中
            if interval_str not in self.cache_map:
                self.logger.warning(f"获取缓存失败：未找到间隔为 {interval_str} 的缓存")
                return None

            # 获取缓存
            value = self.cache_map[interval_str].get(key)
            if value is None:
                self.logger.info(f"缓存未命中：key={key}, interval={interval_str}")
            else:
                self.logger.info(f"缓存命中：key={key}, interval={interval_str}")
            return value
        except Exception as e:
            self.logger.error(
                f"获取缓存时出错：key={key}, interval={interval_str}, error={e}"
            )
            return None

    def set(self, key: str, value, interval: str):
        """设置缓存数据"""
        try:
            # 确保 interval 是字符串类型
            interval_str = str(interval)

            # 打印调试信息
            self.logger.info(
                f"设置缓存：key={key}, interval={interval_str}, 类型={type(interval)}"
            )

            # 检查 interval 是否在 cache_map 中
            if interval_str not in self.cache_map:
                self.logger.warning(f"设置缓存失败：未找到间隔为 {interval_str} 的缓存")
                return

            # 设置缓存
            self.cache_map[interval_str][key] = value
            self.logger.info(f"成功设置缓存：key={key}, interval={interval_str}")
        except Exception as e:
            self.logger.error(
                f"设置缓存时出错：key={key}, interval={interval_str}, error={e}"
            )


# 演示数据常量
DEMO_ADDRESS = "0xAbCdEf123456789AbCdEf123456789AbCdEf1234"
DEMO_ASSETS = {
    "ETH": {"price": 2000.0, "volatility": 0.35},
    "BTC": {"price": 40000.0, "volatility": 0.42},
    "USDC": {"price": 1.0, "volatility": 0.05},
    "USDT": {"price": 1.0, "volatility": 0.05},
}

DEMO_PROTOCOLS = {
    "Aave V3": {
        "risk": 0.25,
        "apy_range": (0.02, 0.05),
    },
    "Compound V3": {"risk": 0.20, "apy_range": (0.03, 0.06)},
    "Curve Finance": {"risk": 0.30, "apy_range": (0.04, 0.10)},
    "Uniswap V3": {"risk": 0.35, "apy_range": (0.05, 0.15)},
    "Balancer": {"risk": 0.30, "apy_range": (0.04, 0.12)},
}


@dataclass
class ProtocolPosition:
    protocol: str
    asset: str
    amount: float
    leverage: Optional[float] = None
    apy: Optional[float] = None


class BlockchainService:
    def __init__(self, web3_provider_url: str):
        """初始化区块链服务"""
        self.w3 = Web3(Web3.HTTPProvider(web3_provider_url))
        self.demo_mode = True  # 将演示模式设置为False
        self.historical_data_cache = HistoricalDataCache()
        self.data_fetch_locks = {}  # 用于防止并发获取相同数据
        self.pending_requests = {}  # 用于合并请求
        self._load_contract_abis()

        DEMO_PROTOCOLS.get("Aave V3")

        # 配置日志
        self.logger = logging.getLogger("blockchain_service")
        # 只在开发环境设置为DEBUG，生产环境设置为INFO或WARNING
        if os.environ.get("ENVIRONMENT") == "development":
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

    async def get_all_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在所有支持的DeFi协议中的存款头寸"""
        try:
            if address.lower() == DEMO_ADDRESS.lower() or self.demo_mode:
                logger.info(f"为演示地址返回预设头寸数据")
                return await self.get_demo_positions()

            if not self.w3.is_connected():
                logger.error("Web3连接不可用，无法获取真实头寸数据")
                return []

            # 检查地址格式
            if not self.w3.is_address(address):
                logger.error(f"无效的以太坊地址: {address}")
                return []

            # 规范化地址格式
            address = self.w3.to_checksum_address(address)

            # 获取各协议的头寸
            positions = []

            # 1. 获取Aave V3头寸
            try:
                aave_positions = await self._get_aave_v3_positions(address)
                positions.extend(aave_positions)
            except Exception as e:
                logger.error(f"获取Aave V3头寸时出错: {e}")

            # 2. 获取Compound V3头寸
            try:
                compound_positions = await self._get_compound_v3_positions(address)
                positions.extend(compound_positions)
            except Exception as e:
                logger.error(f"获取Compound V3头寸时出错: {e}")

            # 3. 获取Curve Finance头寸
            try:
                curve_positions = await self._get_curve_positions(address)
                positions.extend(curve_positions)
            except Exception as e:
                logger.error(f"获取Curve Finance头寸时出错: {e}")

            # 4. 获取Uniswap V3头寸
            try:
                uniswap_positions = await self._get_uniswap_v3_positions(address)
                positions.extend(uniswap_positions)
            except Exception as e:
                logger.error(f"获取Uniswap V3头寸时出错: {e}")

            # 过滤掉金额为0的头寸
            positions = [pos for pos in positions if pos.amount > 0]

            if not positions:
                logger.info(f"地址 {address} 没有找到任何DeFi头寸")
            else:
                logger.info(f"成功获取地址 {address} 的 {len(positions)} 个DeFi头寸")

            return positions
        except Exception as e:
            logger.error(f"获取所有存款头寸时出错: {e}")
            return []

    async def get_market_alerts(self, address: str) -> List[Dict]:
        """获取市场警报"""
        try:
            positions = await self.get_all_positions(address)
            if not positions:
                return []

            alerts = []
            now = int(datetime.now().timestamp())

            # 1. 检查价格波动
            for pos in positions:
                try:
                    asset = pos.asset.split("/")[0]  # 处理LP token的情况

                    # 跳过 USDT 资产的风险警报
                    if asset == "USDT":
                        continue

                    ticker_data = await self._get_24h_data(asset)

                    if ticker_data:
                        # 使用新的数据格式
                        latest_price = float(ticker_data["lastPrice"])
                        open_price = float(ticker_data["openPrice"])
                        price_change_24h = (
                            float(ticker_data["priceChangePercent"]) / 100
                        )  # 转换为小数
                        high_price = float(ticker_data["highPrice"])
                        low_price = float(ticker_data["lowPrice"])

                        # 计算波动率 (使用高低价差作为波动性指标)
                        volatility = (high_price - low_price) / open_price * 100

                        # 价格波动警报
                        if abs(price_change_24h) > 0.05:  # 5%的价格变化
                            severity = (
                                "HIGH" if abs(price_change_24h) > 0.1 else "MEDIUM"
                            )
                            alerts.append(
                                {
                                    "type": "PRICE_VOLATILITY",
                                    "severity": severity,
                                    "asset": asset,
                                    "protocol": pos.protocol,
                                    "message": f"{asset}价格在24小时内{'上涨' if price_change_24h > 0 else '下跌'}{abs(price_change_24h)*100:.1f}%",
                                    "timestamp": now,
                                    "details": {
                                        "price_change": price_change_24h,
                                        "current_price": latest_price,
                                        "previous_price": open_price,
                                        "volatility": volatility,
                                        "high_price": high_price,
                                        "low_price": low_price,
                                        "weighted_avg_price": float(
                                            ticker_data["weightedAvgPrice"]
                                        ),
                                        "volume": float(ticker_data["volume"]),
                                    },
                                }
                            )

                        # 高波动率警报
                        if volatility > 10:  # 波动率超过10%
                            alerts.append(
                                {
                                    "type": "HIGH_VOLATILITY",
                                    "severity": "HIGH" if volatility > 20 else "MEDIUM",
                                    "asset": asset,
                                    "protocol": pos.protocol,
                                    "message": f"{asset}波动率达到{volatility:.1f}%，市场不稳定性增加",
                                    "timestamp": now,
                                    "details": {
                                        "volatility": volatility,
                                        "current_price": latest_price,
                                        "price_change_24h": price_change_24h * 100,
                                        "high_price": high_price,
                                        "low_price": low_price,
                                    },
                                }
                            )

                except Exception as e:
                    logger.error(f"处理{asset}价格警报时出错: {e}")

            # 2. 检查清算风险
            for pos in positions:
                if hasattr(pos, "leverage") and pos.leverage:
                    # 计算清算风险
                    liquidation_threshold = 2.0
                    safe_leverage = 1.5
                    risk_ratio = pos.leverage / liquidation_threshold

                    if pos.leverage > 1.8:
                        alerts.append(
                            {
                                "type": "LIQUIDATION_RISK",
                                "severity": "HIGH",
                                "asset": pos.asset,
                                "protocol": pos.protocol,
                                "message": f"{pos.protocol}上的{pos.asset}头寸接近清算阈值，当前杠杆率{pos.leverage:.2f}",
                                "timestamp": now,
                                "details": {
                                    "leverage": pos.leverage,
                                    "safe_leverage": safe_leverage,
                                    "liquidation_threshold": liquidation_threshold,
                                    "risk_ratio": risk_ratio,
                                    "position_size": pos.amount,
                                    "recommendation": "建议减少杠杆或增加抵押品",
                                },
                            }
                        )
                    elif pos.leverage > 1.5:
                        alerts.append(
                            {
                                "type": "LIQUIDATION_RISK",
                                "severity": "MEDIUM",
                                "asset": pos.asset,
                                "protocol": pos.protocol,
                                "message": f"{pos.protocol}上的{pos.asset}头寸杠杆率较高，建议关注",
                                "timestamp": now,
                                "details": {
                                    "leverage": pos.leverage,
                                    "safe_leverage": safe_leverage,
                                    "liquidation_threshold": liquidation_threshold,
                                    "risk_ratio": risk_ratio,
                                    "position_size": pos.amount,
                                    "recommendation": "建议密切关注市场波动",
                                },
                            }
                        )

            # 3. 检查APY变化
            for pos in positions:
                if pos.apy:
                    # 假设历史APY数据，实际应用中应从数据库或API获取
                    historical_apy = pos.apy * 0.9  # 假设之前的APY
                    apy_change = (pos.apy - historical_apy) / historical_apy

                    # APY异常变化警报
                    if abs(apy_change) > 0.2:  # APY变化超过20%
                        severity = "HIGH" if abs(apy_change) > 0.5 else "MEDIUM"
                        direction = "增加" if apy_change > 0 else "减少"
                        recommendation = (
                            "考虑增加投资" if apy_change > 0 else "评估风险回报比"
                        )

                        alerts.append(
                            {
                                "type": "APY_CHANGE",
                                "severity": severity,
                                "asset": pos.asset,
                                "protocol": pos.protocol,
                                "message": f"{pos.protocol}的{pos.asset} APY{direction}{abs(apy_change)*100:.1f}%",
                                "timestamp": now,
                                "details": {
                                    "current_apy": pos.apy,
                                    "previous_apy": historical_apy,
                                    "apy_change": apy_change,
                                    "recommendation": recommendation,
                                    "potential_impact": (
                                        "高收益可能伴随高风险"
                                        if apy_change > 0.5
                                        else "收益下降可能表明市场风险降低"
                                    ),
                                },
                            }
                        )

            # 5. 检查市场趋势
            try:
                eth_data = await self.get_asset_historical_data("ETH")
                if len(eth_data) > 5:
                    # 计算短期趋势
                    recent_prices = eth_data["price"].values[-5:]
                    trend_change = (
                        recent_prices[-1] - recent_prices[0]
                    ) / recent_prices[0]

                    # 计算移动平均线
                    if len(eth_data) >= 20:
                        ma7 = np.mean(eth_data["price"].values[-7:])
                        ma20 = np.mean(eth_data["price"].values[-20:])
                        ma_cross = recent_prices[-1] > ma20 and recent_prices[-2] < ma20
                    else:
                        ma7 = np.mean(recent_prices)
                        ma20 = ma7
                        ma_cross = False

                    # 市场趋势警报
                    if abs(trend_change) > 0.1:  # 10%的趋势变化
                        direction = "上升" if trend_change > 0 else "下降"
                        recommendation = (
                            "可考虑增加风险敞口"
                            if trend_change > 0
                            else "建议减少风险敞口"
                        )

                        alerts.append(
                            {
                                "type": "MARKET_TREND",
                                "severity": "MEDIUM",
                                "asset": "MARKET",
                                "protocol": "ALL",
                                "message": f"市场趋势{direction}，ETH价格变化{trend_change*100:.1f}%，{recommendation}",
                                "timestamp": now,
                                "details": {
                                    "trend_change": trend_change,
                                    "period": "5d",
                                    "current_price": recent_prices[-1],
                                    "ma7": ma7,
                                    "ma20": ma20,
                                    "recommendation": (
                                        "RISK_ON" if trend_change > 0 else "RISK_OFF"
                                    ),
                                    "analysis": f"价格{'高于' if recent_prices[-1] > ma20 else '低于'}20日均线",
                                },
                            }
                        )

                    # 移动平均线交叉警报
                    if ma_cross:
                        alerts.append(
                            {
                                "type": "MA_CROSS",
                                "severity": "MEDIUM",
                                "asset": "ETH",
                                "protocol": "ALL",
                                "message": f"ETH价格突破20日均线，可能开始上升趋势",
                                "timestamp": now,
                                "details": {
                                    "current_price": recent_prices[-1],
                                    "ma20": ma20,
                                    "ma7": ma7,
                                    "recommendation": "考虑增加ETH敞口",
                                },
                            }
                        )
            except Exception as e:
                logger.error(f"处理市场趋势警报时出错: {e}")

            # 6. 检查资产相关性
            try:
                # 获取主要资产数据
                eth_data = await self.get_asset_historical_data("ETH")
                btc_data = await self.get_asset_historical_data("BTC")

                if len(eth_data) > 10 and len(btc_data) > 10:
                    # 计算相关性
                    eth_prices = eth_data["price"].values[-10:]
                    btc_prices = btc_data["price"].values[-10:]

                    if len(eth_prices) == len(btc_prices):
                        correlation = np.corrcoef(eth_prices, btc_prices)[0, 1]

                        # 相关性异常警报
                        if abs(correlation) < 0.5:  # 相关性减弱
                            alerts.append(
                                {
                                    "type": "CORRELATION_CHANGE",
                                    "severity": "MEDIUM",
                                    "asset": "MARKET",
                                    "protocol": "ALL",
                                    "message": f"ETH和BTC相关性减弱 ({correlation:.2f})，市场可能出现分化",
                                    "timestamp": now,
                                    "details": {
                                        "correlation": correlation,
                                        "period": "10d",
                                        "recommendation": "关注资产间轮动机会",
                                    },
                                }
                            )
            except Exception as e:
                logger.error(f"处理资产相关性警报时出错: {e}")

            return alerts

        except Exception as e:
            logger.error(f"获取市场警报时出错: {e}")
            return []

    async def _get_aave_v3_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在Aave V3的存款头寸"""
        positions = []

        try:
            # 如果是演示模式，返回演示数据
            if address.lower() == DEMO_ADDRESS.lower() or self.demo_mode:
                logger.info(f"为演示地址返回预设Aave V3头寸数据")
                # 返回一些演示的Aave V3头寸
                return [
                    ProtocolPosition(
                        protocol="Aave-V3",
                        asset="ETH",
                        amount=1.2,
                        leverage=1.5,
                        apy=0.02,
                    ),
                    ProtocolPosition(
                        protocol="Aave-V3",
                        asset="USDC",
                        amount=5000,
                        leverage=1.0,
                        apy=0.04,
                    ),
                    ProtocolPosition(
                        protocol="Aave-V3",
                        asset="BTC",
                        amount=0.15,
                        leverage=1.2,
                        apy=0.015,
                    ),
                ]

            # 使用Aave V3 Subgraph获取用户的头寸信息
            # 根据网络选择合适的subgraph端点
            # 以太坊主网的Aave V3 subgraph端点
            subgraph_url = "https://gateway.thegraph.com/api/95d759c3b12e4dd174e4f7e2adfa4882/subgraphs/id/JCNWRypm7FYwV8fx5HhzZPSFaMxgkPuw4TnR3Gpi81zk"

            # 构建GraphQL查询，获取用户的存款和借款头寸
            # 根据最新的Messari Subgraph Schema进行查询
            query = """
            query GetUserPositions($userAddress: String!) {
              account(id: $userAddress) {
                id
                positions(where: {side: LENDER}) {
                  id
                  side
                  balance
                  isCollateral
                  isIsolated
                  market {
                    id
                    name
                    inputToken {
                      id
                      name
                      symbol
                      decimals
                    }
                    outputToken {
                      id
                      name
                      symbol
                      decimals
                    }
                    rates(where: {side: LENDER}) {
                      rate
                      side
                      type
                    }
                    maximumLTV
                    liquidationThreshold
                    liquidationPenalty
                    totalValueLockedUSD
                    totalBorrowBalanceUSD
                    inputTokenPriceUSD
                    canUseAsCollateral
                  }
                }
                # 获取借款头寸
                borrowingPositions: positions(where: {side: BORROWER}) {
                  id
                  balance
                  side
                  type
                  market {
                    id
                    inputToken {
                      id
                      symbol
                      decimals
                    }
                    inputTokenPriceUSD
                    rates(where: {side: BORROWER}) {
                      rate
                      side
                      type
                    }
                  }
                }
                _enabledCollaterals {
                  id
                }
                _eMode
              }
            }
            """

            # 设置查询变量
            variables = {"userAddress": address.lower()}

            # 发送GraphQL请求
            logger.info(f"向Aave V3 Subgraph发送查询，获取地址{address}的头寸")
            response = requests.post(
                subgraph_url,
                json={"query": query, "variables": variables},
                proxies=proxies,
            )

            if response.status_code != 200:
                logger.error(
                    f"Subgraph请求失败: {response.status_code}, {response.text}"
                )
                # 如果subgraph请求失败，回退到合约调用方法
                return await self._get_aave_v3_positions_fallback(address)

            data = response.json()

            if "errors" in data:
                logger.error(f"Subgraph查询错误: {data['errors']}")
                return await self._get_aave_v3_positions_fallback(address)

            if (
                "data" not in data
                or "account" not in data["data"]
                or not data["data"]["account"]
            ):
                logger.warning(f"Subgraph返回的数据格式不正确或用户不存在: {data}")
                return []

            # 处理存款头寸
            account_data = data["data"]["account"]
            lender_positions = account_data.get("positions", [])

            # 处理借款头寸以计算杠杆率
            borrower_positions = account_data.get("borrowingPositions", [])

            # 获取用户的eMode状态
            emode_enabled = account_data.get("_eMode", False)

            # 获取用户启用的抵押品市场
            enabled_collaterals = account_data.get("_enabledCollaterals", [])
            enabled_collateral_ids = (
                [collateral["id"] for collateral in enabled_collaterals]
                if enabled_collaterals
                else []
            )

            # 如果没有找到任何头寸，返回空列表
            if not lender_positions and not borrower_positions:
                logger.info(f"地址 {address} 在Aave V3上没有找到任何头寸")
                return []

            # 计算总存款价值和总借款价值（用于计算杠杆率）
            total_deposit_value_usd = 0
            total_borrow_value_usd = 0

            # 计算借款价值
            for borrow_pos in borrower_positions:
                token_decimals = int(borrow_pos["market"]["inputToken"]["decimals"])
                token_price_usd = float(borrow_pos["market"]["inputTokenPriceUSD"])
                borrow_balance = int(borrow_pos["balance"]) / (10**token_decimals)
                borrow_value_usd = borrow_balance * token_price_usd
                total_borrow_value_usd += borrow_value_usd

                # 获取借款利率
                borrow_apy = 0.0
                borrow_type = borrow_pos.get("type", "VARIABLE")
                for rate in borrow_pos["market"]["rates"]:
                    if rate["side"] == "BORROWER" and rate["type"] == borrow_type:
                        borrow_apy = float(rate["rate"])
                        break

                logger.info(
                    f"发现Aave V3 {borrow_pos['market']['inputToken']['symbol']}借款: {borrow_balance:.6f} "
                    f"(APY: {borrow_apy*100:.2f}%, 价值: ${borrow_value_usd:.2f}, "
                    f"类型: {borrow_type})"
                )

            # 处理每个存款头寸
            for pos in lender_positions:
                try:
                    market = pos["market"]
                    token = market["inputToken"]
                    token_symbol = token["symbol"]
                    token_decimals = int(token["decimals"])

                    # 获取存款余额
                    balance = int(pos["balance"])
                    amount = balance / (10**token_decimals)

                    # 获取代币价格
                    token_price_usd = float(market["inputTokenPriceUSD"])
                    deposit_value_usd = amount * token_price_usd
                    total_deposit_value_usd += deposit_value_usd

                    # 获取存款APY
                    apy = 0.0
                    for rate in market["rates"]:
                        if rate["side"] == "LENDER" and rate["type"] == "VARIABLE":
                            apy = float(rate["rate"])
                            break

                    # 是否用作抵押品
                    is_collateral = pos["isCollateral"]

                    # 是否为隔离资产
                    is_isolated = pos.get("isIsolated", False)

                    # 创建头寸对象
                    position = ProtocolPosition(
                        protocol="Aave-V3",
                        asset=token_symbol,
                        amount=amount,
                        leverage=None,  # 稍后计算整体杠杆率
                        apy=apy,
                    )

                    positions.append(position)
                    logger.info(
                        f"发现Aave V3 {token_symbol}存款: {amount:.6f} "
                        f"(APY: {apy*100:.2f}%, 价值: ${deposit_value_usd:.2f}, "
                        f"用作抵押品: {is_collateral}, 隔离资产: {is_isolated})"
                    )
                except Exception as e:
                    logger.error(f"处理Aave V3存款头寸时出错: {e}")

            # 计算整体杠杆率
            leverage = 1.0
            if total_deposit_value_usd > 0:
                leverage = (
                    total_deposit_value_usd + total_borrow_value_usd
                ) / total_deposit_value_usd

            # 更新所有头寸的杠杆率
            for position in positions:
                position.leverage = leverage

            # 记录eMode状态
            if emode_enabled:
                logger.info(f"用户已启用eMode (高效模式)")

            return positions

        except Exception as e:
            logger.error(f"获取Aave V3头寸时出错: {e}")
            # 如果出现任何错误，尝试回退到合约调用方法
            try:
                return await self._get_aave_v3_positions_fallback(address)
            except Exception as fallback_error:
                logger.error(f"回退方法也失败: {fallback_error}")
                return []

    async def _get_aave_v3_positions_fallback(
        self, address: str
    ) -> List[ProtocolPosition]:
        """获取用户在Aave V3的存款头寸（回退方法，使用合约调用）"""
        positions = []

        try:
            # 获取Aave V3合约
            pool_address = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
            data_provider_address = "0x7B4EB56E7CD4b454BA8ff71E4518426369a138a3"

            pool_contract = self.w3.eth.contract(
                address=pool_address, abi=self.aave_pool_abi
            )

            data_provider_contract = self.w3.eth.contract(
                address=data_provider_address, abi=self.aave_data_provider_abi
            )

            # 获取所有支持的代币
            all_reserves = (
                data_provider_contract.functions.getAllReservesTokens().call()
            )

            # 获取用户账户数据（总抵押品、总债务等）
            account_data = pool_contract.functions.getUserAccountData(address).call()
            total_collateral_eth = account_data[0]
            total_debt_eth = account_data[1]
            health_factor = account_data[5]

            # 计算杠杆率
            leverage = 1.0
            if total_collateral_eth > 0:
                leverage = (
                    total_collateral_eth + total_debt_eth
                ) / total_collateral_eth

            # 遍历所有资产，检查用户的存款
            for reserve in all_reserves:
                token_symbol = reserve[0]
                token_address = reserve[1]

                # 获取用户在该资产上的数据
                user_reserve_data = data_provider_contract.functions.getUserReserveData(
                    token_address, address
                ).call()

                current_atoken_balance = user_reserve_data[0]

                # 如果用户有存款
                if current_atoken_balance > 0:
                    # 获取代币信息
                    token_contract = self.w3.eth.contract(
                        address=token_address, abi=self.erc20_abi
                    )

                    # 获取代币精度
                    try:
                        decimals = token_contract.functions.decimals().call()
                    except Exception:
                        decimals = 18  # 默认精度

                    # 计算实际金额
                    amount = current_atoken_balance / (10**decimals)

                    # 获取存款APY
                    liquidity_rate = user_reserve_data[6]
                    apy = liquidity_rate / (10**27)  # Aave使用ray单位(10^27)

                    # 创建头寸对象
                    position = ProtocolPosition(
                        protocol="Aave-V3",
                        asset=token_symbol,
                        amount=amount,
                        leverage=leverage,
                        apy=apy,
                    )

                    positions.append(position)

            return positions

        except Exception as e:
            logger.error(f"获取Aave V3头寸时出错（回退方法）: {e}")
            return []
