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
import time

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
            cached_data = self.historical_data_cache.get(asset, "1d")
            if cached_data is not None:
                logger.info(f"从缓存获取 {asset} 的历史数据")
                return cached_data
            else:
                logger.info(f"缓存中未找到 {asset} 的历史数据")

            # 资产ID映射（不同API可能使用不同的ID）
            asset_ids = {
                # Binance交易对
                "binance": {
                    "ETH": "ETHUSDT",
                    "BTC": "BTCUSDT",  # 使用BTC作为BTC的代理
                    "USDC": "USDCUSDT",
                    "USDT": "BUSDUSDT",  # USDT/USDC交易对
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

            if asset not in asset_ids["binance"]:
                logger.warning(f"不支持的资产 {asset}，使用演示数据")
                return []

            # 尝试从不同的数据源获取数据
            df = None
            error_messages = []

            # 1. 尝试Binance API
            if asset in asset_ids["binance"]:
                try:
                    logger.info(f"尝试从Binance获取{asset}数据")
                    df = await self._get_binance_data(
                        asset, asset_ids["binance"][asset]
                    )
                    if df is not None and not df.empty:
                        logger.info(f"成功从Binance获取{asset}数据，设置到缓存")
                        self.historical_data_cache.set(asset, df, "1d")
                        return df
                    else:
                        logger.warning(f"从Binance获取的{asset}数据为空")
                except Exception as e:
                    error_msg = f"从Binance获取{asset}数据失败: {e}"
                    logger.warning(error_msg)
                    error_messages.append(error_msg)

            # 5. 所有数据源都失败，使用演示数据
            logger.error(
                f"所有数据源获取{asset}数据失败，使用演示数据。错误: {error_messages}"
            )
            return []

        except Exception as e:
            logger.error(f"获取{asset}历史数据时出错: {e}")
            return []

    # 获取24小时数据
    async def _get_24h_data(
        self,
        asset: str,
    ) -> Optional[Dict]:
        """从Binance API获取24小时行情数据"""
        # 手动实现缓存逻辑
        cache_key = f"24h_data_{asset}"
        if cache_key in cache:
            return cache[cache_key]

        url = "https://api.binance.com/api/v3/ticker/24hr"

        asset_ids = {
            # Binance交易对
            "binance": {
                "ETH": "ETHUSDT",
                "BTC": "BTCUSDT",  # 使用BTC作为BTC的代理
                "USDC": "USDCUSDT",
                "USDT": "BUSDUSDT",  # USDT/USDC交易对
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

        # 设置请求参数
        params = {
            "symbol": asset_ids["binance"].get(asset, f"{asset}USDT"),
        }

        try:
            response = requests.get(url, params=params, proxies=proxies)
            if response.status_code == 200:
                data = response.json()

                if not data:
                    logger.warning(f"Binance返回的{asset}数据为空")
                    return None

                # 将结果存入缓存
                cache[cache_key] = data

                # 返回数据
                return data
            else:
                logger.error(f"Binance API返回错误: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"从Binance获取{asset}数据失败: {e}")
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
                "ETH": await self.get_asset_price("ETH"),  # 假设当前ETH价格
                "USDC": await self.get_asset_price("USDC"),
                "USDT": await self.get_asset_price("USDT"),
                "BTC": await self.get_asset_price("BTC"),  # 假设当前BTC价格
                "LINK": await self.get_asset_price("LINK"),
                "UNI": await self.get_asset_price("UNI"),
            }

            # 更真实的APY范围（基于当前市场情况）
            apy_ranges = {
                "Aave-V3": {
                    "ETH": (0.01, 0.025),
                    "USDC": (0.03, 0.045),
                    "USDT": (0.025, 0.04),
                    "BTC": (0.01, 0.02),
                },
                "Compound-V3": {
                    "ETH": (0.015, 0.03),
                    "USDC": (0.035, 0.05),
                    "USDT": (0.03, 0.045),
                    "BTC": (0.012, 0.022),
                },
                "Curve Finance": {
                    "USDT": (0.04, 0.06),
                    "USDC": (0.04, 0.06),
                },
                "Uniswap-V3": {
                    "ETH": (0.05, 0.12),
                    "BTC": (0.04, 0.1),
                    "LINK": (0.06, 0.15),
                    "UNI": (0.07, 0.18),
                },
            }

            # 更真实的杠杆率限制
            max_leverage = {
                "Aave-V3": {"ETH": 2.5, "USDC": 1.1, "USDT": 1.1, "BTC": 2.0},
                "Compound-V3": {"ETH": 2.0, "USDC": 1.0, "USDT": 1.0, "BTC": 1.8},
            }

            # 设置总投资组合价值（美元）
            total_portfolio_value = random.uniform(30000, 50000)

            # 分配资产比例
            asset_allocation = {
                "ETH": random.uniform(0.3, 0.5),  # 30-50% ETH
                "USDC": random.uniform(0.2, 0.3),  # 20-30% USDC
                "USDT": random.uniform(0.1, 0.2),  # 10-20% USDT
                "BTC": random.uniform(0.1, 0.25),  # 10-25% BTC
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
                    protocol="Aave-V3",
                    asset="ETH",
                    amount=round(eth_aave_amount, 4),
                    leverage=random.uniform(1.0, max_leverage["Aave-V3"]["ETH"]),
                    apy=random.uniform(*apy_ranges["Aave-V3"]["ETH"]),
                )
            )

            # ETH在Uniswap
            eth_uni_amount = (
                total_portfolio_value * asset_allocation["ETH"] * 0.4
            ) / current_prices["ETH"]
            positions.append(
                ProtocolPosition(
                    protocol="Uniswap-V3",
                    asset="ETH/USDC",  # LP代币
                    amount=round(eth_uni_amount, 4),
                    apy=random.uniform(*apy_ranges["Uniswap-V3"]["ETH"]),
                )
            )

            # USDC在Compound
            usdc_amount = (
                total_portfolio_value * asset_allocation["USDC"]
            ) / current_prices["USDC"]
            positions.append(
                ProtocolPosition(
                    protocol="Compound-V3",
                    asset="USDC",
                    amount=round(usdc_amount, 2),
                    leverage=1.0,
                    apy=random.uniform(*apy_ranges["Compound-V3"]["USDC"]),
                )
            )

            # USDT在Curve Finance
            usdt_amount = (
                total_portfolio_value * asset_allocation["USDT"]
            ) / current_prices["USDT"]
            positions.append(
                ProtocolPosition(
                    protocol="Curve Finance",
                    asset="USDT/USDC",  # 稳定币池
                    amount=round(usdt_amount, 2),
                    apy=random.uniform(*apy_ranges["Curve Finance"]["USDT"]),
                )
            )

            # BTC在Aave
            wbtc_amount = (
                total_portfolio_value * asset_allocation["BTC"]
            ) / current_prices["BTC"]
            positions.append(
                ProtocolPosition(
                    protocol="Aave-V3",
                    asset="BTC",
                    amount=round(wbtc_amount, 6),
                    leverage=random.uniform(1.0, max_leverage["Aave-V3"]["BTC"]),
                    apy=random.uniform(*apy_ranges["Aave-V3"]["BTC"]),
                )
            )

            random.seed()  # 重置随机种子
            return positions

        except Exception as e:
            logger.error(f"生成演示头寸时出错: {e}")
            # 提供一个备用的固定数据集
            return [
                ProtocolPosition(
                    protocol="Aave-V3",
                    asset="ETH",
                    amount=1.2,
                    leverage=1.5,
                    apy=0.02,
                ),
                ProtocolPosition(
                    protocol="Compound-V3",
                    asset="USDC",
                    amount=12000,
                    leverage=1.0,
                    apy=0.04,
                ),
                ProtocolPosition(
                    protocol="Curve Finance", asset="USDT/USDC", amount=8000, apy=0.05
                ),
                ProtocolPosition(
                    protocol="Aave V3",
                    asset="BTC",
                    amount=0.15,
                    leverage=1.2,
                    apy=0.015,
                ),
                ProtocolPosition(
                    protocol="Uniswap-V2", asset="ETH/USDC", amount=0.8, apy=0.08
                ),
            ]

    async def get_asset_price(self, asset: str) -> float:
        """获取资产的当前价格

        Args:
            asset: 资产符号（例如：'ETH', 'USDC', 'BTC'等）

        Returns:
            float: 资产的当前美元价格
        """
        try:
            # 如果缓存中没有，获取最新的历史数据
            url = "https://api.binance.com/api/v3/ticker/price"
            if asset == "USDT":
                params = {"symbol": "BUSDUSDT"}
            else:
                params = {"symbol": f"{asset}USDT"}

            response = requests.get(url, params=params, proxies=proxies)
            if response.status_code == 200:
                data = response.json()

                if not data:
                    logger.warning(f"Binance返回的{asset}数据为空")
                    return None

                return float(data["price"])
            else:
                logger.error(f"Binance API返回错误: {response.status_code}")
                return None

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
            {
                "inputs": [],
                "name": "baseTokenPriceFeed",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "priceFeed", "type": "address"}
                ],
                "name": "getPrice",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
        ]

        # Curve Finance ABI
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

    async def _get_aave_v3_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在Aave V3的存款头寸"""
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
        """获取用户在Compound V3的存款和借款头寸"""
        positions = []

        try:
            # Compound V3 subgraph API地址
            compound_v3_subgraph_url = (
                "https://api.thegraph.com/subgraphs/name/messari/compound-v3-ethereum"
            )

            # 构建GraphQL查询，获取用户的所有头寸
            query = """
              # 获取用户账户信息
              account(id: $userAddress) {
                id
                positionCount
                openPositionCount

                # 获取用户的所有头寸
                positions(where: {account: $userAddress}) {
                  id
                  account {
                    id
                  }
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
                    borrowedToken {
                      id
                      name
                      symbol
                      decimals
                    }
                    inputTokenPriceUSD
                    outputTokenPriceUSD
                    exchangeRate
                    maximumLTV
                    liquidationThreshold
                    liquidationPenalty
                    # 获取市场利率
                    rates {
                      id
                      rate
                      side
                      type
                    }
                  }
                  asset {
                    id
                    name
                    symbol
                    decimals
                  }
                  side
                  balance
                  principal
                  isCollateral

                  # 获取头寸的快照，用于计算APY
                  snapshots(orderBy: timestamp, orderDirection: desc, first: 1) {
                    id
                    balance
                    balanceUSD
                    timestamp
                  }
                }
              }
            """

            # 发送GraphQL查询
            try:
                response = requests.post(
                    compound_v3_subgraph_url,
                    json={
                        "query": query,
                    },
                    proxies=self.proxies,
                )

                if response.status_code == 200:
                    data = response.json()

                    if (
                        "data" in data
                        and "account" in data["data"]
                        and data["data"]["account"]
                    ):
                        account_data = data["data"]["account"]
                        user_positions = account_data.get("positions", [])

                        logger.info(
                            f"从Compound V3 subgraph获取到 {len(user_positions)} 个头寸"
                        )

                        # 处理用户头寸
                        for position_data in user_positions:
                            try:
                                # 获取头寸信息
                                market = position_data["market"]
                                asset = position_data["asset"]
                                side = position_data["side"]
                                balance = float(position_data["balance"]) / (
                                    10 ** int(asset["decimals"])
                                )
                                is_collateral = position_data["isCollateral"]

                                # 获取市场信息
                                market_name = market.get("name", "Unknown Market")
                                input_token = market["inputToken"]
                                input_token_symbol = input_token["symbol"]
                                input_token_price_usd = float(
                                    market["inputTokenPriceUSD"]
                                )

                                # 获取利率信息
                                apy = 0.0
                                for rate in market["rates"]:
                                    # 根据头寸类型选择对应的利率
                                    if (
                                        side == "COLLATERAL"
                                        and rate["side"] == "LENDER"
                                    ):
                                        apy = float(rate["rate"])
                                    elif (
                                        side == "BORROWER"
                                        and rate["side"] == "BORROWER"
                                    ):
                                        apy = -float(rate["rate"])  # 借款利率为负

                                # 计算杠杆率（如果是借款头寸）
                                leverage = None
                                if side == "BORROWER":
                                    # 获取用户所有抵押品头寸
                                    collateral_positions = [
                                        p
                                        for p in user_positions
                                        if p["side"] == "COLLATERAL"
                                        and p["isCollateral"]
                                    ]

                                    # 计算总抵押品价值
                                    total_collateral_value = 0
                                    for collateral_position in collateral_positions:
                                        collateral_asset = collateral_position["asset"]
                                        collateral_market = collateral_position[
                                            "market"
                                        ]
                                        collateral_balance = float(
                                            collateral_position["balance"]
                                        ) / (10 ** int(collateral_asset["decimals"]))
                                        collateral_price_usd = float(
                                            collateral_market["inputTokenPriceUSD"]
                                        )
                                        collateral_value = (
                                            collateral_balance * collateral_price_usd
                                        )
                                        total_collateral_value += collateral_value

                                    # 计算借款价值
                                    borrow_value = balance * input_token_price_usd

                                    # 计算杠杆率
                                    if total_collateral_value > 0:
                                        leverage = borrow_value / total_collateral_value

                                # 创建头寸对象
                                position_type = ""
                                if side == "COLLATERAL":
                                    if is_collateral:
                                        position_type = "(抵押品)"
                                    else:
                                        position_type = "(存款)"
                                else:
                                    position_type = "(借款)"

                                position = ProtocolPosition(
                                    protocol="Compound V3",
                                    asset=f"{asset['symbol']}{position_type}",
                                    amount=balance,
                                    leverage=leverage,
                                    apy=apy,
                                )

                                positions.append(position)

                                # 记录日志
                                logger.info(
                                    f"发现Compound V3 {asset['symbol']}{position_type}: {balance:.6f} "
                                    f"(APY: {apy*100:.2f}%{', 杠杆率: ' + str(leverage) if leverage else ''})"
                                )

                            except Exception as e:
                                logger.error(f"处理Compound V3头寸数据时出错: {e}")
                    else:
                        logger.info(f"用户 {address} 在Compound V3没有头寸")
                        return []
                else:
                    logger.error(
                        f"Compound V3 subgraph API返回错误: {response.status_code} {response.text}"
                    )
                    return []

            except Exception as e:
                logger.error(f"查询Compound V3 subgraph时出错: {e}")
                return []

            return positions

        except Exception as e:
            logger.error(f"获取Compound V3头寸时出错: {e}")
            return []

    async def _get_curve_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在Curve的存款头寸"""
        positions = []

        try:
            # 从Curve API获取所有池子信息
            try:
                # 获取所有池子信息
                pools_response = requests.get(
                    "https://api.curve.fi/api/getPools/ethereum", proxies=self.proxies
                )

                curve_pools = []

                if pools_response.status_code == 200:
                    pools_data = pools_response.json()
                    if "data" in pools_data and "poolData" in pools_data["data"]:
                        curve_pools = pools_data["data"]["poolData"]
                        logger.info(f"从Curve API获取到 {len(curve_pools)} 个池子信息")
                    else:
                        logger.error("Curve API返回数据格式不正确")
                else:
                    logger.error(f"获取Curve池失败: {pools_response.status_code}")
                    curve_pools = []

                # 获取所有池子交易量和APY信息
                volumes_response = requests.get(
                    "https://api.curve.fi/api/getVolumes/ethereum", proxies=self.proxies
                )

                pools_apy_data = {}

                if volumes_response.status_code == 200:
                    volumes_data = volumes_response.json()
                    if "data" in volumes_data and "pools" in volumes_data["data"]:
                        for pool_apy in volumes_data["data"]["pools"]:
                            if "address" in pool_apy:
                                pools_apy_data[pool_apy["address"].lower()] = pool_apy
                        logger.info(
                            f"从Curve API获取到 {len(pools_apy_data)} 个池子APY信息"
                        )
                    else:
                        logger.error("Curve API返回APY数据格式不正确")
                else:
                    logger.error(f"获取Curve交易量失败: {volumes_response.status_code}")

                # 遍历所有Curve池
                for pool_info in curve_pools:
                    try:
                        pool_address = pool_info["address"]

                        # 获取LP代币地址
                        lp_token_address = pool_info.get("lpTokenAddress")

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
                            symbol = pool_info.get("symbol", "")
                            if not symbol:
                                try:
                                    symbol = lp_token_contract.functions.symbol().call()
                                except Exception:
                                    # 如果无法获取符号，使用池名称
                                    symbol = f"Curve-{pool_info.get('name', 'Unknown')}"

                            # 获取池子USD总价值
                            usd_total = pool_info.get("usdTotal", 0)

                            # 获取池子总供应量
                            total_supply_str = pool_info.get("totalSupply", "0")
                            try:
                                total_supply = int(total_supply_str) / (10**decimals)
                            except (ValueError, TypeError):
                                total_supply = 0

                            # 计算用户份额价值（USD）
                            user_value_usd = 0
                            if total_supply > 0:
                                user_share = amount / total_supply
                                user_value_usd = user_share * usd_total

                            # 获取APY信息
                            apy = 0.0
                            pool_apy_info = pools_apy_data.get(pool_address.lower())

                            if pool_apy_info:
                                # 交易费APY
                                trading_apy = (
                                    pool_apy_info.get("latestDailyApyPcent", 0) / 100
                                )

                                # CRV奖励APY
                                crv_apy = 0.0
                                if (
                                    "gaugeCrvApy" in pool_info
                                    and pool_info["gaugeCrvApy"]
                                ):
                                    if (
                                        isinstance(pool_info["gaugeCrvApy"], list)
                                        and len(pool_info["gaugeCrvApy"]) > 0
                                    ):
                                        crv_apy = pool_info["gaugeCrvApy"][0]

                                # 总APY
                                apy = trading_apy + crv_apy

                            # 创建头寸对象
                            position = ProtocolPosition(
                                protocol="Curve Finance",
                                asset=symbol,
                                amount=amount,
                                leverage=None,  # Curve Finance LP没有杠杆
                                apy=apy,
                            )

                            positions.append(position)
                            logger.info(
                                f"发现Curve {pool_info.get('name', 'Unknown')} 存款: "
                                f"{amount:.6f} {symbol} (APY: {apy*100:.2f}%, "
                                f"价值: ${user_value_usd:.2f})"
                            )
                    except Exception as e:
                        pool_name = pool_info.get("name", "Unknown")
                        logger.error(f"获取Curve池 {pool_name} 数据时出错: {e}")

                return positions

            except Exception as e:
                logger.error(f"从Curve API获取数据时出错: {e}")
                return []

        except Exception as e:
            logger.error(f"获取Curve Finance头寸时出错: {e}")
            return []

    async def _get_uniswap_v3_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在Uniswap V3的LP头寸"""
        positions = []

        try:
            # 使用TheGraph查询Uniswap V3头寸数据
            uniswap_v3_graph_url = "https://gateway.thegraph.com/api/95d759c3b12e4dd174e4f7e2adfa4882/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"

            # 使用用户提供的GraphQL查询结构
            query = (
                """
            {
              positions(
                where: { owner: "%s" }
                orderBy: liquidity
                orderDirection: desc
                first: 100
              ) {
                id
                liquidity
                tickLower { tickIdx }
                tickUpper { tickIdx }
                pool {
                  id
                  token0 {
                    symbol
                    id
                    decimals
                  }
                  token1 {
                    symbol
                    id
                    decimals
                  }
                  feeTier
                  liquidity
                  sqrtPrice
                  tick
                  createdAtTimestamp
                }
                depositedToken0
                depositedToken1
                withdrawnToken0
                withdrawnToken1
                collectedFeesToken0
                collectedFeesToken1
              }
            }
            """
                % address.lower()
            )

            try:
                response = requests.post(
                    uniswap_v3_graph_url, json={"query": query}, proxies=self.proxies
                )

                if response.status_code == 200:
                    data = response.json()

                    if "data" in data and "positions" in data["data"]:
                        v3_positions = data["data"]["positions"]
                        logger.info(
                            f"从TheGraph获取到 {len(v3_positions)} 个Uniswap V3头寸"
                        )

                        for position_data in v3_positions:
                            try:
                                # 跳过流动性为0的头寸
                                if int(position_data["liquidity"]) == 0:
                                    continue

                                pool = position_data["pool"]
                                token0 = pool["token0"]
                                token1 = pool["token1"]

                                token0_symbol = token0["symbol"]
                                token1_symbol = token1["symbol"]
                                token0_decimals = int(token0["decimals"])
                                token1_decimals = int(token1["decimals"])

                                # 计算当前头寸中的代币数量
                                # 存入的代币
                                deposited_token0 = float(
                                    position_data["depositedToken0"]
                                ) / (10**token0_decimals)
                                deposited_token1 = float(
                                    position_data["depositedToken1"]
                                ) / (10**token1_decimals)

                                # 提取的代币
                                withdrawn_token0 = float(
                                    position_data["withdrawnToken0"]
                                ) / (10**token0_decimals)
                                withdrawn_token1 = float(
                                    position_data["withdrawnToken1"]
                                ) / (10**token1_decimals)

                                # 收集的手续费
                                fees_token0 = float(
                                    position_data["collectedFeesToken0"]
                                ) / (10**token0_decimals)
                                fees_token1 = float(
                                    position_data["collectedFeesToken1"]
                                ) / (10**token1_decimals)

                                # 计算净头寸
                                net_token0 = (
                                    deposited_token0 - withdrawn_token0 + fees_token0
                                )
                                net_token1 = (
                                    deposited_token1 - withdrawn_token1 + fees_token1
                                )

                                # 获取当前价格
                                current_tick = int(pool["tick"])
                                tick_lower = int(position_data["tickLower"]["tickIdx"])
                                tick_upper = int(position_data["tickUpper"]["tickIdx"])

                                # 计算价格范围
                                lower_price = 1.0001**tick_lower
                                upper_price = 1.0001**tick_upper
                                current_price = 1.0001**current_tick

                                # 计算费率
                                fee_tier = (
                                    int(pool["feeTier"]) / 1000000
                                )  # 转换为百分比

                                # 尝试估算APY
                                apy = None
                                try:
                                    # 获取池创建时间
                                    created_timestamp = int(pool["createdAtTimestamp"])
                                    current_timestamp = int(time.time())
                                    pool_age_days = (
                                        current_timestamp - created_timestamp
                                    ) / 86400

                                    if pool_age_days > 0:
                                        # 估算每日费用收入
                                        daily_fees_token0 = fees_token0 / pool_age_days
                                        daily_fees_token1 = fees_token1 / pool_age_days

                                        # 获取代币价格
                                        token0_price = await self.get_asset_price(
                                            token0_symbol
                                        )
                                        token1_price = await self.get_asset_price(
                                            token1_symbol
                                        )

                                        # 计算每日费用的USD价值
                                        daily_fees_usd = (
                                            daily_fees_token0 * token0_price
                                        ) + (daily_fees_token1 * token1_price)

                                        # 计算头寸的USD价值
                                        position_value_usd = (
                                            net_token0 * token0_price
                                        ) + (net_token1 * token1_price)

                                        if position_value_usd > 0:
                                            # 年化收益率
                                            apy = (
                                                daily_fees_usd * 365
                                            ) / position_value_usd
                                except Exception as e:
                                    logger.error(f"计算Uniswap V3头寸APY时出错: {e}")

                                # 创建头寸对象
                                position = ProtocolPosition(
                                    protocol="Uniswap V3",
                                    asset=f"{token0_symbol}/{token1_symbol} ({fee_tier*100}%)",
                                    amount=1.0,  # V3头寸是NFT，数量始终为1
                                    leverage=None,  # Uniswap没有杠杆
                                    apy=apy,
                                )

                                position = ProtocolPosition(
                                    protocol="Uniswap V3",
                                    asset=f"{token0_symbol}/{token1_symbol} ({fee_tier*100}%)",
                                    amount=1.0,  # V3头寸是NFT，数量始终为1
                                    leverage=None,  # Uniswap没有杠杆
                                    apy=apy,
                                )

                                positions.append(position)

                                # 记录详细信息
                                logger.info(
                                    f"发现Uniswap V3 {token0_symbol}/{token1_symbol} 头寸: "
                                    f"ID {position_data['id']} "
                                    f"价格范围: {lower_price:.6f} - {upper_price:.6f} "
                                    f"({net_token0:.6f} {token0_symbol}, {net_token1:.6f} {token1_symbol})"
                                )
                                if apy:
                                    logger.info(f"  估计APY: {apy*100:.2f}%")

                            except Exception as e:
                                logger.error(
                                    f"处理Uniswap V3头寸 {position_data.get('id', 'Unknown')} 时出错: {e}"
                                )
                else:
                    logger.error(
                        f"从TheGraph获取Uniswap V3数据失败: {response.status_code} {response.text}"
                    )

            except Exception as e:
                logger.error(f"从TheGraph获取Uniswap V3头寸数据时出错: {e}")

            return positions

        except Exception as e:
            logger.error(f"获取Uniswap V3头寸时出错: {e}")
            return []

    async def get_gas_price(self) -> float:
        """获取当前gas价格（单位：Gwei）

        Returns:
            float: 当前gas价格，单位为Gwei
        """
        try:
            gas_price = self.historical_data_cache.get("gas_price", "1m")
            if gas_price is not None:
                return gas_price
            try:
                # 尝试从ETH API获取ETH gas价格
                url = "https://api.etherscan.io/v2/api?chainid=1&module=gastracker&action=gasoracle"
                """
                {
                    "status": "1",
                    "message": "OK-Missing/Invalid API Key, rate limit of 1/5sec applied",
                    "result": {
                        "LastBlock": "22027483",
                        "SafeGasPrice": "0.638579654",
                        "ProposeGasPrice": "0.639519654",
                        "FastGasPrice": "0.703471619",
                        "suggestBaseFee": "0.638579654",
                        "gasUsedRatio": "0.798531,0.483220166666667,0.492903416666667,0.982302996161946,0.451882105996492"
                    }
                }
                """

                response = requests.get(url, proxies=proxies)
                if response.status_code == 200:
                    data = response.json()
                    gas_price = float(data["result"]["suggestBaseFee"])
                    self.historical_data_cache.set("gas_price", gas_price, "1m")
                    logger.info(f"从ETH API估算gas价格: {gas_price:.2f} Gwei")
                    return gas_price
                else:
                    logger.error(f"ETH API返回错误: {response.status_code}")
            except Exception as e:
                logger.error(f"从ETH API获取gas价格失败: {e}")

            # 如果都失败了，返回一个合理的默认值
            default_gas_price = 0.5  # 0.5 Gwei
            logger.warning(f"无法获取实时gas价格，使用默认值: {default_gas_price} Gwei")
            return default_gas_price

        except Exception as e:
            logger.error(f"获取gas价格时出错: {e}")
            return 30.0  # 返回默认值
