"""
投资组合风险分析模块 - 用于分析整体投资组合的风险
"""

from typing import Dict, List, Optional
import logging
import hashlib
import json
from cachetools import TTLCache
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger("defi_risk.portfolio_risk")


class RiskLevel(Enum):
    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    EXTREME = "极高风险"


class RiskType(Enum):
    MARKET = "市场风险"
    SMART_CONTRACT = "智能合约风险"
    LIQUIDITY = "流动性风险"
    PROTOCOL = "协议风险"
    CORRELATION = "相关性风险"
    REGULATORY = "监管风险"


@dataclass
class Position:
    protocol: str
    asset: str
    amount: float
    apy: Optional[float] = None
    invest_type: Optional[int] = None


@dataclass
class RiskAssessment:
    risk_score: int  # 0-100的综合风险评分
    risk_level: RiskLevel
    risk_scores: Dict[RiskType, float]  # 原有风险类型评分（0-1范围）
    risk_factors: Dict[str, Dict]  # 新的风险因素结构（0-100范围）
    trend_analysis: Dict[str, any]  # 趋势分析
    warnings: List[str]  # 警告列表
    recommendations: List[str]  # 建议列表
    risk_mitigation_strategies: List[str]  # 风险缓解策略
    monitoring_points: List[str]  # 需要监控的关键指标
    detailed_analysis: Dict[str, any]  # 详细分析（保留原有结构）


class PortfolioRiskAnalyzer:
    """投资组合风险分析器"""

    def __init__(
        self,
        market_risk_analyzer=None,
        investment_type_risk_analyzer=None,
        ai_predictor=None,
        blockchain_service=None,
    ):
        """
        初始化投资组合风险分析器

        Args:
            market_risk_analyzer: 市场风险分析器实例
            investment_type_risk_analyzer: 投资类型风险分析器实例
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.market_risk_analyzer = market_risk_analyzer
        self.investment_type_risk_analyzer = investment_type_risk_analyzer
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service

        # 风险权重配置
        self.risk_weights = {
            RiskType.MARKET: 0.3,
            RiskType.SMART_CONTRACT: 0.2,
            RiskType.LIQUIDITY: 0.2,
            RiskType.PROTOCOL: 0.15,
            RiskType.CORRELATION: 0.1,
            RiskType.REGULATORY: 0.05,
        }

        # 缓存
        self.portfolio_cache = TTLCache(maxsize=100, ttl=300)  # 5分钟过期

    def _generate_cache_key(self, positions: List[Position], **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            "positions": [
                {"protocol": p.protocol, "asset": p.asset, "amount": p.amount}
                for p in positions
            ],
            "extra": kwargs,
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    def assess_portfolio_risk(self, positions: List[Position]) -> RiskAssessment:
        """
        评估整个投资组合的风险，包含多个维度的风险分析

        Args:
            positions: 投资头寸列表

        Returns:
            RiskAssessment: 风险评估结果
        """
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(positions)

            # 检查缓存
            cached_result = self.portfolio_cache.get(cache_key)
            if cached_result:
                logger.info("使用缓存的投资组合风险评估结果")
                return cached_result

            if not positions:
                return RiskAssessment(
                    risk_score=0,
                    risk_level=RiskLevel.LOW,
                    risk_scores={rt: 0.0 for rt in RiskType},
                    risk_factors={
                        "tvl_risk": {"score": 0, "analysis": "无资产", "factors": []},
                        "chain_risk": {"score": 0, "analysis": "无资产", "factors": []},
                        "market_risk": {
                            "score": 0,
                            "analysis": "无资产",
                            "factors": [],
                        },
                        "technical_risk": {
                            "score": 0,
                            "analysis": "无资产",
                            "factors": [],
                        },
                        "investment_type_risk": {
                            "score": 0,
                            "analysis": "无资产",
                            "factors": [],
                        },
                    },
                    trend_analysis={
                        "short_term": "无数据",
                        "medium_term": "无数据",
                        "key_indicators": {
                            "macd_signal": "无数据",
                            "rsi_signal": "无数据",
                            "volume_analysis": "无数据",
                        },
                    },
                    warnings=["未发现任何DeFi存款"],
                    recommendations=["考虑开始DeFi投资以获取收益"],
                    risk_mitigation_strategies=[],
                    monitoring_points=[],
                    detailed_analysis={},
                )

            # 初始化风险评分和分析结果
            risk_scores = {rt: 0.0 for rt in RiskType}  # 原始风险评分（0-1范围）
            risk_factors = {  # 新的风险因素结构（0-100范围）
                "tvl_risk": {"score": 0, "analysis": "", "factors": []},
                "chain_risk": {"score": 0, "analysis": "", "factors": []},
                "market_risk": {"score": 0, "analysis": "", "factors": []},
                "technical_risk": {"score": 0, "analysis": "", "factors": []},
                "investment_type_risk": {
                    "score": 0,
                    "analysis": "基于投资类型的风险分析",
                    "factors": [],
                },
            }
            warnings = []
            recommendations = []
            risk_mitigation_strategies = []
            monitoring_points = []
            detailed_analysis = {}
            protocol_analysis = {}
            investment_type_analysis = {}

            # 计算总投资金额
            total_value = sum(p.amount for p in positions)

            # 投资类型分布分析
            investment_type_distribution = {}
            investment_type_names = {}

            # 初始化投资类型分布
            if self.investment_type_risk_analyzer:
                for (
                    invest_type_id
                ) in self.investment_type_risk_analyzer.invest_type_map:
                    invest_type_name = (
                        self.investment_type_risk_analyzer.get_investment_type_name(
                            invest_type_id
                        )
                    )
                    investment_type_distribution[invest_type_id] = 0
                    investment_type_names[invest_type_id] = invest_type_name

            # 计算各投资类型的分布
            for pos in positions:
                invest_type = pos.invest_type if pos.invest_type is not None else 1
                if invest_type in investment_type_distribution:
                    investment_type_distribution[invest_type] += pos.amount

            # 计算投资类型分布百分比
            investment_type_percentage = {}
            for invest_type, amount in investment_type_distribution.items():
                percentage = (amount / total_value * 100) if total_value > 0 else 0
                investment_type_percentage[invest_type] = percentage

            # 保存投资类型分布分析
            detailed_analysis["investment_type_distribution"] = {
                "distribution": investment_type_distribution,
                "percentage": investment_type_percentage,
                "names": investment_type_names,
            }

            # 分析投资类型分布风险
            high_risk_concentration = False
            highest_risk_type = None
            highest_risk_percentage = 0

            if self.investment_type_risk_analyzer:
                # 找出风险最高的投资类型及其占比
                for invest_type, percentage in investment_type_percentage.items():
                    risk_score = self.investment_type_risk_analyzer.get_base_risk_score(
                        invest_type
                    )
                    weighted_risk = risk_score * percentage / 100

                    if (
                        percentage > 50 and risk_score > 0.3
                    ):  # 如果高于中等风险的投资类型占比超过50%
                        high_risk_concentration = True
                        if risk_score > highest_risk_percentage:
                            highest_risk_type = invest_type
                            highest_risk_percentage = percentage

            # 添加投资类型分布风险警告和建议
            if high_risk_concentration and highest_risk_type:
                invest_type_name = investment_type_names.get(
                    highest_risk_type, "未知类型"
                )
                warnings.append(
                    f"投资组合中{invest_type_name}占比过高({highest_risk_percentage:.1f}%)，增加了整体风险"
                )
                recommendations.append(
                    f"建议降低{invest_type_name}的投资比例，分散到其他低风险投资类型"
                )
                risk_factors["investment_type_risk"]["factors"].append(
                    f"{invest_type_name}投资集中度过高"
                )

            # 分析市场风险
            market_risk_score = 0.0
            if self.market_risk_analyzer:
                # 获取所有资产
                assets = [p.asset for p in positions]
                # 分析相关性风险
                correlation_analysis = (
                    self.market_risk_analyzer.analyze_correlation_risk(assets)
                )
                if correlation_analysis:
                    risk_scores[RiskType.CORRELATION] = correlation_analysis.get(
                        "correlation_risk", 0.3
                    )
                    risk_factors["market_risk"]["factors"].extend(
                        correlation_analysis.get("risk_factors", [])
                    )
                    detailed_analysis["correlation_analysis"] = correlation_analysis

                # 分析每个资产的市场风险
                for pos in positions:
                    # 分析市场趋势
                    market_trend = self.market_risk_analyzer.analyze_market_trend(
                        pos.asset
                    )
                    if market_trend:
                        # 添加市场趋势分析
                        if pos.asset not in detailed_analysis:
                            detailed_analysis[pos.asset] = {}
                        detailed_analysis[pos.asset]["market_trend"] = market_trend

                        # 添加风险因素
                        if "risk_factors" in market_trend:
                            risk_factors["market_risk"]["factors"].extend(
                                market_trend["risk_factors"]
                            )

                        # 添加警告
                        if market_trend.get("risk_level") == "HIGH":
                            warnings.append(f"{pos.asset}市场风险较高")

                        # 计算市场风险得分
                        if "volatility" in market_trend:
                            # 加权计算市场风险
                            weight = pos.amount / total_value if total_value > 0 else 0
                            market_risk_score += (
                                min(market_trend["volatility"], 1.0) * weight
                            )

            # 如果没有市场风险分析器或分析失败，使用默认值
            if market_risk_score == 0.0:
                market_risk_score = 0.3  # 默认中等风险

            risk_scores[RiskType.MARKET] = market_risk_score
            risk_factors["market_risk"]["score"] = int(market_risk_score * 100)
            risk_factors["market_risk"]["analysis"] = "基于市场波动性和趋势的风险分析"

            # 分析投资类型风险
            investment_type_risk_score = 0.0
            investment_type_risk_details = {}

            if self.investment_type_risk_analyzer:
                for pos in positions:
                    # 分析投资类型风险
                    invest_risk = (
                        self.investment_type_risk_analyzer.analyze_investment_type_risk(
                            protocol=pos.protocol,
                            asset=pos.asset,
                            invest_type=(
                                pos.invest_type if pos.invest_type is not None else 1
                            ),
                            amount=pos.amount,
                        )
                    )

                    if invest_risk:
                        # 保存投资类型分析
                        key = f"{pos.protocol}_{pos.asset}"
                        investment_type_analysis[key] = invest_risk

                        # 保存详细的投资类型风险信息
                        invest_type = (
                            pos.invest_type if pos.invest_type is not None else 1
                        )
                        if invest_type not in investment_type_risk_details:
                            investment_type_risk_details[invest_type] = {
                                "name": invest_risk.get("invest_type_name", "未知类型"),
                                "positions": [],
                                "total_amount": 0,
                                "risk_score": 0,
                                "risk_factors": [],
                                "recommendations": [],
                                "monitoring_points": [],
                                "risk_mitigation_strategies": [],
                            }

                        # 更新投资类型风险详情
                        investment_type_risk_details[invest_type]["positions"].append(
                            {
                                "protocol": pos.protocol,
                                "asset": pos.asset,
                                "amount": pos.amount,
                            }
                        )
                        investment_type_risk_details[invest_type][
                            "total_amount"
                        ] += pos.amount
                        investment_type_risk_details[invest_type]["risk_score"] = max(
                            investment_type_risk_details[invest_type]["risk_score"],
                            invest_risk.get("risk_score", 0),
                        )
                        investment_type_risk_details[invest_type][
                            "risk_factors"
                        ].extend(invest_risk.get("risk_factors", []))
                        investment_type_risk_details[invest_type][
                            "recommendations"
                        ].extend(invest_risk.get("recommendations", []))
                        investment_type_risk_details[invest_type][
                            "monitoring_points"
                        ].extend(invest_risk.get("monitoring_points", []))
                        investment_type_risk_details[invest_type][
                            "risk_mitigation_strategies"
                        ].extend(invest_risk.get("risk_mitigation_strategies", []))

                        # 添加风险因素
                        risk_factors["investment_type_risk"]["factors"].extend(
                            invest_risk.get("risk_factors", [])
                        )

                        # 添加建议
                        recommendations.extend(invest_risk.get("recommendations", []))

                        # 添加监控点
                        monitoring_points.extend(
                            invest_risk.get("monitoring_points", [])
                        )

                        # 添加风险缓解策略
                        risk_mitigation_strategies.extend(
                            invest_risk.get("risk_mitigation_strategies", [])
                        )

                        # 添加高风险警告
                        if invest_risk.get("risk_score", 0) > 0.7:
                            warnings.append(
                                f"{pos.protocol}的{invest_risk['invest_type_name']}投资风险较高"
                            )

                        # 计算投资类型风险得分
                        weight = pos.amount / total_value if total_value > 0 else 0
                        investment_type_risk_score += (
                            invest_risk.get("risk_score", 0.3) * weight
                        )

                # 保存投资类型风险详情到详细分析
                detailed_analysis["investment_type_risk_details"] = (
                    investment_type_risk_details
                )

                # 分析投资类型组合风险
                if len(investment_type_risk_details) > 0:
                    # 计算投资类型多样性得分 (0-1，越高越多样)
                    diversity_score = min(1.0, len(investment_type_risk_details) / 4)

                    # 如果投资类型过于单一，增加警告
                    if diversity_score < 0.5:
                        warnings.append("投资类型多样性不足，增加了集中度风险")
                        recommendations.append("建议增加投资类型的多样性，分散风险")

                    # 分析高风险投资类型的占比
                    high_risk_types_percentage = 0
                    for invest_type, details in investment_type_risk_details.items():
                        if details["risk_score"] > 0.7:  # 高风险投资类型
                            high_risk_types_percentage += (
                                (details["total_amount"] / total_value * 100)
                                if total_value > 0
                                else 0
                            )

                    # 如果高风险投资类型占比过高，增加警告
                    if high_risk_types_percentage > 40:
                        warnings.append(
                            f"高风险投资类型占比过高({high_risk_types_percentage:.1f}%)，增加了整体风险"
                        )
                        recommendations.append(
                            "建议降低高风险投资类型的比例，增加低风险投资"
                        )
                        risk_factors["investment_type_risk"]["factors"].append(
                            "高风险投资类型占比过高"
                        )

            # 如果没有投资类型风险分析器或分析失败，使用默认值
            if investment_type_risk_score == 0.0:
                investment_type_risk_score = 0.3  # 默认中等风险

            risk_factors["investment_type_risk"]["score"] = int(
                investment_type_risk_score * 100
            )

            # 获取每个协议的AI深度分析
            for pos in positions:
                try:
                    if self.ai_predictor:
                        ai_analysis = (
                            self.ai_predictor.analyze_protocol_risk_from_position(pos)
                        )
                        if ai_analysis:
                            protocol_analysis[pos.protocol] = ai_analysis

                            # 整合AI分析的风险警告
                            if "ai_risk_analysis" in ai_analysis:
                                risk_data = ai_analysis["ai_risk_analysis"]

                                # 添加风险警告
                                if risk_data.get("risk_level") == "HIGH":
                                    warnings.append(f"{pos.protocol}协议风险等级较高")

                                # 添加风险因素
                                if "risk_factors" in risk_data:
                                    for risk_type, risk_info in risk_data[
                                        "risk_factors"
                                    ].items():
                                        if risk_info.get("score", 0) > 70:  # 高风险阈值
                                            warnings.extend(
                                                risk_info.get("factors", [])
                                            )

                                # 添加建议
                                if "recommendations" in risk_data:
                                    recommendations.extend(risk_data["recommendations"])

                                # 添加监控点
                                if "monitoring_points" in risk_data:
                                    monitoring_points.extend(
                                        risk_data["monitoring_points"]
                                    )

                                # 添加风险缓解策略
                                if "risk_mitigation_strategies" in risk_data:
                                    risk_mitigation_strategies.extend(
                                        risk_data["risk_mitigation_strategies"]
                                    )

                                # 更新协议风险评分
                                if "risk_score" in risk_data:
                                    protocol_risk = (
                                        risk_data["risk_score"] / 100
                                    )  # 转换为0-1范围
                                    weight = (
                                        pos.amount / total_value
                                        if total_value > 0
                                        else 0
                                    )
                                    risk_scores[RiskType.PROTOCOL] += (
                                        protocol_risk * weight
                                    )

                                # 更新智能合约风险评分
                                if (
                                    "risk_factors" in risk_data
                                    and "smart_contract" in risk_data["risk_factors"]
                                ):
                                    contract_risk = (
                                        risk_data["risk_factors"]["smart_contract"].get(
                                            "score", 50
                                        )
                                        / 100
                                    )
                                    weight = (
                                        pos.amount / total_value
                                        if total_value > 0
                                        else 0
                                    )
                                    risk_scores[RiskType.SMART_CONTRACT] += (
                                        contract_risk * weight
                                    )

                                # 更新流动性风险评分
                                if (
                                    "risk_factors" in risk_data
                                    and "liquidity" in risk_data["risk_factors"]
                                ):
                                    liquidity_risk = (
                                        risk_data["risk_factors"]["liquidity"].get(
                                            "score", 50
                                        )
                                        / 100
                                    )
                                    weight = (
                                        pos.amount / total_value
                                        if total_value > 0
                                        else 0
                                    )
                                    risk_scores[RiskType.LIQUIDITY] += (
                                        liquidity_risk * weight
                                    )
                except Exception as e:
                    logger.error(f"分析{pos.protocol}协议风险时出错: {e}")

            # 如果没有协议风险分析或分析失败，使用默认值
            if risk_scores[RiskType.PROTOCOL] == 0.0:
                risk_scores[RiskType.PROTOCOL] = 0.3  # 默认中等风险

            if risk_scores[RiskType.SMART_CONTRACT] == 0.0:
                risk_scores[RiskType.SMART_CONTRACT] = 0.3  # 默认中等风险

            if risk_scores[RiskType.LIQUIDITY] == 0.0:
                risk_scores[RiskType.LIQUIDITY] = 0.3  # 默认中等风险

            if risk_scores[RiskType.REGULATORY] == 0.0:
                risk_scores[RiskType.REGULATORY] = 0.2  # 默认较低风险

            # 计算综合风险分数（加权平均）
            # 更新风险权重，加入投资类型风险
            updated_risk_weights = self.risk_weights.copy()
            # 调整权重以包含投资类型风险
            for risk_type in updated_risk_weights:
                updated_risk_weights[risk_type] *= 0.8  # 减少原有权重
            investment_type_risk_weight = 0.2  # 增加投资类型风险权重

            # 计算综合风险分数
            total_risk_score = (
                sum(
                    score * updated_risk_weights[risk_type]
                    for risk_type, score in risk_scores.items()
                )
                + investment_type_risk_score * investment_type_risk_weight
            )

            # 转换为0-100的评分
            normalized_risk_score = int(total_risk_score * 100)

            # 确定风险等级
            risk_level = RiskLevel.LOW
            if total_risk_score > 0.7:
                risk_level = RiskLevel.HIGH
            elif total_risk_score > 0.5:
                risk_level = RiskLevel.MEDIUM
            elif total_risk_score > 0.3:
                risk_level = RiskLevel.LOW

            # 整合AI分析的详细信息
            for pos in positions:
                if pos.protocol in protocol_analysis:
                    detailed_analysis[pos.protocol] = protocol_analysis[pos.protocol]

                # 添加投资类型分析
                key = f"{pos.protocol}_{pos.asset}"
                if key in investment_type_analysis:
                    if "investment_types" not in detailed_analysis:
                        detailed_analysis["investment_types"] = {}
                    detailed_analysis["investment_types"][key] = (
                        investment_type_analysis[key]
                    )

            # 生成投资组合优化建议
            if len(positions) < 3:
                recommendations.append("建议增加投资组合的多样性")
                risk_mitigation_strategies.append("增加不同类型的资产以分散风险")

            # 分析稳定币比例
            stable_coin_ratio = (
                sum(p.amount for p in positions if p.asset in ["USDC", "USDT", "DAI"])
                / total_value
                if total_value > 0
                else 0
            )

            if stable_coin_ratio < 0.2:
                recommendations.append("建议适当增加稳定币的比例以降低整体风险")
            elif stable_coin_ratio > 0.8:
                recommendations.append(
                    "稳定币比例过高，可以考虑适当增加其他资产以提高收益"
                )

            # 基于投资类型的投资组合优化建议
            if self.investment_type_risk_analyzer:
                # 检查是否缺少低风险投资类型
                has_low_risk_type = False
                for invest_type, percentage in investment_type_percentage.items():
                    risk_score = self.investment_type_risk_analyzer.get_base_risk_score(
                        invest_type
                    )
                    if (
                        risk_score <= 0.2 and percentage > 10
                    ):  # 如果低风险投资类型占比超过10%
                        has_low_risk_type = True
                        break

                if not has_low_risk_type:
                    recommendations.append(
                        "建议增加低风险投资类型(如存币)的比例，平衡整体风险"
                    )

                # 检查投资类型是否过于集中
                max_percentage = (
                    max(investment_type_percentage.values())
                    if investment_type_percentage
                    else 0
                )
                if max_percentage > 70:
                    # 找出占比最高的投资类型
                    max_type = None
                    for invest_type, percentage in investment_type_percentage.items():
                        if percentage == max_percentage:
                            max_type = invest_type
                            break

                    if max_type:
                        max_type_name = (
                            self.investment_type_risk_analyzer.get_investment_type_name(
                                max_type
                            )
                        )
                        recommendations.append(
                            f"建议降低{max_type_name}的投资比例，分散到其他投资类型"
                        )
                        risk_mitigation_strategies.append(
                            f"将部分{max_type_name}资金转移到其他投资类型，降低集中度风险"
                        )

            # 生成趋势分析
            trend_analysis = self._generate_trend_analysis(positions)

            # 去重并排序建议、警告、风险缓解策略和监控点
            recommendations = sorted(list(set(recommendations)))
            warnings = sorted(list(set(warnings)))
            risk_mitigation_strategies = sorted(list(set(risk_mitigation_strategies)))
            monitoring_points = sorted(list(set(monitoring_points)))

            # 确保风险因素中没有重复项
            for risk_type in risk_factors:
                if "factors" in risk_factors[risk_type]:
                    risk_factors[risk_type]["factors"] = list(
                        set(risk_factors[risk_type]["factors"])
                    )

            result = RiskAssessment(
                risk_score=normalized_risk_score,
                risk_level=risk_level,
                risk_scores=risk_scores,
                risk_factors=risk_factors,
                trend_analysis=trend_analysis,
                warnings=warnings,
                recommendations=recommendations,
                risk_mitigation_strategies=risk_mitigation_strategies,
                monitoring_points=monitoring_points,
                detailed_analysis=detailed_analysis,
            )

            # 缓存结果
            self.portfolio_cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"评估投资组合风险时出错: {e}")
            return RiskAssessment(
                risk_score=50,  # 默认中等风险分数
                risk_level=RiskLevel.MEDIUM,
                risk_scores={rt: 0.5 for rt in RiskType},
                risk_factors={
                    "tvl_risk": {
                        "score": 50,
                        "analysis": "风险评估出错",
                        "factors": ["系统错误"],
                    },
                    "chain_risk": {
                        "score": 50,
                        "analysis": "风险评估出错",
                        "factors": ["系统错误"],
                    },
                    "market_risk": {
                        "score": 50,
                        "analysis": "风险评估出错",
                        "factors": ["系统错误"],
                    },
                    "technical_risk": {
                        "score": 50,
                        "analysis": "风险评估出错",
                        "factors": ["系统错误"],
                    },
                    "investment_type_risk": {
                        "score": 50,
                        "analysis": "风险评估出错",
                        "factors": ["系统错误"],
                    },
                },
                trend_analysis={
                    "short_term": "无法评估",
                    "medium_term": "无法评估",
                    "key_indicators": {
                        "macd_signal": "无法评估",
                        "rsi_signal": "无法评估",
                        "volume_analysis": "无法评估",
                    },
                },
                warnings=["风险评估过程中出现错误，建议手动检查存款状态"],
                recommendations=["建议在修复风险评估系统之前保持谨慎"],
                risk_mitigation_strategies=["暂时减少投资敞口"],
                monitoring_points=["系统错误修复状态"],
                detailed_analysis={"error": str(e)},
            )

    def _generate_trend_analysis(self, positions: List[Position]) -> Dict:
        """
        生成趋势分析

        Args:
            positions: 投资头寸列表

        Returns:
            Dict: 趋势分析结果
        """
        try:
            if not positions or not self.market_risk_analyzer:
                return {
                    "short_term": "无数据",
                    "medium_term": "无数据",
                    "key_indicators": {
                        "macd_signal": "无数据",
                        "rsi_signal": "无数据",
                        "volume_analysis": "无数据",
                    },
                }

            # 获取主要资产的趋势分析
            main_assets = []
            for pos in positions:
                if pos.asset not in main_assets:
                    main_assets.append(pos.asset)

            if not main_assets:
                return {
                    "short_term": "无数据",
                    "medium_term": "无数据",
                    "key_indicators": {
                        "macd_signal": "无数据",
                        "rsi_signal": "无数据",
                        "volume_analysis": "无数据",
                    },
                }

            # 分析每个资产的趋势
            asset_trends = {}
            for asset in main_assets:
                trend_analysis = self.market_risk_analyzer.analyze_market_trend(asset)
                if trend_analysis:
                    asset_trends[asset] = trend_analysis

            if not asset_trends:
                return {
                    "short_term": "无数据",
                    "medium_term": "无数据",
                    "key_indicators": {
                        "macd_signal": "无数据",
                        "rsi_signal": "无数据",
                        "volume_analysis": "无数据",
                    },
                }

            # 综合分析趋势
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0

            for asset, trend in asset_trends.items():
                if trend.get("trend") == "bullish":
                    bullish_count += 1
                elif trend.get("trend") == "bearish":
                    bearish_count += 1
                else:
                    neutral_count += 1

            # 确定短期趋势
            if bullish_count > bearish_count and bullish_count > neutral_count:
                short_term = "看涨"
            elif bearish_count > bullish_count and bearish_count > neutral_count:
                short_term = "看跌"
            else:
                short_term = "中性"

            # 确定中期趋势（如果有AI预测）
            medium_term = "无法确定"
            if self.ai_predictor:
                try:
                    # 使用AI预测中期趋势
                    medium_term_prediction = (
                        self.ai_predictor.predict_medium_term_trend(asset_trends)
                    )
                    if medium_term_prediction:
                        medium_term = medium_term_prediction
                except Exception as e:
                    logger.error(f"预测中期趋势时出错: {e}")

            # 生成关键指标
            key_indicators = {
                "macd_signal": "无数据",
                "rsi_signal": "无数据",
                "volume_analysis": "无数据",
            }

            # 如果有AI预测器，使用它生成关键指标
            if self.ai_predictor:
                try:
                    indicators = self.ai_predictor.analyze_technical_indicators(
                        asset_trends
                    )
                    if indicators:
                        key_indicators = indicators
                except Exception as e:
                    logger.error(f"分析技术指标时出错: {e}")

            return {
                "short_term": short_term,
                "medium_term": medium_term,
                "key_indicators": key_indicators,
                "asset_trends": {
                    asset: {
                        "trend": trend.get("trend", "unknown"),
                        "risk_level": trend.get("risk_level", "MEDIUM"),
                    }
                    for asset, trend in asset_trends.items()
                },
            }

        except Exception as e:
            logger.error(f"生成趋势分析时出错: {e}")
            return {
                "short_term": "无法评估",
                "medium_term": "无法评估",
                "key_indicators": {
                    "macd_signal": "无法评估",
                    "rsi_signal": "无法评估",
                    "volume_analysis": "无法评估",
                },
                "error": str(e),
            }

    def generate_ai_portfolio_recommendations(self, positions: List[Position]) -> Dict:
        """
        生成AI驱动的投资组合优化建议

        Args:
            positions: 投资头寸列表

        Returns:
            Dict: 投资组合优化建议
        """
        try:
            if not positions or not self.ai_predictor:
                return {
                    "portfolio_risk_score": 50,
                    "diversification_score": 0.5,
                    "high_correlation_pairs": [],
                    "rebalance_recommendations": ["无法生成优化建议"],
                    "risk_reduction_strategies": ["无法生成风险缓解策略"],
                }

            # 使用AI预测器分析投资组合
            return self.ai_predictor.analyze_portfolio_optimization(positions)

        except Exception as e:
            logger.error(f"生成AI投资组合建议时出错: {e}")
            return {
                "portfolio_risk_score": 50,
                "diversification_score": 0.5,
                "high_correlation_pairs": [],
                "rebalance_recommendations": ["生成优化建议时出错"],
                "risk_reduction_strategies": ["建议手动评估投资组合风险"],
                "error": str(e),
            }
