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

# 设置日志记录器
logger = logging.getLogger("defi_risk.blockchain")

# 设置代理
proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}


class HistoricalDataCache:
    def __init__(self, max_size: int = 100, expiration_minutes: int = 5):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.expiration_minutes = expiration_minutes

    def get(self, key: str) -> Optional[Tuple[pd.DataFrame, datetime]]:
        """获取缓存的数据和时间戳"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(minutes=self.expiration_minutes):
                return data
            else:
                del self.cache[key]
        return None

    def set(self, key: str, data: pd.DataFrame):
        """设置缓存数据"""
        if len(self.cache) >= self.max_size:
            # 移除最旧的项目
            self.cache.popitem(last=False)
        self.cache[key] = (data, datetime.now())


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
        self.demo_mode = True  # 演示模式
        self.historical_data_cache = HistoricalDataCache(
            max_size=100, expiration_minutes=5
        )

    async def get_all_positions(self, address: str) -> List[ProtocolPosition]:
        """获取用户在所有支持的DeFi协议中的存款头寸"""
        try:
            if address.lower() == DEMO_ADDRESS.lower() or self.demo_mode:
                logger.info(f"为演示地址返回预设头寸数据")
                return await self.get_demo_positions()
            return []
        except Exception as e:
            logger.error(f"获取所有存款头寸时出错: {e}")
            return await self.get_demo_positions()

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
        """获取资产的历史价格数据

        支持多种数据源，按优先级尝试：
        1. CoinGecko API
        2. CoinMarketCap API
        3. Binance API
        4. 链上数据（通过Chainlink价格预言机）
        5. 演示数据（如果所有API都失败）
        """
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

            # 1. 尝试CoinGecko API
            if asset in asset_ids["coingecko"]:
                try:
                    logger.info(f"尝试从CoinGecko获取{asset}数据")
                    df = self._get_coingecko_data(asset, asset_ids["coingecko"][asset])
                    if df is not None:
                        logger.info(f"成功从CoinGecko获取{asset}数据")
                        self.historical_data_cache.set(asset, df)
                        return df
                except Exception as e:
                    error_msg = f"从CoinGecko获取{asset}数据失败: {e}"
                    logger.warning(error_msg)
                    error_messages.append(error_msg)

            # 2. 尝试CoinMarketCap API
            if asset in asset_ids["coinmarketcap"]:
                try:
                    logger.info(f"尝试从CoinMarketCap获取{asset}数据")
                    df = self._get_coinmarketcap_data(
                        asset, asset_ids["coinmarketcap"][asset]
                    )
                    if df is not None:
                        logger.info(f"成功从CoinMarketCap获取{asset}数据")
                        self.historical_data_cache.set(asset, df)
                        return df
                except Exception as e:
                    error_msg = f"从CoinMarketCap获取{asset}数据失败: {e}"
                    logger.warning(error_msg)
                    error_messages.append(error_msg)

            # 3. 尝试Binance API
            if asset in asset_ids["binance"]:
                try:
                    logger.info(f"尝试从Binance获取{asset}数据")
                    df = self._get_binance_data(asset, asset_ids["binance"][asset])
                    if df is not None:
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
                if df is not None:
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

    def _get_coingecko_data(self, asset: str, asset_id: str) -> Optional[pd.DataFrame]:
        """从CoinGecko API获取历史数据"""
        url = f"https://pro-api.coingecko.com/api/v3/coins/{asset_id}/market_chart"
        headers = {
            "accept": "application/json",
            "x-cg-pro-api-key": "CG-2TiEpWzWzfnpD5hnRzk4ufDg",
        }
        params = {"vs_currency": "usd", "days": "30", "interval": "daily"}

        try:
            response = requests.get(
                url, params=params, headers=headers, proxies=proxies
            )
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(
                    {
                        "timestamp": [
                            datetime.fromtimestamp(p[0] / 1000) for p in data["prices"]
                        ],
                        "price": [p[1] for p in data["prices"]],
                        "volume": [v[1] for v in data["total_volumes"]],
                        "market_cap": [m[1] for m in data["market_caps"]],
                    }
                )
                df["source"] = "coingecko"
                return df
            else:
                logger.warning(f"CoinGecko API返回状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"从CoinGecko获取数据时出错: {e}")
            return None

    def _get_coinmarketcap_data(
        self, asset: str, asset_id: str
    ) -> Optional[pd.DataFrame]:
        """从CoinMarketCap API获取历史数据"""
        # 注意：CoinMarketCap API需要API密钥
        api_key = os.getenv("COINMARKETCAP_API_KEY")
        if not api_key:
            logger.warning("未设置COINMARKETCAP_API_KEY环境变量")
            return None

        url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical"
        params = {
            "id": asset_id,
            "time_start": (datetime.now() - timedelta(days=30)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "time_end": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "interval": "daily",
        }
        headers = {"X-CMC_PRO_API_KEY": api_key}

        try:
            response = requests.get(
                url, params=params, headers=headers, proxies=proxies
            )
            if response.status_code == 200:
                data = response.json()
                quotes = data["data"]["quotes"]

                df = pd.DataFrame(
                    {
                        "timestamp": [
                            datetime.fromisoformat(
                                q["timestamp"].replace("Z", "+00:00")
                            )
                            for q in quotes
                        ],
                        "price": [q["quote"]["USD"]["price"] for q in quotes],
                        "volume": [q["quote"]["USD"]["volume_24h"] for q in quotes],
                        "market_cap": [q["quote"]["USD"]["market_cap"] for q in quotes],
                    }
                )
                df["source"] = "coinmarketcap"
                return df
            else:
                logger.warning(f"CoinMarketCap API返回状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"从CoinMarketCap获取数据时出错: {e}")
            return None

    def _get_binance_data(
        self, asset: str, trading_pair: str
    ) -> Optional[pd.DataFrame]:
        """从Binance API获取历史数据"""
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": trading_pair, "interval": "1d", "limit": 30}

        try:
            response = requests.get(url, params=params, proxies=proxies)
            if response.status_code == 200:
                data = response.json()

                df = pd.DataFrame(
                    {
                        "timestamp": [
                            datetime.fromtimestamp(k[0] / 1000) for k in data
                        ],
                        "price": [float(k[4]) for k in data],  # 收盘价
                        "volume": [float(k[5]) for k in data],  # 交易量
                        "market_cap": [0.0] * len(data),  # Binance不提供市值数据
                    }
                )
                df["source"] = "binance"
                return df
            else:
                logger.warning(f"Binance API返回状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"从Binance获取数据时出错: {e}")
            return None

    async def _get_onchain_data(self, asset: str) -> Optional[pd.DataFrame]:
        """从链上获取历史数据（通过Chainlink价格预言机）"""
        if not self.w3.is_connected():
            logger.warning("Web3连接不可用，无法获取链上数据")
            return None

        # Chainlink价格预言机地址映射
        chainlink_feeds = {
            "ETH": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
            "WBTC": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
            "USDC": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
            "DAI": "0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9",
            "AAVE": "0x547a514d5e3769680Ce22B2361c10Ea13619e8a9",
            "COMP": "0xdbd020CAeF83eFd542f4De03e3cF0C28A4428bd5",
            "UNI": "0x553303d460EE0afB37EdFf9bE42922D8FF63220e",
            "LINK": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c",
        }

        if asset not in chainlink_feeds:
            logger.warning(f"没有{asset}的Chainlink价格预言机")
            return None

        # Chainlink价格预言机ABI（简化版）
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
            }
        ]

        # 由于链上数据通常只能获取当前价格，我们需要模拟历史数据
        # 在实际应用中，可以使用历史区块号查询历史价格，或使用事件日志
        contract = self.w3.eth.contract(address=chainlink_feeds[asset], abi=abi)

        try:
            # 获取当前价格
            round_data = contract.functions.latestRoundData().call()
            current_price = round_data[1] / 10**8  # 假设8位小数
            current_time = datetime.fromtimestamp(round_data[3])

            # 模拟30天的历史数据（在实际应用中应该查询历史区块）
            dates = pd.date_range(end=current_time, periods=30, freq="D")

            # 使用当前价格作为基准，添加一些随机波动
            np.random.seed(42 + hash(asset) % 100)
            volatility = DEMO_ASSETS.get(asset, {"volatility": 0.01})["volatility"]
            price_changes = np.random.normal(0, volatility / 2, size=30)

            # 确保最后一个价格是当前价格
            prices = current_price * (1 + np.cumsum(price_changes))
            price_factor = current_price / prices[-1]
            prices = prices * price_factor

            volumes = np.random.uniform(10000, 100000, size=30)

            df = pd.DataFrame(
                {
                    "timestamp": dates,
                    "price": prices,
                    "volume": volumes,
                    "market_cap": [0.0] * 30,  # 链上数据通常不提供市值
                }
            )
            df["source"] = "onchain"
            return df

        except Exception as e:
            logger.error(f"获取链上价格数据时出错: {e}")
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
        """为演示提供预设的用户头寸数据"""
        try:
            today = datetime.now().date()
            seed = int(f"{today.year}{today.month:02d}{today.day:02d}")
            random.seed(seed)

            positions = [
                ProtocolPosition(
                    protocol="Aave V3",
                    asset="ETH",
                    amount=random.uniform(2.0, 4.0),
                    leverage=random.uniform(1.5, 2.0),
                    apy=random.uniform(0.03, 0.05),
                ),
                ProtocolPosition(
                    protocol="Compound V3",
                    asset="USDC",
                    amount=random.uniform(8000, 12000),
                    leverage=1.0,
                    apy=random.uniform(0.04, 0.06),
                ),
                ProtocolPosition(
                    protocol="Curve",
                    asset="DAI",
                    amount=random.uniform(5000, 10000),
                    apy=random.uniform(0.06, 0.09),
                ),
                ProtocolPosition(
                    protocol="Uniswap V2",
                    asset="WBTC",
                    amount=random.uniform(0.2, 0.5),
                    apy=random.uniform(0.05, 0.08),
                ),
            ]

            random.seed()
            return positions

        except Exception as e:
            logger.error(f"生成演示头寸时出错: {e}")
            return [
                ProtocolPosition(
                    protocol="Aave V3", asset="ETH", amount=2.5, leverage=1.5, apy=0.04
                ),
                ProtocolPosition(
                    protocol="Compound V3",
                    asset="USDC",
                    amount=10000,
                    leverage=1.0,
                    apy=0.05,
                ),
                ProtocolPosition(protocol="Curve", asset="DAI", amount=7500, apy=0.07),
                ProtocolPosition(
                    protocol="Uniswap V2", asset="WBTC", amount=0.35, apy=0.06
                ),
            ]
