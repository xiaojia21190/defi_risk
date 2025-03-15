from typing import Dict, List, Any, Optional
from app.models.domain.risk import RiskFactor, RiskAssessment, RiskLevel, RiskType
import uuid
from datetime import datetime
import logging
import asyncio
from app.core.config import settings
from app.services.ai_predictor import AiPredictor


class RiskEngine:
    """风险评估引擎"""

    def __init__(self, blockchain_service=None):
        self.logger = logging.getLogger("defi_risk.risk_engine")
        self.risk_analyzers = {}
        self.risk_weights = settings.RISK_WEIGHTS
        self.blockchain_service = blockchain_service
        self.ai_predictor = AiPredictor()

    def register_analyzer(self, risk_type: str, analyzer):
        """
        注册风险分析器

        Args:
            risk_type: 风险类型
            analyzer: 分析器实例
        """
        self.logger.info(
            f"注册风险分析器: {risk_type} -> {analyzer.__class__.__name__}"
        )
        self.risk_analyzers[risk_type] = analyzer

    async def analyze_wallet_risk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析钱包风险 - 处理来自ai_service.analyze("wallet_risk", context)的请求

        Args:
            context: 包含钱包地址和头寸的上下文

        Returns:
            Dict: 包含风险分析结果的字典
        """
        self.logger.info(
            f"开始分析钱包风险: {context.get('wallet_address', '未知钱包')}"
        )

        try:
            # 提取钱包头寸
            positions = context.get("positions", [])

            if not positions:
                self.logger.warning(f"钱包 {context.get('wallet_address')} 没有头寸")
                return self._get_empty_risk_analysis(context.get("wallet_address"))

            # 转换为RiskCalculator使用的Position对象
            portfolio_positions = []
            for pos in positions:
                # 创建Position对象
                portfolio_positions.append(
                    {
                        "protocol": pos.get("protocol", "unknown"),
                        "asset": pos.get("asset", "unknown"),
                        "amount": float(pos.get("amount", 0)),
                        "invest_type": int(pos.get("invest_type", 0)),
                        "apy": pos.get("apy"),
                    }
                )

            # 分析投资组合风险
            portfolio_risk = await self.analyze_portfolio(
                {
                    "wallet_address": context.get("wallet_address"),
                    "positions": portfolio_positions,
                }
            )

            # 生成AI投资组合建议
            ai_recommendations = await self._generate_ai_recommendations(positions)

            # 合并结果
            result = {
                "supporting_data": {
                    "market_risk_score": self._get_risk_type_score(
                        portfolio_risk, "MARKET"
                    ),
                    "protocol_risk_score": self._get_risk_type_score(
                        portfolio_risk, "PROTOCOL"
                    ),
                    "liquidity_risk_score": self._get_risk_type_score(
                        portfolio_risk, "LIQUIDITY"
                    ),
                    "smart_contract_risk_score": self._get_risk_type_score(
                        portfolio_risk, "SMART_CONTRACT"
                    ),
                    "correlation_risk_score": self._get_risk_type_score(
                        portfolio_risk, "CORRELATION"
                    ),
                },
                "insights": self._generate_insights(portfolio_risk),
                "recommendations": ai_recommendations.get("recommendations", [])
                + portfolio_risk.recommendations,
                "confidence": 0.85,  # 置信度
            }

            self.logger.info(f"钱包风险分析完成: {context.get('wallet_address')}")
            return result

        except Exception as e:
            self.logger.error(f"分析钱包风险时出错: {str(e)}")
            return {
                "supporting_data": {
                    "market_risk_score": 50,
                    "protocol_risk_score": 50,
                    "liquidity_risk_score": 50,
                    "smart_contract_risk_score": 50,
                    "correlation_risk_score": 50,
                },
                "insights": [f"分析过程中出错: {str(e)}"],
                "recommendations": ["建议重新分析或联系技术支持"],
                "confidence": 0.3,
            }

    def _get_risk_type_score(self, assessment: RiskAssessment, risk_type: str) -> float:
        """获取特定风险类型的评分"""
        if not assessment or not assessment.detailed_analysis:
            return 50.0

        risk_by_type = assessment.detailed_analysis.get("risk_by_type", {})
        risk_data = risk_by_type.get(risk_type.lower(), {})
        return risk_data.get("score", 50.0)

    def _generate_insights(self, assessment: RiskAssessment) -> List[str]:
        """从风险评估生成洞察"""
        insights = []

        # 添加总体风险评估
        insights.append(
            f"总体风险评分: {assessment.total_score:.1f}/100，风险等级: {assessment.risk_level.value}"
        )

        # 添加主要风险因素
        if assessment.risk_factors:
            high_risk_factors = sorted(
                [f for f in assessment.risk_factors.values() if f.score > 70],
                key=lambda x: x.score,
                reverse=True,
            )[
                :3
            ]  # 取前三个高风险因素

            if high_risk_factors:
                insights.append("主要风险因素:")
                for factor in high_risk_factors:
                    insights.append(f"- {factor.name}: {factor.description}")

        # 添加投资组合摘要
        if (
            assessment.detailed_analysis
            and "portfolio_summary" in assessment.detailed_analysis
        ):
            summary = assessment.detailed_analysis["portfolio_summary"]
            insights.append(
                f"投资组合包含 {summary.get('position_count', 0)} 个头寸，分布在 {summary.get('protocol_count', 0)} 个协议和 {summary.get('asset_count', 0)} 种资产"
            )

            # 添加最大协议敞口
            if summary.get("top_protocols"):
                top_protocol = summary["top_protocols"][0]
                insights.append(
                    f"最大协议敞口: {top_protocol['name']} ({top_protocol['percentage']:.1f}%)"
                )

            # 添加最大资产敞口
            if summary.get("top_assets"):
                top_asset = summary["top_assets"][0]
                insights.append(
                    f"最大资产敞口: {top_asset['name']} ({top_asset['percentage']:.1f}%)"
                )

        return insights

    async def _generate_ai_recommendations(
        self, positions: List[Dict]
    ) -> Dict[str, Any]:
        """生成AI驱动的投资组合建议"""
        try:
            # 调用AiPredictor的analyze_portfolio_risk方法生成AI驱动的建议
            if not positions:
                self.logger.warning("没有提供头寸数据，无法生成AI建议")
                return {
                    "recommendations": ["开始投资以获取收益"],
                    "rebalancing_suggestions": [],
                    "risk_reduction_strategies": [],
                }

            # 准备投资组合数据
            portfolio_data = {
                "positions": positions,
                "total_value": sum(float(pos.get("amount", 0)) for pos in positions),
                "asset_count": len(
                    set(pos.get("asset", "").split("/")[0] for pos in positions)
                ),
                "protocol_count": len(
                    set(pos.get("protocol", "") for pos in positions)
                ),
            }

            # 调用AI预测器分析投资组合风险
            try:
                ai_analysis = self.ai_predictor.analyze_portfolio_risk(portfolio_data)

                # 如果AI分析成功，提取建议
                if isinstance(ai_analysis, dict) and "recommendations" in ai_analysis:
                    return {
                        "recommendations": ai_analysis.get("recommendations", []),
                        "rebalancing_suggestions": ai_analysis.get(
                            "rebalancing_suggestions", []
                        ),
                        "risk_reduction_strategies": ai_analysis.get(
                            "risk_reduction_strategies", []
                        ),
                    }
            except Exception as ai_error:
                self.logger.error(
                    f"调用AI预测器分析投资组合风险时出错: {str(ai_error)}"
                )
                # 继续执行备用逻辑

            # 备用逻辑：如果AI分析失败，使用基于规则的方法生成建议
            self.logger.info("使用基于规则的方法生成投资组合建议")
            assets = [pos.get("asset", "").split("/")[0] for pos in positions]
            protocols = [pos.get("protocol", "") for pos in positions]

            # 生成基本建议
            recommendations = []

            # 资产多样性建议
            if len(set(assets)) < 3:
                recommendations.append("增加资产多样性，避免集中在少数几种资产")
            else:
                recommendations.append("保持良好的资产多样性，继续监控资产相关性")

            # 协议多样性建议
            if len(set(protocols)) < 2:
                recommendations.append("考虑分散投资到多个不同的协议，降低协议风险")
            else:
                recommendations.append("保持协议分散度，关注各协议的安全更新和审计报告")

            # 稳定币建议
            stablecoins = ["USDC", "USDT", "DAI", "BUSD"]
            has_stablecoin = any(
                any(stable in asset.upper() for stable in stablecoins)
                for asset in assets
            )
            if not has_stablecoin:
                recommendations.append("考虑增加稳定币比例，降低整体波动风险")

            # 添加一般性建议
            recommendations.extend(
                [
                    "定期重新平衡投资组合以维持目标风险水平",
                    "考虑使用智能合约保险保护高价值投资",
                    "关注高收益投资的风险暴露",
                ]
            )

            # 分类建议
            return {
                "recommendations": recommendations,
                "rebalancing_suggestions": recommendations[:2],
                "risk_reduction_strategies": recommendations[2:4],
            }

        except Exception as e:
            self.logger.error(f"生成AI建议时出错: {str(e)}")
            return {
                "recommendations": ["定期重新平衡投资组合以维持目标风险水平"],
                "rebalancing_suggestions": [],
                "risk_reduction_strategies": [],
            }

    def _get_empty_risk_analysis(self, wallet_address: str) -> Dict[str, Any]:
        """返回空钱包的风险分析"""
        return {
            "supporting_data": {
                "market_risk_score": 0,
                "protocol_risk_score": 0,
                "liquidity_risk_score": 0,
                "smart_contract_risk_score": 0,
                "correlation_risk_score": 0,
            },
            "insights": [f"钱包 {wallet_address} 没有检测到任何DeFi头寸"],
            "recommendations": [
                "开始投资以获取收益",
                "从小额投资开始，逐步了解DeFi生态",
            ],
            "confidence": 0.9,
        }

    async def analyze_portfolio(self, portfolio_data: Dict[str, Any]) -> RiskAssessment:
        """
        分析投资组合风险

        Args:
            portfolio_data: 投资组合数据

        Returns:
            风险评估结果
        """
        self.logger.info(
            f"开始分析投资组合风险: {portfolio_data.get('wallet_address', '未知钱包')}"
        )

        # 收集各模块的风险因子
        all_risk_factors = {}

        # 并行执行各风险分析器
        tasks = []
        for risk_type, analyzer in self.risk_analyzers.items():
            tasks.append(self._get_risk_factors(risk_type, analyzer, portfolio_data))

        # 等待所有分析器完成
        results = await asyncio.gather(*tasks)

        # 合并结果
        for factors in results:
            for factor in factors:
                all_risk_factors[factor.id] = factor

        # 计算总体风险评分
        total_score = self._calculate_total_score(all_risk_factors)

        # 确定风险等级
        risk_level = self._determine_risk_level(total_score)

        # 生成建议和监控点
        recommendations = await self._generate_recommendations(all_risk_factors)
        monitoring_points = await self._generate_monitoring_points(all_risk_factors)

        # 创建风险评估结果
        assessment = RiskAssessment(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            total_score=total_score,
            risk_level=risk_level,
            risk_factors=all_risk_factors,
            warnings=self._generate_warnings(all_risk_factors),
            recommendations=recommendations,
            mitigation_strategies=self._generate_mitigation_strategies(
                all_risk_factors
            ),
            monitoring_points=monitoring_points,
            detailed_analysis=self._generate_detailed_analysis(
                all_risk_factors, portfolio_data
            ),
            metadata={
                "portfolio_id": portfolio_data.get("portfolio_id", ""),
                "analysis_version": "1.0",
            },
        )

        self.logger.info(
            f"投资组合风险分析完成: 风险评分={total_score}, 风险等级={risk_level.value}"
        )

        return assessment

    async def _get_risk_factors(
        self, risk_type: str, analyzer, portfolio_data: Dict[str, Any]
    ) -> List[RiskFactor]:
        """获取风险因子"""
        try:
            return await analyzer.get_risk_factors(portfolio_data)
        except Exception as e:
            self.logger.error(f"获取风险因子时出错 ({risk_type}): {str(e)}")
            return []

    def _calculate_total_score(self, risk_factors: Dict[str, RiskFactor]) -> float:
        """计算总体风险评分"""
        if not risk_factors:
            return 0

        total_weighted_score = 0
        total_weight = 0

        for factor in risk_factors.values():
            # 获取风险类型权重
            risk_type = factor.id.split(".")[0]  # 假设ID格式为"RISK_TYPE.factor_name"
            weight = self.risk_weights.get(risk_type, 0.1) * factor.weight

            total_weighted_score += factor.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0

        return total_weighted_score / total_weight

    def _determine_risk_level(self, total_score: float) -> RiskLevel:
        """确定风险等级"""
        if total_score <= 25:
            return RiskLevel.LOW
        elif total_score <= 50:
            return RiskLevel.MEDIUM
        elif total_score <= 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    def _generate_warnings(self, risk_factors: Dict[str, RiskFactor]) -> List[str]:
        """生成警告信息"""
        warnings = []

        # 提取高风险因子作为警告
        for factor in risk_factors.values():
            if factor.score > 75:
                warnings.append(f"{factor.name}: {factor.description}")

        return warnings

    async def _generate_recommendations(
        self, risk_factors: Dict[str, RiskFactor]
    ) -> List[str]:
        """生成建议"""
        all_recommendations = []

        # 从各分析器获取建议
        for risk_type, analyzer in self.risk_analyzers.items():
            # 过滤出当前风险类型的因子
            type_factors = [
                f for f in risk_factors.values() if f.id.startswith(risk_type)
            ]
            if type_factors:
                try:
                    recommendations = await analyzer.get_recommendations(type_factors)
                    all_recommendations.extend(recommendations)
                except Exception as e:
                    self.logger.error(f"获取建议时出错 ({risk_type}): {str(e)}")

        # 去重
        return list(set(all_recommendations))

    def _generate_mitigation_strategies(
        self, risk_factors: Dict[str, RiskFactor]
    ) -> List[str]:
        """生成风险缓解策略"""
        strategies = []

        # 根据高风险因子生成缓解策略
        high_risk_factors = [f for f in risk_factors.values() if f.score > 60]

        if any(f.id.startswith("MARKET") for f in high_risk_factors):
            strategies.append("考虑增加投资组合多样性，减少对单一市场的依赖")

        if any(f.id.startswith("SMART_CONTRACT") for f in high_risk_factors):
            strategies.append("使用经过审计的协议，并考虑使用智能合约保险")

        if any(f.id.startswith("LIQUIDITY") for f in high_risk_factors):
            strategies.append("增加流动性较高的资产比例，避免流动性陷阱")

        # 添加更多策略...

        return strategies

    async def _generate_monitoring_points(
        self, risk_factors: Dict[str, RiskFactor]
    ) -> List[str]:
        """生成监控点"""
        all_monitoring_points = []

        # 从各分析器获取监控点
        for risk_type, analyzer in self.risk_analyzers.items():
            # 过滤出当前风险类型的因子
            type_factors = [
                f for f in risk_factors.values() if f.id.startswith(risk_type)
            ]
            if type_factors:
                try:
                    monitoring_points = await analyzer.get_monitoring_points(
                        type_factors
                    )
                    all_monitoring_points.extend(monitoring_points)
                except Exception as e:
                    self.logger.error(f"获取监控点时出错 ({risk_type}): {str(e)}")

        # 去重
        return list(set(all_monitoring_points))

    def _generate_detailed_analysis(
        self, risk_factors: Dict[str, RiskFactor], portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成详细分析"""
        # 按风险类型分组
        analysis_by_type = {}

        for risk_type in RiskType:
            type_name = risk_type.name
            type_factors = [
                f for f in risk_factors.values() if f.id.startswith(type_name)
            ]

            if type_factors:
                type_score = sum(f.score * f.weight for f in type_factors) / sum(
                    f.weight for f in type_factors
                )

                analysis_by_type[risk_type.value] = {
                    "score": type_score,
                    "level": self._determine_risk_level(type_score).value,
                    "factors": [
                        {
                            "name": f.name,
                            "score": f.score,
                            "description": f.description,
                            "trend": f.trend,
                        }
                        for f in type_factors
                    ],
                }

        # 添加投资组合分析
        return {
            "risk_by_type": analysis_by_type,
            "portfolio_summary": self._generate_portfolio_summary(portfolio_data),
        }

    def _generate_portfolio_summary(
        self, portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成投资组合摘要"""
        positions = portfolio_data.get("positions", [])

        # 计算总价值
        total_value = sum(pos.get("amount", 0) for pos in positions)

        # 按协议分组
        protocols = {}
        for pos in positions:
            protocol = pos.get("protocol", "unknown")
            if protocol not in protocols:
                protocols[protocol] = 0
            protocols[protocol] += pos.get("amount", 0)

        # 按资产分组
        assets = {}
        for pos in positions:
            asset = pos.get("asset", "unknown")
            if asset not in assets:
                assets[asset] = 0
            assets[asset] += pos.get("amount", 0)

        return {
            "total_value": total_value,
            "position_count": len(positions),
            "protocol_count": len(protocols),
            "asset_count": len(assets),
            "top_protocols": [
                {
                    "name": k,
                    "value": v,
                    "percentage": (v / total_value) * 100 if total_value > 0 else 0,
                }
                for k, v in sorted(protocols.items(), key=lambda x: x[1], reverse=True)[
                    :5
                ]
            ],
            "top_assets": [
                {
                    "name": k,
                    "value": v,
                    "percentage": (v / total_value) * 100 if total_value > 0 else 0,
                }
                for k, v in sorted(assets.items(), key=lambda x: x[1], reverse=True)[:5]
            ],
        }
