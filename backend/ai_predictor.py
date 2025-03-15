import httpx
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime, timedelta
import os
from openai import OpenAI
import logging
import json
from functools import lru_cache
from cachetools import TTLCache
from dfllama import DefiLlamaClient, Coin


# 设置日志记录器
logger = logging.getLogger("defi_risk.ai_predictor")

# 设置代理
proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

# 在模块级别初始化缓存
analysis_cache = TTLCache(maxsize=100, ttl=900)  # 15分钟过期时间

# 在模块级别初始化 DeFiLlama 客户端
llama = DefiLlamaClient()

# 在模块级别初始化OpenAI客户端
try:
    # 创建带有代理的HTTP客户端
    try:
        client_http = httpx.Client(proxy="http://127.0.0.1:7890")
    except TypeError:
        client_http = httpx.Client()
        logger.warning("您的httpx版本不支持proxies参数，将使用默认连接")

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_URL"),
        http_client=client_http,
    )
    logger.info("成功初始化OpenAI客户端")
except Exception as e:
    logger.error(f"初始化OpenAI客户端时出错: {e}")
    client = None


class AiPredictor:
    def __init__(self):
        self.client = client

    def _prepare_market_data(
        self, historical_data: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, float, float, float, float]:
        """准备市场数据，返回可哈希的数据类型"""
        prices = historical_data["price"].values
        volumes = historical_data["volume"].values
        current_price = prices[-1]
        price_change_24h = (prices[-1] / prices[-2] - 1) * 100 if len(prices) > 1 else 0
        volatility = np.std(np.diff(prices) / prices[:-1]) * 100
        rsi = self.calculate_rsi(prices)
        return prices, volumes, current_price, price_change_24h, volatility, rsi

    def analyze_market_trend(self, historical_data: pd.DataFrame, asset: str) -> Dict:
        """分析市场趋势并预测价格走势"""
        try:
            # 首先检查缓存
            cached_result = analysis_cache.get(asset)
            if cached_result:
                logger.info(f"使用缓存的{asset}分析结果")
                return cached_result

            # 准备市场数据
            prices, volumes, current_price, price_change_24h, volatility, rsi = (
                self._prepare_market_data(historical_data)
            )

            # 计算技术指标
            ma7 = np.mean(prices[-7:]) if len(prices) >= 7 else current_price
            ma30 = np.mean(prices) if len(prices) >= 30 else current_price
            ma50 = np.mean(prices[-50:]) if len(prices) >= 50 else current_price
            ma200 = np.mean(prices[-200:]) if len(prices) >= 200 else current_price

            # 计算指数移动平均线
            ema12 = self._calculate_ema(prices, 12) if len(prices) >= 12 else prices
            ema26 = self._calculate_ema(prices, 26) if len(prices) >= 26 else prices

            # MACD指标
            macd, signal, histogram = self.calculate_macd(prices)
            macd_trend = "上升" if macd[-1] > signal[-1] else "下降"
            macd_strength = (
                "强" if abs(macd[-1] - signal[-1]) > 0.02 * current_price else "弱"
            )

            # 布林带指标
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(prices)
            bb_width = (bb_upper[-1] - bb_lower[-1]) / bb_middle[-1]  # 布林带宽度
            bb_position = (
                "上轨"
                if current_price >= bb_upper[-1]
                else ("下轨" if current_price <= bb_lower[-1] else "中轨")
            )

            # 成交量分析
            volume_trend = "上升" if volumes[-1] > np.mean(volumes[-7:]) else "下降"
            volume_strength = (
                "强"
                if volumes[-1] > np.mean(volumes) * 1.5
                else ("弱" if volumes[-1] < np.mean(volumes) * 0.5 else "中等")
            )

            # 趋势强度分析
            price_trend = "上升" if ma7 > ma30 else "下降"
            trend_strength = "强" if abs(ma7 / ma30 - 1) > 0.05 else "弱"

            # 支撑位和阻力位计算
            support_levels = self._calculate_support_levels(prices, current_price)
            resistance_levels = self._calculate_resistance_levels(prices, current_price)

            # 风险评估
            risk_factors = []
            if volatility > 5:
                risk_factors.append(f"高波动率 ({volatility:.2f}%)")
            if rsi > 70:
                risk_factors.append(f"RSI超买 ({rsi:.2f})")
            elif rsi < 30:
                risk_factors.append(f"RSI超卖 ({rsi:.2f})")
            if bb_width > 0.1:
                risk_factors.append("布林带宽度异常")
            if current_price > bb_upper[-1]:
                risk_factors.append("价格突破布林带上轨")
            if current_price < bb_lower[-1]:
                risk_factors.append("价格跌破布林带下轨")

            # 风险等级评估
            risk_level = "MEDIUM"
            if volatility > 8 or rsi > 75 or rsi < 25 or bb_width > 0.15:
                risk_level = "HIGH"
            elif volatility < 3 and 40 < rsi < 60 and bb_width < 0.05:
                risk_level = "LOW"

            # 获取缓存的分析结果
            analysis = self._get_cached_analysis(
                asset,
                current_price,
                price_change_24h,
                volatility,
                rsi,
                ma7,
                ma30,
                macd_trend,
                bb_position,
                volume_trend,
                volume_strength,
            )

            # 添加技术指标数据
            analysis.update(
                {
                    "asset": asset,
                    "current_price": current_price,
                    "price_change_24h": price_change_24h,
                    "volatility": volatility,
                    "rsi": rsi,
                    "risk_level": risk_level,
                    "risk_factors": risk_factors,
                    "technical_indicators": {
                        "ma7": ma7,
                        "ma30": ma30,
                        "ma50": ma50,
                        "ma200": ma200,
                        "ema12": ema12[-1] if len(ema12) > 0 else current_price,
                        "ema26": ema26[-1] if len(ema26) > 0 else current_price,
                        "macd": macd[-1],
                        "macd_signal": signal[-1],
                        "macd_histogram": histogram[-1] if len(histogram) > 0 else 0,
                        "macd_trend": macd_trend,
                        "macd_strength": macd_strength,
                        "bollinger_bands": {
                            "upper": bb_upper[-1],
                            "middle": bb_middle[-1],
                            "lower": bb_lower[-1],
                            "width": bb_width,
                            "position": bb_position,
                        },
                        "volume": {
                            "current": volumes[-1] if len(volumes) > 0 else 0,
                            "avg_7d": np.mean(volumes[-7:]) if len(volumes) >= 7 else 0,
                            "trend": volume_trend,
                            "strength": volume_strength,
                        },
                    },
                    "support_levels": support_levels,
                    "resistance_levels": resistance_levels,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 缓存结果
            analysis_cache[asset] = analysis
            logger.info(f"成功获取 {asset} 的AI市场分析")
            return analysis

        except Exception as e:
            logger.error(f"分析市场趋势时出错: {e}")
            return self._get_basic_analysis(
                asset, current_price, price_change_24h, volatility, rsi
            )

    def calculate_macd(
        self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple:
        """计算MACD指标"""
        try:
            # 将numpy数组转换为pandas Series
            price_series = pd.Series(prices)

            # 计算快线和慢线的指数移动平均
            exp1 = price_series.ewm(span=fast, adjust=False).mean()
            exp2 = price_series.ewm(span=slow, adjust=False).mean()

            # 计算MACD线
            macd = exp1 - exp2

            # 计算信号线
            signal_line = macd.ewm(span=signal, adjust=False).mean()

            # 计算MACD柱状图
            histogram = macd - signal_line

            return macd.values, signal_line.values, histogram.values
        except Exception as e:
            logger.error(f"计算MACD时出错: {e}")
            return np.zeros(len(prices)), np.zeros(len(prices)), np.zeros(len(prices))

    def calculate_bollinger_bands(
        self, prices: np.ndarray, window: int = 20, num_std: float = 2
    ) -> tuple:
        """计算布林带指标"""
        try:
            if len(prices) < window:
                return prices, prices, prices

            # 计算移动平均线
            middle_band = pd.Series(prices).rolling(window=window).mean()

            # 计算标准差
            std = pd.Series(prices).rolling(window=window).std()

            # 计算上下轨
            upper_band = middle_band + (std * num_std)
            lower_band = middle_band - (std * num_std)

            return upper_band.values, middle_band.values, lower_band.values
        except Exception as e:
            logger.error(f"计算布林带时出错: {e}")
            return prices, prices, prices

    def _get_cached_analysis(
        self,
        asset: str,
        current_price: float,
        price_change_24h: float,
        volatility: float,
        rsi: float,
        ma7: float,
        ma30: float,
        macd_trend: str,
        bb_position: str,
        volume_trend: str,
        volume_strength: str,
    ) -> Dict:
        """缓存分析结果的核心逻辑"""
        try:
            # 构建市场分析提示
            prompt = f"""
分析以下{asset}资产的市场数据，并提供详细的趋势分析和预测：

基本指标：
- 当前价格: ${current_price:.2f}
- 24小时价格变化: {price_change_24h:.2f}%
- 波动率: {volatility:.2f}%
- RSI指标: {rsi:.2f}（超买>70，超卖<30）

技术指标：
- 7日均价: ${ma7:.2f}
- 30日均价: ${ma30:.2f}
- MACD趋势: {macd_trend}
- 布林带位置: {bb_position}

成交量分析：
- 成交量趋势: {volume_trend}
- 成交量强度: {volume_strength}

请提供以下JSON格式的分析结果：
{{
    "trend": "bullish/bearish/neutral",
    "trend_strength": "strong/moderate/weak",
    "risk_level": "HIGH/MEDIUM/LOW",
    "predicted_price_range": {{
        "24h": [最低预期价格, 最高预期价格],
        "7d": [最低预期价格, 最高预期价格]
    }},
    "technical_analysis": {{
        "ma_trend": "上升/下降/盘整",
        "macd_signal": "买入/卖出/观望",
        "bollinger_signal": "超买/超卖/中性",
        "volume_analysis": "放量/缩量/平稳"
    }},
    "risk_factors": [
        "主要风险因素1",
        "主要风险因素2",
        ...
    ],
    "trading_signals": [
        "交易信号1",
        "交易信号2",
        ...
    ],
    "key_levels": {{
        "support": [主要支撑位1, 主要支撑位2],
        "resistance": [主要阻力位1, 主要阻力位2],
        "stop_loss": 建议止损价格,
        "take_profit": [目标获利价格1, 目标获利价格2]
    }},
    "analysis_summary": "详细的市场分析总结",
    "recommendations": [
        "具体建议1",
        "具体建议2",
        ...
    ]
}}

注意：
1. 基于所有技术指标提供综合分析
2. 考虑价格、成交量和技术指标的配合
3. 给出明确的交易建议和风险控制措施
4. 分析要客观且有数据支持
5. 建议要具体且可操作
"""
            if self.client is not None:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个专业的DeFi风险分析师，擅长评估协议安全性、流动性和去中心化程度。请基于详细的数据指标和深度分析结果，提供全面的风险评估。重点关注技术指标和多维度风险因素。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                return json.loads(response.choices[0].message.content)
            return self._get_basic_analysis(
                asset, current_price, price_change_24h, volatility, rsi
            )
        except Exception as e:
            logger.error(f"获取缓存分析时出错: {e}")
            return self._get_basic_analysis(
                asset, current_price, price_change_24h, volatility, rsi
            )

    def _get_basic_analysis(
        self,
        asset: str,
        current_price: float,
        price_change_24h: float,
        volatility: float,
        rsi: float,
    ) -> Dict:
        """生成基本的市场分析结果"""
        trend = "neutral"
        risk_level = "MEDIUM"

        if price_change_24h > 5:
            trend = "bullish"
        elif price_change_24h < -5:
            trend = "bearish"

        if volatility > 5:
            risk_level = "HIGH"
        elif volatility < 2:
            risk_level = "LOW"

        return {
            "asset": asset,
            "current_price": current_price,
            "trend": trend,
            "trend_strength": "moderate",
            "risk_level": risk_level,
            "predicted_price_range": {
                "24h": [current_price * 0.95, current_price * 1.05],
                "7d": [current_price * 0.9, current_price * 1.1],
            },
            "technical_analysis": {
                "ma_trend": "盘整",
                "macd_signal": "观望",
                "bollinger_signal": "中性",
                "volume_analysis": "平稳",
            },
            "risk_factors": [
                f"市场波动率: {volatility:.2f}%",
                f"RSI指标: {rsi:.2f}",
                f"24小时价格变化: {price_change_24h:.2f}%",
            ],
            "trading_signals": ["建议观察市场动向", "保持适度仓位"],
            "key_levels": {
                "support": [current_price * 0.95, current_price * 0.9],
                "resistance": [current_price * 1.05, current_price * 1.1],
                "stop_loss": current_price * 0.93,
                "take_profit": [current_price * 1.07, current_price * 1.15],
            },
            "analysis_summary": f"{asset}市场波动率{volatility:.2f}%，建议谨慎操作",
            "recommendations": ["关注市场变化", "设置止损位置", "控制仓位风险"],
            "timestamp": datetime.now().isoformat(),
        }

    def calculate_volatility(self, prices: List[float]) -> float:
        """计算价格波动率"""
        try:
            if len(prices) < 2:
                return 0
            returns = np.diff(prices) / prices[:-1]
            return np.std(returns)
        except Exception as e:
            logger.error(f"计算波动率时出错: {e}")
            return 0.2  # 返回默认中等波动率

    def calculate_rsi(self, prices: List[float], periods: int = 14) -> float:
        """计算相对强弱指数 (RSI)"""
        try:
            if len(prices) <= periods:
                return 50

            # 计算价格变化
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            # 计算平均上涨和下跌
            avg_gain = np.mean(gains[:periods])
            avg_loss = np.mean(losses[:periods])

            if avg_loss == 0:
                return 100

            # 计算RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            return rsi
        except Exception as e:
            logger.error(f"计算RSI时出错: {e}")
            return 50  # 返回默认中性RSI

    def analyze_defi_protocol_risk(self, protocol_name: str) -> Dict:
        """分析DeFi协议风险"""
        try:
            # 获取DefiLlama数据
            defillama_data = self._fetch_defillama_data(protocol_name)
            if not defillama_data:
                logger.warning(f"无法获取{protocol_name}的DefiLlama数据，使用默认数据")
                return self._get_basic_protocol_risk_analysis(protocol_name)

            # 构建AI分析提示
            # 将复杂的嵌套表达式拆分为多个部分
            basic_data_section = f"""
协议名称：{protocol_name}

基础数据：
- 当前TVL：${defillama_data['basic_data']['current_tvl']:,.2f}
- 24小时TVL变化：{defillama_data['basic_data']['tvl_change_24h']:.2f}%
- 市值/TVL比率：{defillama_data['basic_data']['mcap_tvl_ratio']:.2f}
- 支持链数量：{defillama_data['basic_data']['chain_count']}
- 审计次数：{defillama_data['basic_data']['audit_count']}"""

            tvl_analysis_section = f"""
TVL分析：
- 7日增长率：{defillama_data['risk_metrics']['tvl_metrics']['tvl_growth_7d']:.2f}%
- TVL波动率：{defillama_data['risk_metrics']['tvl_metrics']['tvl_volatility']:.4f}
- 趋势方向：{defillama_data['risk_metrics']['tvl_metrics']['trend']}
- TVL均值：${defillama_data['tvl_analysis']['summary_stats']['mean']:,.2f}
- TVL标准差：${defillama_data['tvl_analysis']['summary_stats']['std']:,.2f}"""

            technical_indicators_section = f"""
技术指标：
- MACD趋势：{defillama_data['tvl_analysis']['trend_analysis']['trend']}
- 趋势强度：{defillama_data['tvl_analysis']['trend_analysis']['strength']}
- RSI指标：{defillama_data['tvl_analysis']['trend_analysis']['rsi']:.2f}"""

            chain_distribution_section = f"""
链分布分析：
- 最高链集中度：{defillama_data['risk_metrics']['chain_metrics']['max_chain_concentration']:.2f}%
- 高风险链数量：{defillama_data['risk_metrics']['chain_metrics']['high_risk_chains']}
- 多链分散度：{defillama_data['risk_metrics']['chain_metrics']['diversification_score']:.2f}"""

            # 删除相关性部分，直接显示风险评分
            risk_score_section = f"""
综合风险评分：{defillama_data['risk_score']}/100"""

            # 将各部分组合成完整的提示
            prompt = f"""
分析以下DeFi协议的风险状况，基于DefiLlama实时数据和深度分析结果：
{basic_data_section}
{tvl_analysis_section}
{technical_indicators_section}
{chain_distribution_section}
{risk_score_section}

请提供以下JSON格式的详细风险分析：
{{
    "risk_score": 0-100的综合风险评分,
    "risk_level": "LOW/MEDIUM/HIGH",
    "risk_factors": {{
        "tvl_risk": {{
            "score": 0-100的TVL风险评分,
            "analysis": "基于TVL数据、趋势和波动性的深度分析",
            "factors": ["具体风险因素"]
        }},
        "chain_risk": {{
            "score": 0-100的跨链风险评分,
            "analysis": "基于链分布和集中度的风险分析",
            "factors": ["具体风险因素"]
        }},
        "market_risk": {{
            "score": 0-100的市场风险评分,
            "analysis": "基于市场趋势的分析",
            "factors": ["具体风险因素"]
        }},
        "technical_risk": {{
            "score": 0-100的技术风险评分,
            "analysis": "基于技术指标的风险分析",
            "factors": ["具体风险因素"]
        }},
    }},
    "trend_analysis": {{
        "short_term": "短期趋势预测",
        "medium_term": "中期趋势预测",
        "key_indicators": {{
            "macd_signal": "MACD信号解读",
            "rsi_signal": "RSI信号解读",
            "volume_analysis": "交易量分析"
        }}
    }},
    "recommendations": [
        "具体建议1",
        "具体建议2"
    ],
    "risk_mitigation_strategies": [
        "风险缓解策略1",
        "风险缓解策略2"
    ],
    "monitoring_points": [
        "需要持续监控的关键指标1",
        "需要持续监控的关键指标2"
    ]
}}

注意：
1. 重点关注TVL变化趋势和技术指标的组合信号
2. 评估跨链风险和链间分布的集中度
3. 考虑市场周期和宏观环境因素
4. 提供具体可行的风险缓解建议
5. 特别关注异常的技术指标信号
6. 评估审计情况对安全性的影响
"""

            if self.client is not None:
                # 调用OpenAI API进行分析
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个专业的DeFi风险分析师，擅长评估协议安全性、流动性和去中心化程度。请基于详细的数据指标和深度分析结果，提供全面的风险评估。重点关注技术指标和多维度风险因素。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )

                # 解析AI分析结果
                ai_analysis = json.loads(response.choices[0].message.content)

                # 合并所有数据
                final_analysis = {
                    "protocol_info": defillama_data["basic_data"],
                    "defi_llama_data": defillama_data,
                    "ai_risk_analysis": ai_analysis,
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "DefiLlama + AI Analysis",
                }

                logger.info(f"成功完成 {protocol_name} 的综合风险分析")
                return final_analysis
            else:
                logger.warning("AI客户端未初始化，返回基础分析结果")
                return self._get_basic_protocol_risk_analysis(protocol_name)

        except Exception as e:
            logger.error(f"分析协议风险时出错: {e}")
            return self._get_basic_protocol_risk_analysis(protocol_name)

    def _process_tvl_data(self, tvl_history: List[Dict]) -> pd.DataFrame:
        """将TVL历史数据转换为pandas DataFrame并进行分析"""
        try:
            # 创建DataFrame
            df = pd.DataFrame(tvl_history)
            df["date"] = pd.to_datetime(df["date"], unit="s")
            df.set_index("date", inplace=True)

            # 计算统计指标
            df["tvl"] = df["totalLiquidityUSD"]
            df["tvl_change"] = df["tvl"].pct_change()
            df["volatility"] = df["tvl_change"].rolling(window=7).std()
            df["ma7"] = df["tvl"].rolling(window=7).mean()
            df["ma30"] = df["tvl"].rolling(window=30).mean()

            return df
        except Exception as e:
            logger.error(f"处理TVL数据时出错: {e}")
            return pd.DataFrame()

    def _analyze_chain_distribution(self, chain_tvls: Dict) -> pd.DataFrame:
        """分析链分布数据"""
        try:
            # 提取每条链的最新TVL和历史数据
            chain_analysis = {}
            for chain, data in chain_tvls.items():
                if isinstance(data, dict):
                    chain_data = {
                        "tvl_history": [],
                        "token_distribution": {},
                        "token_count": 0,
                        "stablecoin_ratio": 0,
                        "tvl_growth_7d": 0,
                        "tvl_volatility": 0,
                    }

                    # 处理TVL历史数据
                if "tvl" in data and isinstance(data["tvl"], list):
                    tvl_data = data["tvl"]
                    if tvl_data:
                        # 获取最新TVL
                        current_tvl = tvl_data[-1]["totalLiquidityUSD"]
                        chain_data["current_tvl"] = current_tvl

                        # 计算7天增长率
                        if len(tvl_data) >= 7:
                            week_ago_tvl = tvl_data[-7]["totalLiquidityUSD"]
                            # 修复除零错误
                            if week_ago_tvl > 0:
                                chain_data["tvl_growth_7d"] = (
                                    (current_tvl / week_ago_tvl) - 1
                                ) * 100
                            else:
                                chain_data["tvl_growth_7d"] = 0

                        # 计算波动率
                        tvl_values = [d["totalLiquidityUSD"] for d in tvl_data[-30:]]
                        if tvl_values:
                            # 修复除零错误
                            mean_tvl = np.mean(tvl_values)
                            if mean_tvl > 0:
                                chain_data["tvl_volatility"] = (
                                    np.std(tvl_values) / mean_tvl
                                )
                            else:
                                chain_data["tvl_volatility"] = 0
                    # 处理代币分布数据
                    if "tokensInUsd" in data and isinstance(data["tokensInUsd"], list):
                        latest_tokens = (
                            data["tokensInUsd"][-1] if data["tokensInUsd"] else None
                        )
                        if latest_tokens and "tokens" in latest_tokens:
                            tokens = latest_tokens["tokens"]
                            total_value = sum(tokens.values())

                            # 计算代币分布
                            if total_value > 0:
                                chain_data["token_distribution"] = {
                                    token: value / total_value * 100
                                    for token, value in tokens.items()
                                }

                            # 计算代币数量
                            chain_data["token_count"] = len(tokens)

                            # 计算稳定币比例
                            stablecoin_value = sum(
                                value
                                for token, value in tokens.items()
                                if any(
                                    stable in token.upper()
                                    for stable in ["USDT", "USDC", "DAI", "UST", "BUSD"]
                                )
                            )
                            chain_data["stablecoin_ratio"] = (
                                (stablecoin_value / total_value * 100)
                                if total_value > 0
                                else 0
                            )

                    chain_analysis[chain] = chain_data

            # 创建DataFrame
            rows = []
            for chain, analysis in chain_analysis.items():
                row = {
                    "chain": chain,
                    "tvl": analysis.get("current_tvl", 0),
                    "tvl_growth_7d": analysis.get("tvl_growth_7d", 0),
                    "tvl_volatility": analysis.get("tvl_volatility", 0),
                    "token_count": analysis.get("token_count", 0),
                    "stablecoin_ratio": analysis.get("stablecoin_ratio", 0),
                }
                rows.append(row)

            df = pd.DataFrame(rows)
            if df.empty:
                return pd.DataFrame(
                    columns=["chain", "tvl", "percentage", "risk_metrics"]
                )

            # 计算基础指标
            total_tvl = df["tvl"].sum()
            if total_tvl > 0:
                df["percentage"] = df["tvl"] / total_tvl * 100
            else:
                df["percentage"] = 0
            df["hhi_contribution"] = (df["percentage"] / 100) ** 2

            # 计算链风险评级
            chain_risk_levels = {
                "Ethereum": "LOW",
                "BSC": "MEDIUM",
                "Polygon": "LOW",
                "Avalanche": "MEDIUM",
                "Arbitrum": "LOW",
                "Optimism": "LOW",
                "Fantom": "MEDIUM",
                "Solana": "MEDIUM",
                "Terra2": "HIGH",
                "Neutron": "MEDIUM",
                "Injective": "MEDIUM",
                "Sei": "HIGH",
            }
            df["chain_risk"] = df["chain"].map(
                lambda x: chain_risk_levels.get(x, "HIGH")
            )

            # 计算综合风险指标
            df["concentration_risk"] = df["percentage"].apply(
                lambda x: "HIGH" if x > 50 else ("MEDIUM" if x > 20 else "LOW")
            )

            # 计算代币多样性风险
            df["token_diversity_risk"] = df["token_count"].apply(
                lambda x: "HIGH" if x < 3 else ("MEDIUM" if x < 5 else "LOW")
            )

            # 计算稳定币风险
            df["stablecoin_risk"] = df["stablecoin_ratio"].apply(
                lambda x: "HIGH" if x > 80 else ("MEDIUM" if x > 50 else "LOW")
            )

            # 计算TVL增长风险
            df["growth_risk"] = df["tvl_growth_7d"].apply(
                lambda x: "HIGH" if x < -20 else ("MEDIUM" if x < 0 else "LOW")
            )

            # 计算波动性风险
            df["volatility_risk"] = df["tvl_volatility"].apply(
                lambda x: "HIGH" if x > 0.5 else ("MEDIUM" if x > 0.2 else "LOW")
            )

            # 计算综合风险评分
            risk_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
            risk_weights = {
                "chain_risk": 0.2,
                "concentration_risk": 0.2,
                "token_diversity_risk": 0.15,
                "stablecoin_risk": 0.15,
                "growth_risk": 0.15,
                "volatility_risk": 0.15,
            }

            for risk_type in risk_weights.keys():
                df[f"{risk_type}_score"] = df[risk_type].map(risk_scores)

            df["risk_score"] = sum(
                df[f"{risk_type}_score"] * weight
                for risk_type, weight in risk_weights.items()
            )

            # 添加风险评估结果
            df["risk_metrics"] = df.apply(
                lambda row: {
                    "overall_risk_score": row["risk_score"],
                    "risk_factors": [
                        f"链风险: {row['chain_risk']}",
                        f"集中度风险: {row['concentration_risk']}",
                        f"代币多样性风险: {row['token_diversity_risk']}",
                        f"稳定币风险: {row['stablecoin_risk']}",
                        f"增长风险: {row['growth_risk']}",
                        f"波动性风险: {row['volatility_risk']}",
                    ],
                    "metrics": {
                        "tvl_growth_7d": row["tvl_growth_7d"],
                        "tvl_volatility": row["tvl_volatility"],
                        "token_count": row["token_count"],
                        "stablecoin_ratio": row["stablecoin_ratio"],
                    },
                },
                axis=1,
            )

            # 排序并返回结果
            return df.sort_values("tvl", ascending=False)

        except Exception as e:
            logger.error(f"分析链分布时出错: {e}")
            return pd.DataFrame(columns=["chain", "tvl", "percentage", "risk_metrics"])

    def _calculate_risk_metrics(
        self, tvl_df: pd.DataFrame, chain_df: pd.DataFrame
    ) -> Dict:
        """计算综合风险指标"""
        try:
            # TVL相关指标
            current_tvl = tvl_df["tvl"].iloc[-1] if not tvl_df.empty else 0
            tvl_growth_7d = (
                (tvl_df["tvl"].iloc[-1] / tvl_df["tvl"].iloc[-7] - 1) * 100
                if len(tvl_df) >= 7
                else 0
            )
            tvl_growth_30d = (
                (tvl_df["tvl"].iloc[-1] / tvl_df["tvl"].iloc[-30] - 1) * 100
                if len(tvl_df) >= 30
                else 0
            )

            # 计算波动率（标准差/均值）
            volatility = (
                tvl_df["tvl"].std() / tvl_df["tvl"].mean() if not tvl_df.empty else 0
            )

            # 趋势分析
            ma7 = tvl_df["tvl"].rolling(window=7).mean()
            ma30 = tvl_df["tvl"].rolling(window=30).mean()
            current_trend = (
                "up"
                if ma7.iloc[-1] > ma30.iloc[-1]
                else "down" if not tvl_df.empty else "neutral"
            )

            # 计算TVL稳定性指标
            tvl_stability = (
                1 - (tvl_df["tvl"].std() / tvl_df["tvl"].mean())
                if not tvl_df.empty
                else 0
            )

            # 链分布指标
            chain_metrics = {
                "chain_count": len(chain_df),
                "max_chain_concentration": (
                    chain_df["percentage"].max() if not chain_df.empty else 0
                ),
                "high_risk_chains": (
                    len(chain_df[chain_df["concentration_risk"] == "HIGH"])
                    if not chain_df.empty and "concentration_risk" in chain_df.columns
                    else 0
                ),
                "diversification_score": (
                    1 - chain_df["hhi_contribution"].sum()
                    if not chain_df.empty and "hhi_contribution" in chain_df.columns
                    else 0
                ),
                "avg_chain_risk": (
                    chain_df["risk_score"].mean()
                    if not chain_df.empty and "risk_score" in chain_df.columns
                    else 3
                ),
                "chain_stability": (
                    1 - chain_df["percentage"].std() / 100
                    if not chain_df.empty and "percentage" in chain_df.columns
                    else 0
                ),
            }

            # 计算综合风险指标
            risk_metrics = {
                "tvl_metrics": {
                    "current_tvl": current_tvl,
                    "tvl_growth_7d": tvl_growth_7d,
                    "tvl_growth_30d": tvl_growth_30d,
                    "tvl_volatility": volatility,
                    "tvl_stability": tvl_stability,
                    "trend": current_trend,
                },
                "chain_metrics": chain_metrics,
                "composite_metrics": {
                    "overall_stability": (
                        tvl_stability + chain_metrics["chain_stability"]
                    )
                    / 2,
                    "growth_score": (max(min(tvl_growth_7d, 100), -100) + 100) / 200,
                    "risk_score": (
                        0.4 * (1 - tvl_stability)
                        + 0.3 * (chain_metrics["avg_chain_risk"] / 3)
                        + 0.3 * (1 - chain_metrics["diversification_score"])
                    ),
                },
            }

            return risk_metrics
        except Exception as e:
            logger.error(f"计算风险指标时出错: {e}")
            return {}

    def get_protocol_data(self, protocol_name: str) -> Dict:
        """从DefiLlama获取协议数据"""
        try:

            # 加入缓存
            cache_key = f"protocol_data_{protocol_name}"
            if analysis_cache.get(cache_key):
                return analysis_cache[cache_key]

            # 获取协议基本信息
            protocol_data = llama.get_protocol(protocol_name)
            if not protocol_data:
                logger.warning(f"无法获取{protocol_name}的基本信息")
                return None

            # 转换为字典格式
            protocol_data = {
                "name": protocol_data.get("name", ""),
                "symbol": protocol_data.get("symbol", ""),
                "description": protocol_data.get("description", ""),
                "url": protocol_data.get("url", ""),
                "tvl": protocol_data.get("tvl", 0),
                "mcap": protocol_data.get("mcap", 0),
                "audits": protocol_data.get("audits", 0),
                "audit_note": protocol_data.get("audit_note", ""),
                "audit_links": protocol_data.get("audit_links", []),
                "chains": protocol_data.get("chains", []),
                "chainTvls": protocol_data.get("chainTvls", {}),
                "currentChainTvls": protocol_data.get("currentChainTvls", {}),
                "category": protocol_data.get("category", ""),
                "methodology": protocol_data.get("methodology", ""),
                "twitter": protocol_data.get("twitter", ""),
                "github": protocol_data.get("github", ""),
                "openSource": protocol_data.get("openSource", False),
                "listedAt": protocol_data.get("listedAt", 0),
                "gecko_id": protocol_data.get("gecko_id", ""),
                "cmcId": protocol_data.get("cmcId", ""),
            }
            analysis_cache[cache_key] = protocol_data
            return protocol_data
        except Exception as e:
            logger.error(f"获取协议数据时出错: {e}")
            return None

    def _fetch_defillama_data(self, protocol_name: str) -> Dict:
        """处理协议数据并进行分析"""
        try:
            # 如果输入是字符串（协议名称），先获取协议数据
            protocol_data = self.get_protocol_data(protocol_name)

            if not protocol_data:
                logger.warning(f"无法获取{protocol_data}的数据")
                return None

            # 处理TVL历史数据
            tvl_history = protocol_data.get("tvl", [])
            tvl_df = self._process_tvl_data(tvl_history)

            current_tvl = tvl_df["tvl"].iloc[-1]
            # 处理基础数据
            tvl_24h_ago = tvl_df["tvl"].iloc[-2] if len(tvl_df) > 1 else current_tvl
            tvl_change_24h = (
                ((current_tvl - tvl_24h_ago) / tvl_24h_ago * 100) if tvl_24h_ago else 0
            )
            mcap = protocol_data.get("mcap", 0)
            tvl_ratio = mcap / current_tvl if current_tvl and mcap else 0

            # 获取链分布
            chains = protocol_data.get("chains", [])
            chain_tvls = protocol_data.get("chainTvls", {})

            # 分析链分布
            chain_df = self._analyze_chain_distribution(chain_tvls)

            # 计算风险指标
            risk_metrics = self._calculate_risk_metrics(tvl_df, chain_df)

            # 分析趋势
            trend_analysis = self._analyze_trend(tvl_df)

            # 更新风险指标
            risk_metrics.update({"trend_analysis": trend_analysis})

            # 计算综合风险评分
            risk_score = self._calculate_risk_score(
                {
                    "tvl_metrics": risk_metrics["tvl_metrics"],
                    "chain_metrics": risk_metrics["chain_metrics"],
                    "audit_info": {"count": int(protocol_data.get("audits", 0))},
                }
            )

            result = {
                "basic_data": {
                    "name": protocol_data.get("name", ""),
                    "symbol": protocol_data.get("symbol", ""),
                    "description": protocol_data.get("description", ""),
                    "category": protocol_data.get("category", ""),
                    "url": protocol_data.get("url", ""),
                    "current_tvl": current_tvl,
                    "tvl_change_24h": tvl_change_24h,
                    "mcap_tvl_ratio": tvl_ratio,
                    "chain_count": len(chains),
                    "audit_count": int(protocol_data.get("audits", 0)),
                    "methodology": protocol_data.get("methodology", ""),
                },
                "chain_distribution": chain_df.to_dict("records"),
                "risk_metrics": risk_metrics,
                "risk_score": risk_score,
                "tvl_analysis": {
                    "historical_data": tvl_df.to_dict("records"),
                    "summary_stats": {
                        "mean": tvl_df["tvl"].mean(),
                        "std": tvl_df["tvl"].std(),
                        "min": tvl_df["tvl"].min(),
                        "max": tvl_df["tvl"].max(),
                        "current_percentile": np.percentile(tvl_df["tvl"], 75),
                    },
                    "trend_analysis": trend_analysis,
                },
                "correlation_analysis": {},
                "audit_info": {
                    "count": int(protocol_data.get("audits", 0)),
                    "note": protocol_data.get("audit_note", ""),
                    "links": protocol_data.get("audit_links", []),
                },
                "additional_info": {
                    "github": protocol_data.get("github", []),
                    "twitter": protocol_data.get("twitter", ""),
                    "open_source": protocol_data.get("openSource", False),
                    "listed_at": protocol_data.get("listedAt", 0),
                    "gecko_id": protocol_data.get("gecko_id", ""),
                    "cmc_id": protocol_data.get("cmcId", ""),
                },
            }

            return result

        except Exception as e:
            logger.error(f"处理协议数据时出错: {e}")
            return None

    def _analyze_trend(self, tvl_df: pd.DataFrame) -> Dict:
        """分析TVL趋势"""
        try:
            if tvl_df.empty:
                return {
                    "trend": "neutral",
                    "strength": "weak",
                    "rsi": 50,
                    "indicators": {},
                }

            df = tvl_df.copy()

            # 计算移动平均线
            df["ma7"] = df["tvl"].rolling(window=7).mean()
            df["ma30"] = df["tvl"].rolling(window=30).mean()
            df["ma90"] = df["tvl"].rolling(window=90).mean()

            # 计算MACD
            exp1 = df["tvl"].ewm(span=12, adjust=False).mean()
            exp2 = df["tvl"].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal

            # 计算RSI
            delta = df["tvl"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # 计算布林带
            df["bb_middle"] = df["tvl"].rolling(window=20).mean()
            df["bb_std"] = df["tvl"].rolling(window=20).std()
            df["bb_upper"] = df["bb_middle"] + (df["bb_std"] * 2)
            df["bb_lower"] = df["bb_middle"] - (df["bb_std"] * 2)

            # 趋势强度分析
            current_trend = "bullish" if macd.iloc[-1] > signal.iloc[-1] else "bearish"
            trend_strength = abs(macd.iloc[-1] - signal.iloc[-1]) / df["tvl"].iloc[-1]

            # 计算动量指标
            df["momentum"] = df["tvl"].diff(periods=7)
            df["rate_of_change"] = df["tvl"].pct_change(periods=7) * 100

            # 趋势确认
            trend_signals = []
            if df["ma7"].iloc[-1] > df["ma30"].iloc[-1]:
                trend_signals.append("ma7_above_ma30")
            if df["momentum"].iloc[-1] > 0:
                trend_signals.append("positive_momentum")
            if rsi.iloc[-1] > 50:
                trend_signals.append("rsi_bullish")
            if macd.iloc[-1] > signal.iloc[-1]:
                trend_signals.append("macd_bullish")

            # 超买超卖信号
            overbought_oversold = (
                "overbought"
                if rsi.iloc[-1] > 70
                else "oversold" if rsi.iloc[-1] < 30 else "neutral"
            )

            return {
                "trend": current_trend,
                "strength": (
                    "strong"
                    if trend_strength > 0.05
                    else "moderate" if trend_strength > 0.02 else "weak"
                ),
                "rsi": rsi.iloc[-1],
                "indicators": {
                    "macd": {
                        "value": macd.iloc[-1],
                        "signal": signal.iloc[-1],
                        "histogram": histogram.iloc[-1],
                    },
                    "moving_averages": {
                        "ma7": df["ma7"].iloc[-1],
                        "ma30": df["ma30"].iloc[-1],
                        "ma90": df["ma90"].iloc[-1],
                    },
                    "bollinger_bands": {
                        "upper": df["bb_upper"].iloc[-1],
                        "middle": df["bb_middle"].iloc[-1],
                        "lower": df["bb_lower"].iloc[-1],
                    },
                    "momentum": {
                        "value": df["momentum"].iloc[-1],
                        "roc": df["rate_of_change"].iloc[-1],
                    },
                },
                "signals": {
                    "trend_signals": trend_signals,
                    "overbought_oversold": overbought_oversold,
                    "price_position": (
                        "above_bb"
                        if df["tvl"].iloc[-1] > df["bb_upper"].iloc[-1]
                        else (
                            "below_bb"
                            if df["tvl"].iloc[-1] < df["bb_lower"].iloc[-1]
                            else "within_bb"
                        )
                    ),
                },
            }
        except Exception as e:
            logger.error(f"分析趋势时出错: {e}")
            return {}

    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均线"""
        if len(prices) < period:
            return prices

        ema = np.zeros_like(prices)
        ema[:period] = np.mean(prices[:period])

        multiplier = 2 / (period + 1)
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]

        return ema

    def _calculate_support_levels(
        self, prices: np.ndarray, current_price: float
    ) -> List[float]:
        """计算支撑位"""
        if len(prices) < 30:
            return [current_price * 0.95, current_price * 0.9]

        # 找出局部最低点
        min_points = []
        for i in range(2, len(prices) - 2):
            if (
                prices[i] < prices[i - 1]
                and prices[i] < prices[i - 2]
                and prices[i] < prices[i + 1]
                and prices[i] < prices[i + 2]
            ):
                min_points.append(prices[i])

        # 过滤掉高于当前价格的支撑位
        support_levels = [p for p in min_points if p < current_price]

        # 如果没有找到足够的支撑位，使用百分比计算
        if len(support_levels) < 2:
            support_levels = [current_price * 0.95, current_price * 0.9]

        # 返回最接近当前价格的两个支撑位
        support_levels.sort(reverse=True)
        return support_levels[:2]

    def _calculate_resistance_levels(
        self, prices: np.ndarray, current_price: float
    ) -> List[float]:
        """计算阻力位"""
        if len(prices) < 30:
            return [current_price * 1.05, current_price * 1.1]

        # 找出局部最高点
        max_points = []
        for i in range(2, len(prices) - 2):
            if (
                prices[i] > prices[i - 1]
                and prices[i] > prices[i - 2]
                and prices[i] > prices[i + 1]
                and prices[i] > prices[i + 2]
            ):
                max_points.append(prices[i])

        # 过滤掉低于当前价格的阻力位
        resistance_levels = [p for p in max_points if p > current_price]

        # 如果没有找到足够的阻力位，使用百分比计算
        if len(resistance_levels) < 2:
            resistance_levels = [current_price * 1.05, current_price * 1.1]

        # 返回最接近当前价格的两个阻力位
        resistance_levels.sort()
        return resistance_levels[:2]

    def _get_basic_protocol_risk_analysis(self, protocol_name: str) -> Dict:
        """生成基本的协议风险分析结果"""
        return {
            "protocol_name": protocol_name,
            "risk_score": 50,
            "risk_level": "MEDIUM",
            "security_score": 75,
            "liquidity_score": 70,
            "centralization_risk": "MEDIUM",
            "audit_status": {
                "score": 80,
                "last_audit_date": "2023-12-01",
                "audit_firms": ["Basic Security Audit"],
            },
            "audit_details": {
                "last_audit_date": "2023-12-01",
                "audit_firms": ["Basic Security Audit"],
                "vulnerabilities": [],
            },
            "risk_factors": ["缺乏实时风险数据", "使用基础风险评估模型"],
            "recommendations": [
                "建议进行更深入的风险评估",
                "关注协议的最新更新和审计报告",
                "分散投资以降低风险",
            ],
            "timestamp": datetime.now().isoformat(),
            "data_source": "Default",
        }

    def _calculate_risk_score(self, metrics: Dict) -> float:
        """计算综合风险评分"""
        try:
            # 权重设置
            weights = {
                "tvl": 0.5,
                "volatility": 0.3,
                "concentration": 0.2,
            }

            # TVL得分 (0-100)
            tvl_score = min(
                100, metrics["tvl_metrics"]["current_tvl"] / 1000000
            )  # 每100万TVL一分，最高100分

            # 波动性得分 (100为最稳定)
            volatility_score = max(
                0, 100 - metrics["tvl_metrics"]["tvl_volatility"] * 100
            )

            # 集中度得分 (100为最分散)
            concentration_score = max(
                0, 100 - metrics["chain_metrics"]["max_chain_concentration"]
            )

            # 计算加权总分
            total_score = (
                weights["tvl"] * tvl_score
                + weights["volatility"] * volatility_score
                + weights["concentration"] * concentration_score
            )

            return round(total_score, 2)
        except Exception as e:
            logger.error(f"计算风险评分时出错: {e}")
            return 50.0

    def analyze_investment_type_risk(
        self,
        protocol: str,
        asset: str,
        invest_type: int,
        amount: float,
        invest_type_name: str,
    ) -> Dict:
        """
        分析特定投资类型的风险

        Args:
            protocol: 协议名称
            asset: 资产名称
            invest_type: 投资类型ID
            amount: 投资金额
            invest_type_name: 投资类型名称

        Returns:
            Dict: 包含风险分析结果的字典
        """
        try:
            # 构建AI分析提示
            prompt = f"""
分析以下DeFi投资的风险状况:
- 协议: {protocol}
- 资产: {asset}
- 投资类型: {invest_type_name} (类型{invest_type})
- 金额: {amount}

请提供以下JSON格式的详细风险分析:
{{
    "risk_score": 0-100的综合风险评分,
    "risk_level": "LOW/MEDIUM/HIGH",
    "risk_factors": [
        "具体风险因素1",
        "具体风险因素2"
    ],
    "recommendations": [
        "具体建议1",
        "具体建议2"
    ],
    "monitoring_points": [
        "需要监控的指标1",
        "需要监控的指标2"
    ]
}}

注意:
1. 特别关注{invest_type_name}类型投资的特定风险
2. 考虑{asset}资产的特性
3. 评估{protocol}协议的安全性
4. 提供具体可行的风险缓解建议
"""

            if hasattr(self, "client") and self.client is not None:
                # 调用OpenAI API进行分析
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个专业的DeFi风险分析师，擅长评估不同类型投资的风险特性。请基于投资类型、资产特性和协议安全性，提供全面的风险评估。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )

                # 解析AI分析结果
                ai_analysis = json.loads(response.choices[0].message.content)

                # 添加元数据
                ai_analysis["timestamp"] = datetime.now().isoformat()
                ai_analysis["invest_type"] = invest_type
                ai_analysis["invest_type_name"] = invest_type_name
                ai_analysis["protocol"] = protocol
                ai_analysis["asset"] = asset

                logger.info(f"成功完成{protocol}的{invest_type_name}投资风险分析")
                return ai_analysis
            else:
                logger.warning("AI客户端未初始化，返回基础分析结果")
                return self._get_basic_investment_risk_analysis(
                    protocol, asset, invest_type, invest_type_name
                )

        except Exception as e:
            logger.error(f"分析投资类型风险时出错: {e}")
            return self._get_basic_investment_risk_analysis(
                protocol, asset, invest_type, invest_type_name
            )

    def _get_basic_investment_risk_analysis(
        self, protocol: str, asset: str, invest_type: int, invest_type_name: str
    ) -> Dict:
        """
        获取基础投资风险分析（当AI分析不可用时）

        Args:
            protocol: 协议名称
            asset: 资产名称
            invest_type: 投资类型ID
            invest_type_name: 投资类型名称

        Returns:
            Dict: 包含基础风险分析的字典
        """
        # 基础风险评分映射
        base_risk_scores = {
            1: 20,  # 存币 - 较低风险
            2: 60,  # 流动性池 - 较高风险
            3: 50,  # 挖矿 - 中高风险
            4: 70,  # 机枪池 - 高风险
            5: 40,  # 质押 - 中低风险
            6: 55,  # 借贷 - 中高风险
        }

        # 获取基础风险分数，默认为中等风险
        risk_score = base_risk_scores.get(invest_type, 50)

        # 确定风险等级
        risk_level = "MEDIUM"
        if risk_score >= 65:
            risk_level = "HIGH"
        elif risk_score <= 35:
            risk_level = "LOW"

        # 基础风险因素
        risk_factors = []
        recommendations = []
        monitoring_points = []

        # 根据不同投资类型添加基础风险因素
        if invest_type == 1:  # 存币
            risk_factors = ["平台安全风险", "存款合约风险"]
            recommendations = ["定期检查平台安全状态", "分散存款到多个平台"]
            monitoring_points = ["平台安全审计状态", "存款APY变化"]

        elif invest_type == 2:  # 流动性池
            risk_factors = ["无常损失风险", "流动性池合约风险", "价格波动风险"]
            recommendations = [
                "关注资产价格波动",
                "设置止损策略",
                "分散投资于多个流动性池",
            ]
            monitoring_points = ["资产价格相对变化", "池子总流动性变化", "交易费收益率"]

        elif invest_type == 3:  # 挖矿
            risk_factors = ["收益递减风险", "代币价格波动风险", "智能合约风险"]
            recommendations = [
                "定期评估挖矿收益",
                "关注代币价格趋势",
                "设置自动复投或提取策略",
            ]
            monitoring_points = ["挖矿APY变化", "奖励代币价格", "协议TVL变化"]

        elif invest_type == 4:  # 机枪池
            risk_factors = ["复杂策略风险", "杠杆风险", "协议组合风险", "智能合约风险"]
            recommendations = [
                "限制机枪池资金比例",
                "选择经过多次审计的机枪池",
                "关注策略变更",
            ]
            monitoring_points = ["策略变更", "底层协议安全状态", "收益率变化"]

        elif invest_type == 5:  # 质押
            risk_factors = ["锁定期流动性风险", "质押奖励变化风险", "解质押等待风险"]
            recommendations = [
                "评估锁定期与投资周期",
                "关注质押奖励变化",
                "分散质押到不同协议",
            ]
            monitoring_points = ["质押APY变化", "解质押条件变更", "协议治理变化"]

        elif invest_type == 6:  # 借贷
            risk_factors = ["利率波动风险", "清算风险", "抵押品价值波动风险"]
            recommendations = ["保持健康抵押率", "设置清算预警", "关注借贷市场利率变化"]
            monitoring_points = ["借贷利率变化", "抵押率变化", "清算阈值距离"]

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
            "timestamp": datetime.now().isoformat(),
            "invest_type": invest_type,
            "invest_type_name": invest_type_name,
            "protocol": protocol,
            "asset": asset,
            "note": "基础风险分析（AI分析不可用）",
        }

    def analyze_protocol_risk_from_position(self, position) -> Dict:
        """
        直接从Position对象分析DeFi协议风险

        Args:
            position: Position对象，包含protocol、asset、amount等信息

        Returns:
            Dict: 包含风险分析结果的字典
        """
        try:
            protocol_name = position.protocol
            logger.info(f"从Position对象分析协议风险: {protocol_name}")

            # 调用现有的协议风险分析函数
            risk_analysis = self.analyze_defi_protocol_risk(protocol_name)

            # 添加Position相关信息到分析结果
            risk_analysis["position_info"] = {
                "asset": position.asset,
                "amount": position.amount,
                "apy": position.apy,
            }

            # 如果Position包含invest_type，添加投资类型风险分析
            if position.invest_type is not None:
                invest_type_name = self._get_invest_type_name(position.invest_type)
                investment_risk = self.analyze_investment_type_risk_from_position(
                    position, invest_type_name
                )
                risk_analysis["investment_type_risk"] = investment_risk

            return risk_analysis

        except Exception as e:
            logger.error(f"从Position分析协议风险时出错: {e}")
            return self._get_basic_protocol_risk_analysis(position.protocol)

    def _get_invest_type_name(self, invest_type: int) -> str:
        """获取投资类型名称"""
        invest_type_names = {
            1: "存币",
            2: "流动性池",
            3: "挖矿",
            4: "机枪池",
            5: "质押",
            6: "借贷",
        }
        return invest_type_names.get(invest_type, "未知投资类型")

    def analyze_investment_type_risk_from_position(
        self, position, invest_type_name: str = None
    ) -> Dict:
        """
        从Position对象分析特定投资类型的风险

        Args:
            position: Position对象
            invest_type_name: 投资类型名称，如果为None则自动获取

        Returns:
            Dict: 包含风险分析结果的字典
        """
        if invest_type_name is None:
            invest_type_name = self._get_invest_type_name(position.invest_type)

        return self.analyze_investment_type_risk(
            position.protocol,
            position.asset,
            position.invest_type,
            position.amount,
            invest_type_name,
        )

    def analyze_portfolio_correlation(self, investments: List[Dict]) -> Dict:
        """
        分析投资组合中各资产之间的相关性

        Args:
            investments: 投资列表，每个投资是一个字典，包含协议、资产、金额等信息

        Returns:
            Dict: 包含相关性分析结果的字典
        """
        try:
            # 提取资产列表
            assets = []
            for investment in investments:
                if "asset" in investment:
                    assets.append(investment["asset"])
                elif (
                    "assetsTokenList" in investment
                    and len(investment["assetsTokenList"]) > 0
                ):
                    for asset in investment["assetsTokenList"]:
                        if "tokenSymbol" in asset:
                            assets.append(asset["tokenSymbol"])

            # 去重
            unique_assets = list(set(assets))

            if len(unique_assets) <= 1:
                return {
                    "correlation_matrix": {},
                    "diversification_score": 0,
                    "risk_level": "HIGH",
                    "analysis": "投资组合仅包含单一资产，缺乏多样性",
                    "recommendations": [
                        "增加不同类型的资产以分散风险",
                        "考虑添加负相关资产以降低整体波动性",
                    ],
                }

            # 构建相关性矩阵
            correlation_matrix = {}
            for i, asset1 in enumerate(unique_assets):
                correlation_matrix[asset1] = {}
                for asset2 in unique_assets:
                    if asset1 == asset2:
                        correlation_matrix[asset1][asset2] = 1.0
                    else:
                        # 使用预设的相关性数据或估计值
                        correlation_matrix[asset1][asset2] = (
                            self._estimate_asset_correlation(asset1, asset2)
                        )

            # 计算多样化得分 (0-1，越高越多样化)
            avg_correlation = self._calculate_average_correlation(correlation_matrix)
            diversification_score = 1 - avg_correlation

            # 确定风险等级
            risk_level = "MEDIUM"
            if diversification_score < 0.3:
                risk_level = "HIGH"
            elif diversification_score > 0.6:
                risk_level = "LOW"

            # 生成分析和建议
            analysis = f"投资组合包含{len(unique_assets)}种资产，多样化得分为{diversification_score:.2f}"
            recommendations = []

            if diversification_score < 0.4:
                recommendations.append("增加更多不相关或负相关的资产以提高多样性")
                recommendations.append(
                    "考虑添加不同类别的资产（如稳定币、大型加密货币、DeFi代币等）"
                )
            elif avg_correlation > 0.7:
                recommendations.append("当前资产相关性较高，市场下跌时可能同时贬值")
                recommendations.append("考虑添加与现有资产负相关的资产")

            return {
                "correlation_matrix": correlation_matrix,
                "diversification_score": diversification_score,
                "risk_level": risk_level,
                "analysis": analysis,
                "recommendations": recommendations,
                "assets_analyzed": unique_assets,
            }

        except Exception as e:
            logger.error(f"分析投资组合相关性时出错: {e}")
            return {
                "correlation_matrix": {},
                "diversification_score": 0.5,
                "risk_level": "MEDIUM",
                "analysis": "无法完成相关性分析",
                "recommendations": [
                    "建议手动评估投资组合多样性",
                    "考虑分散投资到不同类型的资产",
                ],
                "error": str(e),
            }

    def _estimate_asset_correlation(self, asset1: str, asset2: str) -> float:
        """
        估计两个资产之间的相关性

        Args:
            asset1: 第一个资产的符号
            asset2: 第二个资产的符号

        Returns:
            float: 估计的相关性系数 (-1 到 1)
        """
        # 预设的相关性数据
        known_correlations = {
            ("BTC", "ETH"): 0.8,
            ("BTC", "USDT"): 0.1,
            ("BTC", "USDC"): 0.1,
            ("ETH", "USDT"): 0.1,
            ("ETH", "USDC"): 0.1,
            ("USDT", "USDC"): 0.9,
        }

        # 标准化资产名称
        asset1 = asset1.upper()
        asset2 = asset2.upper()

        # 检查是否有预设的相关性数据
        if (asset1, asset2) in known_correlations:
            return known_correlations[(asset1, asset2)]
        elif (asset2, asset1) in known_correlations:
            return known_correlations[(asset2, asset1)]

        # 基于资产类型估计相关性
        if self._is_stablecoin(asset1) and self._is_stablecoin(asset2):
            return 0.9  # 稳定币之间高度相关
        elif self._is_stablecoin(asset1) or self._is_stablecoin(asset2):
            return 0.1  # 稳定币与其他资产低相关
        else:
            return 0.6  # 默认中等相关性

    def _is_stablecoin(self, asset: str) -> bool:
        """
        判断资产是否为稳定币

        Args:
            asset: 资产符号

        Returns:
            bool: 是否为稳定币
        """
        stablecoins = [
            "USDT",
            "USDC",
            "DAI",
            "BUSD",
            "UST",
            "TUSD",
            "USDP",
            "GUSD",
            "LUSD",
            "FRAX",
        ]
        return asset.upper() in stablecoins

    def _calculate_average_correlation(self, correlation_matrix: Dict) -> float:
        """
        计算相关性矩阵的平均相关性

        Args:
            correlation_matrix: 相关性矩阵

        Returns:
            float: 平均相关性
        """
        total = 0
        count = 0

        for asset1, correlations in correlation_matrix.items():
            for asset2, value in correlations.items():
                if asset1 != asset2:  # 排除自相关
                    total += abs(value)  # 使用绝对值，因为负相关也是一种多样化
                    count += 1

        if count == 0:
            return 0

        return total / count
