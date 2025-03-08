from typing import List, Dict, Optional
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Position:
    protocol: str
    asset: str
    amount: float
    leverage: Optional[float] = None
    apy: Optional[float] = None

@dataclass
class RiskAssessment:
    risk_level: str
    liquidation_risk: float
    impermanent_loss_risk: float
    market_volatility_risk: float
    recommendations: List[str]

class RiskCalculator:
    def __init__(self):
        # 风险阈值配置
        self.liquidation_threshold = 0.8  # 80% 的抵押率作为清算风险阈值
        self.high_volatility_threshold = 0.5  # 50% 的价格波动作为高波动性阈值
        self.il_threshold = 0.1  # 10% 的价格变化作为无常损失风险阈值

        # 警报存储
        self._alerts = {}  # 用于存储每个地址的活跃警报

    def get_active_alerts(self, address: str) -> List[Dict]:
        """获取地址的活跃警报"""
        # 清理过期警报
        self._clean_expired_alerts(address)

        # 返回活跃警报
        return self._alerts.get(address, [])

    def _clean_expired_alerts(self, address: str):
        """清理过期警报"""
        if address not in self._alerts:
            return

        now = datetime.now()
        active_alerts = []

        for alert in self._alerts[address]:
            alert_time = datetime.fromisoformat(alert["timestamp"])
            # 保留24小时内的警报
            if now - alert_time < timedelta(hours=24):
                active_alerts.append(alert)

        self._alerts[address] = active_alerts

    def _add_alert(self, address: str, alert_type: str, severity: str, message: str,
                  protocol: str, asset: str):
        """添加新警报"""
        if address not in self._alerts:
            self._alerts[address] = []

        self._alerts[address].append({
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "severity": severity,
            "message": message,
            "protocol": protocol,
            "asset": asset
        })

    def calculate_liquidation_risk(self, position: Position) -> float:
        """计算清算风险"""
        if not position.leverage:
            return 0.0

        # 简化的清算风险计算
        # 风险随着杠杆率的增加而增加
        base_risk = (position.leverage - 1) / 5  # 假设最高杠杆为 6x
        return min(max(base_risk, 0), 1)

    def calculate_impermanent_loss_risk(self, position: Position) -> float:
        """计算无常损失风险"""
        if position.protocol != "Uniswap":  # 仅对 Uniswap 等 AMM 计算无常损失风险
            return 0.0

        # 简化的无常损失风险计算
        # 这里应该基于历史价格数据和流动性池组成计算
        # 当前使用模拟数据
        mock_price_change = 0.2  # 20% 的价格变化
        il = (2 * np.sqrt(1 + mock_price_change) / (2 + mock_price_change)) - 1
        return abs(il)

    def calculate_market_volatility_risk(self, position: Position) -> float:
        """计算市场波动风险"""
        # 简化的市场波动风险计算
        # 这里应该使用实际的市场数据和波动率
        # 当前使用模拟数据
        mock_volatility = {
            "ETH": 0.4,
            "BTC": 0.35,
            "USDC": 0.01,
            "DAI": 0.01,
        }
        return mock_volatility.get(position.asset, 0.2)

    def generate_recommendations(self,
                              position: Position,
                              liquidation_risk: float,
                              il_risk: float,
                              volatility_risk: float) -> List[str]:
        """生成风险缓解建议"""
        recommendations = []

        if liquidation_risk > 0.7:
            recommendations.append(f"建议降低 {position.asset} 的杠杆率以避免清算风险")
            # 添加高风险清算警报
            self._add_alert(
                address=position.protocol,  # 使用协议地址作为标识
                alert_type="liquidation",
                severity="high",
                message=f"{position.asset} 存在高清算风险，建议立即降低杠杆率",
                protocol=position.protocol,
                asset=position.asset
            )
        elif liquidation_risk > 0.5:
            recommendations.append(f"注意监控 {position.asset} 的清算阈值")
            # 添加中等风险清算警报
            self._add_alert(
                address=position.protocol,
                alert_type="liquidation",
                severity="medium",
                message=f"{position.asset} 接近清算阈值，请注意监控",
                protocol=position.protocol,
                asset=position.asset
            )

        if il_risk > 0.15:
            recommendations.append(f"考虑调整 {position.protocol} 流动性池的配置以减少无常损失风险")
            # 添加无常损失警报
            self._add_alert(
                address=position.protocol,
                alert_type="impermanentLoss",
                severity="high" if il_risk > 0.2 else "medium",
                message=f"{position.asset} 流动性池存在较高无常损失风险",
                protocol=position.protocol,
                asset=position.asset
            )

        if volatility_risk > 0.4:
            recommendations.append(f"当前 {position.asset} 市场波动较大，建议设置止损")
            # 添加市场波动警报
            self._add_alert(
                address=position.protocol,
                alert_type="marketVolatility",
                severity="high",
                message=f"{position.asset} 市场波动剧烈，建议注意风险",
                protocol=position.protocol,
                asset=position.asset
            )

        return recommendations

    def assess_position_risk(self, position: Position) -> RiskAssessment:
        """评估单个头寸的风险"""
        liquidation_risk = self.calculate_liquidation_risk(position)
        il_risk = self.calculate_impermanent_loss_risk(position)
        volatility_risk = self.calculate_market_volatility_risk(position)

        # 综合风险评分
        total_risk = (liquidation_risk * 0.4 +
                     il_risk * 0.3 +
                     volatility_risk * 0.3)

        # 风险等级判定
        if total_risk < 0.3:
            risk_level = "LOW"
        elif total_risk < 0.7:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        recommendations = self.generate_recommendations(
            position, liquidation_risk, il_risk, volatility_risk
        )

        return RiskAssessment(
            risk_level=risk_level,
            liquidation_risk=liquidation_risk,
            impermanent_loss_risk=il_risk,
            market_volatility_risk=volatility_risk,
            recommendations=recommendations
        )

    def assess_portfolio_risk(self, positions: List[Position]) -> Dict:
        """评估整个投资组合的风险"""
        position_assessments = []
        total_risk = 0
        total_value = 0

        for position in positions:
            assessment = self.assess_position_risk(position)
            position_assessments.append({
                "position": position,
                "assessment": assessment
            })

            # 按金额加权计算总风险
            position_weight = position.amount / sum(p.amount for p in positions)
            if assessment.risk_level == "HIGH":
                total_risk += 0.8 * position_weight
            elif assessment.risk_level == "MEDIUM":
                total_risk += 0.5 * position_weight
            else:
                total_risk += 0.2 * position_weight

            total_value += position.amount

        return {
            "total_risk": total_risk,
            "total_value": total_value,
            "position_assessments": position_assessments,
            "timestamp": datetime.now().isoformat()
        }
