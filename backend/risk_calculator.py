from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

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

    def calculate_market_volatility_risk(self, position: Position) -> float:
        """
        计算市场波动风险
        返回0-1之间的风险值，0表示最低风险，1表示最高风险
        """
        try:
            # 这里可以接入实际的市场数据API来获取真实的波动率数据
            # 目前使用模拟数据
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
        self, positions: List[Position], volatility_risk: float
    ) -> List[str]:
        """根据风险评估生成建议"""
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

        # 根据波动性风险提供建议
        if volatility_risk > 0.7:
            recommendations.append("当前市场波动较大，建议增加稳定币比例")
        elif volatility_risk < 0.3:
            recommendations.append("当前市场稳定，可以考虑适当增加收益率较高的资产配置")

            return recommendations

    def assess_portfolio_risk(self, positions: List[Position]) -> Dict:
        """评估整个投资组合的风险"""
        try:
            if not positions:
                return {
                    "risk_level": self.RISK_LEVELS["LOW"],
                    "volatility_risk": 0.0,
                    "recommendations": ["未发现任何DeFi存款"],
                }

            # 计算每个头寸的波动性风险
            position_risks = [
                (pos, self.calculate_market_volatility_risk(pos)) for pos in positions
            ]

            # 计算加权平均风险
            total_value = sum(pos.amount for pos in positions)
            weighted_risk = sum(
                risk * pos.amount / total_value for pos, risk in position_risks
            )

            # 确定风险等级
            risk_level = self.RISK_LEVELS["LOW"]
            if weighted_risk > 0.7:
                risk_level = self.RISK_LEVELS["HIGH"]
            elif weighted_risk > 0.3:
                risk_level = self.RISK_LEVELS["MEDIUM"]

            # 生成建议
            recommendations = self.generate_recommendations(positions, weighted_risk)

            return {
                "risk_level": risk_level,
                "volatility_risk": weighted_risk,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"评估投资组合风险时出错: {e}")
            return {
                "risk_level": self.RISK_LEVELS["MEDIUM"],
                "volatility_risk": 0.5,
                "recommendations": ["风险评估过程中出现错误，建议手动检查存款状态"],
            }
