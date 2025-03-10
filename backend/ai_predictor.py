import httpx
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import os
import requests
from openai import OpenAI
import logging
import json
from functools import lru_cache

# 设置日志记录器
logger = logging.getLogger("defi_risk.ai_predictor")

# 设置代理
proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}


class AnalysisCache:
    def __init__(self, max_size: int = 100, expiration_minutes: int = 15):
        self.cache = {}
        self.max_size = max_size
        self.expiration_minutes = expiration_minutes
        self.access_order = []  # 用于LRU实现

    def get(self, asset: str) -> Optional[Dict]:
        """获取缓存的分析结果"""
        if asset in self.cache:
            result, timestamp = self.cache[asset]
            if datetime.now() - timestamp < timedelta(minutes=self.expiration_minutes):
                # 更新访问顺序
                self.access_order.remove(asset)
                self.access_order.append(asset)
                return result
            else:
                # 过期数据，删除
                del self.cache[asset]
                self.access_order.remove(asset)
        return None

    def set(self, asset: str, result: Dict):
        """设置缓存数据"""
        # 如果缓存已满，删除最久未使用的项
        if len(self.cache) >= self.max_size and asset not in self.cache:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]

        # 添加或更新缓存
        self.cache[asset] = (result, datetime.now())
        if asset in self.access_order:
            self.access_order.remove(asset)
        self.access_order.append(asset)


class AiPredictor:
    def __init__(self):
        try:
            # 获取API密钥
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_API_URL")
            if not api_key or api_key.startswith("your") or "..." in api_key:
                logger.warning("未设置有效的OpenAI API密钥，AI预测功能将使用模拟数据")
                self.client = None
            else:
                # 创建带有代理的HTTP客户端
                try:
                    client_http = httpx.Client(proxy="http://127.0.0.1:7890")
                except TypeError:
                    # 如果是旧版本httpx
                    client_http = httpx.Client()
                    logger.warning("您的httpx版本不支持proxies参数，将使用默认连接")

                # 将http_client传递给OpenAI客户端
                self.client = OpenAI(
                    api_key=api_key, base_url=base_url, http_client=client_http
                )

                logger.info("成功初始化OpenAI客户端")
        except Exception as e:
            logger.error(f"初始化OpenAI客户端时出错: {e}")
            self.client = None

        # 初始化分析缓存
        self.analysis_cache = AnalysisCache(max_size=100, expiration_minutes=15)

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
            cached_result = self.analysis_cache.get(asset)
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
            self.analysis_cache.set(asset, analysis)
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
                            "content": "你是一个专业的加密货币市场分析师，擅长技术分析和风险评估。",
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

    def _fetch_security_data(self, protocol_name: str) -> Dict:
        """从安全审计API获取协议安全数据

        尝试从安全审计API获取协议的安全评分、审计历史和漏洞记录
        """
        try:
            # 协议名称到安全API标识符的映射
            security_identifiers = {
                "Aave V3": "aave-v3",
                "Compound V3": "compound-v3",
                "Curve": "curve",
                "Uniswap V2": "uniswap-v2",
                # 可以添加更多协议
            }

            protocol_id = security_identifiers.get(
                protocol_name, protocol_name.lower().replace(" ", "-")
            )

            # 尝试从CertiK API获取数据
            certik_data = self._fetch_certik_data(protocol_id)
            if certik_data:
                logger.info(f"成功从CertiK获取{protocol_name}安全数据")
                return certik_data

            # 尝试从DeFiSafety获取数据
            defi_safety_data = self._fetch_defi_safety_data(protocol_id)
            if defi_safety_data:
                logger.info(f"成功从DeFiSafety获取{protocol_name}安全数据")
                return defi_safety_data

            # 尝试从Immunefi获取数据
            immunefi_data = self._fetch_immunefi_data(protocol_id)
            if immunefi_data:
                logger.info(f"成功从Immunefi获取{protocol_name}安全数据")
                return immunefi_data

            # 如果所有API调用失败，使用模拟数据
            # 模拟数据
            security_data = {
                "aave-v3": {
                    "audit_score": 95,
                    "last_audit_date": "2023-06-15",
                    "audit_firms": ["CertiK", "OpenZeppelin", "Trail of Bits"],
                    "vulnerabilities": [],
                    "security_incidents": [],
                },
                "compound-v3": {
                    "audit_score": 92,
                    "last_audit_date": "2023-04-20",
                    "audit_firms": ["Trail of Bits", "OpenZeppelin"],
                    "vulnerabilities": [
                        "Medium severity issue in liquidation mechanism (fixed)"
                    ],
                    "security_incidents": [],
                },
                "curve": {
                    "audit_score": 90,
                    "last_audit_date": "2023-02-10",
                    "audit_firms": ["CertiK", "Quantstamp"],
                    "vulnerabilities": ["Low severity reentrancy issue (fixed)"],
                    "security_incidents": [],
                },
                "uniswap-v2": {
                    "audit_score": 94,
                    "last_audit_date": "2022-11-05",
                    "audit_firms": ["Trail of Bits", "Consensys Diligence"],
                    "vulnerabilities": [],
                    "security_incidents": [],
                },
            }

            if protocol_id in security_data:
                logger.info(f"使用模拟数据获取{protocol_name}安全数据")
                return security_data[protocol_id]
            else:
                logger.warning(f"未找到{protocol_name}的安全数据")
                return {
                    "audit_score": 80,
                    "last_audit_date": "未知",
                    "audit_firms": ["未知"],
                    "vulnerabilities": [],
                    "security_incidents": [],
                }

        except Exception as e:
            logger.error(f"获取安全数据时出错: {e}")
            return {
                "audit_score": 80,
                "last_audit_date": "未知",
                "audit_firms": ["未知"],
                "vulnerabilities": [],
                "security_incidents": [],
            }

    def _fetch_certik_data(self, protocol_id: str) -> Optional[Dict]:
        """从CertiK API获取安全数据"""
        try:
            # 实际实现中，应该使用真实的API端点和密钥
            certik_api_key = os.getenv("CERTIK_API_KEY")
            if not certik_api_key:
                logger.warning("未找到CERTIK_API_KEY环境变量")
                return None

            certik_url = f"https://api.certik.com/projects/{protocol_id}"
            headers = {"Authorization": f"Bearer {certik_api_key}"}

            response = requests.get(
                certik_url, headers=headers, proxies=proxies, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "audit_score": data.get("security_score", 80),
                    "last_audit_date": data.get("last_audit_date", "未知"),
                    "audit_firms": data.get("auditors", ["CertiK"]),
                    "vulnerabilities": data.get("vulnerabilities", []),
                    "security_incidents": data.get("incidents", []),
                }
            else:
                logger.warning(f"CertiK API返回状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"从CertiK获取数据失败: {e}")
            return None

    def _fetch_defi_safety_data(self, protocol_id: str) -> Optional[Dict]:
        """从DeFiSafety获取安全数据"""
        try:
            defi_safety_url = f"https://api.defisafety.com/v1/projects/{protocol_id}"
            response = requests.get(defi_safety_url, proxies=proxies, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "audit_score": data.get("total_score", 80),
                    "last_audit_date": data.get("last_reviewed", "未知"),
                    "audit_firms": data.get("auditors", ["DeFiSafety"]),
                    "vulnerabilities": [],
                    "security_incidents": [],
                }
            else:
                logger.warning(f"DeFiSafety API返回状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"从DeFiSafety获取数据失败: {e}")
            return None

    def _fetch_immunefi_data(self, protocol_id: str) -> Optional[Dict]:
        """从Immunefi获取安全数据"""
        try:
            # 注意：Immunefi可能没有公开API，这里仅作为示例
            immunefi_api_key = os.getenv("IMMUNEFI_API_KEY")
            if not immunefi_api_key:
                logger.warning("未找到IMMUNEFI_API_KEY环境变量")
                return None

            immunefi_url = f"https://api.immunefi.com/v1/projects/{protocol_id}"
            headers = {"Authorization": f"Bearer {immunefi_api_key}"}

            response = requests.get(
                immunefi_url, headers=headers, proxies=proxies, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "audit_score": data.get("security_score", 80),
                    "last_audit_date": data.get("last_audit", "未知"),
                    "audit_firms": data.get("auditors", ["未知"]),
                    "vulnerabilities": data.get("disclosed_vulnerabilities", []),
                    "security_incidents": data.get("incidents", []),
                }
            else:
                logger.warning(f"Immunefi API返回状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"从Immunefi获取数据失败: {e}")
            return None

    def _fetch_protocol_data(self, protocol_name: str) -> Dict:
        """从链上或API获取协议数据

        使用DeFi数据API（如DefiLlama、DeFi Pulse等）获取实时协议数据
        """
        try:
            # 创建一个基础URL字典，用于不同的API端点
            api_endpoints = {
                "defillama": "https://api.llama.fi/protocol/",
                "defi_pulse": "https://data-api.defipulse.com/api/v1/defipulse/api/",
                "dune": "https://api.dune.com/api/v1/query/",  # 需要API密钥
            }

            # 协议名称到API标识符的映射
            protocol_identifiers = {
                "Aave V3": "aave-v3",
                "Compound V3": "compound-v3",
                "Curve": "curve-dex",
                "Uniswap V2": "uniswap-v2",
                # 可以添加更多协议
            }

            # 获取协议标识符
            protocol_id = protocol_identifiers.get(
                protocol_name, protocol_name.lower().replace(" ", "-")
            )

            # 使用requests发起请求
            # 首先尝试DefiLlama API获取TVL和基本数据
            defillama_url = f"{api_endpoints['defillama']}{protocol_id}"
            logger.info(f"正在从DefiLlama获取{protocol_name}数据: {defillama_url}")

            try:
                response = requests.get(defillama_url, timeout=10.0, proxies=proxies)
                if response.status_code == 200:
                    llama_data = response.json()

                    # 提取相关数据
                    tvl = llama_data.get("tvl", 0)
                    daily_volume = (
                        llama_data.get("volume24h", 0)
                        if "volume24h" in llama_data
                        else 0
                    )

                    # 获取安全数据
                    security_data = self._fetch_security_data(protocol_name)

                    # 构建协议数据
                    protocol_data = {
                        "tvl": tvl,
                        "daily_volume": daily_volume,
                        "audit_score": security_data["audit_score"],
                        "decentralization_score": 80,  # 默认值，理想情况下应从治理API获取
                        "insurance_coverage": False,  # 默认值，理想情况下应从保险协议API获取
                        "hack_history": security_data["security_incidents"],
                        "governance_token": llama_data.get("symbol", ""),
                        "implementation": "unknown",  # 默认值，理想情况下应从链上数据获取
                        "last_audit_date": security_data["last_audit_date"],
                        "audit_firms": security_data["audit_firms"],
                        "vulnerabilities": security_data["vulnerabilities"],
                    }

                    logger.info(f"成功获取{protocol_name}数据")
                    return protocol_data
                else:
                    logger.warning(f"DefiLlama API返回状态码: {response.status_code}")
                    # 如果API调用失败，返回默认数据
                    return self._get_default_protocol_data(protocol_name)
            except requests.exceptions.RequestException as e:
                logger.error(f"请求DefiLlama API时出错: {e}")
                return self._get_default_protocol_data(protocol_name)

        except Exception as e:
            logger.error(f"获取协议数据时出错: {e}")
            return self._get_default_protocol_data(protocol_name)

    def _get_default_protocol_data(self, protocol_name: str) -> Dict:
        """当API调用失败时返回默认协议数据"""
        default_data = {
            "Aave V3": {
                "tvl": 5_000_000_000,
                "daily_volume": 100_000_000,
                "audit_score": 95,
                "decentralization_score": 85,
                "insurance_coverage": True,
                "hack_history": [],
                "governance_token": "AAVE",
                "implementation": "upgradeable proxy",
                "last_audit_date": "2023-06-15",
                "audit_firms": ["CertiK", "OpenZeppelin", "Trail of Bits"],
                "vulnerabilities": [],
            },
            "Compound V3": {
                "tvl": 3_000_000_000,
                "daily_volume": 80_000_000,
                "audit_score": 90,
                "decentralization_score": 80,
                "insurance_coverage": True,
                "hack_history": [],
                "governance_token": "COMP",
                "implementation": "upgradeable proxy",
                "last_audit_date": "2023-04-20",
                "audit_firms": ["Trail of Bits", "OpenZeppelin"],
                "vulnerabilities": [
                    "Medium severity issue in liquidation mechanism (fixed)"
                ],
            },
            "Curve": {
                "tvl": 4_000_000_000,
                "daily_volume": 200_000_000,
                "audit_score": 88,
                "decentralization_score": 90,
                "insurance_coverage": False,
                "hack_history": [],
                "governance_token": "CRV",
                "implementation": "immutable",
                "last_audit_date": "2023-02-10",
                "audit_firms": ["CertiK", "Quantstamp"],
                "vulnerabilities": ["Low severity reentrancy issue (fixed)"],
            },
            "Uniswap V2": {
                "tvl": 2_000_000_000,
                "daily_volume": 150_000_000,
                "audit_score": 92,
                "decentralization_score": 95,
                "insurance_coverage": False,
                "hack_history": [],
                "governance_token": "UNI",
                "implementation": "immutable",
                "last_audit_date": "2022-11-05",
                "audit_firms": ["Trail of Bits", "Consensys Diligence"],
                "vulnerabilities": [],
            },
        }

        return default_data.get(
            protocol_name,
            {
                "tvl": 1_000_000_000,
                "daily_volume": 50_000_000,
                "audit_score": 80,
                "decentralization_score": 75,
                "insurance_coverage": False,
                "hack_history": [],
                "governance_token": "Unknown",
                "implementation": "unknown",
                "last_audit_date": "未知",
                "audit_firms": ["未知"],
                "vulnerabilities": [],
            },
        )

    def analyze_defi_protocol_risk(self, protocol_data: Dict) -> Dict:
        """分析DeFi协议风险"""
        try:
            protocol_name = protocol_data.get("name", "")

            # 从链上或API获取协议数据
            protocol = self._fetch_protocol_data(protocol_name)

            if not protocol:
                return self._get_basic_protocol_risk_analysis(protocol_name)

            # 构建风险分析提示
            prompt = f"""
分析以下DeFi协议的风险状况：

协议名称：{protocol_name}
基础数据：
- 总锁仓价值(TVL)：${protocol['tvl']:,}
- 日交易量：${protocol['daily_volume']:,}
- 审计评分：{protocol['audit_score']}/100
- 去中心化评分：{protocol['decentralization_score']}/100
- 保险覆盖：{'是' if protocol['insurance_coverage'] else '否'}
- 历史安全事件：{len(protocol['hack_history'])}次
- 治理代币：{protocol['governance_token']}
- 实现方式：{protocol['implementation']}
- 最近审计日期：{protocol['last_audit_date']}
- 审计公司：{', '.join(protocol['audit_firms'])}
- 已知漏洞：{len(protocol['vulnerabilities'])}个

请提供以下JSON格式的风险分析结果：
{
    "risk_score": 0-100之间的综合风险评分,
    "risk_level": "LOW/MEDIUM/HIGH",
    "security_score": 0-100的安全性评分,
    "liquidity_score": 0-100的流动性评分,
    "centralization_risk": "LOW/MEDIUM/HIGH",
    "audit_status": {
        "score": 0-100的审计评分,
        "last_audit_date": "最近审计日期",
        "audit_firms": ["审计公司列表"]
    },
    "risk_factors": [
        "主要风险因素1",
        "主要风险因素2",
        ...
    ],
    "recommendations": [
        "风险缓解建议1",
        "风险缓解建议2",
        ...
    ]
}

注意：
1. 综合考虑TVL、流动性、安全性等多个维度
2. 特别关注中心化风险和智能合约风险
3. 考虑历史安全记录和审计状况
4. 提供具体的风险缓解建议
"""

            if self.client is not None:
                # 调用OpenAI API
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个专业的DeFi风险分析师，擅长评估协议安全性、流动性和去中心化程度。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )

                # 解析响应
                analysis = json.loads(response.choices[0].message.content)

                # 添加基础数据
                analysis.update(
                    {
                        "protocol_name": protocol_name,
                        "tvl": protocol["tvl"],
                        "daily_volume": protocol["daily_volume"],
                        "audit_details": {
                            "last_audit_date": protocol["last_audit_date"],
                            "audit_firms": protocol["audit_firms"],
                            "vulnerabilities": protocol["vulnerabilities"],
                        },
                        "timestamp": datetime.now().isoformat(),
                        "data_source": (
                            "API"
                            if "tvl" in protocol and protocol["tvl"] > 0
                            else "Default"
                        ),
                    }
                )

                logger.info(f"成功分析 {protocol_name} 协议风险")
                return analysis
            else:
                return self._get_basic_protocol_risk_analysis(protocol_name)

        except Exception as e:
            logger.error(f"分析协议风险时出错: {e}")
            return self._get_basic_protocol_risk_analysis(protocol_name)

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
