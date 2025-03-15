"""
相关性风险分析模块 - 用于分析DeFi投资组合的资产相关性风险
"""

from typing import Dict, List, Any, Optional
import logging
import numpy as np
from app.models.domain.risk import RiskFactor, RiskType
from app.risk_modules.base import RiskAnalyzerBase


class CorrelationRiskAnalyzer(RiskAnalyzerBase):
    """相关性风险分析器"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析相关性风险

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        self.logger.info("开始分析相关性风险")

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

        self.logger.info(f"相关性风险分析完成: 评分={total_score}")

        return {
            "risk_score": total_score,
            "risk_factors": [f.__dict__ for f in risk_factors],
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
        }

    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取相关性风险因子

        Args:
            data: 分析数据

        Returns:
            风险因子列表
        """
        risk_factors = []
        positions = data.get("positions", [])

        # 如果没有头寸或只有一个头寸，返回空列表
        if not positions or len(positions) < 2:
            return []

        # 分析资产相关性风险
        asset_correlation_risk = await self._analyze_asset_correlation(positions)
        if asset_correlation_risk:
            risk_factors.append(asset_correlation_risk)

        # 分析协议相关性风险
        protocol_correlation_risk = await self._analyze_protocol_correlation(positions)
        if protocol_correlation_risk:
            risk_factors.append(protocol_correlation_risk)

        # 分析投资类型相关性风险
        investment_type_correlation_risk = (
            await self._analyze_investment_type_correlation(positions)
        )
        if investment_type_correlation_risk:
            risk_factors.append(investment_type_correlation_risk)

        return risk_factors

    async def _analyze_asset_correlation(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析资产相关性风险"""
        # 提取资产列表
        assets = []
        for pos in positions:
            asset = pos.get("asset", "Unknown").split("/")[0]  # 处理流动性池资产格式
            if asset not in assets:
                assets.append(asset)

        # 如果资产数量少于2，无法计算相关性
        if len(assets) < 2:
            return None

        # 计算资产相关性矩阵
        correlation_matrix = {}
        for i, asset1 in enumerate(assets):
            correlation_matrix[asset1] = {}
            for asset2 in assets[i:]:
                # 这里应该调用AI预测器或区块链服务获取实际的相关性数据
                # 现在使用模拟数据
                correlation = self._estimate_asset_correlation(asset1, asset2)
                correlation_matrix[asset1][asset2] = correlation
                if asset1 != asset2:
                    if asset2 not in correlation_matrix:
                        correlation_matrix[asset2] = {}
                    correlation_matrix[asset2][asset1] = correlation

        # 计算平均相关性
        total_correlation = 0
        count = 0
        for asset1 in correlation_matrix:
            for asset2 in correlation_matrix[asset1]:
                if asset1 != asset2:
                    total_correlation += correlation_matrix[asset1][asset2]
                    count += 1

        if count == 0:
            return None

        average_correlation = total_correlation / count

        # 根据平均相关性评估风险
        if average_correlation > 0.8:
            score = 80  # 高风险
            description = "投资组合中资产高度相关，缺乏多样化保护"
            trend = "上升"
        elif average_correlation > 0.6:
            score = 60  # 中高风险
            description = "投资组合中资产相关性较高，多样化效果有限"
            trend = "稳定"
        elif average_correlation > 0.4:
            score = 40  # 中等风险
            description = "投资组合中资产相关性适中，有一定多样化效果"
            trend = "稳定"
        else:
            score = 20  # 低风险
            description = "投资组合中资产相关性低，多样化效果良好"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="CORRELATION",
            factor_name="资产相关性",
            score=score,
            weight=0.5,
            description=description,
            trend=trend,
            data_points=[
                {
                    "average_correlation": average_correlation,
                    "correlation_matrix": correlation_matrix,
                }
            ],
        )

    def _estimate_asset_correlation(self, asset1: str, asset2: str) -> float:
        """估计两个资产之间的相关性"""
        # 这里应该调用AI预测器或区块链服务获取实际的相关性数据
        # 现在使用模拟数据

        # 检查是否为稳定币
        if self._is_stablecoin(asset1) and self._is_stablecoin(asset2):
            return 0.95  # 稳定币之间高度相关

        # 预定义的相关性数据
        correlations = {
            ("ETH", "BTC"): 0.75,
            ("ETH", "LINK"): 0.65,
            ("ETH", "UNI"): 0.60,
            ("ETH", "AAVE"): 0.55,
            ("BTC", "LINK"): 0.50,
            ("BTC", "UNI"): 0.45,
            ("BTC", "AAVE"): 0.40,
            ("LINK", "UNI"): 0.70,
            ("LINK", "AAVE"): 0.65,
            ("UNI", "AAVE"): 0.75,
        }

        # 标准化资产名称
        asset1 = asset1.upper()
        asset2 = asset2.upper()

        # 查找相关性
        key = (asset1, asset2) if asset1 < asset2 else (asset2, asset1)
        if key in correlations:
            return correlations[key]

        # 默认中等相关性
        return 0.5

    def _is_stablecoin(self, asset: str) -> bool:
        """检查资产是否为稳定币"""
        stablecoins = [
            "USDT",
            "USDC",
            "DAI",
            "BUSD",
            "TUSD",
            "USDP",
            "GUSD",
            "USDN",
            "HUSD",
            "SUSD",
        ]
        return asset.upper() in stablecoins

    async def _analyze_protocol_correlation(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析协议相关性风险"""
        # 按协议分组
        protocols = {}
        for pos in positions:
            protocol = pos.get("protocol", "Unknown")
            if protocol not in protocols:
                protocols[protocol] = 0
            protocols[protocol] += pos.get("amount", 0)

        # 如果协议数量少于2，无法计算相关性
        if len(protocols) < 2:
            return None

        # 计算协议集中度
        total_value = sum(protocols.values())
        if total_value == 0:
            return None

        # 计算赫芬达尔指数 (HHI)
        hhi = sum((v / total_value) ** 2 for v in protocols.values())

        # 根据HHI评估风险
        if hhi > 0.5:
            score = 80  # 高风险
            description = "投资组合高度集中在少数几个协议，增加了相关性风险"
            trend = "上升"
        elif hhi > 0.3:
            score = 60  # 中高风险
            description = "投资组合在协议分布上较为集中，存在一定相关性风险"
            trend = "稳定"
        elif hhi > 0.2:
            score = 40  # 中等风险
            description = "投资组合在协议分布上相对分散，相关性风险适中"
            trend = "稳定"
        else:
            score = 20  # 低风险
            description = "投资组合在协议分布上高度分散，相关性风险较低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="CORRELATION",
            factor_name="协议相关性",
            score=score,
            weight=0.3,
            description=description,
            trend=trend,
            data_points=[{"hhi": hhi, "protocols": protocols}],
        )

    async def _analyze_investment_type_correlation(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析投资类型相关性风险"""
        # 按投资类型分组
        investment_types = {}
        for pos in positions:
            invest_type = pos.get("invest_type", 0)
            invest_type_name = pos.get("invest_type_name", "未知类型")
            if invest_type not in investment_types:
                investment_types[invest_type] = {"name": invest_type_name, "amount": 0}
            investment_types[invest_type]["amount"] += pos.get("amount", 0)

        # 如果投资类型数量少于2，无法计算相关性
        if len(investment_types) < 2:
            return None

        # 计算投资类型集中度
        total_value = sum(data["amount"] for data in investment_types.values())
        if total_value == 0:
            return None

        # 计算赫芬达尔指数 (HHI)
        hhi = sum(
            (data["amount"] / total_value) ** 2 for data in investment_types.values()
        )

        # 根据HHI评估风险
        if hhi > 0.5:
            score = 80  # 高风险
            description = "投资组合高度集中在少数几种投资类型，增加了相关性风险"
            trend = "上升"
        elif hhi > 0.3:
            score = 60  # 中高风险
            description = "投资组合在投资类型分布上较为集中，存在一定相关性风险"
            trend = "稳定"
        elif hhi > 0.2:
            score = 40  # 中等风险
            description = "投资组合在投资类型分布上相对分散，相关性风险适中"
            trend = "稳定"
        else:
            score = 20  # 低风险
            description = "投资组合在投资类型分布上高度分散，相关性风险较低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="CORRELATION",
            factor_name="投资类型相关性",
            score=score,
            weight=0.2,
            description=description,
            trend=trend,
            data_points=[
                {
                    "hhi": hhi,
                    "investment_types": {
                        str(k): {
                            "name": v["name"],
                            "amount": v["amount"],
                            "percentage": v["amount"] / total_value,
                        }
                        for k, v in investment_types.items()
                    },
                }
            ],
        )

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取相关性风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        # 根据风险因子生成建议
        for factor in risk_factors:
            if factor.id == "CORRELATION.资产相关性" and factor.score > 60:
                recommendations.append("增加不同类型资产的配置，如稳定币、非相关代币等")
                recommendations.append("考虑添加与加密市场相关性较低的资产")

            if factor.id == "CORRELATION.协议相关性" and factor.score > 60:
                recommendations.append("分散投资到更多不同的协议，避免过度集中")
                recommendations.append(
                    "关注不同协议之间的相关性，选择相关性较低的协议组合"
                )

            if factor.id == "CORRELATION.投资类型相关性" and factor.score > 60:
                recommendations.append(
                    "平衡不同投资类型的比例，如借贷、流动性池、质押等"
                )
                recommendations.append("考虑增加与现有投资类型相关性较低的新投资类型")

        # 添加一般性建议
        if not recommendations:
            recommendations.append("定期评估投资组合的相关性，确保足够的多样化")

        return recommendations

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取相关性风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        monitoring_points = []

        # 根据风险因子生成监控点
        for factor in risk_factors:
            if factor.id == "CORRELATION.资产相关性" and factor.score > 40:
                monitoring_points.append("监控主要资产之间的相关性变化")

            if factor.id == "CORRELATION.协议相关性" and factor.score > 40:
                monitoring_points.append("关注不同协议之间的相互影响和联动效应")

            if factor.id == "CORRELATION.投资类型相关性" and factor.score > 40:
                monitoring_points.append("跟踪不同投资类型在市场波动时的表现")

        # 添加一般性监控点
        if not monitoring_points:
            monitoring_points.append("定期计算投资组合的相关性矩阵，评估多样化效果")

        return monitoring_points
