from typing import Dict, List, Any, Optional, Union
from app.models.domain.risk import RiskFactor, RiskAssessment, RiskLevel, RiskType
import uuid
from datetime import datetime
import logging
import asyncio
import numpy as np  # <-- Added import
from app.core.config import settings
from app.services.ai_predictor import AiPredictor
from dataclasses import dataclass
from cachetools import TTLCache  # <-- Added import
from app.models.domain.risk import (  # <-- Added imports
    RiskAnalysisResult,
    RiskMetrics,
    RiskAnalysis,
)


@dataclass
class MarketRiskResult:
    """市场风险分析结果"""

    risk_type: str = "MARKET"
    target: str = ""
    score: float = 0.0
    factors: List[RiskFactor] = None
    recommendations: List[str] = None
    monitoring_points: List[str] = None
    ai_insights: List[str] = None

    def __post_init__(self):
        if self.factors is None:
            self.factors = []
        if self.recommendations is None:
            self.recommendations = []
        if self.monitoring_points is None:
            self.monitoring_points = []
        if self.ai_insights is None:
            self.ai_insights = []


class RiskEngine:
    """风险评估引擎"""

    def __init__(
        self, blockchain_service=None, ai_service=None, cache_ttl=3600
    ):  # <-- Added cache_ttl
        """
        初始化风险评估引擎

        Args:
            blockchain_service: 区块链服务实例
            ai_service: AI服务实例，如果为None则不使用AI服务
            cache_ttl: 缓存时间 (秒), 默认1小时
        """
        self.logger = logging.getLogger("defi_risk.risk_engine")
        self.risk_analyzers = {}
        self.risk_weights = settings.RISK_WEIGHTS
        self.blockchain_service = blockchain_service
        self.ai_service = ai_service
        self.analysis_cache = TTLCache(
            maxsize=1024, ttl=cache_ttl
        )  # <-- Added cache instance

        # 风险类型映射表 - 用于将注册时使用的小写风险类型映射到RiskFactor.id中使用的中文风险类型
        self.risk_type_map = {
            "market": "市场风险",
            "protocol": "协议风险",
            "liquidity": "流动性风险",
            "correlation": "相关性风险",
            "smart_contract": "智能合约风险",
            "dex": "DEX风险",  # 添加DEX风险类型映射
        }

        # 不再自动创建ai_predictor，改为通过外部依赖注入
        self.ai_predictor = None
        if ai_service and hasattr(ai_service, "get_predictor"):
            self.ai_predictor = ai_service.get_predictor()

        self.logger.info(
            f"风险引擎初始化完成: blockchain_service={blockchain_service}, ai_service={ai_service}, cache_ttl={cache_ttl}"  # <-- Updated log
        )

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

        # 注入依赖服务
        if hasattr(analyzer, "ai_service") and self.ai_service:
            analyzer.ai_service = self.ai_service

        if hasattr(analyzer, "ai_predictor") and self.ai_predictor:
            analyzer.ai_predictor = self.ai_predictor

        if hasattr(analyzer, "blockchain_service") and self.blockchain_service:
            analyzer.blockchain_service = self.blockchain_service

        # 只为需要 risk_engine 的分析器设置引用
        # 目前只有 ProtocolRiskAnalyzer 需要此引用
        if (
            hasattr(analyzer, "risk_engine")
            and analyzer.__class__.__name__ == "ProtocolRiskAnalyzer"
        ):
            analyzer.risk_engine = self

        self.risk_analyzers[risk_type] = analyzer

    def _get_risk_type_score(
        self, risk_factors: Dict[str, RiskFactor], risk_type: str
    ) -> float:
        """
        计算特定风险类型的加权平均分

        Args:
            risk_factors: 风险因子字典
            risk_type: 风险类型 (例如: "市场风险", "协议风险" 等)

        Returns:
            float: 该风险类型的加权平均分
        """
        try:
            if not risk_factors:
                self.logger.warning(f"没有找到风险因子，返回默认分数50")
                return 50.0

            # 筛选出特定风险类型的因子
            type_factors = [
                f for f in risk_factors.values() if f.id.startswith(risk_type)
            ]

            if not type_factors:
                self.logger.warning(
                    f"没有找到{risk_type}类型的风险因子，返回默认分数50"
                )
                return 50.0

            # 计算加权总分和权重总和
            total_weighted_score = 0.0
            total_weight = 0.0

            for factor in type_factors:
                # 获取基础权重
                weight = factor.weight

                # 应用趋势调整
                trend_adjustment = 1.0
                if factor.trend == "上升":
                    trend_adjustment = 1.1  # 上升趋势增加10%权重
                elif factor.trend == "下降":
                    trend_adjustment = 0.9  # 下降趋势减少10%权重

                # 计算调整后的权重和分数
                adjusted_weight = weight * trend_adjustment
                total_weighted_score += factor.score * adjusted_weight
                total_weight += adjusted_weight

            # 计算加权平均分
            if total_weight > 0:
                average_score = total_weighted_score / total_weight
                self.logger.info(f"{risk_type}的加权平均分: {average_score:.2f}")
                return average_score
            else:
                self.logger.warning(f"{risk_type}的总权重为0，返回默认分数50")
                return 50.0

        except Exception as e:
            self.logger.error(f"计算{risk_type}风险评分时出错: {str(e)}")
            return 50.0  # 出错时返回默认分数

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
        analyzers_map = {}  # 用于记录任务和分析器的映射关系

        for risk_type, analyzer in self.risk_analyzers.items():
            task = self._get_risk_factors(risk_type, analyzer, portfolio_data)
            tasks.append(task)
            analyzers_map[task] = risk_type

        try:
            # 等待所有分析器完成，使用return_exceptions=True来避免一个任务失败导致所有任务失败
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果，包括可能的异常
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 获取对应的风险类型
                    risk_type = analyzers_map.get(tasks[i], f"Unknown_{i}")
                    self.logger.error(f"风险分析器 {risk_type} 执行失败: {str(result)}")
                    # 对于失败的分析器，添加一个空列表作为其结果
                    continue

                # 正常处理结果
                for factor in result:
                    all_risk_factors[factor.id] = factor

        except Exception as e:
            self.logger.error(f"执行风险分析任务时出错: {str(e)}")
            # 即使出错，我们仍然尝试继续处理已收集到的风险因子

        # 计算总体风险评分
        total_score = self._calculate_total_score(all_risk_factors)

        # 确定风险等级
        risk_level = self._determine_risk_level(total_score)

        try:
            # 生成建议和监控点
            recommendations = await self._generate_recommendations(all_risk_factors)
        except Exception as e:
            self.logger.error(f"生成建议时出错: {str(e)}")
            recommendations = ["无法生成建议，请稍后再试"]

        try:
            monitoring_points = await self._generate_monitoring_points(all_risk_factors)
        except Exception as e:
            self.logger.error(f"生成监控点时出错: {str(e)}")
            monitoring_points = ["监控投资组合总体表现", "关注主要资产的市场动态"]

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
            chinese_risk_type = self.risk_type_map.get(risk_type, risk_type)
            # 过滤出当前风险类型的因子
            type_factors = [
                f for f in risk_factors.values() if f.id.startswith(chinese_risk_type)
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

        if any(f.id.startswith("市场风险") for f in high_risk_factors):
            strategies.append("考虑增加投资组合多样性，减少对单一市场的依赖")

        if any(f.id.startswith("智能合约风险") for f in high_risk_factors):
            strategies.append("使用经过审计的协议，并考虑使用智能合约保险")

        if any(f.id.startswith("流动性风险") for f in high_risk_factors):
            strategies.append("增加流动性较高的资产比例，避免流动性陷阱")

        if any(f.id.startswith("协议风险") for f in high_risk_factors):
            strategies.append("考虑使用多协议分散风险")

        if any(f.id.startswith("相关性风险") for f in high_risk_factors):
            strategies.append("考虑使用多资产分散风险")

        # 添加更多策略...

        return strategies

    async def _generate_monitoring_points(
        self, risk_factors: Dict[str, RiskFactor]
    ) -> List[str]:
        """生成监控点"""
        all_monitoring_points = []

        # 从各分析器获取监控点
        for risk_type, analyzer in self.risk_analyzers.items():
            # 使用风险类型映射表获取对应的中文风险类型
            chinese_risk_type = self.risk_type_map.get(risk_type, risk_type)

            # 过滤出当前风险类型的因子
            type_factors = [
                f for f in risk_factors.values() if f.id.startswith(chinese_risk_type)
            ]

            self.logger.debug(
                f"风险类型 {risk_type} (中文映射: {chinese_risk_type}) 找到 {len(type_factors)} 个风险因子"
            )

            if type_factors:
                try:
                    monitoring_points = await analyzer.get_monitoring_points(
                        type_factors
                    )
                    self.logger.info(
                        f"风险类型 {risk_type} 生成了 {len(monitoring_points)} 个监控点"
                    )
                    all_monitoring_points.extend(monitoring_points)
                except Exception as e:
                    self.logger.error(f"获取监控点时出错 ({risk_type}): {str(e)}")
                    # 记录更多调试信息
                    self.logger.error(f"错误详情: {e.__class__.__name__}: {str(e)}")
                    import traceback

                    self.logger.error(f"调用栈: {traceback.format_exc()}")
            else:
                self.logger.warning(
                    f"风险类型 {risk_type} 没有找到匹配的风险因子，无法生成监控点"
                )
                # 记录所有可用的风险因子ID，帮助调试
                if risk_factors:
                    self.logger.debug(
                        f"可用的风险因子ID: {[f.id for f in risk_factors.values()]}"
                    )

        # 如果没有收集到任何监控点，添加默认监控点
        if not all_monitoring_points:
            self.logger.warning("没有从任何风险分析器收集到监控点，添加默认监控点")
            all_monitoring_points = [
                "定期评估投资组合的整体风险状况",
                "监控主要资产的价格和波动性变化",
                "关注使用的DeFi协议的安全状态和TVL变化",
                "追踪投资组合中资产的相关性变化",
                "注意市场整体趋势和情绪指标的变化",
            ]

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
            # 将RiskType枚举值映射到中文风险类型
            chinese_type_name = self.risk_type_map.get(type_name, type_name)

            # 过滤出当前风险类型的因子
            type_factors = [
                f for f in risk_factors.values() if f.id.startswith(chinese_type_name)
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
            # 初始化数据收集对象
            protocol_data = {
                "protocol_metadata": {"name": protocol},
                "basic_analysis": {},
                "historical_tvl": [],
                "chain_distribution": {},
            }

            # 获取DeFi Safety评分（如果区块链服务可用）
            defi_safety_factor = None
            if self.blockchain_service:
                try:
                    # 直接调用blockchain_service的analyze_protocol_security方法获取DeFi Safety数据
                    defi_safety_factor = (
                        await self.blockchain_service.analyze_protocol_security(
                            protocol
                        )
                    )

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
                    self.logger.error(f"获取协议安全数据时出错: {str(e)}")

            # 使用AI预测器分析风险（如果可用）
            ai_analysis = None
            if self.ai_predictor:
                try:
                    # 使用AI预测器分析
                    ai_analysis = self.ai_predictor.analyze_defi_protocol_risk(
                        protocol_data
                    )
                except Exception as e:
                    self.logger.error(f"使用AI预测器分析协议风险时出错: {str(e)}")

            # 生成最终风险分析结果
            if defi_safety_factor and ai_analysis:
                # 如果两种方法都可用，结合二者的分析结果
                # AI分析的权重0.6，DeFi Safety的权重0.4
                ai_score = ai_analysis.get("risk_metrics", {}).get("security_risk", 50)
                defi_safety_score = defi_safety_factor.score

                final_score = ai_score * 0.6 + defi_safety_score * 0.4

                # 合并描述
                description = f"{protocol}协议安全风险评分: {final_score:.1f}。"
                description += f"DeFi Safety评分: {defi_safety_factor.data_points[0].get('pqr_score', 'N/A') if defi_safety_factor.data_points else 'N/A'}。"
                if "recommendations" in ai_analysis and ai_analysis["recommendations"]:
                    description += f" AI建议: {ai_analysis['recommendations'][0]}"

                # 创建合并后的风险因子
                merged_data_points = []
                if defi_safety_factor.data_points:
                    merged_data_points.extend(defi_safety_factor.data_points)
                if ai_analysis and "data_points" in ai_analysis:
                    merged_data_points.extend(ai_analysis["data_points"])

                # 创建合并的元数据
                merged_metadata = {
                    "ai_analysis": ai_analysis,
                    "defi_safety": defi_safety_factor.metadata,
                }

                return self.create_risk_factor(
                    risk_type="PROTOCOL",
                    factor_name="协议安全性",
                    score=final_score,
                    weight=0.4,
                    description=description,
                    trend=defi_safety_factor.trend,
                    data_points=merged_data_points,
                    metadata=merged_metadata,
                )
            elif defi_safety_factor:
                # 如果只有DeFi Safety数据可用
                return defi_safety_factor
            elif ai_analysis:
                # 如果只有AI分析可用
                security_score = ai_analysis.get("risk_metrics", {}).get(
                    "security_risk", 50
                )

                # 生成描述
                description = f"{protocol}协议安全风险评分: {security_score}"
                if "recommendations" in ai_analysis and ai_analysis["recommendations"]:
                    description += f"。建议: {ai_analysis['recommendations'][0]}"

                return self.create_risk_factor(
                    risk_type="PROTOCOL",
                    factor_name="协议安全性",
                    score=security_score,
                    weight=0.4,
                    description=description,
                    trend="稳定",
                    data_points=ai_analysis.get("data_points", []),
                    metadata=ai_analysis,
                )
            else:
                # 如果两种方法都不可用，返回默认风险因子
                return self.create_risk_factor(
                    risk_type="PROTOCOL",
                    factor_name="协议安全性",
                    score=70,  # 默认高风险
                    weight=0.4,
                    description=f"{protocol}协议安全风险分析失败",
                    trend="稳定",
                    data_points=[{"protocol": protocol, "security_score": 70}],
                )

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
                # 检查对象类型，根据不同类型处理
                is_dict = isinstance(position, dict)

                # 检查是否为嵌套结构（协议包含多个positions）
                if (
                    is_dict
                    and "positions" in position
                    and isinstance(position["positions"], list)
                ):
                    # 处理嵌套结构
                    inner_positions = position.get("positions", [])
                    for pos in inner_positions:
                        try:
                            # 检查内部位置对象类型
                            pos_is_dict = isinstance(pos, dict)

                            # 根据对象类型获取资产名称和价值
                            if pos_is_dict:
                                asset_name = pos.get("asset", "unknown")
                                # 尝试获取usd_value，如果不存在则使用amount字段
                                asset_value = float(
                                    pos.get("usd_value", pos.get("amount", 0))
                                )
                            else:
                                # 假设是PlatformAsset或类似对象，直接访问属性
                                asset_name = getattr(pos, "asset", "unknown")
                                # 尝试获取usd_value，如果不存在则使用amount字段
                                asset_value = float(
                                    getattr(pos, "usd_value", getattr(pos, "amount", 0))
                                )

                            # 处理资产名称
                            if (
                                isinstance(asset_name, str) and "/" in asset_name
                            ):  # 处理类似 "ETH/USDC" 格式的资产名称
                                asset_name = asset_name.split("/")[0]  # 使用主资产

                            # 累加资产价值
                            if asset_name in assets:
                                assets[asset_name] += asset_value
                            else:
                                assets[asset_name] = asset_value

                            total_value += asset_value
                        except (ValueError, TypeError, AttributeError) as e:
                            self.logger.warning(
                                f"处理位置数据时出错: {str(e)}, position: {pos}"
                            )
                else:
                    # 处理非嵌套结构
                    try:
                        # 根据对象类型获取资产名称和价值
                        if is_dict:
                            asset_name = position.get("asset", "unknown")
                            # 尝试获取usd_value，如果不存在则使用amount字段
                            asset_value = float(
                                position.get("usd_value", position.get("amount", 0))
                            )
                        else:
                            # 假设是PlatformAsset或类似对象，直接访问属性
                            asset_name = getattr(position, "asset", "unknown")
                            # 尝试获取usd_value，如果不存在则使用amount字段
                            asset_value = float(
                                getattr(
                                    position,
                                    "usd_value",
                                    getattr(position, "amount", 0),
                                )
                            )

                        # 处理资产名称
                        if (
                            isinstance(asset_name, str) and "/" in asset_name
                        ):  # 处理类似 "ETH/USDC" 格式的资产名称
                            asset_name = asset_name.split("/")[0]  # 使用主资产

                        # 累加资产价值
                        if asset_name in assets:
                            assets[asset_name] += asset_value
                        else:
                            assets[asset_name] = asset_value

                        total_value += asset_value
                    except (ValueError, TypeError, AttributeError) as e:
                        self.logger.warning(
                            f"处理位置数据时出错: {str(e)}, position类型: {type(position)}"
                        )

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
                    # 修改数据结构，转换为字典格式而不是列表格式
                    assets_dict = (
                        {
                            item["name"]: item["value"] / total_value
                            for item in concentration_data["assets"]
                        }
                        if total_value > 0
                        else {}
                    )
                    concentration_data_dict = {
                        "assets": assets_dict,
                        "total_value": total_value,
                    }

                    concentration_risk = self.ai_predictor.analyze_concentration_risk(
                        concentration_data_dict
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

            # 添加AI洞察内容 - 新增的部分
            # 基于风险因素生成AI洞察
            if len(result.factors) > 0:
                # 确保ai_insights已初始化
                if not result.ai_insights:
                    result.ai_insights = []

                # 根据总体风险分数生成总体洞察
                if result.score < 30:
                    result.ai_insights.append(
                        f"您的投资组合市场风险较低(评分:{result.score:.1f})，整体风险状况良好"
                    )
                elif result.score < 50:
                    result.ai_insights.append(
                        f"您的投资组合市场风险适中(评分:{result.score:.1f})，保持合理平衡"
                    )
                elif result.score < 70:
                    result.ai_insights.append(
                        f"您的投资组合市场风险偏高(评分:{result.score:.1f})，建议适当调整"
                    )
                else:
                    result.ai_insights.append(
                        f"您的投资组合市场风险较高(评分:{result.score:.1f})，需要注意风险控制"
                    )

                # 针对每个风险因素添加具体洞察
                for factor in result.factors:
                    if factor.name == "资产集中度风险" and factor.score > 60:
                        result.ai_insights.append(
                            f"资产集中度风险偏高({factor.score:.1f})，建议增加资产多样性"
                        )
                    elif factor.name == "资产相关性风险" and factor.score > 60:
                        result.ai_insights.append(
                            f"资产相关性风险偏高({factor.score:.1f})，建议投资相关性较低的资产"
                        )
                    elif factor.name == "市场波动风险" and factor.score > 60:
                        result.ai_insights.append(
                            f"市场波动风险明显({factor.score:.1f})，市场可能即将进入动荡期"
                        )
                    elif "集中" in factor.name and factor.score > 60:
                        result.ai_insights.append(
                            f"{factor.name}偏高({factor.score:.1f})，建议优化资产分配"
                        )
                    elif "相关" in factor.name and factor.score > 60:
                        result.ai_insights.append(
                            f"{factor.name}偏高({factor.score:.1f})，建议关注资产间关联性"
                        )
                    elif "波动" in factor.name and factor.score > 60:
                        result.ai_insights.append(
                            f"{factor.name}偏高({factor.score:.1f})，建议关注市场趋势变化"
                        )

                # 添加整体投资组合洞察
                if len(assets) > 5:
                    result.ai_insights.append(
                        f"您的投资组合包含{len(assets)}种资产，多样性较好"
                    )
                elif len(assets) > 2:
                    result.ai_insights.append(
                        f"您的投资组合包含{len(assets)}种资产，多样性一般"
                    )
                else:
                    result.ai_insights.append(
                        f"您的投资组合仅包含{len(assets)}种资产，建议增加多样性"
                    )

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
                                "name": factor.name,  # 使用name而不是factor_name
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
                        self.ai_predictor.generate_market_risk_recommendations(
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
                                "name": factor.name,  # 使用name而不是factor_name
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
                        self.ai_predictor.generate_market_risk_monitoring_points(
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
            result.ai_insights = ["由于分析过程中出现错误，无法提供详细的市场风险洞察"]
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

        # 使用风险类型和因子名称组合成风险因子ID
        factor_id = f"{risk_type}.{factor_name}"

        return RiskFactor(
            id=factor_id,  # 使用组合的ID
            name=factor_name,  # 只使用name，不使用factor_name
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
                    "monitoring_points": [
                        "关注市场整体趋势以寻找入场机会",
                        "追踪主流DeFi协议的安全性和稳定性",
                        "监控主要加密资产的价格走势",
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
                    "market_risk": self._get_risk_type_score(
                        assessment.risk_factors, "市场风险"
                    ),
                    "protocol_risk": self._get_risk_type_score(
                        assessment.risk_factors, "协议风险"
                    ),
                    "liquidity_risk": self._get_risk_type_score(
                        assessment.risk_factors, "流动性风险"
                    ),
                    "smart_contract_risk": self._get_risk_type_score(
                        assessment.risk_factors, "智能合约风险"
                    ),
                    "correlation_risk": self._get_risk_type_score(
                        assessment.risk_factors, "相关性风险"
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
                "monitoring_points": [
                    "监控投资组合总价值变化趋势",
                    "关注主要资产的价格波动",
                    "定期检查投资组合的资产配置比例",
                    "留意市场整体风险指标变化",
                    "观察协议安全性和黑客攻击新闻",
                ],
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

    def set_weights(self, weights: Dict[str, float]):
        """
        设置风险权重

        Args:
            weights: 风险类型到权重的映射
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
            scenario: 市场情景类型，支持:
                     - market_crash: 市场崩盘
                     - bull_run: 牛市
                     - defi_hack: DeFi黑客事件
                     - regulatory_crackdown: 监管打击
                     - stablecoin_depeg: 稳定币脱锚
                     - chain_outage: 公链故障
                     - liquidity_crisis: 流动性危机
                     - inflation_surge: 通胀飙升
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
                "stablecoin_depeg",
                "chain_outage",
                "liquidity_crisis",
                "inflation_surge",
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
            current_total = 0
            for position in positions:
                # 尝试获取usd_value或amount字段
                if "usd_value" in position:
                    current_total += float(position.get("usd_value", 0))
                elif "amount" in position:
                    current_total += float(position.get("amount", 0))
                # 处理嵌套结构
                elif "positions" in position and isinstance(
                    position["positions"], list
                ):
                    for pos in position["positions"]:
                        if hasattr(pos, "amount"):
                            current_total += float(pos.amount)
                        elif isinstance(pos, dict):
                            current_total += float(pos.get("amount", 0))

            # 创建基础资产价格变化映射
            # 扩展为更全面的加密资产列表
            base_assets = {
                # 主要公链代币
                "BTC": {
                    "large_cap": True,
                    "type": "layer1",
                    "volatility": 0.8,
                    "market_corr": 0.9,
                },
                "ETH": {
                    "large_cap": True,
                    "type": "layer1",
                    "volatility": 0.9,
                    "market_corr": 0.95,
                },
                "SOL": {
                    "large_cap": True,
                    "type": "layer1",
                    "volatility": 1.2,
                    "market_corr": 0.85,
                },
                "BNB": {
                    "large_cap": True,
                    "type": "exchange",
                    "volatility": 0.85,
                    "market_corr": 0.8,
                },
                "ADA": {
                    "large_cap": True,
                    "type": "layer1",
                    "volatility": 1.1,
                    "market_corr": 0.8,
                },
                "XRP": {
                    "large_cap": True,
                    "type": "payment",
                    "volatility": 0.9,
                    "market_corr": 0.7,
                },
                "AVAX": {
                    "large_cap": True,
                    "type": "layer1",
                    "volatility": 1.25,
                    "market_corr": 0.85,
                },
                "DOT": {
                    "large_cap": True,
                    "type": "layer1",
                    "volatility": 1.15,
                    "market_corr": 0.8,
                },
                "MATIC": {
                    "large_cap": True,
                    "type": "layer2",
                    "volatility": 1.2,
                    "market_corr": 0.85,
                },
                "NEAR": {
                    "large_cap": False,
                    "type": "layer1",
                    "volatility": 1.3,
                    "market_corr": 0.8,
                },
                "FTM": {
                    "large_cap": False,
                    "type": "layer1",
                    "volatility": 1.4,
                    "market_corr": 0.85,
                },
                "ATOM": {
                    "large_cap": False,
                    "type": "layer1",
                    "volatility": 1.1,
                    "market_corr": 0.8,
                },
                # DeFi协议代币
                "UNI": {
                    "large_cap": True,
                    "type": "defi",
                    "volatility": 1.3,
                    "market_corr": 0.9,
                },
                "AAVE": {
                    "large_cap": True,
                    "type": "defi",
                    "volatility": 1.35,
                    "market_corr": 0.9,
                },
                "COMP": {
                    "large_cap": False,
                    "type": "defi",
                    "volatility": 1.4,
                    "market_corr": 0.9,
                },
                "MKR": {
                    "large_cap": False,
                    "type": "defi",
                    "volatility": 1.3,
                    "market_corr": 0.85,
                },
                "SNX": {
                    "large_cap": False,
                    "type": "defi",
                    "volatility": 1.5,
                    "market_corr": 0.9,
                },
                "CRV": {
                    "large_cap": False,
                    "type": "defi",
                    "volatility": 1.45,
                    "market_corr": 0.9,
                },
                "SUSHI": {
                    "large_cap": False,
                    "type": "defi",
                    "volatility": 1.6,
                    "market_corr": 0.85,
                },
                "BAL": {
                    "large_cap": False,
                    "type": "defi",
                    "volatility": 1.5,
                    "market_corr": 0.85,
                },
                "LINK": {
                    "large_cap": True,
                    "type": "oracle",
                    "volatility": 1.2,
                    "market_corr": 0.8,
                },
                # 稳定币
                "USDC": {
                    "large_cap": True,
                    "type": "stablecoin",
                    "volatility": 0.05,
                    "market_corr": 0.1,
                },
                "USDT": {
                    "large_cap": True,
                    "type": "stablecoin",
                    "volatility": 0.08,
                    "market_corr": 0.15,
                },
                "DAI": {
                    "large_cap": True,
                    "type": "stablecoin",
                    "volatility": 0.1,
                    "market_corr": 0.2,
                },
                "BUSD": {
                    "large_cap": True,
                    "type": "stablecoin",
                    "volatility": 0.07,
                    "market_corr": 0.15,
                },
                "TUSD": {
                    "large_cap": False,
                    "type": "stablecoin",
                    "volatility": 0.12,
                    "market_corr": 0.2,
                },
                "FRAX": {
                    "large_cap": False,
                    "type": "stablecoin",
                    "volatility": 0.15,
                    "market_corr": 0.25,
                },
                # NFT相关代币
                "APE": {
                    "large_cap": False,
                    "type": "nft",
                    "volatility": 1.7,
                    "market_corr": 0.75,
                },
                "SAND": {
                    "large_cap": False,
                    "type": "metaverse",
                    "volatility": 1.6,
                    "market_corr": 0.8,
                },
                "MANA": {
                    "large_cap": False,
                    "type": "metaverse",
                    "volatility": 1.6,
                    "market_corr": 0.8,
                },
            }

            # 协议特定影响
            protocol_impacts = {
                "Aave": {
                    "market_crash": {
                        "risk_multiplier": 1.2,
                        "liquidation_threshold_change": -0.05,
                    },
                    "bull_run": {
                        "risk_multiplier": 0.8,
                        "liquidation_threshold_change": 0.02,
                    },
                    "defi_hack": {"risk_multiplier": 1.8, "affected_chance": 0.3},
                    "regulatory_crackdown": {
                        "risk_multiplier": 1.3,
                        "compliance_score": 0.7,
                    },
                    "stablecoin_depeg": {
                        "risk_multiplier": 1.4,
                        "affected_assets": ["USDC", "USDT", "DAI"],
                    },
                    "chain_outage": {
                        "risk_multiplier": 1.1,
                        "affected_chains": ["Ethereum", "Polygon", "Avalanche"],
                    },
                    "liquidity_crisis": {
                        "risk_multiplier": 1.5,
                        "withdrawal_haircut": 0.2,
                    },
                    "inflation_surge": {
                        "risk_multiplier": 1.1,
                        "interest_rate_change": 0.15,
                    },
                },
                "Compound": {
                    "market_crash": {
                        "risk_multiplier": 1.25,
                        "liquidation_threshold_change": -0.04,
                    },
                    "bull_run": {
                        "risk_multiplier": 0.85,
                        "liquidation_threshold_change": 0.01,
                    },
                    "defi_hack": {"risk_multiplier": 1.7, "affected_chance": 0.25},
                    "regulatory_crackdown": {
                        "risk_multiplier": 1.35,
                        "compliance_score": 0.7,
                    },
                    "stablecoin_depeg": {
                        "risk_multiplier": 1.45,
                        "affected_assets": ["USDC", "DAI"],
                    },
                    "chain_outage": {
                        "risk_multiplier": 1.05,
                        "affected_chains": ["Ethereum"],
                    },
                    "liquidity_crisis": {
                        "risk_multiplier": 1.4,
                        "withdrawal_haircut": 0.18,
                    },
                    "inflation_surge": {
                        "risk_multiplier": 1.15,
                        "interest_rate_change": 0.2,
                    },
                },
                "Uniswap": {
                    "market_crash": {"risk_multiplier": 1.1, "slippage_increase": 0.15},
                    "bull_run": {"risk_multiplier": 0.7, "volume_multiplier": 2.0},
                    "defi_hack": {"risk_multiplier": 1.4, "affected_chance": 0.15},
                    "regulatory_crackdown": {
                        "risk_multiplier": 1.5,
                        "compliance_score": 0.5,
                    },
                    "stablecoin_depeg": {
                        "risk_multiplier": 1.3,
                        "slippage_increase": 0.3,
                    },
                    "chain_outage": {
                        "risk_multiplier": 1.2,
                        "affected_chains": ["Ethereum", "Optimism", "Arbitrum"],
                    },
                    "liquidity_crisis": {
                        "risk_multiplier": 1.6,
                        "slippage_increase": 0.5,
                    },
                    "inflation_surge": {
                        "risk_multiplier": 0.9,
                        "volume_multiplier": 1.2,
                    },
                },
                "Curve": {
                    "market_crash": {
                        "risk_multiplier": 1.1,
                        "peg_stability_impact": -0.1,
                    },
                    "bull_run": {"risk_multiplier": 0.8, "volume_multiplier": 1.5},
                    "defi_hack": {"risk_multiplier": 1.5, "affected_chance": 0.2},
                    "regulatory_crackdown": {
                        "risk_multiplier": 1.4,
                        "compliance_score": 0.55,
                    },
                    "stablecoin_depeg": {
                        "risk_multiplier": 1.7,
                        "peg_stability_impact": -0.3,
                    },
                    "chain_outage": {
                        "risk_multiplier": 1.15,
                        "affected_chains": ["Ethereum", "Optimism", "Fantom"],
                    },
                    "liquidity_crisis": {
                        "risk_multiplier": 1.5,
                        "withdrawal_haircut": 0.15,
                    },
                    "inflation_surge": {
                        "risk_multiplier": 1.05,
                        "interest_rate_change": 0.1,
                    },
                },
                # 设置其他协议的默认影响
                "OTHER": {
                    "market_crash": {
                        "risk_multiplier": 1.3,
                        "liquidation_threshold_change": -0.05,
                    },
                    "bull_run": {
                        "risk_multiplier": 0.9,
                        "liquidation_threshold_change": 0.0,
                    },
                    "defi_hack": {"risk_multiplier": 1.6, "affected_chance": 0.4},
                    "regulatory_crackdown": {
                        "risk_multiplier": 1.4,
                        "compliance_score": 0.5,
                    },
                    "stablecoin_depeg": {
                        "risk_multiplier": 1.5,
                        "affected_assets": ["All"],
                    },
                    "chain_outage": {
                        "risk_multiplier": 1.2,
                        "affected_chains": ["All"],
                    },
                    "liquidity_crisis": {
                        "risk_multiplier": 1.5,
                        "withdrawal_haircut": 0.25,
                    },
                    "inflation_surge": {
                        "risk_multiplier": 1.2,
                        "interest_rate_change": 0.2,
                    },
                },
            }

            # 设置不同情景的参数
            if scenario == "market_crash":
                title = "市场崩盘情景模拟"
                description = (
                    "模拟加密市场急剧下跌30-50%的情景下，您的投资组合可能受到的影响"
                )
                asset_changes = {}

                # 根据资产特性动态生成价格变化
                for asset, properties in base_assets.items():
                    volatility = properties["volatility"]
                    market_corr = properties["market_corr"]
                    asset_type = properties["type"]

                    # 基础下跌幅度，根据资产类型调整
                    if asset_type == "stablecoin":
                        # 稳定币轻微受影响
                        change = -0.02 * volatility
                    elif asset_type in ["layer1", "layer2"]:
                        # 公链代币受影响较大
                        change = -0.4 * volatility * market_corr
                    elif asset_type == "defi":
                        # DeFi代币受影响更大
                        change = -0.5 * volatility * market_corr
                    elif asset_type in ["metaverse", "nft"]:
                        # 元宇宙和NFT相关代币受影响最大
                        change = -0.6 * volatility * market_corr
                    else:
                        # 其他代币
                        change = -0.45 * volatility * market_corr

                    asset_changes[asset] = max(
                        -0.95, min(0, change)
                    )  # 限制在0到-95%之间

                # 为未列出的资产设置默认变化率
                default_change = -0.5
                liquidation_risk = "高"
                impermanent_loss = "极高"
                market_sentiment = "恐慌"
                market_direction = "下跌"
                volatility_level = "极高"

            elif scenario == "bull_run":
                title = "牛市情景模拟"
                description = (
                    "模拟加密市场强势上涨50-100%的情景下，您的投资组合可能获得的收益"
                )
                asset_changes = {}

                for asset, properties in base_assets.items():
                    volatility = properties["volatility"]
                    market_corr = properties["market_corr"]
                    asset_type = properties["type"]

                    if asset_type == "stablecoin":
                        # 稳定币保持稳定
                        change = 0.0
                    elif asset_type in ["layer1", "layer2"]:
                        # 公链代币大幅上涨
                        change = 0.7 * volatility * market_corr
                    elif asset_type == "defi":
                        # DeFi代币可能涨得更多
                        change = 0.9 * volatility * market_corr
                    elif asset_type in ["metaverse", "nft"]:
                        # 元宇宙和NFT相关代币涨幅可能最大
                        change = 1.1 * volatility * market_corr
                    else:
                        # 其他代币
                        change = 0.8 * volatility * market_corr

                    asset_changes[asset] = max(0, min(3.0, change))  # 限制在0到300%之间

                default_change = 0.8
                liquidation_risk = "极低"
                impermanent_loss = "中等"
                market_sentiment = "贪婪"
                market_direction = "上涨"
                volatility_level = "高"

            elif scenario == "defi_hack":
                title = "DeFi协议黑客攻击情景模拟"
                description = (
                    "模拟主要DeFi协议遭受黑客攻击的情景下，您的投资组合可能面临的风险"
                )
                asset_changes = {}

                for asset, properties in base_assets.items():
                    volatility = properties["volatility"]
                    asset_type = properties["type"]

                    if asset_type == "stablecoin":
                        # 稳定币轻微受影响
                        change = -0.01 * volatility
                    elif asset_type == "defi":
                        # DeFi代币受影响最大
                        change = -0.3 * volatility
                    else:
                        # 其他代币受到中等影响
                        change = -0.15 * volatility

                    asset_changes[asset] = max(-0.7, min(0, change))

                default_change = -0.25
                liquidation_risk = "中等"
                impermanent_loss = "高"
                market_sentiment = "恐惧"
                market_direction = "下跌"
                volatility_level = "高"

            elif scenario == "regulatory_crackdown":
                title = "监管打击情景模拟"
                description = "模拟全球监管机构对加密货币实施严厉监管的情景下，您的投资组合可能面临的影响"
                asset_changes = {}

                for asset, properties in base_assets.items():
                    volatility = properties["volatility"]
                    asset_type = properties["type"]

                    if asset_type == "stablecoin":
                        # 稳定币受到较大影响，因为监管往往针对稳定币
                        change = -0.1 * volatility
                    elif asset_type == "defi":
                        # DeFi代币受影响较大
                        change = -0.35 * volatility
                    elif asset_type == "exchange":
                        # 交易所代币受到严重影响
                        change = -0.4 * volatility
                    else:
                        # 其他代币
                        change = -0.25 * volatility

                    asset_changes[asset] = max(-0.8, min(0, change))

                default_change = -0.3
                liquidation_risk = "高"
                impermanent_loss = "高"
                market_sentiment = "恐惧"
                market_direction = "下跌"
                volatility_level = "高"

            elif scenario == "stablecoin_depeg":
                title = "稳定币脱锚情景模拟"
                description = (
                    "模拟主要稳定币与美元脱锚的情景下，您的投资组合可能面临的风险"
                )
                asset_changes = {}

                # 选择一个主要稳定币作为"脱锚"的目标
                depeg_target = "USDT"  # 可以是USDC、USDT、DAI等

                for asset, properties in base_assets.items():
                    volatility = properties["volatility"]
                    asset_type = properties["type"]

                    if asset == depeg_target:
                        # 目标稳定币大幅脱锚
                        change = -0.5
                    elif asset_type == "stablecoin":
                        # 其他稳定币受到连带影响
                        change = -0.1 * volatility
                    elif asset_type == "defi":
                        # DeFi代币受到较大影响
                        change = -0.25 * volatility
                    else:
                        # 其他代币
                        change = -0.15 * volatility

                    asset_changes[asset] = max(-0.95, min(0, change))

                default_change = -0.2
                liquidation_risk = "极高"
                impermanent_loss = "极高"
                market_sentiment = "恐慌"
                market_direction = "下跌"
                volatility_level = "极高"

            elif scenario == "chain_outage":
                title = "公链故障情景模拟"
                description = (
                    "模拟主要公链(如Solana或Polygon)发生技术故障或网络拥堵的情景"
                )
                asset_changes = {}

                # 选择一个主要公链作为"故障"的目标
                outage_target = "SOL"  # 可以是ETH、SOL、AVAX等
                affected_assets = ["SOL", "RAY", "SRM"]  # 受影响的相关生态资产

                for asset, properties in base_assets.items():
                    volatility = properties["volatility"]

                    if asset == outage_target:
                        # 目标公链大幅下跌
                        change = -0.3
                    elif asset in affected_assets:
                        # 相关生态资产受到较大影响
                        change = -0.25 * volatility
                    else:
                        # 其他资产轻微受影响
                        change = -0.05 * volatility

                    asset_changes[asset] = max(-0.6, min(0, change))

                default_change = -0.1
                liquidation_risk = "中等"
                impermanent_loss = "中等"
                market_sentiment = "谨慎"
                market_direction = "下跌"
                volatility_level = "中等"

            elif scenario == "liquidity_crisis":
                title = "流动性危机情景模拟"
                description = (
                    "模拟市场流动性枯竭，大量投资者集中抛售导致无法有效成交的情景"
                )
                asset_changes = {}

                for asset, properties in base_assets.items():
                    volatility = properties["volatility"]
                    market_corr = properties["market_corr"]
                    large_cap = properties["large_cap"]

                    if large_cap:
                        # 大市值资产受影响较小
                        change = -0.2 * volatility * market_corr
                    else:
                        # 小市值资产受影响更大
                        change = -0.4 * volatility * market_corr

                    asset_changes[asset] = max(-0.9, min(0, change))

                default_change = -0.3
                liquidation_risk = "极高"
                impermanent_loss = "极高"
                market_sentiment = "恐慌"
                market_direction = "下跌"
                volatility_level = "极高"

            else:  # inflation_surge
                title = "通胀飙升情景模拟"
                description = "模拟全球通胀率急剧上升，中央银行大幅加息的情景下，您的投资组合可能面临的影响"
                asset_changes = {}

                for asset, properties in base_assets.items():
                    volatility = properties["volatility"]
                    asset_type = properties["type"]

                    if asset_type == "stablecoin":
                        # 稳定币价值下降
                        change = -0.05 * volatility
                    elif asset == "BTC":
                        # 比特币作为"数字黄金"可能受益
                        change = 0.1 * volatility
                    else:
                        # 其他资产受到负面影响
                        change = -0.15 * volatility

                    asset_changes[asset] = max(-0.5, min(0.3, change))

                default_change = -0.1
                liquidation_risk = "中等"
                impermanent_loss = "中等"
                market_sentiment = "谨慎"
                market_direction = "混合"
                volatility_level = "高"

            # 计算情景下的资产价值变化
            simulated_positions = []
            simulated_total = 0
            liquidations = []
            protocol_impacts_map = {}

            # 处理每个头寸的模拟
            for position in positions:
                # 检查是否为嵌套结构
                if "positions" in position and isinstance(position["positions"], list):
                    protocol = position.get("protocol", "Unknown")
                    protocol_impact = protocol_impacts.get(
                        protocol, protocol_impacts.get("OTHER", {})
                    )
                    protocol_impacts_map[protocol] = protocol_impact.get(scenario, {})

                    # 处理平台级别的头寸（如协议头寸）
                    platform_simulated_total = 0
                    platform_current_total = 0
                    platform_inner_positions = []

                    # 遍历内部头寸
                    for pos in position.get("positions", []):
                        inner_simulated_value, inner_current_value, inner_position = (
                            self._simulate_position_value(
                                pos,
                                asset_changes,
                                scenario,
                                protocol_impact,
                                default_change,
                            )
                        )
                        if inner_position.get("liquidated", False):
                            liquidations.append(inner_position)

                        platform_simulated_total += inner_simulated_value
                        platform_current_total += inner_current_value
                        platform_inner_positions.append(inner_position)

                    # 计算平台级别的影响
                    platform_position = {
                        "protocol": protocol,
                        "type": "protocol",
                        "current_value_usd": platform_current_total,
                        "simulated_value_usd": platform_simulated_total,
                        "change_usd": platform_simulated_total - platform_current_total,
                        "change_percent": (
                            (platform_simulated_total / platform_current_total - 1)
                            * 100
                            if platform_current_total > 0
                            else 0
                        ),
                        "positions": platform_inner_positions,
                        "risk_multiplier": protocol_impacts_map.get(protocol, {}).get(
                            "risk_multiplier", 1.0
                        ),
                    }
                    simulated_positions.append(platform_position)
                    simulated_total += platform_simulated_total
                else:
                    # 单个资产头寸
                    sim_value, curr_value, sim_position = self._simulate_position_value(
                        position,
                        asset_changes,
                        scenario,
                        protocol_impacts.get(
                            position.get("protocol", "Unknown"),
                            protocol_impacts.get("OTHER", {}),
                        ),
                        default_change,
                    )
                    if sim_position.get("liquidated", False):
                        liquidations.append(sim_position)

                    simulated_positions.append(sim_position)
                    simulated_total += sim_value

            # 获取风险缓解建议
            risk_mitigation = self._get_scenario_risk_mitigation(
                scenario,
                simulated_positions,
                liquidations,
                current_total,
                simulated_total,
                wallet_address,
                protocol_impacts_map,
            )

            # 根据情景计算市场风险指标
            market_metrics = self._calculate_market_risk_metrics(
                scenario,
                current_total,
                simulated_total,
                simulated_positions,
                liquidations,
                market_sentiment,
                market_direction,
                volatility_level,
            )

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
                    "market_sentiment": market_sentiment,
                    "market_direction": market_direction,
                    "volatility_level": volatility_level,
                    "protocol_risk": "高" if scenario == "defi_hack" else "中",
                    "regulatory_risk": (
                        "高" if scenario == "regulatory_crackdown" else "中"
                    ),
                },
                "risk_mitigation": risk_mitigation,
                "simulation_metrics": market_metrics,
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

    def _simulate_position_value(
        self, position, asset_changes, scenario, protocol_impact, default_change
    ):
        """
        模拟头寸价值变化

        Args:
            position: 头寸对象
            asset_changes: 资产价格变化
            scenario: 情景类型
            protocol_impact: 协议特定影响
            default_change: 默认价格变化

        Returns:
            tuple: (模拟价值, 当前价值, 模拟头寸对象)
        """
        # 获取资产信息
        if hasattr(position, "asset"):
            asset = position.asset
            current_value = float(position.amount)
            position_type = getattr(position, "invest_type", 1)
            protocol = getattr(position, "protocol", "Unknown")
            health_factor = getattr(position, "health_factor", 2.0)
        else:
            asset = position.get("asset", "Unknown")
            current_value = float(position.get("usd_value", position.get("amount", 0)))
            position_type = position.get("invest_type", position.get("type", 1))
            protocol = position.get("protocol", "Unknown")
            health_factor = position.get("health_factor", 2.0)

        # 处理资产名称，提取主资产
        if "/" in asset:
            primary_asset = asset.split("/")[0].upper()
        else:
            primary_asset = asset.upper()

        # 获取资产价格变化率
        change_rate = asset_changes.get(primary_asset)
        if change_rate is None:
            # 尝试匹配资产前缀
            for key in asset_changes:
                if primary_asset.startswith(key):
                    change_rate = asset_changes[key]
                    break

        # 如果仍未找到匹配，使用默认变化率
        if change_rate is None:
            change_rate = default_change

        # 获取协议风险倍数
        risk_multiplier = protocol_impact.get(scenario, {}).get("risk_multiplier", 1.0)

        # 调整价格变化率
        adjusted_change_rate = change_rate * risk_multiplier

        # 计算新价值
        new_value = current_value * (1 + adjusted_change_rate)

        # 检查是否为借贷头寸，判断清算风险
        is_borrowing = False
        collateral_asset = None
        debt_asset = None

        # 根据头寸类型判断是否为借贷
        if isinstance(position_type, int) and position_type == 6:  # 假设6代表借贷
            is_borrowing = True
        elif isinstance(position_type, str) and position_type.lower() in [
            "borrowing",
            "borrow",
            "loan",
            "debt",
        ]:
            is_borrowing = True

        # 获取抵押物和债务资产
        if hasattr(position, "collateral"):
            collateral_asset = position.collateral
        elif isinstance(position, dict) and "collateral" in position:
            collateral_asset = position["collateral"]

        if hasattr(position, "debt"):
            debt_asset = position.debt
        elif isinstance(position, dict) and "debt" in position:
            debt_asset = position["debt"]

        # 清算计算
        will_liquidate = False
        liquidation_threshold = 0.75  # 默认清算阈值
        new_health_factor = health_factor

        if is_borrowing:
            # 如果有特定的清算阈值变化
            threshold_change = protocol_impact.get(scenario, {}).get(
                "liquidation_threshold_change", 0
            )
            liquidation_threshold += threshold_change

            # 如果有特定的抵押物和债务资产，计算新的健康因子
            if collateral_asset and debt_asset:
                collateral_change = asset_changes.get(
                    collateral_asset.upper(), default_change
                )
                debt_change = asset_changes.get(debt_asset.upper(), default_change)

                # 计算新的健康因子
                new_health_factor = (
                    health_factor * (1 + collateral_change) / (1 + debt_change)
                )
            else:
                # 简化计算：根据健康因子和市场变化估算清算风险
                new_health_factor = health_factor + (
                    adjusted_change_rate * health_factor
                )

            # 判断是否会被清算
            will_liquidate = new_health_factor < 1.0

            # 如果是黑客事件，增加随机清算概率
            if scenario == "defi_hack":
                hack_chance = protocol_impact.get(scenario, {}).get(
                    "affected_chance", 0.2
                )
                import random

                will_liquidate = will_liquidate or random.random() < hack_chance

        # 构建模拟头寸对象
        simulated_position = {
            "asset": asset,
            "protocol": protocol,
            "type": "borrowing" if is_borrowing else "investment",
            "current_value_usd": current_value,
            "simulated_value_usd": new_value,
            "change_usd": new_value - current_value,
            "change_percent": adjusted_change_rate * 100,
            "liquidated": will_liquidate,
            "health_factor": (
                {"current": health_factor, "simulated": new_health_factor}
                if is_borrowing
                else None
            ),
            "risk_multiplier": risk_multiplier,
        }

        return new_value, current_value, simulated_position

    def _get_scenario_risk_mitigation(
        self,
        scenario,
        positions,
        liquidations,
        current_total,
        simulated_total,
        wallet_address,
        protocol_impacts,
    ):
        """获取情景风险缓解建议"""
        # 使用AI预测器生成风险缓解建议
        risk_mitigation = []
        if self.ai_predictor:
            try:
                # 准备AI分析上下文
                analysis_context = {
                    "scenario": scenario,
                    "positions": positions,
                    "liquidations": liquidations,
                    "value_change_percent": (
                        (simulated_total - current_total) / current_total * 100
                        if current_total > 0
                        else 0
                    ),
                    "protocol_impacts": protocol_impacts,
                    "wallet_address": wallet_address,
                }

                # 调用AI预测器的analyze_generic方法
                ai_result = self.ai_predictor.analyze_generic(
                    "market_scenario", analysis_context
                )

                if isinstance(ai_result, dict) and "recommendations" in ai_result:
                    risk_mitigation = ai_result.get("recommendations", [])
            except Exception as e:
                self.logger.error(f"生成AI风险缓解建议时出错: {str(e)}")

        # 如果AI未能生成建议，使用更详细的情景特定建议
        if not risk_mitigation:
            if scenario == "market_crash":
                risk_mitigation = [
                    "减少借贷头寸，降低杠杆率",
                    "增加稳定币储备，准备在市场低点买入",
                    "设置止损点，防止进一步下跌",
                    "增加抵押品，防止清算",
                    "关注市场动态，避免在下跌过程中恐慌性抛售",
                    "重点保护高价值头寸，必要时优先卖出小额资产",
                ]

                # 根据是否有清算风险，添加特定建议
                if liquidations:
                    risk_mitigation.append(
                        f"紧急增加以下头寸的抵押品，防止清算: {', '.join([l.get('asset', '') for l in liquidations])}"
                    )

                # 根据投资组合构成，添加特定建议
                defi_exposure = sum(
                    1
                    for p in positions
                    if p.get("protocol", "").lower()
                    in ["aave", "compound", "curve", "uniswap"]
                )
                if defi_exposure > 3:
                    risk_mitigation.append("考虑减少DeFi协议敞口，分散到不同类型的资产")

            elif scenario == "bull_run":
                risk_mitigation = [
                    "定期获利了结，锁定部分盈利",
                    "调整资产配置，防止过度集中",
                    "关注市场情绪指标，警惕市场过热",
                    "考虑对冲策略，防范突然回调",
                    "设置止盈点，防止错失高点",
                    "定期重新平衡投资组合，确保风险分散",
                ]

                # 根据投资组合构成，添加特定建议
                alt_coins = sum(
                    1
                    for p in positions
                    if p.get("asset", "").upper()
                    not in ["BTC", "ETH", "USDC", "USDT", "DAI"]
                )
                if alt_coins > 5:
                    risk_mitigation.append(
                        "考虑将部分小市值代币的收益转换为BTC/ETH，降低风险"
                    )

            elif scenario == "defi_hack":
                risk_mitigation = [
                    "分散资产到多个协议，降低单一协议风险",
                    "优先使用经过多次审计的成熟协议",
                    "关注协议安全更新和公告",
                    "考虑使用去中心化保险产品",
                    "持续监控黑客事件相关新闻",
                    "重点保护大额存款，必要时暂时转移到中心化交易所",
                ]

                # 根据投资组合构成，添加特定建议
                high_risk_protocols = ["未审计的新协议", "历史上有安全问题的协议"]
                high_risk_exposure = sum(
                    1 for p in positions if p.get("protocol", "") in high_risk_protocols
                )
                if high_risk_exposure > 0:
                    risk_mitigation.append("立即从未经充分审计的新协议中提取资金")

            elif scenario == "regulatory_crackdown":
                risk_mitigation = [
                    "关注各国监管动态，适时调整投资策略",
                    "增加合规性高的资产比例",
                    "考虑分散到不同司法管辖区的协议",
                    "准备应急撤离计划，确保资金安全",
                    "咨询法律专业人士，了解监管影响",
                    "密切跟踪交易所和稳定币发行方的合规状态",
                ]

            elif scenario == "stablecoin_depeg":
                risk_mitigation = [
                    "分散稳定币持仓，避免集中在单一稳定币",
                    "优先持有完全抵押的稳定币",
                    "设置自动兑换脚本，在脱锚初期快速反应",
                    "建立稳定币预警系统，监控脱锚风险",
                    "关注稳定币发行方的财务状况和负面新闻",
                ]

                # 分析投资组合的稳定币敞口
                stablecoin_exposure = sum(
                    p.get("current_value_usd", 0)
                    for p in positions
                    if p.get("asset", "").upper()
                    in ["USDC", "USDT", "DAI", "BUSD", "TUSD", "FRAX"]
                )
                if stablecoin_exposure > current_total * 0.3:
                    risk_mitigation.append(
                        "您的稳定币敞口较大，建议分散到多种不同抵押机制的稳定币"
                    )

            elif scenario == "chain_outage":
                risk_mitigation = [
                    "将资产分散到多个不同公链，降低单链风险",
                    "保持适当的链外资产比例",
                    "为跨链转账预先做好准备",
                    "了解各链的应急机制和恢复程序",
                    "在多个钱包中保留一些ETH/BTC作为应急资金",
                ]

            elif scenario == "liquidity_crisis":
                risk_mitigation = [
                    "增加高流动性资产的比例",
                    "将资金分散在多个不同类型的交易所和协议",
                    "建立分阶段撤离策略，避免一次性大额提款",
                    "持有适量稳定币，作为流动性缓冲",
                    "关注协议和交易所的流动性指标变化",
                    "避免参与TVL低的流动性池",
                ]

            else:  # inflation_surge
                risk_mitigation = [
                    "增加商品类和通胀对冲型资产的比例",
                    "降低固定收益资产的敞口",
                    "密切关注央行政策动向",
                    "关注比特币在通胀环境中的表现",
                    "考虑增加实物资产或与实物资产挂钩的数字资产配置",
                    "短期内避免长周期的锁仓",
                ]

        return risk_mitigation

    def _calculate_market_risk_metrics(
        self,
        scenario,
        current_total,
        simulated_total,
        positions,
        liquidations,
        market_sentiment,
        market_direction,
        volatility_level,
    ):
        """计算市场风险指标"""
        # 计算最大回撤
        max_drawdown = 0
        if current_total > 0:
            max_drawdown = max(
                0, abs((simulated_total - current_total) / current_total * 100)
            )

        # 计算风险等级
        if simulated_total < current_total * 0.7:
            risk_level = "高"
        elif simulated_total < current_total:
            risk_level = "中"
        else:
            risk_level = "低"

        # 计算受影响的协议
        affected_protocols = set()
        severely_affected_protocols = set()
        for p in positions:
            protocol = p.get("protocol", "")
            change_percent = p.get("change_percent", 0)

            if change_percent < -10:
                affected_protocols.add(protocol)

            if change_percent < -20:
                severely_affected_protocols.add(protocol)

        # 计算受影响的资产
        affected_assets = set()
        severely_affected_assets = set()

        # 递归处理嵌套结构
        def process_position(position):
            if "positions" in position and isinstance(position["positions"], list):
                for sub_pos in position["positions"]:
                    process_position(sub_pos)
            else:
                asset = position.get("asset", "")
                change_percent = position.get("change_percent", 0)

                if change_percent < -10:
                    affected_assets.add(asset)

                if change_percent < -20:
                    severely_affected_assets.add(asset)

        for p in positions:
            process_position(p)

        # 市场相关性分析
        market_correlation = "高" if scenario in ["market_crash", "bull_run"] else "中"

        # 如果使用了杠杆，风险级别上调
        has_leverage = any(
            p.get("type", "") == "borrowing" or p.get("health_factor") is not None
            for p in positions
        )
        if has_leverage and risk_level == "中":
            risk_level = "高"

        # 如果有清算，风险级别上调到最高
        if liquidations:
            risk_level = "极高"

        # 返回市场风险指标
        return {
            "max_drawdown": max_drawdown,
            "risk_level": risk_level,
            "affected_protocols_count": len(affected_protocols),
            "severely_affected_protocols_count": len(severely_affected_protocols),
            "affected_assets_count": len(affected_assets),
            "severely_affected_assets_count": len(severely_affected_assets),
            "liquidation_count": len(liquidations),
            "market_correlation": market_correlation,
            "market_sentiment": market_sentiment,
            "market_direction": market_direction,
            "volatility_level": volatility_level,
            "has_leverage": has_leverage,
            "portfolio_diversity_score": min(10, len(affected_assets)),
            "protocol_diversity_score": min(10, len(affected_protocols)),
        }

    # --- Start of Migrated Methods ---

    def _generate_asset_risk_recommendations(
        self, risk_score: int, metrics: Dict[str, Any]
    ) -> List[str]:
        """
        根据风险评分和指标生成资产风险建议 (内部辅助方法)
        """
        recommendations = []

        # 基于市值
        if metrics.get("market_cap", 0) < 100000000:  # < 1亿
            recommendations.append("市值较小，建议控制仓位")

        # 基于流动性
        if metrics.get("volume_to_mcap_ratio", 0) < 0.01:
            recommendations.append("流动性较低，建议关注交易风险")

        # 基于波动性
        if metrics.get("price_volatility", 0) > 10:
            recommendations.append("价格波动较大，建议设置止损")

        # 基于趋势
        if metrics.get("price_trend", {}).get("current", 0) < metrics.get(
            "price_trend", {}
        ).get("ma30", 0):
            recommendations.append("处于下降趋势，建议谨慎操作")

        return recommendations

    async def analyze_asset_risk(self, asset: str) -> RiskAnalysisResult:
        """
        分析资产的风险指标 (迁移自 BlockchainService)

        Args:
            asset: 资产符号或ID

        Returns:
            RiskAnalysisResult: 资产风险分析结果
        """
        try:
            if not self.blockchain_service:
                raise ValueError("BlockchainService is not initialized in RiskEngine")

            # 获取24小时数据
            # 注意: _get_coingecko_24h_data 是 blockchain_service 的私有方法, 需要确认是否能调用
            # 假设它可以调用或有等效的公共方法
            data_24h = await self.blockchain_service._get_coingecko_24h_data(asset)
            if not data_24h:
                return RiskAnalysisResult(
                    asset_id=asset,
                    risk_score=0,
                    risk_level="未知",
                    metrics=RiskMetrics(),
                    analysis=RiskAnalysis(),
                    error=f"无法获取{asset}的市场数据",
                )

            # 获取历史数据
            historical_data = (
                await self.blockchain_service.get_coingecko_historical_data(asset)
            )
            if historical_data is None or historical_data.empty:
                return RiskAnalysisResult(
                    asset_id=asset,
                    risk_score=0,
                    risk_level="未知",
                    metrics=RiskMetrics(),
                    analysis=RiskAnalysis(),
                    error=f"无法获取{asset}的历史数据",
                )

            # 1. 价格波动性分析
            price_volatility = historical_data["price"].pct_change().std() * 100

            # 2. 市值分析
            market_cap = data_24h.get("market_cap", 0)
            market_cap_rank = data_24h.get("market_cap_rank", 0)

            # 3. 流动性分析
            volume = data_24h.get("volume", 0)
            volume_to_mcap_ratio = volume / market_cap if market_cap > 0 else 0

            # 4. 价格趋势分析
            current_price = historical_data["price"].iloc[-1]
            price_ma7 = historical_data["price"].rolling(window=7).mean().iloc[-1]
            price_ma30 = historical_data["price"].rolling(window=30).mean().iloc[-1]

            # 5. 计算风险评分
            risk_score = 0
            max_score = 100

            # 市值风险 (30分)
            if market_cap > 10000000000:  # > 100亿
                risk_score += 30
            elif market_cap > 1000000000:  # > 10亿
                risk_score += 20
            elif market_cap > 100000000:  # > 1亿
                risk_score += 10

            # 流动性风险 (20分)
            if volume_to_mcap_ratio > 0.1:  # 日交易量超过市值的10%
                risk_score += 20
            elif volume_to_mcap_ratio > 0.05:  # 日交易量超过市值的5%
                risk_score += 10

            # 波动性风险 (20分)
            if price_volatility < 5:  # 波动率小于5%
                risk_score += 20
            elif price_volatility < 10:  # 波动率小于10%
                risk_score += 10

            # 趋势风险 (30分)
            if current_price > price_ma7 > price_ma30:  # 上升趋势
                risk_score += 30
            elif current_price > price_ma7:  # 短期上升
                risk_score += 20
            elif current_price > price_ma30:  # 长期上升
                risk_score += 10

            # 确定风险等级
            risk_level = "高风险"
            if risk_score >= 80:
                risk_level = "低风险"
            elif risk_score >= 60:
                risk_level = "中低风险"
            elif risk_score >= 40:
                risk_level = "中等风险"
            elif risk_score >= 20:
                risk_level = "中高风险"

            return RiskAnalysisResult(
                asset_id=asset,
                risk_score=risk_score,
                risk_level=risk_level,
                metrics=RiskMetrics(
                    price_volatility=price_volatility,
                    market_cap=market_cap,
                    market_cap_rank=market_cap_rank,
                    volume_to_mcap_ratio=volume_to_mcap_ratio,
                ),
                analysis=RiskAnalysis(
                    market_cap_analysis=f"市值{market_cap:,.0f}美元，排名第{market_cap_rank}位",
                    liquidity_analysis=f"日交易量/市值比率{volume_to_mcap_ratio:.2%}",
                    volatility_analysis=f"价格波动率{price_volatility:.2f}%",
                    trend_analysis=(
                        "上升趋势" if current_price > price_ma7 else "下降趋势"
                    ),
                ),
                recommendations=self._generate_asset_risk_recommendations(
                    risk_score,
                    {
                        "price_volatility": price_volatility,
                        "market_cap": market_cap,
                        "market_cap_rank": market_cap_rank,
                        "volume_to_mcap_ratio": volume_to_mcap_ratio,
                        "price_trend": {
                            "current": current_price,
                            "ma7": price_ma7,
                            "ma30": price_ma30,
                        },
                    },
                ),
            )
        except Exception as e:
            self.logger.error(f"分析资产{asset}风险时出错: {str(e)}")
            return RiskAnalysisResult(
                asset_id=asset,
                risk_score=0,
                risk_level="未知",
                metrics=RiskMetrics(),
                analysis=RiskAnalysis(),
                error=f"风险分析失败: {str(e)}",
            )

    def _calculate_base_protocol_risk(
        self, protocol_data: Dict, historical_tvl: List, audit_status: Dict
    ) -> RiskAnalysisResult:
        """
        执行基础协议风险计算 (内部辅助方法，迁移自 BlockchainService.analyze_protocol_risk)

        Args:
            protocol_data: 从 get_protocol 获取的数据
            historical_tvl: 从 get_protocol_historical_tvl 获取的数据
            audit_status: 从 get_protocol_audit_status 获取的数据

        Returns:
            RiskAnalysisResult: 基础协议风险分析结果
        """
        protocol_name = "未知协议"  # Default value
        try:
            protocol_name = protocol_data.get("name", "未知协议")
            protocol_category = protocol_data.get("category", "未知")
            protocol_chains = protocol_data.get("chains", [])

            # 使用 protocol_data 中的 TVL，因为它通常更新
            tvl = protocol_data.get("tvl", 0)

            # 提取审计信息
            audit_count = audit_status.get("audit_count", 0)
            audit_links = audit_status.get("audit_links", [])
            is_open_source = audit_status.get("is_open_source", False)

            # 计算TVL稳定性
            tvl_stability = 0
            if historical_tvl and len(historical_tvl) > 7:  # 至少需要一周的数据
                recent_tvl = [item.get("tvl", 0) for item in historical_tvl[-30:]]
                # Ensure recent_tvl is not empty and sum > 0 to avoid division by zero and errors
                if recent_tvl and sum(recent_tvl) > 0:
                    try:
                        tvl_std = np.std(recent_tvl)
                        tvl_mean = np.mean(recent_tvl)
                        if tvl_mean != 0:  # Avoid division by zero
                            tvl_stability = 1 - min(1, tvl_std / tvl_mean)
                        else:
                            tvl_stability = 0  # Set stability to 0 if mean is 0
                    except Exception as np_err:
                        self.logger.warning(
                            f"Numpy calculation error for TVL stability ({protocol_name}): {np_err}"
                        )
                        tvl_stability = 0  # Default to 0 on error

            # 重新构建审计状态字典以便计算分数
            internal_audit_status = {
                "audited": audit_count > 0,
                "audit_count": audit_count,
                "audit_links": audit_links,
                "open_source": is_open_source,
                "audit_score": min(
                    100, audit_count * 20 + (50 if is_open_source else 0)
                ),
            }

            # 根据各项指标计算综合风险评分
            risk_score = 0.0  # Use float for score
            max_score = 0.0  # Use float for max_score

            # TVL因素 (TVL越高，风险越低)
            if tvl > 0:
                try:
                    # Ensure tvl is a valid number for log10
                    if isinstance(tvl, (int, float)) and tvl > 0:
                        tvl_score = min(5.0, np.log10(tvl) - 5.0)
                        risk_score += tvl_score
                    else:
                        tvl_score = 0.0
                        self.logger.warning(
                            f"Invalid TVL value {tvl} for log10 calculation ({protocol_name})"
                        )
                except ValueError:
                    tvl_score = 0.0
                    self.logger.warning(
                        f"TVL value {tvl} caused ValueError in log10 for {protocol_name}"
                    )
                max_score += 5.0

            # TVL稳定性因素
            if tvl_stability >= 0:  # Stability should be non-negative
                stability_score = tvl_stability * 3.0
                risk_score += stability_score
                max_score += 3.0

            # 审计因素
            if internal_audit_status.get("audited", False):
                audit_score_val = (
                    internal_audit_status.get("audit_score", 0) / 20.0
                )  # Use float division
                risk_score += audit_score_val
                max_score += 5.0

            # 多链部署因素 (部署在多条链上可能增加风险面)
            chain_count = len(protocol_chains)
            if chain_count > 0:
                chain_factor = (
                    2.0 if chain_count <= 2 else (1.0 if chain_count <= 5 else 0.0)
                )
                risk_score += chain_factor
                max_score += 2.0

            # 开源因素
            if is_open_source:
                risk_score += 2.0
                max_score += 2.0

            # 规范化风险分数 (0-100，越高表示风险越低)
            normalized_risk_score = 0.0
            if max_score > 0:
                normalized_risk_score = max(
                    0.0, min(100.0, (risk_score / max_score) * 100.0)
                )
            else:
                self.logger.warning(
                    f"Max score is zero for {protocol_name}, cannot normalize score."
                )

            # 风险等级
            risk_level = "极高"  # Default to highest risk
            if normalized_risk_score >= 80:
                risk_level = "极低"
            elif normalized_risk_score >= 60:
                risk_level = "低"
            elif normalized_risk_score >= 40:
                risk_level = "中"
            elif normalized_risk_score >= 20:
                risk_level = "高"

            # 构建分析文本
            tvl_low_text = "较低"
            tvl_med_text = "中等"
            tvl_high_text = "较高"
            tvl_text = (
                tvl_high_text
                if tvl > 100000000
                else (tvl_med_text if tvl > 10000000 else tvl_low_text)
            )
            tvl_analysis_text = f"TVL为{tvl:,.2f}美元，{tvl_text}"

            stability_low_text = "波动较大"
            stability_med_text = "较稳定"
            stability_high_text = "很稳定"
            stability_text = (
                stability_high_text
                if tvl_stability > 0.8
                else (stability_med_text if tvl_stability > 0.5 else stability_low_text)
            )
            stability_analysis_text = (
                f"TVL稳定性为{tvl_stability*100:.2f}%，{stability_text}"
            )

            audit_text = (
                "已通过" + str(audit_count) + "次专业审计"
                if internal_audit_status.get("audited", False)
                else "未经专业审计或缺乏审计信息"
            )
            source_text = "且代码开源" if is_open_source else "代码未开源"
            audit_analysis_text = f"{audit_text}，{source_text}"

            chain_text = "风险分散" if chain_count <= 2 else "增加了一定的风险面"
            chain_analysis_text = f"部署在{chain_count}条链上，{chain_text}"

            rec_high_text = "建议可以适量配置"
            rec_med_text = "建议谨慎参与"
            rec_low_text = "建议避免参与或严格控制仓位"
            rec_text = (
                rec_high_text
                if normalized_risk_score >= 60
                else (rec_med_text if normalized_risk_score >= 40 else rec_low_text)
            )
            recommendations_text = [
                f"综合评估，{protocol_name}协议的基础风险等级为{risk_level}，{rec_text}"
            ]

            return RiskAnalysisResult(
                asset_id=protocol_name,
                risk_score=normalized_risk_score,
                risk_level=risk_level,
                metrics=RiskMetrics(
                    tvl_stability=tvl_stability * 100,
                    audit_score=internal_audit_status.get("audit_score", 0),
                    market_cap=tvl,  # Using TVL as a proxy for market cap in this context
                ),
                # Ensure all required fields for RiskAnalysis are provided or Optional
                analysis=RiskAnalysis(
                    tvl_factor=tvl_analysis_text,
                    stability_factor=stability_analysis_text,
                    audit_factor=audit_analysis_text,
                    chain_factor=chain_analysis_text,
                    # Add other necessary fields for RiskAnalysis here if they exist and are required
                    # e.g., liquidity_analysis="N/A (Base Protocol)", volatility_analysis="N/A (Base Protocol)", trend_analysis="N/A (Base Protocol)"...
                ),
                recommendations=recommendations_text,
                raw_data={"protocol_data": protocol_data},  # Keep raw data if needed
            )
        except Exception as e:
            self.logger.error(
                f"计算基础协议风险失败 ({protocol_name}): {str(e)}", exc_info=True
            )
            # Return a default error result
            return RiskAnalysisResult(
                asset_id=protocol_name,
                risk_score=0,
                risk_level="未知",
                metrics=RiskMetrics(),
                analysis=RiskAnalysis(),
                error=f"计算基础协议风险时出错: {str(e)}",
            )

    async def get_protocol_risk_analysis(self, protocol_name: str) -> Dict[str, Any]:
        """
        获取协议的风险摘要信息，协调AI和基础分析 (替代 BlockchainService._get_protocol_risk_summary)

        Args:
            protocol_name: 协议名称

        Returns:
            Dict: 包含风险等级、评分、建议等的字典
        """
        cache_key = f"protocol_risk_{protocol_name.lower()}"
        # Correctly check cache
        try:
            cached_result = self.analysis_cache.get(cache_key)
            if cached_result is not None:
                self.logger.info(f"从缓存获取协议 {protocol_name} 的风险分析")
                return cached_result
        except KeyError:  # TTLCache raises KeyError if key not found
            self.logger.debug(f"协议 {protocol_name} 的风险分析不在缓存中")
            # Pass, continue to fetch and analyze
            pass

        try:
            if not self.blockchain_service:
                raise ValueError("BlockchainService is not initialized in RiskEngine")

            # 1. 获取原始数据
            protocol_data: Optional[Dict] = None
            historical_tvl_raw: Optional[List] = None
            audit_status: Optional[Dict] = None
            try:
                protocol_data = await self.blockchain_service.get_protocol(
                    protocol_name
                )
                historical_tvl_raw = (
                    await self.blockchain_service.get_protocol_historical_tvl(
                        protocol_name
                    )
                )
                audit_status = await self.blockchain_service.get_protocol_audit_status(
                    protocol_name
                )
                # Basic validation
                if not protocol_data or not audit_status:
                    raise ValueError("获取到的协议数据或审计状态为空")
            except Exception as data_err:
                self.logger.error(
                    f"获取协议 {protocol_name} 基础数据失败: {data_err}", exc_info=True
                )
                # Return error immediately if core data fetching fails
                return {
                    "risk_level": "未知",
                    "risk_score": 0,
                    "audit_status": False,
                    "error": f"获取协议基础数据失败: {str(data_err)}",
                    "analysis_source": "Data Error",
                }

            # 处理历史TVL格式 (如果需要)
            historical_tvl = []
            if historical_tvl_raw:  # Check if list is not None or empty
                for item in historical_tvl_raw:
                    try:
                        # Assume item keys are 'date' (timestamp) and 'totalLiquidityUSD'
                        date_val = item.get("date")
                        tvl_val = item.get("totalLiquidityUSD")
                        if date_val is not None and tvl_val is not None:
                            dt_object = datetime.fromtimestamp(date_val)
                            historical_tvl.append(
                                {
                                    "date": dt_object,
                                    "tvl": tvl_val,
                                }
                            )
                        else:
                            self.logger.warning(
                                f"历史TVL项缺少 date 或 totalLiquidityUSD: {item}"
                            )
                    except (TypeError, ValueError, OSError) as fmt_e:
                        self.logger.warning(
                            f"处理历史TVL项时出错 (跳过): {item}, 错误: {fmt_e}"
                        )
                        continue  # 跳过格式错误的数据点
            else:
                self.logger.warning(f"协议 {protocol_name} 的历史TVL数据为空或获取失败")

            # 2. 准备AI分析数据
            ai_protocol_data = {
                "protocol_metadata": protocol_data,
                "historical_tvl": (
                    historical_tvl_raw if historical_tvl_raw else []
                ),  # Pass raw or empty list
                "audit_status": audit_status,
                "basic_analysis": {
                    "name": protocol_data.get("name", protocol_name),
                    "category": protocol_data.get("category", "未知"),
                    "chains": protocol_data.get("chains", []),
                    "tvl": protocol_data.get("tvl", 0),
                    "audit_count": audit_status.get("audit_count", 0),
                    "is_open_source": audit_status.get("is_open_source", False),
                },
                "chain_distribution": protocol_data.get("chainTvls", {}),
            }

            # 3. 尝试AI分析
            ai_success = False
            risk_summary = None  # Initialize risk_summary
            if self.ai_predictor:
                try:
                    self.logger.info(f"使用AI预测器分析协议 {protocol_name} 的风险")
                    # Ensure predictor method exists and is callable
                    if hasattr(
                        self.ai_predictor, "analyze_defi_protocol_risk"
                    ) and callable(
                        getattr(self.ai_predictor, "analyze_defi_protocol_risk")
                    ):
                        ai_risk_analysis = self.ai_predictor.analyze_defi_protocol_risk(
                            ai_protocol_data
                        )

                        if (
                            ai_risk_analysis
                            and isinstance(ai_risk_analysis, dict)
                            and "risk_score" in ai_risk_analysis
                        ):
                            # 提取AI分析的关键风险信息
                            risk_summary = {
                                "risk_level": ai_risk_analysis.get(
                                    "risk_level", "未知"
                                ),
                                "risk_score": ai_risk_analysis.get("risk_score", 0),
                                "audit_status": audit_status.get("audited", False),
                                "tvl_trend": ai_risk_analysis.get("tvl_trend", {}),
                                "recommendations": ai_risk_analysis.get(
                                    "recommendations", []
                                )[:3],
                                "ai_confidence": ai_risk_analysis.get(
                                    "confidence", 0.8
                                ),
                                "analysis_timestamp": ai_risk_analysis.get(
                                    "analysis_timestamp", datetime.utcnow().isoformat()
                                ),
                                "analysis_source": "AI Predictor",
                            }
                            ai_success = True
                            self.logger.info(
                                f"成功使用AI预测器分析协议 {protocol_name} 的风险"
                            )
                        else:
                            self.logger.warning(
                                f"AI预测器未返回有效的风险评分给 {protocol_name}. 返回: {ai_risk_analysis}"
                            )
                    else:
                        self.logger.error(
                            f"AI Predictor does not have a callable method 'analyze_defi_protocol_risk'"
                        )

                except Exception as ai_err:
                    self.logger.error(
                        f"使用AI预测器分析协议 {protocol_name} 风险失败: {str(ai_err)}，将使用基础方法",
                        exc_info=True,
                    )
            else:
                self.logger.info(
                    f"AI预测器未配置，将使用基础方法分析协议 {protocol_name} 的风险"
                )

            # 4. 如果AI分析未成功，回退到基础分析
            if not ai_success:
                self.logger.info(f"使用基础方法分析协议 {protocol_name} 的风险")
                base_risk_result: RiskAnalysisResult = (
                    self._calculate_base_protocol_risk(
                        protocol_data, historical_tvl, audit_status
                    )
                )

                # 格式化基础分析结果
                risk_summary = {
                    "risk_level": base_risk_result.risk_level,
                    "risk_score": base_risk_result.risk_score,
                    "audit_status": audit_status.get("audited", False),
                    "recommendations": (
                        base_risk_result.recommendations[:3]
                        if base_risk_result.recommendations
                        else []
                    ),
                    "tvl_trend": {},  # 基础分析目前不提供TVL趋势字典
                    "ai_confidence": 0.0,  # 基础分析没有AI置信度
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "analysis_source": "Base Calculation",  # 标记来源
                }
                # Add error from base calculation if any
                if base_risk_result.error:
                    risk_summary["error"] = base_risk_result.error

            # 5. 缓存并返回结果 (确保 risk_summary 被赋值)
            if risk_summary is not None:
                try:
                    self.analysis_cache[cache_key] = risk_summary
                    return risk_summary
                except Exception as cache_err:
                    self.logger.error(
                        f"写入缓存失败 ({protocol_name}): {cache_err}", exc_info=True
                    )
                    # Return the result even if caching failed
                    return risk_summary
            else:
                # This case should ideally not be reached if logic is correct
                self.logger.error(
                    f"未能生成 {protocol_name} 的风险分析结果，risk_summary 为 None"
                )
                raise ValueError(f"未能生成 {protocol_name} 的风险分析结果")

        except Exception as e:
            self.logger.error(
                f"获取协议 {protocol_name} 风险分析失败: {str(e)}", exc_info=True
            )
            # 返回统一的错误结构
            return {
                "risk_level": "未知",
                "risk_score": 0,
                "audit_status": False,
                "recommendations": [],
                "tvl_trend": {},
                "ai_confidence": 0.0,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "error": f"分析失败: {str(e)}",
                "analysis_source": "Error",
            }

    # --- End of Migrated Methods ---
