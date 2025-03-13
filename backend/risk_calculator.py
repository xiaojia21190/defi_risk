from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import pandas as pd
from datetime import datetime
from ai_predictor import AiPredictor
from cachetools import TTLCache, LRUCache
import json
import hashlib
import pandas_ta

logger = logging.getLogger("defi_risk.calculator")


class PerformanceMetrics:
    """性能指标收集和分析"""

    _metrics = {
        "execution_times": {},
        "memory_usage": {},
        "cache_hits": {},
        "cache_misses": {},
    }

    @classmethod
    def record_metric(
        cls, function_name: str, execution_time: float, memory_used: float
    ):
        """记录性能指标"""
        if function_name not in cls._metrics["execution_times"]:
            cls._metrics["execution_times"][function_name] = []
        if function_name not in cls._metrics["memory_usage"]:
            cls._metrics["memory_usage"][function_name] = []

        cls._metrics["execution_times"][function_name].append(execution_time)
        cls._metrics["memory_usage"][function_name].append(memory_used)

    @classmethod
    def record_cache_access(cls, function_name: str, hit: bool):
        """记录缓存访问"""
        metric_key = "cache_hits" if hit else "cache_misses"
        if function_name not in cls._metrics[metric_key]:
            cls._metrics[metric_key][function_name] = 0
        cls._metrics[metric_key][function_name] += 1

    @classmethod
    def get_metrics_summary(cls) -> Dict:
        """获取性能指标摘要"""
        summary = {}
        for function_name in cls._metrics["execution_times"]:
            times = cls._metrics["execution_times"][function_name]
            memory = cls._metrics["memory_usage"][function_name]
            hits = cls._metrics["cache_hits"].get(function_name, 0)
            misses = cls._metrics["cache_misses"].get(function_name, 0)

            summary[function_name] = {
                "avg_execution_time": sum(times) / len(times),
                "max_execution_time": max(times),
                "avg_memory_usage": sum(memory) / len(memory),
                "max_memory_usage": max(memory),
                "cache_hit_rate": hits / (hits + misses) if (hits + misses) > 0 else 0,
            }

        return summary


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
class LiquidityMetrics:
    depth_score: float  # 0-1
    volume_24h: float
    slippage_impact: float
    withdrawal_limits: Optional[Dict[str, float]]


@dataclass
class Position:
    protocol: str
    asset: str
    amount: float
    apy: Optional[float] = None


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


class RiskCalculator:
    def __init__(self):
        # 风险阈值配置
        self.high_volatility_threshold = 0.5  # 50% 的价格波动作为高波动性阈值

        # 风险等级定义
        self.RISK_LEVELS = {"LOW": "低风险", "MEDIUM": "中等风险", "HIGH": "高风险"}

        # 初始化AI预测器
        self.ai_predictor = AiPredictor()

        # 缓存
        self.market_analysis_cache = {}
        self.protocol_security_cache = {}
        self.liquidity_analysis_cache = {}

        # 资产链映射
        self.asset_chain_map = {
            # 以太坊资产
            "ETH": "Ethereum",
            "WETH": "Ethereum",
            "DAI": "Ethereum",
            "USDC": "Ethereum",
            "USDT": "Ethereum",
            # BSC资产
            "BNB": "BSC",
            "CAKE": "BSC",
            "BUSD": "BSC",
            # Solana资产
            "SOL": "Solana",
            # Polygon资产
            "MATIC": "Polygon",
            "AAVE": "Polygon",
            # Avalanche资产
            "AVAX": "Avalanche",
        }

        # 多链资产的默认链映射
        self.multichain_assets = {
            "USDC": ["Ethereum", "BSC", "Solana", "Polygon", "Avalanche"],
            "USDT": ["Ethereum", "BSC", "Solana", "Polygon", "Avalanche"],
            "BTC": ["Ethereum", "BSC", "Solana"],  # 包装形式
        }

        # 风险权重配置
        self.risk_weights = {
            RiskType.MARKET: 0.3,
            RiskType.SMART_CONTRACT: 0.2,
            RiskType.LIQUIDITY: 0.2,
            RiskType.PROTOCOL: 0.15,
            RiskType.CORRELATION: 0.1,
            RiskType.REGULATORY: 0.05,
        }

        # 协议安全基准数据
        self.protocol_security_baseline = {
            "Aave": {"audit_count": 5, "security_score": 0.9},
            "Compound": {"audit_count": 4, "security_score": 0.85},
            "Uniswap": {"audit_count": 3, "security_score": 0.8},
            # 可以添加更多协议的基准数据
        }

        # 缓存配置
        self.protocol_cache = TTLCache(maxsize=1000, ttl=3600)  # 1小时过期
        self.portfolio_cache = TTLCache(maxsize=100, ttl=300)  # 5分钟过期
        self.market_data_cache = LRUCache(maxsize=500)  # LRU缓存

        # 性能监控阈值
        self.performance_thresholds = {
            "execution_time_warning": 5.0,  # 秒
            "memory_usage_warning": 500.0,  # MB
            "cache_hit_rate_warning": 0.5,  # 50%
        }

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

    def _check_cache_performance(self):
        """检查缓存性能"""
        metrics = PerformanceMetrics.get_metrics_summary()
        for func_name, data in metrics.items():
            if (
                data["avg_execution_time"]
                > self.performance_thresholds["execution_time_warning"]
            ):
                logger.warning(f"性能警告: {func_name} 平均执行时间过长")
            if (
                data["cache_hit_rate"]
                < self.performance_thresholds["cache_hit_rate_warning"]
            ):
                logger.warning(f"缓存警告: {func_name} 缓存命中率过低")

    def calculate_market_volatility_risk(
        self, position: Position, historical_data: Optional[pd.DataFrame] = None
    ) -> float:
        """
        计算市场波动风险
        返回0-1之间的风险值，0表示最低风险，1表示最高风险

        如果提供了历史数据，则使用AI预测器进行更准确的风险评估
        """
        cache_key = f"market_vol_{position.asset}_{position.protocol}"

        # 检查缓存
        cached_result = self.market_data_cache.get(cache_key)
        if cached_result:
            PerformanceMetrics.record_cache_access(
                "calculate_market_volatility_risk", True
            )
            return cached_result

        PerformanceMetrics.record_cache_access(
            "calculate_market_volatility_risk", False
        )

        try:
            # 如果有历史数据，使用AI预测器进行分析
            if historical_data is not None and not historical_data.empty:
                # 检查缓存中是否已有分析结果
                if position.asset in self.market_analysis_cache:
                    market_analysis = self.market_analysis_cache[position.asset]
                else:
                    # 使用AI预测器分析市场趋势
                    market_analysis = self.ai_predictor.analyze_market_trend(
                        historical_data, position.asset
                    )
                    # 缓存分析结果
                    self.market_analysis_cache[position.asset] = market_analysis

                # 从AI分析结果中提取风险信息
                if market_analysis and "risk_level" in market_analysis:
                    risk_level = market_analysis["risk_level"]
                    # 将风险等级转换为数值
                    if risk_level == "HIGH":
                        return 0.8
                    elif risk_level == "MEDIUM":
                        return 0.5
                    elif risk_level == "LOW":
                        return 0.2

                # 如果有波动率数据，使用它来计算风险
                if market_analysis and "volatility" in market_analysis:
                    volatility = market_analysis["volatility"]
                    # 将波动率标准化为0-1之间的风险值
                    return min(volatility / 20, 1.0)  # 假设20%的波动率对应最高风险

            # 如果没有历史数据或AI分析失败，使用预设的映射表
            volatility_map = {
                "ETH": 0.4,
                "USDC": 0.01,
                "DAI": 0.02,
                "BTC": 0.5,
                "USDT": 0.01,
            }

            base_volatility = volatility_map.get(position.asset, 0.3)
            return min(base_volatility, 1.0)

        except Exception as e:
            logger.error(f"计算市场波动风险时出错: {e}")
            return 0.5

    def generate_recommendations(
        self,
        positions: List[Position],
        volatility_risk: float,
        historical_data_map: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> List[str]:
        """根据风险评估生成建议，可选择使用AI增强的建议"""
        recommendations = []

        # 分析存款分布
        total_value = sum(p.amount for p in positions)
        protocol_exposure = {}
        asset_exposure = {}

        for pos in positions:
            protocol_exposure[pos.protocol] = (
                protocol_exposure.get(pos.protocol, 0) + pos.amount
            )
            asset_exposure[pos.asset] = asset_exposure.get(pos.asset, 0) + pos.amount

        # 检查协议集中度
        for protocol, amount in protocol_exposure.items():
            if amount / total_value > 0.5:  # 如果单个协议占比超过50%
                recommendations.append(
                    f"建议分散 {protocol} 协议的存款，降低单一协议风险"
                )

        # 检查资产集中度
        for asset, amount in asset_exposure.items():
            if amount / total_value > 0.4:  # 如果单个资产占比超过40%
                recommendations.append(f"建议分散 {asset} 资产的存款配置")

                # 如果有历史数据，使用AI分析该资产的市场趋势
                if historical_data_map and asset in historical_data_map:
                    market_analysis = self.ai_predictor.analyze_market_trend(
                        historical_data_map[asset], asset
                    )

                    # 根据AI分析结果提供更具体的建议
                    if market_analysis:
                        if "trend" in market_analysis:
                            trend = market_analysis["trend"]
                            if trend == "bearish":
                                recommendations.append(
                                    f"{asset}当前处于下跌趋势，建议减少持仓或设置止损"
                                )
                            elif trend == "bullish":
                                recommendations.append(
                                    f"{asset}当前处于上涨趋势，可以考虑持有或适量增加"
                                )

                        # 添加AI推荐的交易信号
                        if (
                            "trading_signals" in market_analysis
                            and market_analysis["trading_signals"]
                        ):
                            for signal in market_analysis["trading_signals"][
                                :2
                            ]:  # 只取前两个信号
                                recommendations.append(f"{asset}交易信号: {signal}")

        # 根据波动性风险提供建议
        if volatility_risk > 0.7:
            recommendations.append("当前市场波动较大，建议增加稳定币比例")
        elif volatility_risk < 0.3:
            recommendations.append("当前市场稳定，可以考虑适当增加收益率较高的资产配置")

        return recommendations

    def assess_portfolio_risk(
        self,
        positions: List[Position],
        historical_data_map: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> RiskAssessment:
        """评估整个投资组合的风险，包含多个维度的风险分析"""
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(
                positions, historical_data=bool(historical_data_map)
            )

            # 检查缓存
            cached_result = self.portfolio_cache.get(cache_key)
            if cached_result:
                PerformanceMetrics.record_cache_access("assess_portfolio_risk", True)
                logger.info("使用缓存的投资组合风险评估结果")
                return cached_result

            PerformanceMetrics.record_cache_access("assess_portfolio_risk", False)

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
            risk_scores = {}  # 原始风险评分（0-1范围）
            risk_factors = {  # 新的风险因素结构（0-100范围）
                "tvl_risk": {"score": 0, "analysis": "", "factors": []},
                "chain_risk": {"score": 0, "analysis": "", "factors": []},
                "market_risk": {"score": 0, "analysis": "", "factors": []},
                "technical_risk": {"score": 0, "analysis": "", "factors": []},
            }
            warnings = []
            recommendations = []
            risk_mitigation_strategies = []
            monitoring_points = []
            detailed_analysis = {}
            protocol_analysis = {}

            # 获取每个协议的AI深度分析
            for pos in positions:
                try:
                    ai_analysis = self.ai_predictor.analyze_defi_protocol_risk(
                        pos.protocol
                    )
                    if ai_analysis:
                        protocol_analysis[pos.protocol] = ai_analysis

                        # 整合AI分析的风险警告
                        if "ai_risk_analysis" in ai_analysis:
                            risk_data = ai_analysis["ai_risk_analysis"]

                            # 添加风险警告
                            if risk_data["risk_level"] == "HIGH":
                                warnings.append(f"{pos.protocol}协议风险等级较高")

                            # 添加风险因素
                            for risk_type, risk_info in risk_data[
                                "risk_factors"
                            ].items():
                                if risk_info["score"] > 70:  # 高风险阈值
                                    warnings.extend(risk_info["factors"])

                            # 添加建议
                            recommendations.extend(risk_data["recommendations"])

                            # 添加监控点
                            monitoring_points.extend(risk_data["monitoring_points"])

                            # 添加风险缓解策略
                            if "risk_mitigation_strategies" in risk_data:
                                risk_mitigation_strategies.extend(
                                    risk_data["risk_mitigation_strategies"]
                                )

                except Exception as e:
                    logger.warning(f"获取{pos.protocol}的AI分析时出错: {e}")

            # 1. 计算市场风险
            position_market_risks = []
            for pos in positions:
                historical_data = (
                    historical_data_map.get(pos.asset) if historical_data_map else None
                )
                risk = self.calculate_market_volatility_risk(pos, historical_data)
                position_market_risks.append((pos, risk))

                # 整合AI分析的市场风险
                if pos.protocol in protocol_analysis:
                    ai_risk_score = (
                        protocol_analysis[pos.protocol]
                        .get("ai_risk_analysis", {})
                        .get("risk_factors", {})
                        .get("market_risk", {})
                        .get("score", 50)
                    )

                    # 更新市场风险因素
                    if "market_risk" not in risk_factors:
                        risk_factors["market_risk"] = {
                            "score": ai_risk_score,
                            "analysis": "",
                            "factors": [],
                        }
                    else:
                        risk_factors["market_risk"]["score"] = max(
                            risk_factors["market_risk"]["score"], ai_risk_score
                        )

                    # 添加分析和因素
                    if "analysis" in protocol_analysis[pos.protocol].get(
                        "ai_risk_analysis", {}
                    ).get("risk_factors", {}).get("market_risk", {}):
                        risk_factors["market_risk"]["analysis"] = protocol_analysis[
                            pos.protocol
                        ]["ai_risk_analysis"]["risk_factors"]["market_risk"]["analysis"]

                    if "factors" in protocol_analysis[pos.protocol].get(
                        "ai_risk_analysis", {}
                    ).get("risk_factors", {}).get("market_risk", {}):
                        risk_factors["market_risk"]["factors"].extend(
                            protocol_analysis[pos.protocol]["ai_risk_analysis"][
                                "risk_factors"
                            ]["market_risk"]["factors"]
                        )

            total_value = sum(pos.amount for pos in positions)
            weighted_market_risk = sum(
                risk * pos.amount / total_value for pos, risk in position_market_risks
            )
            risk_scores[RiskType.MARKET] = weighted_market_risk

            # 如果没有AI分析，使用计算的风险值
            if (
                "market_risk" not in risk_factors
                or risk_factors["market_risk"]["score"] == 0
            ):
                risk_factors["market_risk"] = {
                    "score": int(weighted_market_risk * 100),
                    "analysis": "基于历史波动性的市场风险分析",
                    "factors": ["市场波动性", "价格趋势"],
                }

            # 2. 计算智能合约风险（整合AI分析）
            contract_risks = []
            for pos in positions:
                base_risk = 0.5  # 默认中等风险

                # 整合AI分析的技术风险
                if pos.protocol in protocol_analysis:
                    ai_technical_risk_score = (
                        protocol_analysis[pos.protocol]
                        .get("ai_risk_analysis", {})
                        .get("risk_factors", {})
                        .get("technical_risk", {})
                        .get("score", 50)
                    )

                    # 更新技术风险因素
                    if "technical_risk" not in risk_factors:
                        risk_factors["technical_risk"] = {
                            "score": ai_technical_risk_score,
                            "analysis": "",
                            "factors": [],
                        }
                    else:
                        risk_factors["technical_risk"]["score"] = max(
                            risk_factors["technical_risk"]["score"],
                            ai_technical_risk_score,
                        )

                    # 添加分析和因素
                    if "analysis" in protocol_analysis[pos.protocol].get(
                        "ai_risk_analysis", {}
                    ).get("risk_factors", {}).get("technical_risk", {}):
                        risk_factors["technical_risk"]["analysis"] = protocol_analysis[
                            pos.protocol
                        ]["ai_risk_analysis"]["risk_factors"]["technical_risk"][
                            "analysis"
                        ]

                    if "factors" in protocol_analysis[pos.protocol].get(
                        "ai_risk_analysis", {}
                    ).get("risk_factors", {}).get("technical_risk", {}):
                        risk_factors["technical_risk"]["factors"].extend(
                            protocol_analysis[pos.protocol]["ai_risk_analysis"][
                                "risk_factors"
                            ]["technical_risk"]["factors"]
                        )

                    ai_technical_risk = ai_technical_risk_score / 100
                    risk = (base_risk + ai_technical_risk) / 2  # 综合评分
                else:
                    risk = base_risk

                contract_risks.append((pos, risk))
                if risk > 0.7:
                    warnings.append(f"{pos.protocol}协议的智能合约风险较高")
                    monitoring_points.append(f"{pos.protocol}的安全审计状态")
                    risk_mitigation_strategies.append(
                        f"限制在{pos.protocol}上的资产敞口"
                    )

            weighted_contract_risk = sum(
                risk * pos.amount / total_value for pos, risk in contract_risks
            )
            risk_scores[RiskType.SMART_CONTRACT] = weighted_contract_risk

            # 如果没有AI分析，使用计算的风险值
            if (
                "technical_risk" not in risk_factors
                or risk_factors["technical_risk"]["score"] == 0
            ):
                risk_factors["technical_risk"] = {
                    "score": int(weighted_contract_risk * 100),
                    "analysis": "基于智能合约安全性的技术风险分析",
                    "factors": ["代码审计状态", "历史漏洞"],
                }

            # 3. 计算流动性风险（整合AI分析）
            liquidity_risks = []
            for pos in positions:
                base_risk = 0.5  # 默认中等风险

                # 整合AI分析的流动性风险
                if pos.protocol in protocol_analysis:
                    ai_tvl_risk_score = (
                        protocol_analysis[pos.protocol]
                        .get("ai_risk_analysis", {})
                        .get("risk_factors", {})
                        .get("tvl_risk", {})
                        .get("score", 50)
                    )

                    # 更新TVL风险因素
                    if "tvl_risk" not in risk_factors:
                        risk_factors["tvl_risk"] = {
                            "score": ai_tvl_risk_score,
                            "analysis": "",
                            "factors": [],
                        }
                    else:
                        risk_factors["tvl_risk"]["score"] = max(
                            risk_factors["tvl_risk"]["score"], ai_tvl_risk_score
                        )

                    # 添加分析和因素
                    if "analysis" in protocol_analysis[pos.protocol].get(
                        "ai_risk_analysis", {}
                    ).get("risk_factors", {}).get("tvl_risk", {}):
                        risk_factors["tvl_risk"]["analysis"] = protocol_analysis[
                            pos.protocol
                        ]["ai_risk_analysis"]["risk_factors"]["tvl_risk"]["analysis"]

                    if "factors" in protocol_analysis[pos.protocol].get(
                        "ai_risk_analysis", {}
                    ).get("risk_factors", {}).get("tvl_risk", {}):
                        risk_factors["tvl_risk"]["factors"].extend(
                            protocol_analysis[pos.protocol]["ai_risk_analysis"][
                                "risk_factors"
                            ]["tvl_risk"]["factors"]
                        )

                    ai_liquidity_risk = ai_tvl_risk_score / 100
                    risk = (base_risk + ai_liquidity_risk) / 2  # 综合评分
                else:
                    risk = base_risk

                liquidity_risks.append((pos, risk))
                if risk > 0.7:
                    warnings.append(f"{pos.asset}资产的流动性风险较高")
                    recommendations.append(
                        f"建议减少{pos.asset}的持仓量或分散到其他资产"
                    )
                    monitoring_points.append(f"{pos.protocol}的TVL变化趋势")
                    risk_mitigation_strategies.append(
                        f"为{pos.asset}设置流动性阈值警报"
                    )

            weighted_liquidity_risk = sum(
                risk * pos.amount / total_value for pos, risk in liquidity_risks
            )
            risk_scores[RiskType.LIQUIDITY] = weighted_liquidity_risk

            # 如果没有AI分析，使用计算的风险值
            if "tvl_risk" not in risk_factors or risk_factors["tvl_risk"]["score"] == 0:
                risk_factors["tvl_risk"] = {
                    "score": int(weighted_liquidity_risk * 100),
                    "analysis": "基于TVL数据和流动性指标的风险分析",
                    "factors": ["TVL变化趋势", "流动性深度"],
                }

            # 4. 计算协议风险（整合AI分析）
            protocol_risks = {}
            for pos in positions:
                if pos.protocol in protocol_analysis:
                    ai_risk_score = (
                        protocol_analysis[pos.protocol].get("risk_score", 50) / 100
                    )
                    protocol_risks[pos.protocol] = ai_risk_score
                else:
                    protocol_risks[pos.protocol] = 0.5  # 默认中等风险

            weighted_protocol_risk = sum(
                risk * positions[i].amount / total_value
                for i, (protocol, risk) in enumerate(protocol_risks.items())
            )
            risk_scores[RiskType.PROTOCOL] = weighted_protocol_risk

            # 更新链风险因素（基于相关性）
            chain_distribution = {}
            for pos in positions:
                chain = self._get_asset_chain(pos.asset)
                if chain in chain_distribution:
                    chain_distribution[chain] += pos.amount
                else:
                    chain_distribution[chain] = pos.amount

            # 计算链集中度
            chain_concentration = (
                max(chain_distribution.values()) / total_value if total_value > 0 else 0
            )
            chain_risk_score = int(chain_concentration * 100)

            risk_factors["chain_risk"] = {
                "score": chain_risk_score,
                "analysis": "基于链分布和集中度的风险分析",
                "factors": [
                    f"{chain}链占比{chain_amount/total_value*100:.1f}%"
                    for chain, chain_amount in chain_distribution.items()
                ],
            }

            # 5. 计算监管风险（整合AI分析）
            regulatory_risks = []
            for pos in positions:
                base_risk = self.calculate_regulatory_risk(pos)
                risk = base_risk

                regulatory_risks.append((pos, risk))
                if risk > 0.7:
                    warnings.append(f"{pos.asset}面临较高的监管风险")
                    monitoring_points.append(f"{pos.asset}相关的监管动态")
                    risk_mitigation_strategies.append(f"降低{pos.asset}的持仓比例")

            weighted_regulatory_risk = sum(
                risk * pos.amount / total_value for pos, risk in regulatory_risks
            )
            risk_scores[RiskType.REGULATORY] = weighted_regulatory_risk

            # 添加趋势分析
            trend_analysis = {
                "short_term": "无数据",
                "medium_term": "无数据",
                "key_indicators": {
                    "macd_signal": "无数据",
                    "rsi_signal": "无数据",
                    "volume_analysis": "无数据",
                },
            }

            # 从历史数据中分析趋势
            if historical_data_map:
                for asset, data in historical_data_map.items():
                    if len(data) > 30:  # 确保有足够数据
                        try:
                            # 计算技术指标
                            macd, signal, _ = pandas_ta.MACD(data["close"])
                            rsi = pandas_ta.RSI(data["close"])

                            # 填充趋势分析
                            trend_analysis["short_term"] = (
                                "上升趋势" if macd[-1] > signal[-1] else "下降趋势"
                            )
                            trend_analysis["medium_term"] = (
                                self._analyze_medium_term_trend(data)
                            )
                            trend_analysis["key_indicators"][
                                "macd_signal"
                            ] = f"MACD: {'看涨' if macd[-1] > signal[-1] else '看跌'}"
                            trend_analysis["key_indicators"][
                                "rsi_signal"
                            ] = f"RSI: {rsi[-1]:.2f} - {'超买' if rsi[-1] > 70 else '超卖' if rsi[-1] < 30 else '中性'}"
                            trend_analysis["key_indicators"]["volume_analysis"] = (
                                self._analyze_volume(data)
                            )
                            break  # 暂时只分析第一个资产的趋势
                        except Exception as e:
                            logger.warning(f"计算{asset}的技术指标时出错: {e}")

            # 计算综合风险分数（整合AI分析）
            total_risk_score = sum(
                score * self.risk_weights[risk_type]
                for risk_type, score in risk_scores.items()
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

            # 生成投资组合优化建议
            if len(positions) < 3:
                recommendations.append("建议增加投资组合的多样性")
                risk_mitigation_strategies.append("增加不同类型的资产以分散风险")

            stable_coin_ratio = (
                (
                    sum(
                        p.amount
                        for p in positions
                        if p.asset in ["USDC", "USDT", "DAI"]
                    )
                    / total_value
                )
                if total_value > 0
                else 0
            )

            if stable_coin_ratio < 0.2:
                recommendations.append("建议适当增加稳定币的比例以降低整体风险")
            elif stable_coin_ratio > 0.8:
                recommendations.append(
                    "稳定币比例过高，可以考虑适当增加其他资产以提高收益"
                )

            # 添加市场波动性相关建议
            market_volatility = (
                sum(risk for _, risk in position_market_risks)
                / len(position_market_risks)
                if position_market_risks
                else 0
            )
            if market_volatility > 0.7:
                recommendations.append("当前市场波动较大，建议增加稳定币比例")
                monitoring_points.append("市场波动指标(VIX)")
            elif market_volatility < 0.3:
                recommendations.append(
                    "当前市场稳定，可以考虑适当增加收益率较高的资产配置"
                )

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

            # 检查性能
            self._check_cache_performance()

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

    def calculate_regulatory_risk(self, position: Position) -> float:
        """评估监管风险"""
        try:
            # 基于资产类型的基础风险评分
            base_risk_scores = {
                "USDC": 0.2,  # 受监管的稳定币
                "USDT": 0.3,  # 有争议的稳定币
                "DAI": 0.4,  # 去中心化稳定币
                "ETH": 0.5,  # 主流加密货币
                "BTC": 0.5,  # 主流加密货币
            }

            # 获取基础风险分数，默认为0.6
            base_risk = base_risk_scores.get(position.asset, 0.6)

            # 根据协议类型调整风险
            protocol_risk_multipliers = {
                "Aave": 0.9,  # 较为成熟的借贷协议
                "Compound": 0.9,  # 较为成熟的借贷协议
                "Uniswap": 1.0,  # DEX
                "Curve Finance": 1.0,  # DEX
            }

            # 获取协议风险乘数，默认为1.1
            protocol_multiplier = protocol_risk_multipliers.get(position.protocol, 1.1)

            # 计算最终风险分数
            risk_score = base_risk * protocol_multiplier

            return min(max(risk_score, 0), 1)
        except Exception as e:
            logger.error(f"计算监管风险时出错: {e}")
            return 0.5

    def _get_asset_chain(self, asset: str) -> str:
        """
        根据资产名称确定其所在的区块链

        参数:
            asset: 资产名称或标识符

        返回:
            str: 区块链名称
        """
        # 处理资产名称中可能包含的链信息，如"ETH.Ethereum"或"USDC-Polygon"
        if "." in asset:
            parts = asset.split(".")
            if len(parts) > 1:
                return parts[1]
        elif "-" in asset:
            parts = asset.split("-")
            if len(parts) > 1:
                return parts[1]

        # 检查资产是否在映射中
        asset_symbol = asset.upper()
        if asset_symbol in self.asset_chain_map:
            return self.asset_chain_map[asset_symbol]

        # 处理资产名称前缀
        if asset_symbol.startswith("A"):
            return "Avalanche"
        elif asset_symbol.startswith("B"):
            return "BSC"
        elif asset_symbol.startswith("P"):
            return "Polygon"
        elif asset_symbol.startswith("S"):
            return "Solana"

        # 默认返回以太坊
        return "Ethereum"
