from typing import Dict, List, Any, Optional, Union
from app.models.domain.risk import RiskFactor, RiskAssessment, RiskLevel, RiskType
import uuid
from datetime import datetime
import logging
import asyncio
from app.core.config import settings
from app.services.ai_predictor import AiPredictor
from dataclasses import dataclass


@dataclass
class MarketRiskResult:
    """市场风险分析结果"""

    risk_type: str = "MARKET"
    target: str = ""
    score: float = 0.0
    factors: List[RiskFactor] = None
    recommendations: List[str] = None
    monitoring_points: List[str] = None

    def __post_init__(self):
        if self.factors is None:
            self.factors = []
        if self.recommendations is None:
            self.recommendations = []
        if self.monitoring_points is None:
            self.monitoring_points = []


class RiskEngine:
    """风险评估引擎"""

    def __init__(self, blockchain_service=None):
        self.logger = logging.getLogger("defi_risk.risk_engine")
        self.risk_analyzers = {}
        self.risk_weights = settings.RISK_WEIGHTS
        self.blockchain_service = blockchain_service
        self.ai_predictor = AiPredictor()
        self.ai_service = None  # 初始化ai_service属性

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
        # 设置AI服务和预测器
        if hasattr(analyzer, "ai_service") and self.ai_service:
            analyzer.ai_service = self.ai_service
        if hasattr(analyzer, "ai_predictor") and self.ai_predictor:
            analyzer.ai_predictor = self.ai_predictor
        if hasattr(analyzer, "blockchain_service") and self.blockchain_service:
            analyzer.blockchain_service = self.blockchain_service

        self.risk_analyzers[risk_type] = analyzer

    async def analyze_wallet_risk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析钱包风险

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

    async def _analyze_protocol_security(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议安全风险"""
        try:
            # 使用AI预测器分析协议风险
            if self.ai_predictor:
                protocol_data = {
                    "protocol_metadata": {"name": protocol},
                    "basic_analysis": {},
                    "historical_tvl": [],
                    "chain_distribution": {},
                }

                # 如果有区块链服务，获取更多数据
                if self.blockchain_service:
                    try:
                        # 获取协议TVL
                        tvl = await self.blockchain_service.get_protocol_tvl(protocol)
                        protocol_data["basic_analysis"]["tvl"] = tvl

                        # 获取协议历史TVL
                        historical_tvl = (
                            await self.blockchain_service.get_protocol_historical_tvl(
                                protocol
                            )
                        )
                        protocol_data["historical_tvl"] = historical_tvl

                        # 获取协议审计状态
                        audit_status = (
                            await self.blockchain_service.get_protocol_audit_status(
                                protocol
                            )
                        )
                        protocol_data["basic_analysis"]["audit_status"] = audit_status
                    except Exception as e:
                        self.logger.error(f"获取协议数据时出错: {str(e)}")

                # 使用AI预测器分析
                analysis = self.ai_predictor.analyze_defi_protocol_risk(protocol_data)

                # 提取安全风险评分
                security_score = analysis.get("risk_metrics", {}).get(
                    "security_risk", 50
                )

                # 生成描述
                description = f"{protocol}协议安全风险评分: {security_score}"
                if "recommendations" in analysis:
                    description += f"。建议: {analysis['recommendations'][0] if analysis['recommendations'] else ''}"

                # 确定趋势
                trend = "稳定"

                return self.create_risk_factor(
                    risk_type="PROTOCOL",
                    factor_name="协议安全性",
                    score=security_score,
                    weight=0.4,
                    description=description,
                    trend=trend,
                    data_points=[
                        {"protocol": protocol, "security_score": security_score}
                    ],
                    metadata=analysis,
                )

            # 如果没有AI预测器，使用现有的硬编码逻辑
            # 现有代码保持不变...

        except Exception as e:
            self.logger.error(f"分析协议安全风险时出错: {str(e)}")
            # 返回默认风险因子
            return self.create_risk_factor(
                risk_type="PROTOCOL",
                factor_name="协议安全性",
                score=70,  # 默认高风险
                weight=0.4,
                description=f"{protocol}协议安全风险分析失败",
                trend="稳定",
                data_points=[{"protocol": protocol, "security_score": 70}],
            )

    async def analyze_market_risk(self, positions: List[Dict]) -> MarketRiskResult:
        """
        分析市场风险

        Args:
            positions: 钱包头寸列表

        Returns:
            MarketRiskResult: 市场风险分析结果
        """
        self.logger.info(f"开始分析市场风险，头寸数量: {len(positions)}")

        result = MarketRiskResult(
            target="portfolio", recommendations=[], monitoring_points=[]
        )

        try:
            # 如果没有头寸，返回低风险结果
            if not positions:
                self.logger.warning("没有头寸数据，无法分析市场风险")
                result.score = 10.0
                result.recommendations = ["添加资产以获取更准确的市场风险分析"]
                return result

            # 提取资产信息
            assets = {}
            total_value = 0.0

            for position in positions:
                asset_name = position.get("asset", "unknown")
                asset_value = float(position.get("usd_value", 0))

                if asset_name in assets:
                    assets[asset_name] += asset_value
                else:
                    assets[asset_name] = asset_value

                total_value += asset_value

            # 计算资产集中度
            concentration_data = {
                "assets": [{"name": k, "value": v} for k, v in assets.items()],
                "total_value": total_value,
            }

            # 使用AI预测器分析集中度风险
            concentration_risk = None
            correlation_risk = None

            try:
                if self.ai_predictor and hasattr(
                    self.ai_predictor, "analyze_concentration_risk"
                ):
                    concentration_risk = (
                        await self.ai_predictor.analyze_concentration_risk(
                            concentration_data
                        )
                    )

                    # 创建集中度风险因子
                    if concentration_risk and "score" in concentration_risk:
                        conc_factor = self.create_risk_factor(
                            risk_type="MARKET",
                            factor_name="资产集中度风险",
                            score=float(concentration_risk.get("score", 50)),
                            weight=0.4,
                            description=concentration_risk.get(
                                "description", "资产集中度分析"
                            ),
                            trend=concentration_risk.get("trend", "稳定"),
                            data_points=concentration_risk.get("data_points", []),
                        )
                        result.factors.append(conc_factor)

                        # 添加建议
                        if "recommendations" in concentration_risk:
                            result.recommendations.extend(
                                concentration_risk["recommendations"]
                            )

                        # 添加监控点
                        if "monitoring_points" in concentration_risk:
                            result.monitoring_points.extend(
                                concentration_risk["monitoring_points"]
                            )
            except Exception as e:
                self.logger.error(f"分析集中度风险时出错: {str(e)}")
                # 添加默认集中度风险因子
                conc_factor = self.create_risk_factor(
                    risk_type="MARKET",
                    factor_name="资产集中度风险",
                    score=60.0,
                    weight=0.4,
                    description="无法分析资产集中度风险",
                    trend="稳定",
                    data_points=[],
                )
                result.factors.append(conc_factor)

            # 分析相关性风险
            try:
                if self.ai_predictor and hasattr(
                    self.ai_predictor, "analyze_correlation_risk"
                ):
                    # 准备相关性分析数据
                    correlation_data = {
                        "assets": list(assets.keys()),
                        "positions": positions,
                    }

                    correlation_risk = await self.ai_predictor.analyze_correlation_risk(
                        correlation_data
                    )

                    # 创建相关性风险因子
                    if correlation_risk and "score" in correlation_risk:
                        corr_factor = self.create_risk_factor(
                            risk_type="MARKET",
                            factor_name="资产相关性风险",
                            score=float(correlation_risk.get("score", 50)),
                            weight=0.3,
                            description=correlation_risk.get(
                                "description", "资产相关性分析"
                            ),
                            trend=correlation_risk.get("trend", "稳定"),
                            data_points=correlation_risk.get("data_points", []),
                        )
                        result.factors.append(corr_factor)

                        # 添加建议
                        if "recommendations" in correlation_risk:
                            result.recommendations.extend(
                                correlation_risk["recommendations"]
                            )

                        # 添加监控点
                        if "monitoring_points" in correlation_risk:
                            result.monitoring_points.extend(
                                correlation_risk["monitoring_points"]
                            )
            except Exception as e:
                self.logger.error(f"分析相关性风险时出错: {str(e)}")
                # 添加默认相关性风险因子
                corr_factor = self.create_risk_factor(
                    risk_type="MARKET",
                    factor_name="资产相关性风险",
                    score=50.0,
                    weight=0.3,
                    description="无法分析资产相关性风险",
                    trend="稳定",
                    data_points=[],
                )
                result.factors.append(corr_factor)

            # 添加市场波动风险因子
            volatility_factor = self.create_risk_factor(
                risk_type="MARKET",
                factor_name="市场波动风险",
                score=55.0,  # 默认中等风险
                weight=0.3,
                description="当前市场波动性处于中等水平",
                trend="上升",
                data_points=[{"volatility_index": 55}],
            )
            result.factors.append(volatility_factor)

            # 计算总体市场风险评分
            total_score = 0.0
            total_weight = 0.0

            for factor in result.factors:
                total_score += factor.score * factor.weight
                total_weight += factor.weight

            if total_weight > 0:
                result.score = total_score / total_weight
            else:
                result.score = 50.0  # 默认中等风险

            # 生成市场风险建议
            if (
                not result.recommendations
                and self.ai_predictor
                and hasattr(self.ai_predictor, "generate_market_risk_recommendations")
            ):
                try:
                    # 准备风险因子数据
                    risk_data = {
                        "risk_factors": [
                            {
                                "factor_name": factor.factor_name,
                                "score": factor.score,
                                "description": factor.description,
                                "trend": factor.trend,
                                "data_points": factor.data_points,
                            }
                            for factor in result.factors
                        ],
                    }

                    # 获取AI建议
                    recommendations = (
                        await self.ai_predictor.generate_market_risk_recommendations(
                            risk_data
                        )
                    )
                    if recommendations and "recommendations" in recommendations:
                        result.recommendations.extend(
                            recommendations["recommendations"]
                        )
                except Exception as e:
                    self.logger.error(f"生成市场风险建议时出错: {str(e)}")
                    result.recommendations.append("无法生成市场风险建议")

            # 生成市场风险监控点
            if (
                not result.monitoring_points
                and self.ai_predictor
                and hasattr(self.ai_predictor, "generate_market_risk_monitoring_points")
            ):
                try:
                    # 准备风险因子数据
                    risk_data = {
                        "risk_factors": [
                            {
                                "factor_name": factor.factor_name,
                                "score": factor.score,
                                "description": factor.description,
                                "trend": factor.trend,
                                "data_points": factor.data_points,
                            }
                            for factor in result.factors
                        ],
                    }

                    # 获取AI监控点
                    monitoring_points = (
                        await self.ai_predictor.generate_market_risk_monitoring_points(
                            risk_data
                        )
                    )
                    if monitoring_points and "monitoring_points" in monitoring_points:
                        result.monitoring_points.extend(
                            monitoring_points["monitoring_points"]
                        )
                except Exception as e:
                    self.logger.error(f"生成市场风险监控点时出错: {str(e)}")
                    result.monitoring_points.append("无法生成市场风险监控点")

            # 如果没有建议，添加默认建议
            if not result.recommendations:
                if result.score > 70:
                    result.recommendations = [
                        "考虑分散投资组合，减少高风险资产敞口",
                        "关注市场波动，设置止损点",
                        "定期重新平衡投资组合",
                    ]
                elif result.score > 40:
                    result.recommendations = [
                        "保持投资组合多样化",
                        "定期监控市场变化",
                        "考虑增加稳定币比例",
                    ]
                else:
                    result.recommendations = [
                        "继续保持当前的多样化策略",
                        "可以考虑适度增加收益型资产",
                    ]

            # 如果没有监控点，添加默认监控点
            if not result.monitoring_points:
                result.monitoring_points = [
                    "关注主要资产价格波动",
                    "监控DeFi协议TVL变化",
                    "关注市场情绪指标",
                ]

            self.logger.info(f"市场风险分析完成，风险评分: {result.score:.1f}")
            return result

        except Exception as e:
            self.logger.error(f"分析市场风险时出错: {str(e)}")
            # 返回默认风险结果
            result.score = 50.0
            result.recommendations = ["无法完成市场风险分析，请稍后重试"]
            result.monitoring_points = ["监控市场整体波动"]
            return result

    def create_risk_factor(
        self,
        risk_type: str,
        factor_name: str,
        score: float,
        weight: float,
        description: str,
        trend: str = "稳定",
        data_points: List[Dict] = None,
        metadata: Dict = None,
    ) -> RiskFactor:
        """创建风险因子"""
        if data_points is None:
            data_points = []
        if metadata is None:
            metadata = {}

        return RiskFactor(
            id=str(uuid.uuid4()),
            risk_type=risk_type,
            name=factor_name,
            factor_name=factor_name,
            score=score,
            weight=weight,
            description=description,
            trend=trend,
            data_points=data_points,
            metadata=metadata,
        )

    async def analyze_portfolio_risk(
        self, positions: List[Dict[str, Any]], wallet_address: str
    ) -> Dict[str, Any]:
        """
        分析投资组合风险（包装器方法）

        Args:
            positions: 投资组合头寸列表

        Returns:
            Dict: 风险分析结果，格式与AI预测器兼容
        """
        self.logger.info(f"开始分析投资组合风险，头寸数量: {len(positions)}")

        try:
            # 如果没有头寸，返回低风险结果
            if not positions:
                self.logger.warning("没有投资组合头寸，返回空结果")
                return {
                    "risk_score": 0,
                    "risk_level": "低",
                    "description": "投资组合为空，无风险",
                    "risk_metrics": {},
                    "risk_factors": [],
                    "recommendations": [
                        "开始投资以获取收益",
                        "从小额投资开始，逐步了解DeFi生态",
                    ],
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }

            # 准备投资组合数据
            portfolio_data = {
                "positions": positions,
                "wallet_address": wallet_address,  # 可以从positions中提取如果有的话
            }

            # 使用核心方法进行分析
            assessment = await self.analyze_portfolio(portfolio_data)

            # 提取风险因子信息
            risk_factors = []
            for factor in assessment.risk_factors.values():
                risk_factors.append(
                    {
                        "name": factor.name,
                        "score": factor.score,
                        "weight": factor.weight,
                        "description": factor.description,
                        "trend": factor.trend,
                    }
                )

            # 转换为AI预测器格式的结果
            result = {
                "risk_score": assessment.total_score,
                "risk_level": assessment.risk_level.value,
                "description": f"投资组合风险分析完成，当前风险等级为{assessment.risk_level.value}",
                "risk_metrics": {
                    "market_risk": self._get_risk_type_score(assessment, "MARKET"),
                    "protocol_risk": self._get_risk_type_score(assessment, "PROTOCOL"),
                    "liquidity_risk": self._get_risk_type_score(
                        assessment, "LIQUIDITY"
                    ),
                    "smart_contract_risk": self._get_risk_type_score(
                        assessment, "SMART_CONTRACT"
                    ),
                    "correlation_risk": self._get_risk_type_score(
                        assessment, "CORRELATION"
                    ),
                },
                "risk_factors": risk_factors,
                "recommendations": assessment.recommendations,
                "warnings": assessment.warnings,
                "monitoring_points": assessment.monitoring_points,
                "analysis_timestamp": assessment.timestamp.isoformat(),
            }

            return result

        except Exception as e:
            self.logger.error(f"分析投资组合风险时出错: {str(e)}")
            return {
                "risk_score": 50,
                "risk_level": "中",
                "description": f"分析过程中出错: {str(e)}",
                "risk_metrics": {},
                "risk_factors": [],
                "recommendations": ["建议重新分析或联系技术支持"],
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

    def set_weights(self, weights: Dict[str, float]) -> None:
        """
        设置风险权重

        Args:
            weights: 风险权重字典，键为风险类型，值为权重
        """
        self.logger.info(f"设置风险权重: {weights}")
        self.risk_weights = weights

    async def simulate_market_scenario(
        self, wallet_address: str, scenario: str, blockchain_service=None
    ) -> Dict[str, Any]:
        """
        模拟极端市场情景下的投资组合表现

        Args:
            wallet_address: 钱包地址
            scenario: 市场情景类型，支持 market_crash(市场崩盘)、bull_run(牛市)、
                     defi_hack(DeFi黑客事件)、regulatory_crackdown(监管打击)
            blockchain_service: 区块链服务实例，用于获取钱包头寸

        Returns:
            模拟情景分析结果
        """
        self.logger.info(f"开始模拟市场情景: {wallet_address}, 情景: {scenario}")

        try:
            # 验证情景类型
            valid_scenarios = [
                "market_crash",
                "bull_run",
                "defi_hack",
                "regulatory_crackdown",
            ]
            if scenario not in valid_scenarios:
                self.logger.warning(
                    f"无效的情景类型: {scenario}, 使用默认值: market_crash"
                )
                scenario = "market_crash"

            # 获取钱包头寸
            positions = []
            if blockchain_service:
                positions = await blockchain_service.get_all_positions(wallet_address)

            if not positions:
                self.logger.warning(f"钱包 {wallet_address} 没有检测到头寸，返回空结果")
                return {
                    "wallet_address": wallet_address,
                    "scenario": scenario,
                    "error": "未检测到投资组合头寸，无法模拟市场情景",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # 计算当前总价值
            current_total = sum(position.get("usd_value", 0) for position in positions)

            # 设置不同情景的参数
            if scenario == "market_crash":
                title = "市场崩盘情景模拟"
                description = (
                    "模拟加密市场急剧下跌30-50%的情景下，您的投资组合可能受到的影响"
                )
                asset_changes = {
                    "ETH": -0.45,  # ETH下跌45%
                    "BTC": -0.40,  # BTC下跌40%
                    "USDC": -0.02,  # USDC轻微下跌(脱锚风险)
                    "USDT": -0.05,  # USDT轻微下跌
                    "DAI": -0.08,  # DAI下跌
                    "OTHER": -0.50,  # 其他代币下跌50%
                }
                liquidation_risk = "高"
                impermanent_loss = "极高"

            elif scenario == "bull_run":
                title = "牛市情景模拟"
                description = (
                    "模拟加密市场强势上涨50-100%的情景下，您的投资组合可能获得的收益"
                )
                asset_changes = {
                    "ETH": 0.80,  # ETH上涨80%
                    "BTC": 0.60,  # BTC上涨60%
                    "USDC": 0.0,  # 稳定币保持不变
                    "USDT": 0.0,  # 稳定币保持不变
                    "DAI": 0.0,  # 稳定币保持不变
                    "OTHER": 1.20,  # 其他代币上涨120%
                }
                liquidation_risk = "极低"
                impermanent_loss = "中等"

            elif scenario == "defi_hack":
                title = "DeFi协议黑客攻击情景模拟"
                description = (
                    "模拟主要DeFi协议遭受黑客攻击的情景下，您的投资组合可能面临的风险"
                )
                asset_changes = {
                    "ETH": -0.15,  # ETH下跌15%
                    "BTC": -0.10,  # BTC下跌10%
                    "USDC": -0.01,  # USDC几乎不变
                    "USDT": -0.01,  # USDT几乎不变
                    "DAI": -0.03,  # DAI轻微下跌
                    "OTHER": -0.25,  # 其他代币下跌25%
                }
                liquidation_risk = "中等"
                impermanent_loss = "高"

            else:  # regulatory_crackdown
                title = "监管打击情景模拟"
                description = "模拟全球监管机构对加密货币实施严厉监管的情景下，您的投资组合可能面临的影响"
                asset_changes = {
                    "ETH": -0.30,  # ETH下跌30%
                    "BTC": -0.25,  # BTC下跌25%
                    "USDC": -0.15,  # USDC下跌15%
                    "USDT": -0.20,  # USDT下跌20%
                    "DAI": -0.10,  # DAI下跌10%
                    "OTHER": -0.40,  # 其他代币下跌40%
                }
                liquidation_risk = "高"
                impermanent_loss = "高"

            # 计算情景下的资产价值变化
            simulated_positions = []
            simulated_total = 0
            liquidations = []

            for position in positions:
                asset = position.get("asset", "OTHER").upper()
                if "/" in asset:
                    asset = asset.split("/")[0]  # 处理类似 "ETH/USDC" 格式的资产名称

                current_value = position.get("usd_value", 0)

                # 获取资产价格变化率
                change_rate = asset_changes.get(asset, asset_changes.get("OTHER", -0.3))

                # 如果是借贷头寸，检查是否会被清算
                is_borrowing = position.get("type", "") == "borrowing"
                health_factor = position.get("health_factor", 2.0)

                new_value = current_value * (1 + change_rate)
                simulated_total += new_value

                # 检查是否会被清算
                will_liquidate = False
                if is_borrowing and health_factor < 1.2 and change_rate < 0:
                    # 简化模型：如果健康因子低，且市场下跌，则可能被清算
                    liquidation_chance = min(
                        0.9, 1.0 - health_factor + abs(change_rate)
                    )
                    import random

                    will_liquidate = random.random() < liquidation_chance

                if will_liquidate:
                    liquidations.append(
                        {
                            "asset": position.get("asset", ""),
                            "protocol": position.get("protocol", ""),
                            "value_usd": current_value,
                            "health_factor": health_factor,
                        }
                    )

                simulated_positions.append(
                    {
                        "asset": position.get("asset", ""),
                        "protocol": position.get("protocol", ""),
                        "type": position.get("type", ""),
                        "current_value_usd": current_value,
                        "simulated_value_usd": new_value,
                        "change_usd": new_value - current_value,
                        "change_percent": change_rate * 100,
                        "liquidated": will_liquidate,
                    }
                )

            # 使用AI预测器生成风险缓解建议
            risk_mitigation = []
            if self.ai_predictor:
                try:
                    # 准备AI分析上下文
                    analysis_context = {
                        "scenario": scenario,
                        "positions": simulated_positions,
                        "liquidations": liquidations,
                        "value_change_percent": (
                            (simulated_total - current_total) / current_total * 100
                            if current_total > 0
                            else 0
                        ),
                    }

                    # 调用AI预测器的analyze_generic方法
                    ai_result = self.ai_predictor.analyze_generic(
                        "market_scenario", analysis_context
                    )

                    if isinstance(ai_result, dict) and "recommendations" in ai_result:
                        risk_mitigation = ai_result.get("recommendations", [])
                except Exception as e:
                    self.logger.error(f"生成AI风险缓解建议时出错: {str(e)}")

            # 如果AI未能生成建议，使用默认建议
            if not risk_mitigation:
                if scenario == "market_crash":
                    risk_mitigation = [
                        "减少借贷头寸，降低杠杆率",
                        "增加稳定币储备，准备在市场低点买入",
                        "设置止损点，防止进一步下跌",
                        "增加抵押品，防止清算",
                    ]
                elif scenario == "bull_run":
                    risk_mitigation = [
                        "定期获利了结，锁定部分盈利",
                        "调整资产配置，防止过度集中",
                        "关注市场情绪指标，警惕市场过热",
                        "考虑对冲策略，防范突然回调",
                    ]
                elif scenario == "defi_hack":
                    risk_mitigation = [
                        "分散资产到多个协议，降低单一协议风险",
                        "优先使用经过多次审计的成熟协议",
                        "关注协议安全更新和公告",
                        "考虑使用去中心化保险产品",
                    ]
                else:  # regulatory_crackdown
                    risk_mitigation = [
                        "关注各国监管动态，适时调整投资策略",
                        "增加合规性高的资产比例",
                        "考虑分散到不同司法管辖区的协议",
                        "准备应急撤离计划，确保资金安全",
                    ]

            # 组装结果
            result = {
                "wallet_address": wallet_address,
                "scenario": scenario,
                "title": title,
                "description": description,
                "current_portfolio_value": current_total,
                "simulated_portfolio_value": simulated_total,
                "value_change_usd": simulated_total - current_total,
                "value_change_percent": (
                    (simulated_total - current_total) / current_total * 100
                    if current_total > 0
                    else 0
                ),
                "positions": simulated_positions,
                "liquidations": liquidations,
                "risk_factors": {
                    "liquidation_risk": liquidation_risk,
                    "impermanent_loss": impermanent_loss,
                    "market_correlation": (
                        "高" if scenario in ["market_crash", "bull_run"] else "中"
                    ),
                    "protocol_risk": "高" if scenario == "defi_hack" else "中",
                    "regulatory_risk": (
                        "高" if scenario == "regulatory_crackdown" else "中"
                    ),
                },
                "risk_mitigation": risk_mitigation,
                "simulation_metrics": {
                    "max_drawdown": (
                        max(
                            abs(
                                (simulated_total - current_total) / current_total * 100
                            ),
                            0,
                        )
                        if current_total > 0
                        else 0
                    ),
                    "risk_level": (
                        "高"
                        if simulated_total < current_total * 0.7
                        else "中" if simulated_total < current_total else "低"
                    ),
                    "affected_protocols": len(
                        set(
                            p.get("protocol", "")
                            for p in simulated_positions
                            if p.get("change_percent", 0) < -20
                        )
                    ),
                    "liquidation_count": len(liquidations),
                },
                "timestamp": datetime.utcnow().isoformat(),
                "is_ai_enhanced": self.ai_predictor is not None,
            }

            self.logger.info(f"市场情景模拟完成: {wallet_address}, 情景: {scenario}")
            return result

        except Exception as e:
            self.logger.error(f"模拟市场情景时出错: {str(e)}")
            return {
                "wallet_address": wallet_address,
                "scenario": scenario,
                "error": f"模拟市场情景失败: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }
