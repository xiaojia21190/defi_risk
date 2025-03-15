"""
流动性风险分析模块 - 用于分析DeFi投资组合的流动性风险
"""

from typing import Dict, List, Any, Optional
import logging
from app.models.domain.risk import RiskFactor, RiskType
from app.risk_modules.base import RiskAnalyzerBase


class LiquidityRiskAnalyzer(RiskAnalyzerBase):
    """流动性风险分析器"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析流动性风险

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        self.logger.info("开始分析流动性风险")

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

        self.logger.info(f"流动性风险分析完成: 评分={total_score}")

        return {
            "risk_score": total_score,
            "risk_factors": [f.__dict__ for f in risk_factors],
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
        }

    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取流动性风险因子

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

        # 分析资产流动性风险
        asset_liquidity_risk = await self._analyze_asset_liquidity(positions)
        if asset_liquidity_risk:
            risk_factors.append(asset_liquidity_risk)

        # 分析协议流动性风险
        protocol_liquidity_risk = await self._analyze_protocol_liquidity(positions)
        if protocol_liquidity_risk:
            risk_factors.append(protocol_liquidity_risk)

        # 分析投资类型流动性风险
        investment_type_liquidity_risk = await self._analyze_investment_type_liquidity(
            positions
        )
        if investment_type_liquidity_risk:
            risk_factors.append(investment_type_liquidity_risk)

        # 分析流动性池风险
        liquidity_pool_risk = await self._analyze_liquidity_pool_risk(positions)
        if liquidity_pool_risk:
            risk_factors.append(liquidity_pool_risk)

        return risk_factors

    async def _analyze_asset_liquidity(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析资产流动性风险"""
        # 这里应该调用区块链服务或AI预测器获取资产流动性数据
        # 现在使用模拟数据

        # 资产流动性评分映射（0-100，越高风险越大）
        liquidity_scores = {
            "ETH": 20,  # 低风险
            "BTC": 25,  # 低风险
            "USDC": 15,  # 低风险
            "USDT": 20,  # 低风险
            "DAI": 30,  # 中低风险
            "LINK": 40,  # 中等风险
            "UNI": 45,  # 中等风险
            "AAVE": 50,  # 中高风险
            "SNX": 60,  # 中高风险
            "YFI": 70,  # 高风险
            "Unknown": 80,  # 高风险
        }

        # 计算加权流动性风险评分
        total_value = sum(pos.get("amount", 0) for pos in positions)
        if total_value == 0:
            return None

        weighted_liquidity_score = 0
        assets_data = []

        for pos in positions:
            asset = pos.get("asset", "Unknown").split("/")[0]  # 处理流动性池资产格式
            amount = pos.get("amount", 0)

            # 获取资产流动性评分
            asset_key = next(
                (k for k in liquidity_scores.keys() if k.lower() == asset.lower()),
                "Unknown",
            )
            liquidity_score = liquidity_scores.get(asset_key, 80)  # 默认高风险

            # 计算加权评分
            weight = amount / total_value
            weighted_liquidity_score += liquidity_score * weight

            assets_data.append(
                {
                    "asset": asset,
                    "amount": amount,
                    "liquidity_score": liquidity_score,
                    "weight": weight,
                }
            )

        # 根据加权评分生成描述
        if weighted_liquidity_score > 70:
            description = "投资组合中包含大量低流动性资产，可能面临流动性风险"
            trend = "上升"
        elif weighted_liquidity_score > 50:
            description = "投资组合中包含一定比例的低流动性资产，流动性风险中等"
            trend = "稳定"
        elif weighted_liquidity_score > 30:
            description = "投资组合中大部分为高流动性资产，流动性风险较低"
            trend = "稳定"
        else:
            description = "投资组合中几乎全部为高流动性资产，流动性风险低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="LIQUIDITY",
            factor_name="资产流动性",
            score=weighted_liquidity_score,
            weight=0.4,
            description=description,
            trend=trend,
            data_points=assets_data,
        )

    async def _analyze_protocol_liquidity(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析协议流动性风险"""
        # 这里应该调用区块链服务或AI预测器获取协议流动性数据
        # 现在使用模拟数据

        # 协议流动性评分映射（0-100，越高风险越大）
        protocol_liquidity_scores = {
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
            "PancakeSwap": 45,  # 中等风险
            "Unknown": 70,  # 高风险
        }

        # 计算加权协议流动性风险评分
        total_value = sum(pos.get("amount", 0) for pos in positions)
        if total_value == 0:
            return None

        weighted_protocol_liquidity_score = 0
        protocols_data = []

        # 按协议分组
        protocol_values = {}
        for pos in positions:
            protocol = pos.get("protocol", "Unknown")
            amount = pos.get("amount", 0)

            if protocol not in protocol_values:
                protocol_values[protocol] = 0
            protocol_values[protocol] += amount

        for protocol, amount in protocol_values.items():
            # 获取协议流动性评分
            protocol_key = next(
                (
                    k
                    for k in protocol_liquidity_scores.keys()
                    if k.lower() in protocol.lower()
                ),
                "Unknown",
            )
            liquidity_score = protocol_liquidity_scores.get(
                protocol_key, 70
            )  # 默认高风险

            # 计算加权评分
            weight = amount / total_value
            weighted_protocol_liquidity_score += liquidity_score * weight

            protocols_data.append(
                {
                    "protocol": protocol,
                    "amount": amount,
                    "liquidity_score": liquidity_score,
                    "weight": weight,
                }
            )

        # 根据加权评分生成描述
        if weighted_protocol_liquidity_score > 70:
            description = "投资组合中使用的协议流动性风险较高"
            trend = "上升"
        elif weighted_protocol_liquidity_score > 50:
            description = "投资组合中使用的协议流动性风险中等"
            trend = "稳定"
        elif weighted_protocol_liquidity_score > 30:
            description = "投资组合中使用的协议流动性风险较低"
            trend = "稳定"
        else:
            description = "投资组合中使用的协议流动性风险低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="LIQUIDITY",
            factor_name="协议流动性",
            score=weighted_protocol_liquidity_score,
            weight=0.3,
            description=description,
            trend=trend,
            data_points=protocols_data,
        )

    async def _analyze_investment_type_liquidity(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析投资类型流动性风险"""
        # 这里应该调用区块链服务或AI预测器获取投资类型流动性数据
        # 现在使用模拟数据

        # 投资类型流动性评分映射（0-100，越高风险越大）
        investment_type_liquidity_scores = {
            1: 20,  # 存币 - 低风险
            2: 50,  # 流动性池 - 中高风险
            3: 60,  # 挖矿 - 中高风险
            4: 70,  # 机枪池 - 高风险
            5: 40,  # 质押 - 中等风险
            6: 30,  # 借贷 - 中低风险
            0: 60,  # 未知 - 中高风险
        }

        # 计算加权投资类型流动性风险评分
        total_value = sum(pos.get("amount", 0) for pos in positions)
        if total_value == 0:
            return None

        weighted_investment_type_liquidity_score = 0
        investment_types_data = []

        # 按投资类型分组
        investment_type_values = {}
        for pos in positions:
            invest_type = pos.get("invest_type", 0)
            invest_type_name = pos.get("invest_type_name", "未知类型")
            amount = pos.get("amount", 0)

            if invest_type not in investment_type_values:
                investment_type_values[invest_type] = {
                    "amount": 0,
                    "name": invest_type_name,
                }
            investment_type_values[invest_type]["amount"] += amount

        for invest_type, data in investment_type_values.items():
            amount = data["amount"]
            name = data["name"]

            # 获取投资类型流动性评分
            liquidity_score = investment_type_liquidity_scores.get(
                invest_type, 60
            )  # 默认中高风险

            # 计算加权评分
            weight = amount / total_value
            weighted_investment_type_liquidity_score += liquidity_score * weight

            investment_types_data.append(
                {
                    "invest_type": invest_type,
                    "name": name,
                    "amount": amount,
                    "liquidity_score": liquidity_score,
                    "weight": weight,
                }
            )

        # 根据加权评分生成描述
        if weighted_investment_type_liquidity_score > 70:
            description = "投资组合中包含大量低流动性投资类型，流动性风险高"
            trend = "上升"
        elif weighted_investment_type_liquidity_score > 50:
            description = "投资组合中包含一定比例的低流动性投资类型，流动性风险中等"
            trend = "稳定"
        elif weighted_investment_type_liquidity_score > 30:
            description = "投资组合中大部分为高流动性投资类型，流动性风险较低"
            trend = "稳定"
        else:
            description = "投资组合中几乎全部为高流动性投资类型，流动性风险低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="LIQUIDITY",
            factor_name="投资类型流动性",
            score=weighted_investment_type_liquidity_score,
            weight=0.2,
            description=description,
            trend=trend,
            data_points=investment_types_data,
        )

    async def _analyze_liquidity_pool_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析流动性池风险"""
        # 筛选出流动性池头寸
        lp_positions = [
            pos
            for pos in positions
            if pos.get("invest_type") == 2
            or "流动性池" in pos.get("invest_type_name", "")
        ]

        if not lp_positions:
            return None

        # 计算流动性池在总投资中的占比
        total_value = sum(pos.get("amount", 0) for pos in positions)
        lp_value = sum(pos.get("amount", 0) for pos in lp_positions)

        if total_value == 0:
            return None

        lp_ratio = lp_value / total_value

        # 根据流动性池占比评估风险
        if lp_ratio > 0.7:
            score = 80  # 高风险
            description = (
                f"流动性池投资占比过高({lp_ratio:.1%})，面临无常损失和流动性风险"
            )
            trend = "上升"
        elif lp_ratio > 0.5:
            score = 60  # 中高风险
            description = f"流动性池投资占比较高({lp_ratio:.1%})，存在一定无常损失风险"
            trend = "稳定"
        elif lp_ratio > 0.3:
            score = 40  # 中等风险
            description = f"流动性池投资占比适中({lp_ratio:.1%})，无常损失风险可控"
            trend = "稳定"
        else:
            score = 20  # 低风险
            description = f"流动性池投资占比较低({lp_ratio:.1%})，无常损失风险较小"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="LIQUIDITY",
            factor_name="流动性池风险",
            score=score,
            weight=0.1,
            description=description,
            trend=trend,
            data_points=[
                {
                    "lp_value": lp_value,
                    "total_value": total_value,
                    "lp_ratio": lp_ratio,
                    "lp_positions": len(lp_positions),
                }
            ],
        )

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取流动性风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        # 根据风险因子生成建议
        for factor in risk_factors:
            if factor.id == "LIQUIDITY.资产流动性" and factor.score > 60:
                recommendations.append("考虑增加高流动性资产的比例，如主流代币和稳定币")
                recommendations.append("避免过度投资于小市值、低交易量的代币")

            if factor.id == "LIQUIDITY.协议流动性" and factor.score > 60:
                recommendations.append("减少在流动性较低的协议中的投资比例")
                recommendations.append("关注所使用协议的TVL变化趋势")

            if factor.id == "LIQUIDITY.投资类型流动性" and factor.score > 60:
                recommendations.append("增加高流动性投资类型的比例，如存币和借贷")
                recommendations.append("减少锁仓期长的投资，如长期质押和某些挖矿项目")

            if factor.id == "LIQUIDITY.流动性池风险" and factor.score > 60:
                recommendations.append(
                    "降低流动性池投资的总体比例，特别是波动性大的代币对"
                )
                recommendations.append("选择交易量大、深度好的流动性池进行投资")

        # 添加一般性建议
        if not recommendations:
            recommendations.append(
                "定期评估投资组合的流动性状况，确保在需要时能够快速退出"
            )

        return recommendations

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取流动性风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        monitoring_points = []

        # 根据风险因子生成监控点
        for factor in risk_factors:
            if factor.id == "LIQUIDITY.资产流动性" and factor.score > 40:
                monitoring_points.append("监控低流动性资产的交易量和价格波动")

            if factor.id == "LIQUIDITY.协议流动性" and factor.score > 40:
                monitoring_points.append("关注协议的TVL变化和用户活跃度")

            if factor.id == "LIQUIDITY.投资类型流动性" and factor.score > 40:
                monitoring_points.append("跟踪各类投资的锁仓期和提取条件变化")

            if factor.id == "LIQUIDITY.流动性池风险" and factor.score > 40:
                monitoring_points.append("监控流动性池的深度和无常损失情况")

        # 添加一般性监控点
        if not monitoring_points:
            monitoring_points.append("定期检查市场整体流动性状况和极端情况下的退出成本")

        return monitoring_points
