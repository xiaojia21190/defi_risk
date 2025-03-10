from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import pandas as pd
from ai_predictor import AiPredictor

logger = logging.getLogger("defi_risk.calculator")


@dataclass
class Position:
    protocol: str
    asset: str
    amount: float
    apy: Optional[float] = None


class RiskCalculator:
    def __init__(self):
        # 风险阈值配置
        self.high_volatility_threshold = 0.5  # 50% 的价格波动作为高波动性阈值

        # 风险等级定义
        self.RISK_LEVELS = {"LOW": "低风险", "MEDIUM": "中等风险", "HIGH": "高风险"}

        # 初始化AI预测器
        self.ai_predictor = AiPredictor()

        # 缓存分析结果
        self.market_analysis_cache = {}

    def calculate_market_volatility_risk(
        self, position: Position, historical_data: Optional[pd.DataFrame] = None
    ) -> float:
        """
        计算市场波动风险
        返回0-1之间的风险值，0表示最低风险，1表示最高风险

        如果提供了历史数据，则使用AI预测器进行更准确的风险评估
        """
        try:
            # 如果有历史数据，使用AI预测器进行分析
            if historical_data is not None and not historical_data.empty:
                # 检查缓存中是否已有分析结果
                if position.asset in self.market_analysis_cache:
                    market_analysis = self.market_analysis_cache[position.asset]
                else:
                    # 使用AI预测器分析市场趋势
                    market_analysis = self.ai_predictor.analyze_market_trend(
                        historical_data, position.asset
                    )
                    # 缓存分析结果
                    self.market_analysis_cache[position.asset] = market_analysis

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
                "WBTC": 0.5,
                "USDT": 0.01,
            }

            base_volatility = volatility_map.get(position.asset, 0.3)
            return min(base_volatility, 1.0)

        except Exception as e:
            logger.error(f"计算市场波动风险时出错: {e}")
            return 0.5

    def generate_recommendations(
        self,
        positions: List[Position],
        volatility_risk: float,
        historical_data_map: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> List[str]:
        """根据风险评估生成建议，可选择使用AI增强的建议"""
        recommendations = []

        # 分析存款分布
        total_value = sum(p.amount for p in positions)
        protocol_exposure = {}
        asset_exposure = {}

        for pos in positions:
            protocol_exposure[pos.protocol] = (
                protocol_exposure.get(pos.protocol, 0) + pos.amount
            )
            asset_exposure[pos.asset] = asset_exposure.get(pos.asset, 0) + pos.amount

        # 检查协议集中度
        for protocol, amount in protocol_exposure.items():
            if amount / total_value > 0.5:  # 如果单个协议占比超过50%
                recommendations.append(
                    f"建议分散 {protocol} 协议的存款，降低单一协议风险"
                )

        # 检查资产集中度
        for asset, amount in asset_exposure.items():
            if amount / total_value > 0.4:  # 如果单个资产占比超过40%
                recommendations.append(f"建议分散 {asset} 资产的存款配置")

                # 如果有历史数据，使用AI分析该资产的市场趋势
                if historical_data_map and asset in historical_data_map:
                    market_analysis = self.ai_predictor.analyze_market_trend(
                        historical_data_map[asset], asset
                    )

                    # 根据AI分析结果提供更具体的建议
                    if market_analysis:
                        if "trend" in market_analysis:
                            trend = market_analysis["trend"]
                            if trend == "bearish":
                                recommendations.append(
                                    f"{asset}当前处于下跌趋势，建议减少持仓或设置止损"
                                )
                            elif trend == "bullish":
                                recommendations.append(
                                    f"{asset}当前处于上涨趋势，可以考虑持有或适量增加"
                                )

                        # 添加AI推荐的交易信号
                        if (
                            "trading_signals" in market_analysis
                            and market_analysis["trading_signals"]
                        ):
                            for signal in market_analysis["trading_signals"][
                                :2
                            ]:  # 只取前两个信号
                                recommendations.append(f"{asset}交易信号: {signal}")

        # 根据波动性风险提供建议
        if volatility_risk > 0.7:
            recommendations.append("当前市场波动较大，建议增加稳定币比例")
        elif volatility_risk < 0.3:
            recommendations.append("当前市场稳定，可以考虑适当增加收益率较高的资产配置")

        return recommendations

    def assess_portfolio_risk(
        self,
        positions: List[Position],
        historical_data_map: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> Dict:
        """评估整个投资组合的风险，可选择使用AI增强的风险评估"""
        try:
            if not positions:
                return {
                    "risk_level": self.RISK_LEVELS["LOW"],
                    "volatility_risk": 0.0,
                    "recommendations": ["未发现任何DeFi存款"],
                }

            # 计算每个头寸的市场波动性风险
            position_market_risks = []
            for pos in positions:
                historical_data = (
                    historical_data_map.get(pos.asset) if historical_data_map else None
                )
                risk = self.calculate_market_volatility_risk(pos, historical_data)
                position_market_risks.append((pos, risk))

            # 计算加权平均风险
            total_value = sum(pos.amount for pos in positions)

            # 市场波动性风险
            weighted_market_risk = sum(
                risk * pos.amount / total_value for pos, risk in position_market_risks
            )

            # 确定风险等级
            risk_level = self.RISK_LEVELS["LOW"]
            if weighted_market_risk > 0.7:
                risk_level = self.RISK_LEVELS["HIGH"]
            elif weighted_market_risk > 0.3:
                risk_level = self.RISK_LEVELS["MEDIUM"]

            # 生成建议
            recommendations = self.generate_recommendations(
                positions, weighted_market_risk, historical_data_map
            )

            # 添加AI分析的详细风险信息
            detailed_risks = []
            for pos in positions:
                if pos.amount / total_value > 0.1:  # 只分析占比超过10%的资产
                    # 获取市场分析
                    if historical_data_map and pos.asset in historical_data_map:
                        market_analysis = self.ai_predictor.analyze_market_trend(
                            historical_data_map[pos.asset], pos.asset
                        )
                        if market_analysis and "analysis_summary" in market_analysis:
                            detailed_risks.append(
                                f"{pos.asset}市场分析: {market_analysis['analysis_summary']}"
                            )

            return {
                "risk_level": risk_level,
                "volatility_risk": weighted_market_risk,
                "recommendations": recommendations,
                "detailed_risks": detailed_risks,
            }

        except Exception as e:
            logger.error(f"评估投资组合风险时出错: {e}")
            return {
                "risk_level": self.RISK_LEVELS["MEDIUM"],
                "volatility_risk": 0.5,
                "recommendations": ["风险评估过程中出现错误，建议手动检查存款状态"],
                "detailed_risks": [],
            }
