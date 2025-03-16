"""
风险建议服务 - 提供生成各类型风险建议的共享功能
"""

from typing import Dict, List, Any
import logging
from app.models.domain.risk import RiskFactor


class RecommendationService:
    """风险建议服务，为各风险分析器提供共享的建议生成功能"""

    def __init__(self):
        """初始化建议服务"""
        self.logger = logging.getLogger("defi_risk.RecommendationService")

    def get_market_risk_recommendations(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """
        生成市场风险建议

        Args:
            risk_factors: 市场风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        for factor in risk_factors:
            if factor.factor_name == "集中度风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合资产过于集中，建议大幅分散投资到更多不同的资产"
                    )
                    recommendations.append(
                        "设置单一资产最大持仓比例限制，建议不超过总资产的20%"
                    )
                elif factor.score > 50:
                    recommendations.append("投资组合资产集中度较高，建议适当分散投资")
                else:
                    recommendations.append(
                        "投资组合资产分散度良好，继续保持当前的多元化投资策略"
                    )

            elif factor.factor_name == "波动性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合波动性风险较高，建议增加稳定币比例或使用对冲策略"
                    )
                    recommendations.append("设置止损策略，限制单次下跌的最大损失")
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合波动性风险中等，建议关注市场波动指标"
                    )
                else:
                    recommendations.append(
                        "投资组合波动性风险较低，继续保持当前的风险管理策略"
                    )

            elif factor.factor_name == "趋势风险":
                if factor.score > 70:
                    recommendations.append(
                        "当前市场趋势对投资组合不利，建议适当降低风险敞口"
                    )
                elif factor.score > 50:
                    recommendations.append("关注市场趋势变化，准备调整投资策略")
                else:
                    recommendations.append("当前市场趋势相对有利，可以保持现有策略")

        # 如果没有生成建议，添加通用建议
        if not recommendations:
            recommendations.append("定期检查市场状况，及时调整投资策略")
            recommendations.append("构建多样化的投资组合，避免过度集中于单一资产")
            recommendations.append("关注宏观经济因素对加密货币市场的影响")

        return recommendations

    def get_liquidity_risk_recommendations(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """
        生成流动性风险建议

        Args:
            risk_factors: 流动性风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        for factor in risk_factors:
            if factor.factor_name == "资产流动性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合包含过多低流动性资产，建议增加高流动性资产比例"
                    )
                    recommendations.append(
                        "为低流动性资产设置较长的持有周期，避免被迫在不利市场条件下卖出"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "关注低流动性资产的市场深度变化，制定流动性应急计划"
                    )
                else:
                    recommendations.append(
                        "投资组合流动性状况良好，继续保持对市场流动性的关注"
                    )

            elif factor.factor_name == "协议流动性风险":
                if factor.score > 70:
                    recommendations.append(
                        "所选择的DeFi协议流动性风险较高，建议分散投资到多个协议"
                    )
                    recommendations.append(
                        "限制在单一协议中的投资比例，特别是流动性较低的协议"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "关注所用DeFi协议的TVL变化，及时调整投资策略"
                    )
                else:
                    recommendations.append(
                        "所使用的DeFi协议流动性状况良好，定期检查TVL变化"
                    )

        # 如果没有生成建议，添加通用建议
        if not recommendations:
            recommendations.append("保持足够的稳定币储备，以应对市场流动性紧缩情况")
            recommendations.append("优先选择流动性较高的交易市场和交易对")
            recommendations.append(
                "定期评估投资组合的流动性情况，确保能够及时应对市场变化"
            )

        return recommendations

    def get_protocol_risk_recommendations(
        self, risk_factors: List[RiskFactor], protocol_name: str
    ) -> List[str]:
        """
        生成协议风险建议

        Args:
            risk_factors: 协议风险因子列表
            protocol_name: 协议名称

        Returns:
            建议列表
        """
        recommendations = []

        for factor in risk_factors:
            if factor.factor_name == "协议安全风险":
                if factor.score > 70:
                    recommendations.append(
                        f"{protocol_name}的安全风险较高，建议限制投资金额或寻找替代方案"
                    )
                    recommendations.append(
                        f"考虑购买{protocol_name}的智能合约保险以对冲风险"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        f"关注{protocol_name}的安全审计报告和历史安全事件"
                    )
                else:
                    recommendations.append(
                        f"{protocol_name}具有良好的安全记录，继续关注其安全状况"
                    )

            elif factor.factor_name == "协议治理风险":
                if factor.score > 70:
                    recommendations.append(
                        f"{protocol_name}的治理风险较高，建议谨慎投资并密切关注治理决策"
                    )
                elif factor.score > 50:
                    recommendations.append(f"关注{protocol_name}的治理提案和决策流程")
                else:
                    recommendations.append(
                        f"{protocol_name}的治理机制健全，继续关注重要的治理更新"
                    )

        # 如果没有生成建议，添加通用建议
        if not recommendations:
            recommendations.append(f"定期关注{protocol_name}的最新动态和公告")
            recommendations.append(f"分散投资，避免将资金过度集中在{protocol_name}上")
            recommendations.append(f"了解{protocol_name}的基本运作机制和风险特点")

        return recommendations

    def get_smart_contract_risk_recommendations(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """
        生成智能合约风险建议

        Args:
            risk_factors: 智能合约风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        for factor in risk_factors:
            if factor.factor_name == "审计状态" and factor.score > 60:
                recommendations.append("优先选择经过多次安全审计的协议进行投资")
                recommendations.append("考虑购买智能合约保险以降低安全风险")

            elif factor.factor_name == "代码质量" and factor.score > 60:
                recommendations.append("关注协议的代码质量和开发团队的技术实力")
                recommendations.append("避免投资代码质量较差的新兴协议")

            elif factor.factor_name == "漏洞历史" and factor.score > 60:
                recommendations.append("研究协议的漏洞历史和安全事件处理能力")
                recommendations.append("减少在历史上多次出现漏洞的协议中的投资")

        # 添加一般性建议
        if not recommendations:
            recommendations.append("定期关注协议的安全审计报告和代码更新")
            recommendations.append("对于新兴协议，等待足够的运行时间和审计后再投资")

        return recommendations

    def get_correlation_risk_recommendations(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """
        生成相关性风险建议

        Args:
            risk_factors: 相关性风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        for factor in risk_factors:
            if factor.factor_name == "资产相关性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合中资产高度相关，建议大幅增加不同类型资产的配置"
                    )
                    recommendations.append(
                        "考虑添加与加密市场相关性较低的资产，如稳定币或跨行业代币"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合中资产相关性较高，建议适当增加不同类型资产"
                    )
                else:
                    recommendations.append(
                        "投资组合资产相关性适中或较低，继续保持多样化策略"
                    )

            elif factor.factor_name == "投资类型相关性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合中投资类型过于单一，建议增加不同投资类型的多样性"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "适当增加不同投资类型的资产，如收益型、增长型和储值型"
                    )
                else:
                    recommendations.append(
                        "投资组合的投资类型多样性良好，继续保持当前策略"
                    )

        # 如果没有生成建议，添加通用建议
        if not recommendations:
            recommendations.append(
                "定期评估投资组合中各资产间的相关性，及时调整高相关性资产"
            )
            recommendations.append(
                "在投资决策中考虑资产之间的相关性，构建更加平衡的投资组合"
            )

        return recommendations

    def get_monitoring_points(
        self, risk_type: str, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """
        根据风险类型和风险因子生成监控点

        Args:
            risk_type: 风险类型
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        monitoring_points = []

        # 根据风险类型生成监控点
        if risk_type == "MARKET":
            monitoring_points.extend(self._get_market_monitoring_points(risk_factors))
        elif risk_type == "LIQUIDITY":
            monitoring_points.extend(
                self._get_liquidity_monitoring_points(risk_factors)
            )
        elif risk_type == "PROTOCOL":
            monitoring_points.extend(self._get_protocol_monitoring_points(risk_factors))
        elif risk_type == "SMART_CONTRACT":
            monitoring_points.extend(
                self._get_smart_contract_monitoring_points(risk_factors)
            )
        elif risk_type == "CORRELATION":
            monitoring_points.extend(
                self._get_correlation_monitoring_points(risk_factors)
            )

        # 如果没有生成监控点，添加通用监控点
        if not monitoring_points:
            monitoring_points.append(f"定期评估{risk_type}风险变化")
            monitoring_points.append("设置关键风险指标的监控阈值")

        return monitoring_points

    def _get_market_monitoring_points(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """生成市场风险监控点"""
        points = []
        for factor in risk_factors:
            if factor.score > 60:
                if "集中度" in factor.factor_name:
                    points.append("监控投资组合中主要资产的占比变化")
                elif "波动性" in factor.factor_name:
                    points.append("监控市场波动性指标（如VIX）的变化")
                elif "趋势" in factor.factor_name:
                    points.append("监控市场趋势指标和移动平均线交叉")
        return points

    def _get_liquidity_monitoring_points(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """生成流动性风险监控点"""
        points = []
        for factor in risk_factors:
            if factor.score > 60:
                if "资产流动性" in factor.factor_name:
                    points.append("监控主要资产的交易量和滑点变化")
                elif "协议流动性" in factor.factor_name:
                    points.append("监控所使用DeFi协议的TVL变化趋势")
        return points

    def _get_protocol_monitoring_points(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """生成协议风险监控点"""
        points = []
        for factor in risk_factors:
            if factor.score > 60:
                if "安全" in factor.factor_name:
                    points.append("监控协议的安全审计报告和漏洞公告")
                elif "治理" in factor.factor_name:
                    points.append("监控协议的治理提案和社区投票情况")
        return points

    def _get_smart_contract_monitoring_points(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """生成智能合约风险监控点"""
        points = []
        for factor in risk_factors:
            if factor.score > 60:
                if "审计" in factor.factor_name:
                    points.append("监控协议的最新安全审计状态")
                elif "漏洞" in factor.factor_name:
                    points.append("关注协议在主要安全平台上的漏洞报告")
        return points

    def _get_correlation_monitoring_points(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """生成相关性风险监控点"""
        points = []
        for factor in risk_factors:
            if factor.score > 60:
                if "资产相关性" in factor.factor_name:
                    points.append("定期计算投资组合中主要资产对的相关系数")
                elif "投资类型" in factor.factor_name:
                    points.append("监控不同投资类型资产的收益相关性变化")
        return points
