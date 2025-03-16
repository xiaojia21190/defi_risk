"""
相关性风险分析模块 - 用于分析DeFi投资组合的资产相关性风险
"""

from typing import Dict, List, Any, Optional
import logging
import numpy as np
import pandas as pd
from app.models.domain.risk import RiskFactor, RiskType, RiskAnalysisResult
from app.risk_modules.base import RiskAnalyzerBase


class CorrelationRiskAnalyzer(RiskAnalyzerBase):
    """相关性风险分析器"""

    async def analyze(self, data: Dict[str, Any]) -> RiskAnalysisResult:
        """
        分析相关性风险

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        self.logger.info("开始分析相关性风险")

        try:
            # 获取风险因子
            risk_factors = await self.get_risk_factors(data)

            # 如果没有收集到任何风险因素，返回默认风险分析结果
            if not risk_factors:
                self.logger.warning("未能收集到任何相关性风险因素")
                return RiskAnalysisResult(
                    risk_type=RiskType.CORRELATION.value,
                    target="投资组合",
                    score=50,  # 默认中等风险
                    factors=[],
                    recommendations=[],
                    monitoring_points=[],
                )

            # 计算总体风险评分（加权平均）
            total_weight = sum(factor.weight for factor in risk_factors)
            if total_weight > 0:
                weighted_score = (
                    sum(factor.score * factor.weight for factor in risk_factors)
                    / total_weight
                )
            else:
                weighted_score = 50  # 默认中等风险

            # 确保评分在0-100范围内
            weighted_score = max(0, min(100, weighted_score))

            # 生成建议和监控点
            recommendations = await self.get_recommendations(risk_factors)
            monitoring_points = await self.get_monitoring_points(risk_factors)

            # 创建风险分析结果
            result = RiskAnalysisResult(
                risk_type=RiskType.CORRELATION.value,
                target="投资组合相关性",
                score=weighted_score,
                factors=risk_factors,
                recommendations=recommendations,
                monitoring_points=monitoring_points,
            )

            self.logger.info(f"完成相关性风险分析，总体风险评分: {weighted_score:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"分析相关性风险时出错: {str(e)}")
            # 返回默认风险分析结果
            return RiskAnalysisResult(
                risk_type=RiskType.CORRELATION.value,
                target="投资组合",
                score=50,  # 默认中等风险
                factors=[],
                recommendations=[
                    "无法完成相关性风险分析，请检查输入数据是否正确",
                    "确保区块链服务正常运行",
                    "尝试稍后再次分析",
                ],
                monitoring_points=[
                    "监控系统日志以排查风险分析失败的原因",
                ],
            )

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
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取资产历史数据")
                return None

            # 提取资产列表和权重
            assets = {}
            for pos in positions:
                # 尝试从tokenList获取更精确的代币信息
                if pos.get("tokenList"):
                    for token in pos.get("tokenList", []):
                        token_symbol = token.get("tokenSymbol", "")
                        if token_symbol:
                            if token_symbol not in assets:
                                assets[token_symbol] = 0
                            # 使用代币在池中的比例分配价值
                            token_value = pos.get("amount", 0) * (
                                1 / len(pos.get("tokenList", []))
                            )
                            assets[token_symbol] += token_value
                else:
                    # 如果没有tokenList，使用资产名称
                    asset = pos.get("asset", "Unknown").split("/")[
                        0
                    ]  # 处理流动性池资产格式
                    if asset not in assets:
                        assets[asset] = 0
                    assets[asset] += pos.get("amount", 0)

            # 如果资产数量少于2，无法计算相关性
            if len(assets) < 2:
                return None

            # 计算总价值
            total_value = sum(assets.values())

            # 尝试使用AI服务进行相关性分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "assets": list(assets.keys()),
                        "weights": {
                            asset: (value / total_value)
                            for asset, value in assets.items()
                        },
                        "analysis_type": "asset_correlation",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="correlation_risk", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get("description", "资产相关性分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.CORRELATION.value,
                            factor_name="资产相关性风险",
                            score=risk_score,
                            weight=0.3,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "assets": assets,
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析资产相关性风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 获取资产历史数据并计算相关性
            asset_pairs = []
            correlation_matrix = {}

            # 获取每个资产的历史数据
            asset_historical_data = {}
            for asset in assets.keys():
                historical_data = (
                    await self.blockchain_service.get_asset_historical_data(asset)
                )
                if historical_data is not None and not historical_data.empty:
                    asset_historical_data[asset] = historical_data

            # 计算资产对之间的相关性
            for i, asset1 in enumerate(assets.keys()):
                correlation_matrix[asset1] = {}
                for j, asset2 in enumerate(assets.keys()):
                    if i >= j:  # 只计算上三角矩阵
                        continue

                    # 计算相关性
                    correlation = 0

                    # 如果两个资产都有历史数据，计算实际相关性
                    if (
                        asset1 in asset_historical_data
                        and asset2 in asset_historical_data
                    ):
                        df1 = asset_historical_data[asset1]
                        df2 = asset_historical_data[asset2]

                        # 确保两个数据集有相同的时间索引
                        if not df1.empty and not df2.empty:
                            # 合并数据集
                            merged = pd.merge(
                                df1[["timestamp", "price"]],
                                df2[["timestamp", "price"]],
                                on="timestamp",
                                how="inner",
                                suffixes=("_1", "_2"),
                            )

                            if len(merged) > 1:
                                # 计算相关系数
                                correlation = np.corrcoef(
                                    merged["price_1"].values, merged["price_2"].values
                                )[0, 1]

                    # 如果无法计算实际相关性，使用估计值
                    if correlation == 0:
                        correlation = self._estimate_asset_correlation(asset1, asset2)

                    # 存储相关性
                    correlation_matrix[asset1][asset2] = correlation

                    # 添加资产对信息
                    weight1 = assets[asset1] / total_value if total_value > 0 else 0
                    weight2 = assets[asset2] / total_value if total_value > 0 else 0

                    asset_pairs.append(
                        {
                            "asset1": asset1,
                            "asset2": asset2,
                            "correlation": correlation,
                            "weight1": weight1,
                            "weight2": weight2,
                            "combined_weight": weight1 + weight2,
                        }
                    )

            # 如果没有资产对，返回None
            if not asset_pairs:
                return None

            # 计算加权平均相关性
            weighted_correlation = sum(
                pair["correlation"] * pair["combined_weight"] for pair in asset_pairs
            ) / sum(pair["combined_weight"] for pair in asset_pairs)

            # 计算高相关性资产对的比例
            high_correlation_pairs = [
                pair for pair in asset_pairs if pair["correlation"] > 0.7
            ]
            high_correlation_ratio = (
                len(high_correlation_pairs) / len(asset_pairs) if asset_pairs else 0
            )

            # 计算风险评分 (0-100)
            # 相关性越高，风险越大
            risk_score = weighted_correlation * 100

            # 构建描述
            if risk_score > 70:
                description = "资产相关性极高，投资组合多样化程度低，系统性风险显著"
                trend = "上升"
            elif risk_score > 50:
                description = "资产相关性较高，投资组合多样化不足，存在一定系统性风险"
                trend = "上升"
            elif risk_score > 30:
                description = "资产相关性中等，投资组合多样化适中，系统性风险可控"
                trend = "稳定"
            else:
                description = "资产相关性较低，投资组合多样化程度高，系统性风险较小"
                trend = "下降"

            # 添加高相关性资产对信息
            if high_correlation_pairs:
                description += (
                    f"，有{len(high_correlation_pairs)}对资产高度相关（>0.7）"
                )

            # 构建数据点
            data_points = []
            for pair in asset_pairs:
                data_points.append(
                    {
                        "asset1": pair["asset1"],
                        "asset2": pair["asset2"],
                        "correlation": pair["correlation"],
                        "weight1": pair["weight1"],
                        "weight2": pair["weight2"],
                        "combined_weight": pair["combined_weight"],
                    }
                )

            return self.create_risk_factor(
                risk_type=RiskType.CORRELATION.value,
                factor_name="资产相关性风险",
                score=risk_score,
                weight=0.3,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "assets": assets,
                    "correlation_matrix": correlation_matrix,
                },
            )
        except Exception as e:
            self.logger.error(f"分析资产相关性风险时出错: {str(e)}")
            return None

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

        # 尝试使用AI服务进行协议相关性分析
        if self.ai_service:
            try:
                # 准备AI分析的数据
                ai_input_data = {
                    "protocols": list(protocols.keys()),
                    "weights": {
                        protocol: (value / total_value)
                        for protocol, value in protocols.items()
                    },
                    "analysis_type": "protocol_correlation",
                }

                # 使用AI服务进行分析
                ai_analysis = await self.ai_service.analyze_with_predictor(
                    analysis_type="protocol_correlation", data=ai_input_data
                )

                # 提取AI分析结果
                if ai_analysis and "risk_score" in ai_analysis:
                    risk_score = ai_analysis.get("risk_score", 50)
                    description = ai_analysis.get("description", "协议相关性分析")
                    trend = ai_analysis.get("trend", "稳定")
                    data_points = ai_analysis.get("data_points", [])

                    return self.create_risk_factor(
                        risk_type=RiskType.CORRELATION.value,
                        factor_name="协议相关性风险",
                        score=risk_score,
                        weight=0.3,
                        description=description,
                        trend=trend,
                        data_points=data_points,
                        metadata={
                            "protocols": protocols,
                            "ai_analysis": ai_analysis,
                        },
                    )
            except Exception as e:
                self.logger.error(f"使用AI分析协议相关性风险时出错: {str(e)}")
                # 如果AI分析失败，继续使用传统方法

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

        # 构建数据点
        data_points = [
            {
                "name": "赫芬达尔指数(HHI)",
                "value": hhi,
                "description": "衡量协议集中度的指标，值越高表示集中度越高",
            },
        ]

        # 添加协议分布数据
        for protocol, amount in protocols.items():
            weight = amount / total_value
            data_points.append(
                {
                    "name": "协议权重",
                    "protocol": protocol,
                    "value": weight,
                    "amount": amount,
                }
            )

        return self.create_risk_factor(
            risk_type=RiskType.CORRELATION.value,
            factor_name="协议相关性风险",
            score=score,
            weight=0.3,
            description=description,
            trend=trend,
            data_points=data_points,
            metadata={"protocols": protocols, "hhi": hhi},
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

        # 尝试使用AI服务进行投资类型相关性分析
        if self.ai_service:
            try:
                # 准备AI分析的数据
                ai_input_data = {
                    "investment_types": {
                        str(k): {"name": v["name"], "weight": v["amount"] / total_value}
                        for k, v in investment_types.items()
                    },
                    "analysis_type": "investment_type_correlation",
                }

                # 使用AI服务进行分析
                ai_analysis = await self.ai_service.analyze_with_predictor(
                    analysis_type="investment_type_correlation", data=ai_input_data
                )

                # 提取AI分析结果
                if ai_analysis and "risk_score" in ai_analysis:
                    risk_score = ai_analysis.get("risk_score", 50)
                    description = ai_analysis.get("description", "投资类型相关性分析")
                    trend = ai_analysis.get("trend", "稳定")
                    data_points = ai_analysis.get("data_points", [])

                    return self.create_risk_factor(
                        risk_type=RiskType.CORRELATION.value,
                        factor_name="投资类型相关性风险",
                        score=risk_score,
                        weight=0.2,
                        description=description,
                        trend=trend,
                        data_points=data_points,
                        metadata={
                            "investment_types": investment_types,
                            "ai_analysis": ai_analysis,
                        },
                    )
            except Exception as e:
                self.logger.error(f"使用AI分析投资类型相关性风险时出错: {str(e)}")
                # 如果AI分析失败，继续使用传统方法

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

        # 构建数据点
        data_points = [
            {
                "name": "赫芬达尔指数(HHI)",
                "value": hhi,
                "description": "衡量投资类型集中度的指标，值越高表示集中度越高",
            },
        ]

        # 添加投资类型分布数据
        for invest_type, data in investment_types.items():
            weight = data["amount"] / total_value
            data_points.append(
                {
                    "name": "投资类型权重",
                    "invest_type": invest_type,
                    "invest_type_name": data["name"],
                    "value": weight,
                    "amount": data["amount"],
                }
            )

        return self.create_risk_factor(
            risk_type=RiskType.CORRELATION.value,
            factor_name="投资类型相关性风险",
            score=score,
            weight=0.2,
            description=description,
            trend=trend,
            data_points=data_points,
            metadata={
                "investment_types": {
                    str(k): {
                        "name": v["name"],
                        "amount": v["amount"],
                        "percentage": v["amount"] / total_value,
                    }
                    for k, v in investment_types.items()
                },
                "hhi": hhi,
            },
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
            if factor.factor_name == "资产相关性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合中资产高度相关，建议大幅增加不同类型资产的配置"
                    )
                    recommendations.append(
                        "考虑添加与加密市场相关性较低的资产，如稳定币或跨行业代币"
                    )
                    recommendations.append("评估引入对冲策略以降低系统性风险")
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合中资产相关性较高，建议适当增加不同类型资产"
                    )
                    recommendations.append(
                        "关注高相关性资产对，考虑减少其中一种资产的比例"
                    )
                else:
                    recommendations.append(
                        "投资组合资产相关性适中或较低，继续保持多样化策略"
                    )

                # 检查是否有高相关性资产对
                high_correlation_pairs = []
                for data_point in factor.data_points:
                    if data_point.get("correlation", 0) > 0.7:
                        high_correlation_pairs.append(
                            (data_point.get("asset1", ""), data_point.get("asset2", ""))
                        )

                if high_correlation_pairs:
                    asset_pairs_str = ", ".join(
                        [f"{a1}/{a2}" for a1, a2 in high_correlation_pairs[:3]]
                    )
                    if len(high_correlation_pairs) > 3:
                        asset_pairs_str += f" 等{len(high_correlation_pairs)}对"
                    recommendations.append(
                        f"特别关注高相关性资产对: {asset_pairs_str}，考虑减少其中一种资产的比例"
                    )

            elif factor.factor_name == "协议相关性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合高度集中在少数协议，建议分散投资到更多不同的协议"
                    )
                    recommendations.append(
                        "考虑引入不同类别的协议，如借贷、DEX、收益聚合器等"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合在协议分布上较为集中，建议适当增加协议多样性"
                    )
                    recommendations.append(
                        "关注主要协议之间的相关性，选择相关性较低的协议组合"
                    )
                else:
                    recommendations.append(
                        "投资组合在协议分布上相对分散，继续保持多样化策略"
                    )

                # 检查是否有高集中度协议
                high_concentration_protocols = []
                for data_point in factor.data_points:
                    if (
                        data_point.get("name") == "协议权重"
                        and data_point.get("value", 0) > 0.3
                    ):
                        high_concentration_protocols.append(
                            data_point.get("protocol", "")
                        )

                if high_concentration_protocols:
                    protocols_str = ", ".join(high_concentration_protocols)
                    recommendations.append(
                        f"考虑降低在以下协议中的高集中度: {protocols_str}"
                    )

            elif factor.factor_name == "投资类型相关性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合高度集中在少数投资类型，建议扩展到更多不同的投资类型"
                    )
                    recommendations.append(
                        "考虑增加与现有投资类型相关性较低的新投资类型"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合在投资类型分布上较为集中，建议适当平衡不同投资类型的比例"
                    )
                    recommendations.append(
                        "评估不同投资类型在市场波动时的表现，选择互补性强的组合"
                    )
                else:
                    recommendations.append(
                        "投资组合在投资类型分布上相对分散，继续保持多样化策略"
                    )

                # 检查是否有高集中度投资类型
                high_concentration_types = []
                for data_point in factor.data_points:
                    if (
                        data_point.get("name") == "投资类型权重"
                        and data_point.get("value", 0) > 0.3
                    ):
                        high_concentration_types.append(
                            data_point.get("invest_type_name", "")
                        )

                if high_concentration_types:
                    types_str = ", ".join(high_concentration_types)
                    recommendations.append(
                        f"考虑降低在以下投资类型中的高集中度: {types_str}"
                    )

        # 添加通用建议
        if not recommendations:
            recommendations.append("定期评估投资组合的相关性，确保足够的多样化")
            recommendations.append("关注市场波动时不同资产、协议和投资类型的相关性变化")
            recommendations.append("考虑使用相关性分析工具优化投资组合配置")

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
            if factor.factor_name == "资产相关性风险":
                if factor.score > 70:
                    monitoring_points.append(
                        "密切监控主要资产之间的相关性变化，特别是在市场波动期间"
                    )
                    monitoring_points.append(
                        "设置相关性阈值警报，当资产相关性超过特定阈值时发出提醒"
                    )
                elif factor.score > 50:
                    monitoring_points.append("定期监控主要资产之间的相关性变化")
                    monitoring_points.append("关注市场波动对资产相关性的影响")
                else:
                    monitoring_points.append("定期检查资产相关性矩阵，确保多样化效果")

                # 检查是否有高相关性资产对
                high_correlation_pairs = []
                for data_point in factor.data_points:
                    if data_point.get("correlation", 0) > 0.7:
                        high_correlation_pairs.append(
                            (data_point.get("asset1", ""), data_point.get("asset2", ""))
                        )

                if high_correlation_pairs:
                    asset_pairs_str = ", ".join(
                        [f"{a1}/{a2}" for a1, a2 in high_correlation_pairs[:3]]
                    )
                    if len(high_correlation_pairs) > 3:
                        asset_pairs_str += f" 等{len(high_correlation_pairs)}对"
                    monitoring_points.append(
                        f"特别监控高相关性资产对: {asset_pairs_str}"
                    )

            elif factor.factor_name == "协议相关性风险":
                if factor.score > 70:
                    monitoring_points.append("密切关注主要协议之间的相互影响和联动效应")
                    monitoring_points.append(
                        "监控协议特定事件（如治理变更、安全事件）对整个投资组合的影响"
                    )
                elif factor.score > 50:
                    monitoring_points.append("定期关注不同协议之间的相互影响")
                    monitoring_points.append("监控主要协议的重大更新和变化")
                else:
                    monitoring_points.append("关注协议间的相关性变化趋势")

                # 检查是否有高集中度协议
                high_concentration_protocols = []
                for data_point in factor.data_points:
                    if (
                        data_point.get("name") == "协议权重"
                        and data_point.get("value", 0) > 0.3
                    ):
                        high_concentration_protocols.append(
                            data_point.get("protocol", "")
                        )

                if high_concentration_protocols:
                    protocols_str = ", ".join(high_concentration_protocols)
                    monitoring_points.append(
                        f"重点监控高集中度协议的风险事件: {protocols_str}"
                    )

            elif factor.factor_name == "投资类型相关性风险":
                if factor.score > 70:
                    monitoring_points.append(
                        "密切跟踪不同投资类型在市场波动时的表现相关性"
                    )
                    monitoring_points.append(
                        "监控投资类型特定风险事件对整个投资组合的影响"
                    )
                elif factor.score > 50:
                    monitoring_points.append("定期评估不同投资类型的相关性变化")
                    monitoring_points.append("关注市场环境变化对投资类型相关性的影响")
                else:
                    monitoring_points.append("关注投资类型多样化效果的长期趋势")

                # 检查是否有高集中度投资类型
                high_concentration_types = []
                for data_point in factor.data_points:
                    if (
                        data_point.get("name") == "投资类型权重"
                        and data_point.get("value", 0) > 0.3
                    ):
                        high_concentration_types.append(
                            data_point.get("invest_type_name", "")
                        )

                if high_concentration_types:
                    types_str = ", ".join(high_concentration_types)
                    monitoring_points.append(
                        f"重点监控高集中度投资类型的风险事件: {types_str}"
                    )

        # 添加通用监控点
        if not monitoring_points:
            monitoring_points.append("定期计算投资组合的相关性矩阵，评估多样化效果")
            monitoring_points.append("关注市场波动期间资产、协议和投资类型的相关性变化")
            monitoring_points.append("监控宏观经济因素对投资组合相关性的影响")

        return monitoring_points
