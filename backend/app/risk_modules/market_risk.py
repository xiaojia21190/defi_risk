"""
市场风险分析模块 - 用于分析市场相关的风险
"""

from typing import Dict, List, Any, Optional
import logging
import asyncio
from app.models.domain.risk import RiskFactor, RiskType
from app.risk_modules.base import RiskAnalyzerBase


class MarketRiskAnalyzer(RiskAnalyzerBase):
    """市场风险分析器"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析市场风险

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        self.logger.info("开始分析市场风险")

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

        self.logger.info(f"市场风险分析完成: 评分={total_score}")

        return {
            "risk_score": total_score,
            "risk_factors": [f.__dict__ for f in risk_factors],
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
        }

    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取市场风险因子

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

        # 分析资产集中度风险
        concentration_risk = await self._analyze_concentration_risk(positions)
        if concentration_risk:
            risk_factors.append(concentration_risk)

        # 分析市场波动性风险
        volatility_risk = await self._analyze_volatility_risk(positions)
        if volatility_risk:
            risk_factors.append(volatility_risk)

        # 分析市场趋势风险
        trend_risk = await self._analyze_trend_risk(positions)
        if trend_risk:
            risk_factors.append(trend_risk)

        # 分析市场相关性风险
        correlation_risk = await self._analyze_correlation_risk(positions)
        if correlation_risk:
            risk_factors.append(correlation_risk)

        return risk_factors

    async def _analyze_concentration_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析资产集中度风险"""
        # 计算总价值
        total_value = sum(pos.get("amount", 0) for pos in positions)

        if total_value == 0:
            return None

        # 按资产分组
        assets = {}
        for pos in positions:
            asset = pos.get("asset", "unknown")
            if asset not in assets:
                assets[asset] = 0
            assets[asset] += pos.get("amount", 0)

        # 计算最大资产占比
        max_asset = max(assets.items(), key=lambda x: x[1])
        max_concentration = max_asset[1] / total_value

        # 根据集中度评分
        if max_concentration > 0.7:
            score = 80  # 高风险
            description = (
                f"投资组合过于集中在{max_asset[0]}，占比{max_concentration:.1%}"
            )
            trend = "上升"
        elif max_concentration > 0.5:
            score = 60  # 中高风险
            description = (
                f"投资组合在{max_asset[0]}上的集中度较高，占比{max_concentration:.1%}"
            )
            trend = "稳定"
        elif max_concentration > 0.3:
            score = 40  # 中等风险
            description = (
                f"投资组合在{max_asset[0]}上有一定集中度，占比{max_concentration:.1%}"
            )
            trend = "稳定"
        else:
            score = 20  # 低风险
            description = (
                f"投资组合分散良好，最大资产{max_asset[0]}占比{max_concentration:.1%}"
            )
            trend = "下降"

        return self.create_risk_factor(
            risk_type="MARKET",
            factor_name="资产集中度",
            score=score,
            weight=0.4,
            description=description,
            trend=trend,
            data_points=[
                {"asset": asset, "amount": amount, "percentage": amount / total_value}
                for asset, amount in assets.items()
            ],
        )

    async def _analyze_volatility_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析市场波动性风险"""
        # 这里应该调用AI预测器或区块链服务获取实际的波动性数据
        # 现在使用模拟数据

        # 假设我们有一个波动性评分（0-100）
        volatility_score = 50  # 中等波动性

        if volatility_score > 75:
            description = "市场波动性极高，可能面临大幅价格波动"
            trend = "上升"
        elif volatility_score > 50:
            description = "市场波动性较高，价格波动风险增加"
            trend = "上升"
        elif volatility_score > 25:
            description = "市场波动性中等，价格波动在可接受范围内"
            trend = "稳定"
        else:
            description = "市场波动性较低，价格相对稳定"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="MARKET",
            factor_name="市场波动性",
            score=volatility_score,
            weight=0.3,
            description=description,
            trend=trend,
            data_points=[{"volatility_score": volatility_score}],
        )

    async def _analyze_trend_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析市场趋势风险"""
        # 这里应该调用AI预测器获取市场趋势预测
        # 现在使用模拟数据

        # 假设我们有一个趋势评分（0-100，越高表示下跌趋势越强）
        trend_score = 40  # 轻微下跌趋势

        if trend_score > 75:
            description = "市场处于强烈下跌趋势，短期内可能继续下跌"
            trend = "上升"
        elif trend_score > 50:
            description = "市场处于下跌趋势，需要谨慎操作"
            trend = "上升"
        elif trend_score > 25:
            description = "市场趋势不明确，可能出现波动"
            trend = "稳定"
        else:
            description = "市场处于上升趋势，风险相对较低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="MARKET",
            factor_name="市场趋势",
            score=trend_score,
            weight=0.2,
            description=description,
            trend=trend,
            data_points=[{"trend_score": trend_score}],
        )

    async def _analyze_correlation_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析市场相关性风险"""
        # 这里应该分析投资组合中资产的相关性
        # 现在使用模拟数据

        # 假设我们有一个相关性评分（0-100，越高表示相关性越高，风险越大）
        correlation_score = 60  # 较高相关性

        if correlation_score > 75:
            description = "投资组合中资产高度相关，缺乏多样性保护"
            trend = "上升"
        elif correlation_score > 50:
            description = "投资组合中资产相关性较高，多样化效果有限"
            trend = "稳定"
        elif correlation_score > 25:
            description = "投资组合中资产相关性适中，有一定多样化效果"
            trend = "稳定"
        else:
            description = "投资组合中资产相关性低，多样化效果良好"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="MARKET",
            factor_name="资产相关性",
            score=correlation_score,
            weight=0.1,
            description=description,
            trend=trend,
            data_points=[{"correlation_score": correlation_score}],
        )

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取市场风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        # 根据风险因子生成建议
        for factor in risk_factors:
            if factor.id == "MARKET.资产集中度" and factor.score > 60:
                recommendations.append("考虑分散投资到更多不同的资产，降低单一资产风险")

            if factor.id == "MARKET.市场波动性" and factor.score > 60:
                recommendations.append(
                    "在高波动性市场中，考虑增加稳定币比例或使用对冲策略"
                )

            if factor.id == "MARKET.市场趋势" and factor.score > 60:
                recommendations.append("市场下跌趋势明显，考虑减少风险敞口或设置止损")

            if factor.id == "MARKET.资产相关性" and factor.score > 60:
                recommendations.append("增加低相关性资产，如不同类别或不同链上的资产")

        # 添加一般性建议
        if not recommendations:
            recommendations.append("定期检查市场状况，及时调整投资策略")

        return recommendations

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取市场风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        monitoring_points = []

        # 根据风险因子生成监控点
        for factor in risk_factors:
            if factor.id == "MARKET.资产集中度" and factor.score > 40:
                monitoring_points.append("监控主要资产的价格波动和市场消息")

            if factor.id == "MARKET.市场波动性" and factor.score > 40:
                monitoring_points.append(
                    "关注市场波动指标，如VIX或加密货币恐惧与贪婪指数"
                )

            if factor.id == "MARKET.市场趋势" and factor.score > 40:
                monitoring_points.append("跟踪主要技术指标，如移动平均线和RSI")

            if factor.id == "MARKET.资产相关性" and factor.score > 40:
                monitoring_points.append("定期评估投资组合的相关性矩阵")

        # 添加一般性监控点
        if not monitoring_points:
            monitoring_points.append("定期检查市场整体状况和宏观经济指标")

        return monitoring_points
