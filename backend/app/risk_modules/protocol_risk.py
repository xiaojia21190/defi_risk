"""
协议风险分析模块 - 用于分析DeFi协议相关的风险
"""

from typing import Dict, List, Any, Optional
import logging
from app.models.domain.risk import RiskFactor, RiskType
from app.risk_modules.base import RiskAnalyzerBase


class ProtocolRiskAnalyzer(RiskAnalyzerBase):
    """协议风险分析器"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析协议风险

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        self.logger.info("开始分析协议风险")

        # 获取风险因子
        risk_factors = await self.get_risk_factors(data)

        # 计算总体风险评分
        if not risk_factors:
            total_score = 0
        else:
            total_score = sum(f.score * f.weight for f in risk_factors) / sum(
                f.weight for f in risk_factors
            )

        # 获取建议
        recommendations = await self.get_recommendations(risk_factors)

        # 获取监控点
        monitoring_points = await self.get_monitoring_points(risk_factors)

        self.logger.info(f"协议风险分析完成: 评分={total_score}")

        return {
            "risk_score": total_score,
            "risk_factors": [f.__dict__ for f in risk_factors],
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
        }

    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取协议风险因子

        Args:
            data: 分析数据

        Returns:
            风险因子列表
        """
        risk_factors = []
        positions = data.get("positions", [])

        # 如果没有头寸，返回空列表
        if not positions:
            return []

        # 按协议分组
        protocols = {}
        for pos in positions:
            protocol = pos.get("protocol", "unknown")
            if protocol not in protocols:
                protocols[protocol] = []
            protocols[protocol].append(pos)

        # 分析每个协议的风险
        for protocol, protocol_positions in protocols.items():
            # 分析协议安全风险
            security_risk = await self._analyze_protocol_security(protocol)
            if security_risk:
                risk_factors.append(security_risk)

            # 分析协议治理风险
            governance_risk = await self._analyze_protocol_governance(protocol)
            if governance_risk:
                risk_factors.append(governance_risk)

            # 分析协议历史风险
            history_risk = await self._analyze_protocol_history(protocol)
            if history_risk:
                risk_factors.append(history_risk)

            # 分析协议复杂性风险
            complexity_risk = await self._analyze_protocol_complexity(protocol)
            if complexity_risk:
                risk_factors.append(complexity_risk)

        return risk_factors

    async def _analyze_protocol_security(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议安全风险"""
        # 这里应该调用区块链服务或AI预测器获取协议安全数据
        # 现在使用模拟数据

        # 协议安全评分映射（0-100，越高风险越大）
        security_scores = {
            "Aave": 20,  # 低风险
            "Compound": 25,  # 低风险
            "Uniswap": 30,  # 中低风险
            "SushiSwap": 40,  # 中等风险
            "Curve": 35,  # 中低风险
            "Yearn": 45,  # 中等风险
            "MakerDAO": 30,  # 中低风险
            "Balancer": 40,  # 中等风险
            "dYdX": 50,  # 中高风险
            "Synthetix": 55,  # 中高风险
            "PancakeSwap": 60,  # 中高风险
            "Unknown": 70,  # 高风险
        }

        # 获取协议安全评分
        protocol_key = next(
            (k for k in security_scores.keys() if k.lower() in protocol.lower()),
            "Unknown",
        )
        security_score = security_scores.get(protocol_key, 70)  # 默认高风险

        # 根据安全评分生成描述
        if security_score > 70:
            description = f"{protocol}协议安全风险极高，缺乏足够的安全审计"
            trend = "上升"
        elif security_score > 50:
            description = f"{protocol}协议存在一定安全风险，安全审计有限"
            trend = "稳定"
        elif security_score > 30:
            description = f"{protocol}协议安全性中等，已有一定安全审计"
            trend = "稳定"
        else:
            description = f"{protocol}协议安全性较高，已经过多次安全审计"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="PROTOCOL",
            factor_name="协议安全性",
            score=security_score,
            weight=0.4,
            description=description,
            trend=trend,
            data_points=[{"protocol": protocol, "security_score": security_score}],
        )

    async def _analyze_protocol_governance(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议治理风险"""
        # 这里应该调用区块链服务或AI预测器获取协议治理数据
        # 现在使用模拟数据

        # 协议治理评分映射（0-100，越高风险越大）
        governance_scores = {
            "Aave": 30,  # 中低风险
            "Compound": 25,  # 低风险
            "Uniswap": 40,  # 中等风险
            "SushiSwap": 50,  # 中高风险
            "Curve": 35,  # 中低风险
            "Yearn": 45,  # 中等风险
            "MakerDAO": 20,  # 低风险
            "Balancer": 40,  # 中等风险
            "dYdX": 55,  # 中高风险
            "Synthetix": 45,  # 中等风险
            "PancakeSwap": 60,  # 中高风险
            "Unknown": 70,  # 高风险
        }

        # 获取协议治理评分
        protocol_key = next(
            (k for k in governance_scores.keys() if k.lower() in protocol.lower()),
            "Unknown",
        )
        governance_score = governance_scores.get(protocol_key, 70)  # 默认高风险

        # 根据治理评分生成描述
        if governance_score > 70:
            description = f"{protocol}协议治理高度中心化，决策透明度低"
            trend = "上升"
        elif governance_score > 50:
            description = f"{protocol}协议治理相对中心化，决策透明度有限"
            trend = "稳定"
        elif governance_score > 30:
            description = f"{protocol}协议治理较为去中心化，决策透明度中等"
            trend = "稳定"
        else:
            description = f"{protocol}协议治理高度去中心化，决策透明度高"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="PROTOCOL",
            factor_name="协议治理",
            score=governance_score,
            weight=0.3,
            description=description,
            trend=trend,
            data_points=[{"protocol": protocol, "governance_score": governance_score}],
        )

    async def _analyze_protocol_history(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议历史风险"""
        # 这里应该调用区块链服务或AI预测器获取协议历史数据
        # 现在使用模拟数据

        # 协议历史评分映射（0-100，越高风险越大）
        history_scores = {
            "Aave": 20,  # 低风险
            "Compound": 25,  # 低风险
            "Uniswap": 30,  # 中低风险
            "SushiSwap": 50,  # 中高风险
            "Curve": 30,  # 中低风险
            "Yearn": 40,  # 中等风险
            "MakerDAO": 35,  # 中低风险
            "Balancer": 45,  # 中等风险
            "dYdX": 40,  # 中等风险
            "Synthetix": 50,  # 中高风险
            "PancakeSwap": 55,  # 中高风险
            "Unknown": 70,  # 高风险
        }

        # 获取协议历史评分
        protocol_key = next(
            (k for k in history_scores.keys() if k.lower() in protocol.lower()),
            "Unknown",
        )
        history_score = history_scores.get(protocol_key, 70)  # 默认高风险

        # 根据历史评分生成描述
        if history_score > 70:
            description = f"{protocol}协议历史上发生过多次安全事件，风险较高"
            trend = "上升"
        elif history_score > 50:
            description = f"{protocol}协议历史上发生过安全事件，需要关注"
            trend = "稳定"
        elif history_score > 30:
            description = f"{protocol}协议历史上发生过少量安全事件，但已修复"
            trend = "稳定"
        else:
            description = f"{protocol}协议历史上安全记录良好，未发生重大事件"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="PROTOCOL",
            factor_name="协议历史",
            score=history_score,
            weight=0.2,
            description=description,
            trend=trend,
            data_points=[{"protocol": protocol, "history_score": history_score}],
        )

    async def _analyze_protocol_complexity(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议复杂性风险"""
        # 这里应该调用区块链服务或AI预测器获取协议复杂性数据
        # 现在使用模拟数据

        # 协议复杂性评分映射（0-100，越高风险越大）
        complexity_scores = {
            "Aave": 40,  # 中等风险
            "Compound": 35,  # 中低风险
            "Uniswap": 30,  # 中低风险
            "SushiSwap": 35,  # 中低风险
            "Curve": 50,  # 中高风险
            "Yearn": 70,  # 高风险
            "MakerDAO": 60,  # 中高风险
            "Balancer": 55,  # 中高风险
            "dYdX": 65,  # 高风险
            "Synthetix": 75,  # 高风险
            "PancakeSwap": 40,  # 中等风险
            "Unknown": 60,  # 中高风险
        }

        # 获取协议复杂性评分
        protocol_key = next(
            (k for k in complexity_scores.keys() if k.lower() in protocol.lower()),
            "Unknown",
        )
        complexity_score = complexity_scores.get(protocol_key, 60)  # 默认中高风险

        # 根据复杂性评分生成描述
        if complexity_score > 70:
            description = f"{protocol}协议架构极其复杂，增加了潜在风险"
            trend = "上升"
        elif complexity_score > 50:
            description = f"{protocol}协议架构较为复杂，存在一定风险"
            trend = "稳定"
        elif complexity_score > 30:
            description = f"{protocol}协议架构复杂度中等，风险可控"
            trend = "稳定"
        else:
            description = f"{protocol}协议架构相对简单，风险较低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="PROTOCOL",
            factor_name="协议复杂性",
            score=complexity_score,
            weight=0.1,
            description=description,
            trend=trend,
            data_points=[{"protocol": protocol, "complexity_score": complexity_score}],
        )

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取协议风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        # 根据风险因子生成建议
        for factor in risk_factors:
            if factor.id == "PROTOCOL.协议安全性" and factor.score > 60:
                recommendations.append("考虑减少在安全性较低的协议中的投资比例")
                recommendations.append("关注协议的安全审计报告和更新")

            if factor.id == "PROTOCOL.协议治理" and factor.score > 60:
                recommendations.append("关注协议的治理提案和决策过程")
                recommendations.append("避免在治理高度中心化的协议中过度投资")

            if factor.id == "PROTOCOL.协议历史" and factor.score > 60:
                recommendations.append("研究协议的历史安全事件和解决方案")
                recommendations.append("考虑购买智能合约保险以降低风险")

            if factor.id == "PROTOCOL.协议复杂性" and factor.score > 60:
                recommendations.append("对复杂协议的投资保持谨慎，确保理解其运作机制")
                recommendations.append("分散投资到不同复杂度的协议中")

        # 添加一般性建议
        if not recommendations:
            recommendations.append("定期关注所使用协议的更新和安全公告")

        return recommendations

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取协议风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        monitoring_points = []

        # 根据风险因子生成监控点
        for factor in risk_factors:
            if factor.id == "PROTOCOL.协议安全性" and factor.score > 40:
                monitoring_points.append("关注协议的安全审计报告和漏洞披露")

            if factor.id == "PROTOCOL.协议治理" and factor.score > 40:
                monitoring_points.append("监控协议的治理提案和投票结果")

            if factor.id == "PROTOCOL.协议历史" and factor.score > 40:
                monitoring_points.append("跟踪协议的事件历史和解决方案")

            if factor.id == "PROTOCOL.协议复杂性" and factor.score > 40:
                monitoring_points.append("关注协议的技术更新和架构变化")

        # 添加一般性监控点
        if not monitoring_points:
            monitoring_points.append("定期检查协议的TVL和用户活跃度变化")

        return monitoring_points
