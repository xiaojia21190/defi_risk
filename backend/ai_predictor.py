import numpy as np
import pandas as pd
from typing import List, Dict
from datetime import datetime, timedelta
import os
from openai import OpenAI


class AiPredictor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._market_alerts = {}  # 存储市场警报

    def get_market_alerts(self, address: str) -> List[Dict]:
        """获取市场警报"""
        # 清理过期警报
        self._clean_expired_alerts(address)
        return self._market_alerts.get(address, [])

    def _clean_expired_alerts(self, address: str):
        """清理过期警报"""
        if address not in self._market_alerts:
            return

        now = datetime.now()
        active_alerts = []

        for alert in self._market_alerts[address]:
            alert_time = datetime.fromisoformat(alert["timestamp"])
            # 保留12小时内的警报
            if now - alert_time < timedelta(hours=12):
                active_alerts.append(alert)

        self._market_alerts[address] = active_alerts

    def _add_market_alert(self, address: str, asset: str, analysis: Dict):
        """基于市场分析添加警报"""
        if address not in self._market_alerts:
            self._market_alerts[address] = []

        # 根据分析结果生成警报
        if analysis["risk_level"] == "HIGH":
            self._market_alerts[address].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "marketVolatility",
                    "severity": "high",
                    "message": f"{asset} 市场风险较高: {analysis['analysis_summary']}",
                    "protocol": "Market",
                    "asset": asset,
                }
            )
        elif (
            analysis.get("trend") == "bearish"
            and analysis.get("risk_level") == "MEDIUM"
        ):
            self._market_alerts[address].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "marketVolatility",
                    "severity": "medium",
                    "message": f"{asset} 呈现下跌趋势，建议关注",
                    "protocol": "Market",
                    "asset": asset,
                }
            )

    def analyze_market_trend(self, historical_data: pd.DataFrame, asset: str) -> Dict:
        """使用 OpenAI 分析市场趋势"""
        # 准备市场数据摘要
        prices = historical_data["price"].values
        volumes = historical_data["volume"].values
        current_price = prices[-1]
        price_change_24h = (prices[-1] - prices[-2]) / prices[-2] * 100
        price_change_7d = (prices[-1] - prices[-7]) / prices[-7] * 100
        avg_volume = np.mean(volumes[-7:])
        volatility = self.calculate_volatility(prices)

        # 构建 prompt
        prompt = f"""作为一个专业的 DeFi 和加密货币分析师，请基于以下市场数据分析 {asset} 的风险和投资机会：

市场数据：
- 当前价格: ${current_price:.2f}
- 24小时价格变化: {price_change_24h:.2f}%
- 7天价格变化: {price_change_7d:.2f}%
- 7天平均交易量: ${avg_volume:.2f}
- 年化波动率: {volatility*100:.2f}%

请从以下几个方面进行分析：
1. 市场趋势判断
2. 风险评估（高/中/低）
3. 具体风险因素
4. 投资建议
5. 需要注意的关键价格点位

请以 JSON 格式输出，包含以下字段：
{
    "trend": "bullish/bearish/neutral",
    "risk_level": "HIGH/MEDIUM/LOW",
    "risk_factors": ["风险因素1", "风险因素2", ...],
    "recommendations": ["建议1", "建议2", ...],
    "key_price_levels": {"support": [价格1, 价格2], "resistance": [价格1, 价格2]},
    "analysis_summary": "总体分析概述"
}"""

        # 调用 OpenAI API
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",  # 或其他适合的模型
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的 DeFi 和加密货币分析师，擅长市场分析和风险评估。",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            # 解析响应
            analysis = eval(response.choices[0].message.content)

            # 添加基础市场数据
            analysis.update(
                {
                    "asset": asset,
                    "current_price": current_price,
                    "predicted_price": current_price
                    * (1 + np.random.normal(0, 0.1)),  # 模拟预测价格
                    "price_change_prediction": price_change_24h,
                    "volatility": volatility,
                    "rsi": self.calculate_rsi(prices),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return analysis

        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            # 返回基础分析结果
            return {
                "asset": asset,
                "current_price": current_price,
                "predicted_price": current_price,
                "price_change_prediction": 0,
                "trend": "neutral",
                "risk_level": "MEDIUM",
                "risk_factors": ["API 调用失败，使用基础分析"],
                "recommendations": ["建议使用其他数据源验证"],
                "volatility": volatility,
                "rsi": 50,  # 默认值
                "timestamp": datetime.now().isoformat(),
            }

    def calculate_volatility(self, prices: List[float]) -> float:
        """计算价格波动率"""
        returns = np.diff(prices) / prices[:-1]
        return np.std(returns) * np.sqrt(252)  # 年化波动率

    def calculate_rsi(self, prices: List[float], periods: int = 14) -> float:
        """计算相对强弱指标 (RSI)"""
        deltas = np.diff(prices)
        gain = deltas.copy()
        loss = deltas.copy()

        gain[gain < 0] = 0
        loss[loss > 0] = 0
        loss = abs(loss)

        avg_gain = np.mean(gain[:periods])
        avg_loss = np.mean(loss[:periods])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def generate_trading_signals(
        self, analysis: Dict, position_size: float
    ) -> List[str]:
        """基于 OpenAI 分析生成交易信号"""
        signals = []

        # 使用 OpenAI 分析结果生成信号
        if "recommendations" in analysis:
            signals.extend(analysis["recommendations"])

        # 添加风险提醒
        if analysis.get("risk_level") == "HIGH":
            signals.append("⚠️ 当前风险等级较高，建议谨慎操作")

        # 添加关键价格点位信息
        if "key_price_levels" in analysis:
            levels = analysis["key_price_levels"]
            if "support" in levels and levels["support"]:
                signals.append(f"📊 最近支撑位: ${levels['support'][0]}")
            if "resistance" in levels and levels["resistance"]:
                signals.append(f"📊 最近阻力位: ${levels['resistance'][0]}")

        return signals

    def analyze_defi_protocol_risk(self, protocol_data: Dict) -> Dict:
        """分析 DeFi 协议特定风险"""
        prompt = f"""作为 DeFi 风险分析专家，请分析以下协议数据的风险：

协议数据：
- 协议名称: {protocol_data['name']}
- TVL: ${protocol_data['tvl']:,.2f}
- 用户头寸: ${protocol_data['position_size']:,.2f}
- 杠杆率: {protocol_data.get('leverage', 1)}x
- 清算阈值: {protocol_data.get('liquidation_threshold', 0)}%

请分析：
1. 清算风险
2. 协议风险
3. 市场风险
4. 建议操作

请以 JSON 格式输出分析结果。"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的 DeFi 风险分析师，专注于协议安全和风险管理。",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            return eval(response.choices[0].message.content)
        except Exception as e:
            print(f"Error analyzing protocol risk: {e}")
            return {
                "risk_level": "MEDIUM",
                "risks": ["无法获取详细分析"],
                "recommendations": ["建议手动评估风险"],
            }
