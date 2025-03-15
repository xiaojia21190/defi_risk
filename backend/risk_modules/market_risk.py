"""
市场风险分析模块 - 用于分析市场波动、趋势和相关性风险
"""

from typing import Dict, List, Optional
import logging
import pandas as pd
import hashlib
import json
from cachetools import LRUCache
import asyncio
import pandas_ta

logger = logging.getLogger("defi_risk.market_risk")


class MarketRiskAnalyzer:
    """市场风险分析器"""

    def __init__(self, ai_predictor=None, blockchain_service=None):
        """
        初始化市场风险分析器

        Args:
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service

        # 缓存
        self.market_data_cache = LRUCache(maxsize=500)  # LRU缓存
        self.market_analysis_cache = {}

        # 风险阈值配置
        self.high_volatility_threshold = 0.5  # 50% 的价格波动作为高波动性阈值

        # 性能指标收集
        self.performance_metrics = None

    def calculate_market_volatility_risk(
        self,
        asset: str,
        protocol: str,
        amount: float,
        historical_data: Optional[pd.DataFrame] = None,
    ) -> float:
        """
        计算市场波动风险
        返回0-1之间的风险值，0表示最低风险，1表示最高风险

        如果提供了历史数据，则使用AI预测器进行更准确的风险评估

        Args:
            asset: 资产符号
            protocol: 协议名称
            amount: 投资金额
            historical_data: 历史价格数据

        Returns:
            float: 0-1之间的风险值
        """
        cache_key = f"market_vol_{asset}_{protocol}"

        # 检查缓存
        cached_result = self.market_data_cache.get(cache_key)
        if cached_result:
            if self.performance_metrics:
                self.performance_metrics.record_cache_access(
                    "calculate_market_volatility_risk", True
                )
            return cached_result

        if self.performance_metrics:
            self.performance_metrics.record_cache_access(
                "calculate_market_volatility_risk", False
            )

        try:
            # 如果有历史数据，使用AI预测器进行分析
            if historical_data is not None and not historical_data.empty:
                # 检查缓存中是否已有分析结果
                if asset in self.market_analysis_cache:
                    market_analysis = self.market_analysis_cache[asset]
                else:
                    # 使用AI预测器分析市场趋势
                    market_analysis = self.ai_predictor.analyze_market_trend(
                        historical_data, asset
                    )
                    # 缓存分析结果
                    self.market_analysis_cache[asset] = market_analysis

                # 从AI分析结果中提取风险信息
                if market_analysis and "risk_level" in market_analysis:
                    risk_level = market_analysis["risk_level"]
                    # 将风险等级转换为数值
                    if risk_level == "HIGH":
                        return 0.8
                    elif risk_level == "MEDIUM":
                        return 0.5
                    elif risk_level == "LOW":
                        return 0.2

                # 如果有波动率数据，使用它来计算风险
                if market_analysis and "volatility" in market_analysis:
                    volatility = market_analysis["volatility"]
                    # 将波动率标准化为0-1之间的风险值
                    return min(volatility / 20, 1.0)  # 假设20%的波动率对应最高风险

            # 如果没有历史数据或AI分析失败，使用预设的映射表
            volatility_map = {
                "ETH": 0.4,
                "USDC": 0.01,
                "DAI": 0.02,
                "BTC": 0.5,
                "USDT": 0.01,
            }

            base_volatility = volatility_map.get(asset, 0.3)
            return min(base_volatility, 1.0)

        except Exception as e:
            logger.error(f"计算市场波动风险时出错: {e}")
            return 0.5

    async def get_asset_historical_data(self, asset: str) -> Optional[pd.DataFrame]:
        """
        获取资产的历史价格数据

        Args:
            asset: 资产符号

        Returns:
            Optional[pd.DataFrame]: 历史价格数据，如果获取失败则返回None
        """
        try:
            # 检查缓存
            cache_key = f"historical_data_{asset}"
            cached_data = self.market_data_cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 如果区块链服务可用，使用它获取历史数据
            if self.blockchain_service:
                # 获取最近30天的历史数据
                historical_data = await self.blockchain_service.get_asset_price_history(
                    asset, days=30
                )

                if historical_data is not None and not historical_data.empty:
                    # 计算技术指标
                    self._calculate_technical_indicators(historical_data)

                    # 缓存数据
                    self.market_data_cache[cache_key] = historical_data
                    return historical_data

            return None
        except Exception as e:
            logger.error(f"获取{asset}历史数据时出错: {e}")
            return None

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> None:
        """
        计算技术指标

        Args:
            df: 价格数据DataFrame
        """
        try:
            # 确保DataFrame包含必要的列
            if "close" not in df.columns:
                if "price" in df.columns:
                    df["close"] = df["price"]
                else:
                    logger.error("DataFrame缺少close或price列，无法计算技术指标")
                    return

            # 计算MACD
            macd = df.ta.macd(close="close", fast=12, slow=26, signal=9)
            if macd is not None:
                df = pd.concat([df, macd], axis=1)

            # 计算RSI
            rsi = df.ta.rsi(close="close", length=14)
            if rsi is not None:
                df["RSI_14"] = rsi

            # 计算布林带
            bbands = df.ta.bbands(close="close", length=20)
            if bbands is not None:
                df = pd.concat([df, bbands], axis=1)

        except Exception as e:
            logger.error(f"计算技术指标时出错: {e}")

    def analyze_market_trend(self, asset: str) -> Dict:
        """
        分析市场趋势

        Args:
            asset: 资产符号

        Returns:
            Dict: 市场趋势分析结果
        """
        try:
            # 检查缓存
            cache_key = f"market_trend_{asset}"
            cached_result = self.market_data_cache.get(cache_key)
            if cached_result:
                return cached_result

            # 获取历史数据
            historical_data = asyncio.run(self.get_asset_historical_data(asset))

            if historical_data is None or historical_data.empty:
                return {
                    "trend": "unknown",
                    "risk_level": "MEDIUM",
                    "volatility": 0.3,
                    "risk_factors": ["无法获取历史数据，使用默认风险评估"],
                    "trading_signals": [],
                }

            # 使用AI预测器分析市场趋势
            if self.ai_predictor:
                market_analysis = self.ai_predictor.analyze_market_trend(
                    historical_data, asset
                )

                # 缓存结果
                self.market_data_cache[cache_key] = market_analysis
                return market_analysis

            # 如果没有AI预测器，进行基本分析
            return self._basic_market_analysis(historical_data, asset)

        except Exception as e:
            logger.error(f"分析{asset}市场趋势时出错: {e}")
            return {
                "trend": "unknown",
                "risk_level": "MEDIUM",
                "volatility": 0.3,
                "risk_factors": ["市场趋势分析过程中出错"],
                "trading_signals": [],
            }

    def _basic_market_analysis(self, df: pd.DataFrame, asset: str) -> Dict:
        """
        基本市场分析

        Args:
            df: 价格数据DataFrame
            asset: 资产符号

        Returns:
            Dict: 市场分析结果
        """
        try:
            # 确保DataFrame包含必要的列
            if "close" not in df.columns:
                if "price" in df.columns:
                    df["close"] = df["price"]
                else:
                    return {
                        "trend": "unknown",
                        "risk_level": "MEDIUM",
                        "volatility": 0.3,
                        "risk_factors": ["数据格式不正确，无法进行分析"],
                        "trading_signals": [],
                    }

            # 计算技术指标（如果尚未计算）
            if "RSI_14" not in df.columns:
                self._calculate_technical_indicators(df)

            # 计算波动率
            if len(df) > 1:
                returns = df["close"].pct_change().dropna()
                volatility = returns.std() * (252**0.5)  # 年化波动率
            else:
                volatility = 0.3  # 默认波动率

            # 确定趋势
            if len(df) >= 20:
                short_ma = df["close"].rolling(window=5).mean().iloc[-1]
                long_ma = df["close"].rolling(window=20).mean().iloc[-1]

                if short_ma > long_ma:
                    trend = "bullish"
                elif short_ma < long_ma:
                    trend = "bearish"
                else:
                    trend = "neutral"
            else:
                trend = "unknown"

            # 确定风险等级
            if volatility > 0.5:
                risk_level = "HIGH"
            elif volatility > 0.2:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            # 生成风险因素
            risk_factors = []

            if volatility > 0.5:
                risk_factors.append(f"{asset}波动率较高，存在较大价格风险")

            if trend == "bearish":
                risk_factors.append(f"{asset}处于下跌趋势，可能面临进一步下跌风险")

            # 生成交易信号
            trading_signals = []

            if "RSI_14" in df.columns:
                last_rsi = df["RSI_14"].iloc[-1]
                if last_rsi > 70:
                    trading_signals.append(f"RSI超买({last_rsi:.2f})，可能面临回调")
                elif last_rsi < 30:
                    trading_signals.append(f"RSI超卖({last_rsi:.2f})，可能出现反弹")

            return {
                "trend": trend,
                "risk_level": risk_level,
                "volatility": volatility,
                "risk_factors": risk_factors,
                "trading_signals": trading_signals,
            }

        except Exception as e:
            logger.error(f"基本市场分析时出错: {e}")
            return {
                "trend": "unknown",
                "risk_level": "MEDIUM",
                "volatility": 0.3,
                "risk_factors": ["市场分析过程中出错"],
                "trading_signals": [],
            }

    def analyze_correlation_risk(self, assets: List[str]) -> Dict:
        """
        分析资产相关性风险

        Args:
            assets: 资产列表

        Returns:
            Dict: 相关性风险分析结果
        """
        try:
            if not assets or len(assets) < 2:
                return {
                    "correlation_risk": 0.1,
                    "risk_factors": ["资产数量不足，相关性风险较低"],
                    "correlation_matrix": {},
                }

            # 获取所有资产的历史数据
            historical_data = {}
            for asset in assets:
                data = asyncio.run(self.get_asset_historical_data(asset))
                if data is not None and not data.empty:
                    historical_data[asset] = data

            if not historical_data or len(historical_data) < 2:
                return {
                    "correlation_risk": 0.3,
                    "risk_factors": ["无法获取足够的历史数据进行相关性分析"],
                    "correlation_matrix": {},
                }

            # 使用AI预测器分析相关性
            if self.ai_predictor:
                return self.ai_predictor.analyze_assets_correlation(historical_data)

            # 如果没有AI预测器，进行基本相关性分析
            return self._basic_correlation_analysis(historical_data)

        except Exception as e:
            logger.error(f"分析资产相关性风险时出错: {e}")
            return {
                "correlation_risk": 0.5,
                "risk_factors": ["相关性分析过程中出错"],
                "correlation_matrix": {},
            }

    def _basic_correlation_analysis(
        self, historical_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        基本相关性分析

        Args:
            historical_data: 各资产的历史数据

        Returns:
            Dict: 相关性分析结果
        """
        try:
            # 提取每个资产的收盘价
            price_data = {}
            for asset, data in historical_data.items():
                if "close" in data.columns:
                    price_data[asset] = data["close"]
                elif "price" in data.columns:
                    price_data[asset] = data["price"]

            if not price_data or len(price_data) < 2:
                return {
                    "correlation_risk": 0.3,
                    "risk_factors": ["无法提取足够的价格数据进行相关性分析"],
                    "correlation_matrix": {},
                }

            # 创建价格DataFrame
            price_df = pd.DataFrame(price_data)

            # 计算相关性矩阵
            correlation_matrix = price_df.corr().to_dict()

            # 计算平均相关性
            correlations = []
            for asset1, corrs in correlation_matrix.items():
                for asset2, corr in corrs.items():
                    if asset1 != asset2:
                        correlations.append(abs(corr))

            avg_correlation = (
                sum(correlations) / len(correlations) if correlations else 0
            )

            # 确定相关性风险
            if avg_correlation > 0.7:
                correlation_risk = 0.8
                risk_factors = ["资产之间高度相关，缺乏多样化"]
            elif avg_correlation > 0.5:
                correlation_risk = 0.5
                risk_factors = ["资产之间中度相关，多样化程度一般"]
            else:
                correlation_risk = 0.2
                risk_factors = ["资产之间相关性较低，多样化程度良好"]

            # 识别高相关性对
            high_correlation_pairs = []
            for asset1, corrs in correlation_matrix.items():
                for asset2, corr in corrs.items():
                    if asset1 != asset2 and abs(corr) > 0.7:
                        high_correlation_pairs.append(
                            f"{asset1}-{asset2}相关性为{corr:.2f}"
                        )

            if high_correlation_pairs:
                risk_factors.extend(high_correlation_pairs[:3])  # 只添加前三个

            return {
                "correlation_risk": correlation_risk,
                "risk_factors": risk_factors,
                "correlation_matrix": correlation_matrix,
                "average_correlation": avg_correlation,
            }

        except Exception as e:
            logger.error(f"基本相关性分析时出错: {e}")
            return {
                "correlation_risk": 0.5,
                "risk_factors": ["相关性分析过程中出错"],
                "correlation_matrix": {},
            }
