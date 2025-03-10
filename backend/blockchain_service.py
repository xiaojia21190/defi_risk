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

# 设置日志记录器
logger = logging.getLogger("defi_risk.blockchain")

# 设置代理
proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}


class HistoricalDataCache:
    def __init__(
        self, max_size: int = 100, expiration_minutes: int = 30
    ):  # 增加缓存时间
        self.cache = {}
        self.max_size = max_size
        self.expiration_delta = timedelta(minutes=expiration_minutes)
        self.access_times = {}  # 记录访问时间用于LRU策略

    def get(self, key: str) -> Optional[Tuple[pd.DataFrame, datetime]]:
        """获取缓存数据，增加访问记录"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            now = datetime.now()

            # 更新访问时间
            self.access_times[key] = now

            # 检查是否过期
            if now - timestamp < self.expiration_delta:
                logger.debug(f"从缓存获取 {key} 的历史数据")
                return data
            else:
                logger.debug(f"{key} 的缓存数据已过期")
                return None
        return None

    def set(self, key: str, data: pd.DataFrame):
        """设置缓存数据，实现LRU淘汰策略"""
        now = datetime.now()

        # 如果缓存已满，删除最久未访问的项
        if len(self.cache) >= self.max_size and key not in self.cache:
            # 按最后访问时间排序
            oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
            logger.debug(f"缓存已满，删除最久未访问的项: {oldest_key}")

        # 添加新数据到缓存
        self.cache[key] = (data, now)
        self.access_times[key] = now
        logger.debug(f"添加 {key} 的历史数据到缓存")


# 演示数据常量
DEMO_ADDRESS = "0xAbCdEf123456789AbCdEf123456789AbCdEf1234"
DEMO_ASSETS = {
    "ETH": {"price": 2000.0, "volatility": 0.35},
    "WBTC": {"price": 40000.0, "volatility": 0.42},
    "USDC": {"price": 1.0, "volatility": 0.05},
    "DAI": {"price": 1.0, "volatility": 0.05},
}

DEMO_PROTOCOLS = {
    "Aave V3": {"risk": 0.25, "apy_range": (0.02, 0.05)},
    "Compound V3": {"risk": 0.20, "apy_range": (0.03, 0.06)},
    "Curve": {"risk": 0.30, "apy_range": (0.04, 0.10)},
    "Uniswap V2": {"risk": 0.35, "apy_range": (0.05, 0.15)},
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
        self.historical_data_cache = HistoricalDataCache(
            max_size=100, expiration_minutes=30
        )
        self.data_fetch_locks = {}  # 用于防止并发获取相同数据
        self.pending_requests = {}  # 用于合并请求

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

            # 3. 获取Curve头寸
            try:
                curve_positions = await self._get_curve_positions(address)
                positions.extend(curve_positions)
            except Exception as e:
                logger.error(f"获取Curve头寸时出错: {e}")

            # 4. 获取Uniswap V2头寸
            try:
                uniswap_positions = await self._get_uniswap_v2_positions(address)
                positions.extend(uniswap_positions)
            except Exception as e:
                logger.error(f"获取Uniswap V2头寸时出错: {e}")

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
                    historical_data = await self.get_asset_historical_data(asset)

                    if len(historical_data) > 1:
                        # 基本价格变化检测
                        latest_price = historical_data["price"].iloc[-1]
                        prev_price = historical_data["price"].iloc[-2]
                        price_change = (latest_price - prev_price) / prev_price

                        # 计算24小时价格变化
                        if len(historical_data) >= 24:
                            price_24h_ago = historical_data["price"].iloc[-24]
                            price_change_24h = (
                                latest_price - price_24h_ago
                            ) / price_24h_ago
                        else:
                            price_change_24h = price_change

                        # 计算波动率
                        if len(historical_data) >= 7:
                            recent_prices = historical_data["price"].iloc[-7:].values
                            volatility = (
                                np.std(np.diff(recent_prices) / recent_prices[:-1])
                                * 100
                            )
                        else:
                            volatility = abs(price_change) * 100

                        # 计算RSI指标
                        if len(historical_data) >= 14:
                            prices = historical_data["price"].values
                            delta = np.diff(prices)
                            gain = np.where(delta > 0, delta, 0)
                            loss = np.where(delta < 0, -delta, 0)
                            avg_gain = np.mean(gain[-14:])
                            avg_loss = np.mean(loss[-14:])
                            rs = avg_gain / avg_loss if avg_loss != 0 else 0
                            rsi = 100 - (100 / (1 + rs))
                        else:
                            rsi = 50  # 默认值

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
                                        "previous_price": (
                                            price_24h_ago
                                            if len(historical_data) >= 24
                                            else prev_price
                                        ),
                                        "volatility": volatility,
                                        "rsi": rsi,
                                    },
                                }
                            )

                        # RSI超买超卖警报
                        if len(historical_data) >= 14:
                            if rsi > 70:
                                alerts.append(
                                    {
                                        "type": "OVERBOUGHT",
                                        "severity": "MEDIUM",
                                        "asset": asset,
                                        "protocol": pos.protocol,
                                        "message": f"{asset}当前RSI为{rsi:.1f}，处于超买区间，可能面临回调风险",
                                        "timestamp": now,
                                        "details": {
                                            "rsi": rsi,
                                            "current_price": latest_price,
                                            "price_change_24h": price_change_24h * 100,
                                        },
                                    }
                                )
                            elif rsi < 30:
                                alerts.append(
                                    {
                                        "type": "OVERSOLD",
                                        "severity": "MEDIUM",
                                        "asset": asset,
                                        "protocol": pos.protocol,
                                        "message": f"{asset}当前RSI为{rsi:.1f}，处于超卖区间，可能出现反弹",
                                        "timestamp": now,
                                        "details": {
                                            "rsi": rsi,
                                            "current_price": latest_price,
                                            "price_change_24h": price_change_24h * 100,
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

            # 按严重程度和时间戳排序
            severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            alerts.sort(key=lambda x: (severity_order[x["severity"]], -x["timestamp"]))

            return alerts

        except Exception as e:
            logger.error(f"生成市场警报时出错: {e}")
            # 出错时返回演示警报
            return self._get_demo_market_alerts()

    async def get_asset_historical_data(self, asset: str) -> pd.DataFrame:
        """获取资产的历史价格数据，实现请求合并"""
        # 创建锁，如果不存在
        if asset not in self.data_fetch_locks:
            self.data_fetch_locks[asset] = asyncio.Lock()

        # 使用锁防止并发获取相同数据
        async with self.data_fetch_locks[asset]:
            # 检查是否有正在处理的请求
            if asset in self.pending_requests:
                # 等待现有请求完成并返回结果
                logger.info(f"合并 {asset} 的历史数据请求")
                return await self.pending_requests[asset]

            # 创建新的请求任务
            request_task = asyncio.create_task(self._fetch_historical_data(asset))
            self.pending_requests[asset] = request_task

            try:
                # 执行请求
                result = await request_task
                return result
            finally:
                # 清理
                del self.pending_requests[asset]

    async def _fetch_historical_data(self, asset: str) -> pd.DataFrame:
        """实际获取历史数据的方法"""
        try:
            # 检查缓存
            cached_data = self.historical_data_cache.get(asset)
            if cached_data is not None:
                logger.info(f"从缓存获取 {asset} 的历史数据")
                return cached_data

            # 资产ID映射（不同API可能使用不同的ID）
            asset_ids = {
                # CoinGecko IDs
                "coingecko": {
                    "ETH": "ethereum",
                    "WBTC": "wrapped-bitcoin",
                    "USDC": "usd-coin",
                    "DAI": "dai",
                    "AAVE": "aave",
                    "COMP": "compound-governance-token",
                    "UNI": "uniswap",
                    "LINK": "chainlink",
                    "SNX": "synthetix-network-token",
                    "MKR": "maker",
                    "YFI": "yearn-finance",
                    "SUSHI": "sushi",
                },
                # CoinMarketCap IDs (通常使用数字ID)
                "coinmarketcap": {
                    "ETH": "1027",
                    "WBTC": "3717",
                    "USDC": "3408",
                    "DAI": "4943",
                    "AAVE": "7278",
                    "COMP": "5692",
                    "UNI": "7083",
                    "LINK": "1975",
                    "SNX": "2586",
                    "MKR": "1518",
                    "YFI": "5864",
                    "SUSHI": "6758",
                },
                # Binance交易对
                "binance": {
                    "ETH": "ETHUSDT",
                    "WBTC": "BTCUSDT",  # 使用BTC作为WBTC的代理
                    "USDC": "USDCUSDT",
                    "DAI": "DAIUSDT",
                    "AAVE": "AAVEUSDT",
                    "COMP": "COMPUSDT",
                    "UNI": "UNIUSDT",
                    "LINK": "LINKUSDT",
                    "SNX": "SNXUSDT",
                    "MKR": "MKRUSDT",
                    "YFI": "YFIUSDT",
                    "SUSHI": "SUSHIUSDT",
                },
            }

            if (
                asset not in asset_ids["coingecko"]
                and asset not in asset_ids["coinmarketcap"]
                and asset not in asset_ids["binance"]
            ):
                logger.warning(f"不支持的资产 {asset}，使用演示数据")
                demo_data = self._get_demo_historical_data(asset)
                self.historical_data_cache.set(asset, demo_data)
                return demo_data

            # 尝试从不同的数据源获取数据
            df = None
            error_messages = []

            # # 1. 尝试CoinGecko API
            # if asset in asset_ids["coingecko"]:
            #     try:
            #         logger.info(f"尝试从CoinGecko获取{asset}数据")
            #         df = await self._get_coingecko_data(
            #             asset, asset_ids["coingecko"][asset]
            #         )
            #         if df is not None and not df.empty:
            #             logger.info(f"成功从CoinGecko获取{asset}数据")
            #             self.historical_data_cache.set(asset, df)
            #             return df
            #     except Exception as e:
            #         error_msg = f"从CoinGecko获取{asset}数据失败: {e}"
            #         logger.warning(error_msg)
            #         error_messages.append(error_msg)

            # # 2. 尝试CoinMarketCap API
            # if asset in asset_ids["coinmarketcap"]:
            #     try:
            #         logger.info(f"尝试从CoinMarketCap获取{asset}数据")
            #         df = await self._get_coinmarketcap_data(
            #             asset, asset_ids["coinmarketcap"][asset]
            #         )
            #         if df is not None and not df.empty:
            #             logger.info(f"成功从CoinMarketCap获取{asset}数据")
            #             self.historical_data_cache.set(asset, df)
            #             return df
            #     except Exception as e:
            #         error_msg = f"从CoinMarketCap获取{asset}数据失败: {e}"
            #         logger.warning(error_msg)
            #         error_messages.append(error_msg)

            # 3. 尝试Binance API
            if asset in asset_ids["binance"]:
                try:
                    logger.info(f"尝试从Binance获取{asset}数据")
                    df = await self._get_binance_data(
                        asset, asset_ids["binance"][asset]
                    )
                    if df is not None and not df.empty:
                        logger.info(f"成功从Binance获取{asset}数据")
                        self.historical_data_cache.set(asset, df)
                        return df
                except Exception as e:
                    error_msg = f"从Binance获取{asset}数据失败: {e}"
                    logger.warning(error_msg)
                    error_messages.append(error_msg)

            # 4. 尝试链上数据（通过Chainlink价格预言机）
            try:
                logger.info(f"尝试从链上获取{asset}数据")
                df = await self._get_onchain_data(asset)
                if df is not None and not df.empty:
                    logger.info(f"成功从链上获取{asset}数据")
                    self.historical_data_cache.set(asset, df)
                    return df
            except Exception as e:
                error_msg = f"从链上获取{asset}数据失败: {e}"
                logger.warning(error_msg)
                error_messages.append(error_msg)

            # 5. 所有数据源都失败，使用演示数据
            logger.error(
                f"所有数据源获取{asset}数据失败，使用演示数据。错误: {error_messages}"
            )
            demo_data = self._get_demo_historical_data(asset)
            self.historical_data_cache.set(asset, demo_data)
            return demo_data

        except Exception as e:
            logger.error(f"获取{asset}历史数据时出错: {e}")
            demo_data = self._get_demo_historical_data(asset)
            self.historical_data_cache.set(asset, demo_data)
            return demo_data

    async def _get_coingecko_data(
        self, asset: str, asset_id: str
    ) -> Optional[pd.DataFrame]:
        """优化CoinGecko API调用"""
        # 实现指数退避重试
        max_retries = 3
        retry_delay = 1  # 初始延迟1秒

        for attempt in range(max_retries):
            try:
                # 使用aiohttp进行异步请求
                async with aiohttp.ClientSession() as session:
                    # 获取过去30天的数据，以天为单位
                    url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/market_chart"
                    params = {
                        "vs_currency": "usd",
                        "days": "30",
                        "interval": "daily",
                    }

                    # 添加API密钥（如果有）
                    if hasattr(self, "coingecko_api_key") and self.coingecko_api_key:
                        params["x_cg_pro_api_key"] = self.coingecko_api_key

                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()

                            # 处理数据
                            prices = data.get("prices", [])
                            market_caps = data.get("market_caps", [])
                            total_volumes = data.get("total_volumes", [])

                            if not prices:
                                logger.warning(f"CoinGecko返回的{asset}价格数据为空")
                                return None

                            # 创建DataFrame
                            df = pd.DataFrame(
                                {
                                    "timestamp": [
                                        datetime.fromtimestamp(p[0] / 1000)
                                        for p in prices
                                    ],
                                    "price": [p[1] for p in prices],
                                    "market_cap": (
                                        [m[1] for m in market_caps]
                                        if market_caps
                                        else [None] * len(prices)
                                    ),
                                    "volume": (
                                        [v[1] for v in total_volumes]
                                        if total_volumes
                                        else [None] * len(prices)
                                    ),
                                }
                            )
                            df["source"] = "coingecko"
                            return df
                        elif response.status == 429:  # 速率限制
                            wait_time = retry_delay * (2**attempt)
                            logger.warning(
                                f"CoinGecko API速率限制，等待{wait_time}秒后重试"
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            logger.error(f"CoinGecko API返回错误: {response.status}")
                            return None
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)
                    logger.warning(
                        f"CoinGecko API请求失败，等待{wait_time}秒后重试: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"CoinGecko API请求失败，已达到最大重试次数: {e}")
                    return None

        return None

    async def _get_coinmarketcap_data(
        self, asset: str, asset_id: str
    ) -> Optional[pd.DataFrame]:
        """从CoinMarketCap获取历史数据"""
        try:
            # 检查是否配置了API密钥
            if (
                not hasattr(self, "coinmarketcap_api_key")
                or not self.coinmarketcap_api_key
            ):
                logger.warning("未配置CoinMarketCap API密钥，跳过")
                return None

            # 使用aiohttp进行异步请求
            async with aiohttp.ClientSession() as session:
                # CoinMarketCap API端点
                url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical"

                # 计算时间范围（过去30天）
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)

                # 设置请求参数
                params = {
                    "id": asset_id,
                    "time_start": start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "time_end": end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "interval": "1d",  # 每天一个数据点
                    "convert": "USD",
                }

                headers = {
                    "X-CMC_PRO_API_KEY": self.coinmarketcap_api_key,
                    "Accept": "application/json",
                }

                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        # 解析响应数据
                        quotes = data.get("data", {}).get("quotes", [])
                        if not quotes:
                            logger.warning(f"CoinMarketCap返回的{asset}数据为空")
                            return None

                        # 创建DataFrame
                        timestamps = []
                        prices = []
                        market_caps = []
                        volumes = []

                        for quote in quotes:
                            quote_time = datetime.fromisoformat(
                                quote.get("timestamp").replace("Z", "+00:00")
                            )
                            quote_data = quote.get("quote", {}).get("USD", {})

                            timestamps.append(quote_time)
                            prices.append(quote_data.get("price"))
                            market_caps.append(quote_data.get("market_cap"))
                            volumes.append(quote_data.get("volume_24h"))

                        df = pd.DataFrame(
                            {
                                "timestamp": timestamps,
                                "price": prices,
                                "market_cap": market_caps,
                                "volume": volumes,
                            }
                        )
                        df["source"] = "coinmarketcap"
                        return df
                    else:
                        logger.error(f"CoinMarketCap API返回错误: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"从CoinMarketCap获取{asset}数据失败: {e}")
            return None

    async def _get_binance_data(
        self, asset: str, symbol: str
    ) -> Optional[pd.DataFrame]:
        """从Binance API获取历史数据"""
        url = "https://api.binance.com/api/v3/klines"
        # 计算时间范围（过去30天）
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (30 * 24 * 60 * 60 * 1000)  # 30天的毫秒数

        # 设置请求参数
        params = {
            "symbol": symbol,
            "interval": "1d",  # 1天的K线
            "startTime": start_time,
            "endTime": end_time,
            "limit": 30,  # 最多30个数据点
        }

        try:
            response = requests.get(url, params=params, proxies=proxies)
            if response.status_code == 200:
                data = response.json()

                if not data:
                    logger.warning(f"Binance返回的{asset}数据为空")
                    return None

                # 创建DataFrame
                # Binance K线数据格式:
                # [
                #   [
                #     开盘时间,
                #     开盘价,
                #     最高价,
                #     最低价,
                #     收盘价,
                #     成交量,
                #     收盘时间,
                #     成交额,
                #     成交笔数,
                #     主动买入成交量,
                #     主动买入成交额,
                #     忽略
                #   ]
                # ]
                df = pd.DataFrame(
                    {
                        "timestamp": [
                            datetime.fromtimestamp(k[0] / 1000) for k in data
                        ],
                        "price": [float(k[4]) for k in data],  # 使用收盘价
                        "volume": [float(k[5]) for k in data],
                        "market_cap": [None] * len(data),  # Binance不提供市值数据
                    }
                )
                df["source"] = "binance"
                return df
            else:
                logger.error(f"Binance API返回错误: {response.status}")
                return None
        except Exception as e:
            logger.error(f"从Binance获取{asset}数据失败: {e}")
            return None

    async def _get_onchain_data(self, asset: str) -> Optional[pd.DataFrame]:
        """从链上获取历史数据（通过Chainlink价格预言机）"""
        try:
            # 检查是否支持该资产的链上数据
            chainlink_feeds = {
                "ETH": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",  # ETH/USD
                "WBTC": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",  # BTC/USD
                "LINK": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c",  # LINK/USD
                "AAVE": "0x547a514d5e3769680Ce22B2361c10Ea13619e8a9",  # AAVE/USD
                "UNI": "0x553303d460EE0afB37EdFf9bE42922D8FF63220e",  # UNI/USD
                "SNX": "0xDC3EA94CD0AC27d9A86C180091e7f78C683d3699",  # SNX/USD
                "COMP": "0xdbd020CAeF83eFd542f4De03e3cF0C28A4428bd5",  # COMP/USD
                "YFI": "0xA027702dbb89fbd58938e4324ac03B58d812b0E1",  # YFI/USD
                "SUSHI": "0xCc70F09A6CC17553b2E31954cD36E4A2d89501f7",  # SUSHI/USD
                "MKR": "0xec1D1B3b0443256cc3860e24a46F108e699484Aa",  # MKR/USD
                "DAI": "0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9",  # DAI/USD
                "USDC": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",  # USDC/USD
            }

            if asset not in chainlink_feeds:
                logger.warning(f"不支持{asset}的链上数据")
                return None

            # 获取Chainlink价格预言机合约地址
            feed_address = chainlink_feeds[asset]

            # 创建合约实例
            abi = [
                {
                    "inputs": [],
                    "name": "latestRoundData",
                    "outputs": [
                        {"name": "roundId", "type": "uint80"},
                        {"name": "answer", "type": "int256"},
                        {"name": "startedAt", "type": "uint256"},
                        {"name": "updatedAt", "type": "uint256"},
                        {"name": "answeredInRound", "type": "uint80"},
                    ],
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "inputs": [{"name": "roundId", "type": "uint80"}],
                    "name": "getRoundData",
                    "outputs": [
                        {"name": "roundId", "type": "uint80"},
                        {"name": "answer", "type": "int256"},
                        {"name": "startedAt", "type": "uint256"},
                        {"name": "updatedAt", "type": "uint256"},
                        {"name": "answeredInRound", "type": "uint80"},
                    ],
                    "stateMutability": "view",
                    "type": "function",
                },
            ]

            contract = self.w3.eth.contract(address=feed_address, abi=abi)

            # 获取最新轮次数据
            latest_data = await self.w3.eth.call_async(
                contract.functions.latestRoundData().build_transaction(
                    {
                        "from": self.w3.eth.default_account
                        or "0x0000000000000000000000000000000000000000"
                    }
                )
            )
            latest_round_id = latest_data[0]

            # 收集历史数据（尝试获取30天的数据点）
            timestamps = []
            prices = []

            # 从最新轮次向前查询30个数据点
            for i in range(30):
                try:
                    round_id = max(1, latest_round_id - i)
                    round_data = await self.w3.eth.call_async(
                        contract.functions.getRoundData(round_id).build_transaction(
                            {
                                "from": self.w3.eth.default_account
                                or "0x0000000000000000000000000000000000000000"
                            }
                        )
                    )

                    # 解析数据
                    # Chainlink价格通常有8位小数
                    price = round_data[1] / 10**8
                    timestamp = datetime.fromtimestamp(round_data[3])

                    timestamps.append(timestamp)
                    prices.append(price)
                except Exception as e:
                    logger.warning(f"获取{asset}轮次{round_id}数据失败: {e}")
                    continue

            if not timestamps:
                logger.warning(f"未能获取{asset}的链上历史数据")
                return None

            # 创建DataFrame
            df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "price": prices,
                    "volume": [None] * len(timestamps),  # 链上数据没有交易量
                    "market_cap": [None] * len(timestamps),  # 链上数据没有市值
                }
            )
            df["source"] = "chainlink"

            # 按时间排序
            df = df.sort_values("timestamp")

            return df
        except Exception as e:
            logger.error(f"从链上获取{asset}数据失败: {e}")
            return None

    def _get_demo_historical_data(self, asset: str) -> pd.DataFrame:
        """生成演示用的历史数据"""
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        base_price = DEMO_ASSETS.get(asset, {"price": 100.0})["price"]
        volatility = DEMO_ASSETS.get(asset, {"volatility": 0.01})["volatility"]

        np.random.seed(42 + hash(asset) % 100)
        price_changes = np.random.normal(0, volatility / 2, size=30)
        prices = base_price * (1 + np.cumsum(price_changes))
        volumes = np.random.uniform(10000, 100000, size=30)

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "price": prices,
                "volume": volumes,
                "market_cap": np.random.uniform(
                    base_price * 1000000, base_price * 10000000, size=30
                ),
            }
        )
        df["source"] = "demo"
        return df

    def _get_demo_market_alerts(self) -> List[Dict]:
        """返回演示警报数据"""
        now = int(datetime.now().timestamp())
        hour = 3600

        return [
            {
                "type": "PRICE_VOLATILITY",
                "severity": "HIGH",
                "asset": "ETH",
                "protocol": "Aave V3",
                "message": "ETH价格在24小时内下跌7.5%",
                "timestamp": now - 1 * hour,
                "details": {
                    "price_change": -0.075,
                    "current_price": 1850.0,
                    "previous_price": 2000.0,
                },
            },
            {
                "type": "LIQUIDATION_RISK",
                "severity": "HIGH",
                "asset": "ETH",
                "protocol": "Aave V3",
                "message": "Aave V3上的ETH头寸接近清算阈值，当前杠杆率1.85",
                "timestamp": now - 2 * hour,
                "details": {
                    "leverage": 1.85,
                    "safe_leverage": 1.5,
                    "position_size": 2.5,
                },
            },
            {
                "type": "APY_CHANGE",
                "severity": "MEDIUM",
                "asset": "USDC",
                "protocol": "Compound V3",
                "message": "Compound V3的USDC APY增加25%",
                "timestamp": now - 3 * hour,
                "details": {
                    "current_apy": 0.05,
                    "previous_apy": 0.04,
                    "apy_change": 0.25,
                },
            },
        ]

    async def get_demo_positions(self) -> List[ProtocolPosition]:
        """为演示提供更真实的用户头寸数据"""
        try:
            today = datetime.now().date()
            seed = int(f"{today.year}{today.month:02d}{today.day:02d}")
            random.seed(seed)

            # 获取当前市场价格（模拟）
            current_prices = {
                "ETH": 3500.0,  # 假设当前ETH价格
                "USDC": 1.0,
                "DAI": 1.0,
                "WBTC": 60000.0,  # 假设当前BTC价格
                "USDT": 1.0,
                "LINK": 15.0,
                "UNI": 8.0,
            }

            # 更真实的APY范围（基于当前市场情况）
            apy_ranges = {
                "Aave V3": {
                    "ETH": (0.01, 0.025),
                    "USDC": (0.03, 0.045),
                    "DAI": (0.025, 0.04),
                    "WBTC": (0.01, 0.02),
                },
                "Compound V3": {
                    "ETH": (0.015, 0.03),
                    "USDC": (0.035, 0.05),
                    "DAI": (0.03, 0.045),
                    "WBTC": (0.012, 0.022),
                },
                "Curve": {
                    "DAI": (0.04, 0.06),
                    "USDC": (0.04, 0.06),
                    "USDT": (0.04, 0.06),
                },
                "Uniswap V2": {
                    "ETH": (0.05, 0.12),
                    "WBTC": (0.04, 0.1),
                    "LINK": (0.06, 0.15),
                    "UNI": (0.07, 0.18),
                },
            }

            # 更真实的杠杆率限制
            max_leverage = {
                "Aave V3": {"ETH": 2.5, "USDC": 1.1, "DAI": 1.1, "WBTC": 2.0},
                "Compound V3": {"ETH": 2.0, "USDC": 1.0, "DAI": 1.0, "WBTC": 1.8},
            }

            # 设置总投资组合价值（美元）
            total_portfolio_value = random.uniform(30000, 50000)

            # 分配资产比例
            asset_allocation = {
                "ETH": random.uniform(0.3, 0.5),  # 30-50% ETH
                "USDC": random.uniform(0.2, 0.3),  # 20-30% USDC
                "DAI": random.uniform(0.1, 0.2),  # 10-20% DAI
                "WBTC": random.uniform(0.1, 0.25),  # 10-25% WBTC
            }

            # 归一化资产分配比例
            total_allocation = sum(asset_allocation.values())
            for asset in asset_allocation:
                asset_allocation[asset] /= total_allocation

            # 生成更真实的头寸
            positions = []

            # ETH在Aave
            eth_aave_amount = (
                total_portfolio_value * asset_allocation["ETH"] * 0.6
            ) / current_prices["ETH"]
            positions.append(
                ProtocolPosition(
                    protocol="Aave V3",
                    asset="ETH",
                    amount=round(eth_aave_amount, 4),
                    leverage=random.uniform(1.0, max_leverage["Aave V3"]["ETH"]),
                    apy=random.uniform(*apy_ranges["Aave V3"]["ETH"]),
                )
            )

            # ETH在Uniswap
            eth_uni_amount = (
                total_portfolio_value * asset_allocation["ETH"] * 0.4
            ) / current_prices["ETH"]
            positions.append(
                ProtocolPosition(
                    protocol="Uniswap V2",
                    asset="ETH/USDC",  # LP代币
                    amount=round(eth_uni_amount, 4),
                    apy=random.uniform(*apy_ranges["Uniswap V2"]["ETH"]),
                )
            )

            # USDC在Compound
            usdc_amount = (
                total_portfolio_value * asset_allocation["USDC"]
            ) / current_prices["USDC"]
            positions.append(
                ProtocolPosition(
                    protocol="Compound V3",
                    asset="USDC",
                    amount=round(usdc_amount, 2),
                    leverage=1.0,
                    apy=random.uniform(*apy_ranges["Compound V3"]["USDC"]),
                )
            )

            # DAI在Curve
            dai_amount = (
                total_portfolio_value * asset_allocation["DAI"]
            ) / current_prices["DAI"]
            positions.append(
                ProtocolPosition(
                    protocol="Curve",
                    asset="DAI/USDC/USDT",  # 3pool
                    amount=round(dai_amount, 2),
                    apy=random.uniform(*apy_ranges["Curve"]["DAI"]),
                )
            )

            # WBTC在Aave
            wbtc_amount = (
                total_portfolio_value * asset_allocation["WBTC"]
            ) / current_prices["WBTC"]
            positions.append(
                ProtocolPosition(
                    protocol="Aave V3",
                    asset="WBTC",
                    amount=round(wbtc_amount, 6),
                    leverage=random.uniform(1.0, max_leverage["Aave V3"]["WBTC"]),
                    apy=random.uniform(*apy_ranges["Aave V3"]["WBTC"]),
                )
            )

            random.seed()  # 重置随机种子
            return positions

        except Exception as e:
            logger.error(f"生成演示头寸时出错: {e}")
            # 提供一个备用的固定数据集
            return [
                ProtocolPosition(
                    protocol="Aave V3", asset="ETH", amount=1.2, leverage=1.5, apy=0.02
                ),
                ProtocolPosition(
                    protocol="Compound V3",
                    asset="USDC",
                    amount=12000,
                    leverage=1.0,
                    apy=0.04,
                ),
                ProtocolPosition(
                    protocol="Curve", asset="DAI/USDC/USDT", amount=8000, apy=0.05
                ),
                ProtocolPosition(
                    protocol="Aave V3",
                    asset="WBTC",
                    amount=0.15,
                    leverage=1.2,
                    apy=0.015,
                ),
                ProtocolPosition(
                    protocol="Uniswap V2", asset="ETH/USDC", amount=0.8, apy=0.08
                ),
            ]

    async def get_asset_price(self, asset: str) -> float:
        """获取资产的当前价格

        Args:
            asset: 资产符号（例如：'ETH', 'USDC', 'WBTC'等）

        Returns:
            float: 资产的当前美元价格
        """
        try:
            # 首先尝试从历史数据缓存中获取价格
            cached_data = self.historical_data_cache.get(asset)
            if cached_data is not None:
                return cached_data["price"].iloc[-1]

            # 如果缓存中没有，获取最新的历史数据
            historical_data = await self.get_asset_historical_data(asset)
            if not historical_data.empty:
                return historical_data["price"].iloc[-1]

            # 如果无法获取实时数据，使用预设的价格
            demo_prices = {
                "ETH": 3500.0,
                "WBTC": 60000.0,
                "USDC": 1.0,
                "DAI": 1.0,
                "USDT": 1.0,
                "LINK": 15.0,
                "UNI": 8.0,
                "AAVE": 150.0,
                "COMP": 200.0,
                "SNX": 3.0,
                "MKR": 1200.0,
                "YFI": 15000.0,
                "SUSHI": 2.0,
                "CRV": 1.5,
                "BAL": 6.0,
                "1INCH": 2.0,
            }

            if asset in demo_prices:
                logger.info(f"使用预设价格: {asset} = ${demo_prices[asset]}")
                return demo_prices[asset]

            # 如果是LP代币，尝试解析并返回基础资产的价格
            if "/" in asset:
                base_asset = asset.split("/")[0]
                if base_asset in demo_prices:
                    return demo_prices[base_asset]

            logger.warning(f"未找到{asset}的价格数据，返回默认价格1.0")
            return 1.0

        except Exception as e:
            logger.error(f"获取{asset}价格时出错: {e}")
            return 1.0  # 发生错误时返回默认价格

    def _load_contract_abis(self):
        """加载各协议合约的ABI"""
        # Aave V3 ABI
        self.aave_pool_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "user", "type": "address"}
                ],
                "name": "getUserAccountData",
                "outputs": [
                    {
                        "internalType": "uint256",
                        "name": "totalCollateralBase",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "totalDebtBase",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "availableBorrowsBase",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "currentLiquidationThreshold",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "ltv", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "healthFactor",
                        "type": "uint256",
                    },
                ],
                "stateMutability": "view",
                "type": "function",
            }
        ]

        self.aave_data_provider_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "asset", "type": "address"},
                    {"internalType": "address", "name": "user", "type": "address"},
                ],
                "name": "getUserReserveData",
                "outputs": [
                    {
                        "internalType": "uint256",
                        "name": "currentATokenBalance",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "currentStableDebt",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "currentVariableDebt",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "principalStableDebt",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "scaledVariableDebt",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "stableBorrowRate",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "liquidityRate",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint40",
                        "name": "stableRateLastUpdated",
                        "type": "uint40",
                    },
                    {
                        "internalType": "bool",
                        "name": "usageAsCollateralEnabled",
                        "type": "bool",
                    },
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "getAllReservesTokens",
                "outputs": [
                    {
                        "components": [
                            {
                                "internalType": "string",
                                "name": "symbol",
                                "type": "string",
                            },
                            {
                                "internalType": "address",
                                "name": "tokenAddress",
                                "type": "address",
                            },
                        ],
                        "internalType": "struct AaveProtocolDataProvider.TokenData[]",
                        "name": "",
                        "type": "tuple[]",
                    }
                ],
                "stateMutability": "view",
                "type": "function",
            },
        ]

        # Compound V3 ABI
        self.compound_comet_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "account", "type": "address"}
                ],
                "name": "userCollateral",
                "outputs": [
                    {"internalType": "uint256", "name": "balance", "type": "uint256"},
                    {"internalType": "uint256", "name": "principal", "type": "uint256"},
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "account", "type": "address"}
                ],
                "name": "userBasic",
                "outputs": [
                    {"internalType": "int104", "name": "principal", "type": "int104"},
                    {
                        "internalType": "uint64",
                        "name": "baseTrackingIndex",
                        "type": "uint64",
                    },
                    {
                        "internalType": "uint64",
                        "name": "baseTrackingAccrued",
                        "type": "uint64",
                    },
                    {"internalType": "uint16", "name": "assetsIn", "type": "uint16"},
                    {"internalType": "uint8", "name": "reserved", "type": "uint8"},
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "getSupplyRate",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
        ]

        # Curve ABI
        self.curve_registry_abi = [
            {
                "name": "get_pool_from_lp_token",
                "outputs": [{"type": "address", "name": ""}],
                "inputs": [{"type": "address", "name": "arg0"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "name": "get_lp_token",
                "outputs": [{"type": "address", "name": ""}],
                "inputs": [{"type": "address", "name": "arg0"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "name": "get_n_coins",
                "outputs": [{"type": "uint256[2]", "name": ""}],
                "inputs": [{"type": "address", "name": "_pool"}],
                "stateMutability": "view",
                "type": "function",
            },
        ]

        # Uniswap V2 ABI
        self.uniswap_factory_abi = [
            {
                "constant": True,
                "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "name": "allPairs",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "allPairsLength",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
        ]

        self.uniswap_pair_abi = [
            {
                "constant": True,
                "inputs": [
                    {"internalType": "address", "name": "owner", "type": "address"}
                ],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token0",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token1",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
                    {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
                    {
                        "internalType": "uint32",
                        "name": "_blockTimestampLast",
                        "type": "uint32",
                    },
                ],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
        ]

        # ERC20 ABI (用于获取代币信息和余额)
        self.erc20_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
        ]

    def _init_token_addresses(self):
        """初始化常用代币地址映射"""
        self.token_addresses = {
            "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # 以太坊原生代币特殊地址
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
            "COMP": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
            "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
            "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        }

        # Aave V3代币地址映射
        self.aave_v3_atokens = {}  # 将在运行时从数据提供者获取

        # Compound V3抵押品地址
        self.compound_v3_collaterals = {
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            "COMP": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
            "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
            "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        }

    async def _get_aave_v3_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在Aave V3的存款头寸"""
        positions = []

        try:
            # 获取Aave V3合约
            pool_address = self.protocol_contracts["Aave V3"]["pool"]
            data_provider_address = self.protocol_contracts["Aave V3"]["data_provider"]

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
                        protocol="Aave V3",
                        asset=token_symbol,
                        amount=amount,
                        leverage=leverage,
                        apy=apy,
                    )

                    positions.append(position)

            return positions

        except Exception as e:
            logger.error(f"获取Aave V3头寸时出错: {e}")
            return []

    async def _get_compound_v3_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在Compound V3的存款头寸"""
        positions = []

        try:
            # 获取Compound V3 Comet合约（USDC市场）
            comet_address = self.protocol_contracts["Compound V3"]["comet"]
            comet_contract = self.w3.eth.contract(
                address=comet_address, abi=self.compound_comet_abi
            )

            # 获取用户基本数据
            user_basic = comet_contract.functions.userBasic(address).call()
            principal = user_basic[0]

            # 获取供应利率
            supply_rate = comet_contract.functions.getSupplyRate().call()
            apy = supply_rate / (10**18) * 365 * 24 * 60 * 60  # 转换为年化利率

            # 如果用户有USDC存款（principal < 0表示存款）
            if principal < 0:
                # 转换为正数并调整精度
                usdc_amount = abs(principal) / (10**6)  # USDC有6位小数

                # 创建USDC头寸
                usdc_position = ProtocolPosition(
                    protocol="Compound V3",
                    asset="USDC",
                    amount=usdc_amount,
                    leverage=1.0,  # Compound V3 USDC市场不支持杠杆
                    apy=apy,
                )

                positions.append(usdc_position)

            # 检查用户的抵押品
            for symbol, collateral_address in self.compound_v3_collaterals.items():
                try:
                    # 获取用户抵押品数据
                    collateral_data = comet_contract.functions.userCollateral(
                        address, collateral_address
                    ).call()

                    collateral_balance = collateral_data[0]

                    if collateral_balance > 0:
                        # 获取代币精度
                        token_contract = self.w3.eth.contract(
                            address=collateral_address, abi=self.erc20_abi
                        )

                        try:
                            decimals = token_contract.functions.decimals().call()
                        except Exception:
                            decimals = 18  # 默认精度

                        # 计算实际金额
                        amount = collateral_balance / (10**decimals)

                        # 创建抵押品头寸
                        position = ProtocolPosition(
                            protocol="Compound V3",
                            asset=symbol,
                            amount=amount,
                            leverage=None,  # 抵押品没有杠杆
                            apy=0.0,  # 抵押品没有APY
                        )

                        positions.append(position)
                except Exception as e:
                    logger.error(f"获取Compound V3 {symbol}抵押品时出错: {e}")

            return positions

        except Exception as e:
            logger.error(f"获取Compound V3头寸时出错: {e}")
            return []

    async def _get_curve_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在Curve的存款头寸"""
        positions = []

        try:
            # 获取Curve注册表合约
            registry_address = self.protocol_contracts["Curve"]["registry"]
            registry_contract = self.w3.eth.contract(
                address=registry_address, abi=self.curve_registry_abi
            )

            # 常见的Curve池
            common_curve_pools = [
                # 3pool (DAI/USDC/USDT)
                "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
                # stETH/ETH
                "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022",
                # frxETH/ETH
                "0xa1F8A6807c402E4A15ef4EBa36528A3FED24E577",
                # WBTC/renBTC
                "0x93054188d876f558f4a66B2EF1d97d16eDf0895B",
            ]

            for pool_address in common_curve_pools:
                try:
                    # 获取LP代币地址
                    lp_token_address = registry_contract.functions.get_lp_token(
                        pool_address
                    ).call()

                    # 创建LP代币合约
                    lp_token_contract = self.w3.eth.contract(
                        address=lp_token_address, abi=self.erc20_abi
                    )

                    # 获取用户LP代币余额
                    balance = lp_token_contract.functions.balanceOf(address).call()

                    if balance > 0:
                        # 获取代币精度
                        try:
                            decimals = lp_token_contract.functions.decimals().call()
                        except Exception:
                            decimals = 18  # 默认精度

                        # 计算实际金额
                        amount = balance / (10**decimals)

                        # 获取代币符号
                        try:
                            symbol = lp_token_contract.functions.symbol().call()
                        except Exception:
                            # 如果无法获取符号，使用池地址的简短形式
                            symbol = f"Curve-{pool_address[:6]}...{pool_address[-4:]}"

                        # 创建头寸对象
                        position = ProtocolPosition(
                            protocol="Curve",
                            asset=symbol,
                            amount=amount,
                            leverage=None,  # Curve LP没有杠杆
                            apy=None,  # 需要从外部API获取APY
                        )

                        positions.append(position)
                except Exception as e:
                    logger.error(f"获取Curve池 {pool_address} 数据时出错: {e}")

            return positions

        except Exception as e:
            logger.error(f"获取Curve头寸时出错: {e}")
            return []

    async def _get_uniswap_v2_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在Uniswap V2的LP头寸"""
        positions = []

        try:
            # 获取Uniswap V2工厂合约
            factory_address = self.protocol_contracts["Uniswap V2"]["factory"]
            factory_contract = self.w3.eth.contract(
                address=factory_address, abi=self.uniswap_factory_abi
            )

            # 常见的Uniswap V2对
            common_pairs = [
                # ETH/USDC
                "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc",
                # ETH/WBTC
                "0xBb2b8038a1640196FbE3e38816F3e67Cba72D940",
                # ETH/DAI
                "0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11",
                # USDC/DAI
                "0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5",
            ]

            for pair_address in common_pairs:
                try:
                    # 创建对合约
                    pair_contract = self.w3.eth.contract(
                        address=pair_address, abi=self.uniswap_pair_abi
                    )

                    # 获取用户LP代币余额
                    balance = pair_contract.functions.balanceOf(address).call()

                    if balance > 0:
                        # 获取代币0和代币1
                        token0_address = pair_contract.functions.token0().call()
                        token1_address = pair_contract.functions.token1().call()

                        # 创建代币合约
                        token0_contract = self.w3.eth.contract(
                            address=token0_address, abi=self.erc20_abi
                        )
                        token1_contract = self.w3.eth.contract(
                            address=token1_address, abi=self.erc20_abi
                        )

                        # 获取代币符号
                        try:
                            token0_symbol = token0_contract.functions.symbol().call()
                            token1_symbol = token1_contract.functions.symbol().call()
                        except Exception:
                            # 如果无法获取符号，使用地址的简短形式
                            token0_symbol = (
                                f"{token0_address[:6]}...{token0_address[-4:]}"
                            )
                            token1_symbol = (
                                f"{token1_address[:6]}...{token1_address[-4:]}"
                            )

                        # 获取池中的储备量
                        reserves = pair_contract.functions.getReserves().call()
                        reserve0 = reserves[0]
                        reserve1 = reserves[1]

                        # 获取总供应量
                        total_supply = pair_contract.functions.totalSupply().call()

                        # 计算用户在池中的份额
                        share = balance / total_supply if total_supply > 0 else 0

                        # 计算用户的代币数量
                        token0_amount = share * reserve0
                        token1_amount = share * reserve1

                        # 获取代币精度
                        try:
                            token0_decimals = (
                                token0_contract.functions.decimals().call()
                            )
                            token1_decimals = (
                                token1_contract.functions.decimals().call()
                            )
                        except Exception:
                            token0_decimals = 18  # 默认精度
                            token1_decimals = 18  # 默认精度

                        # 调整精度
                        token0_amount = token0_amount / (10**token0_decimals)
                        token1_amount = token1_amount / (10**token1_decimals)

                        # 创建头寸对象
                        position = ProtocolPosition(
                            protocol="Uniswap V2",
                            asset=f"{token0_symbol}/{token1_symbol}",
                            amount=balance / (10**18),  # LP代币通常是18位小数
                            leverage=None,  # Uniswap LP没有杠杆
                            apy=None,  # 需要从外部API获取APY
                        )

                        positions.append(position)
                except Exception as e:
                    logger.error(f"获取Uniswap V2对 {pair_address} 数据时出错: {e}")

            return positions

        except Exception as e:
            logger.error(f"获取Uniswap V2头寸时出错: {e}")
            return []
