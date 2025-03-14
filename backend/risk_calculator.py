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
    invest_type: Optional[int] = None  # 添加 invest_type 字段以兼容 PlatformAsset


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
    def __init__(self, blockchain_service=None):
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

        # 缓存配置
        self.protocol_cache = TTLCache(maxsize=1000, ttl=3600)  # 1小时过期
        self.portfolio_cache = TTLCache(maxsize=100, ttl=300)  # 5分钟过期
        self.market_data_cache = LRUCache(maxsize=500)  # LRU缓存

        # 区块链服务引用
        self.blockchain_service = blockchain_service

        # 投资类型风险权重配置
        self.invest_type_risk_weights = {
            1: 0.1,  # 存币 - 较低风险
            2: 0.4,  # 流动性池 - 较高风险
            3: 0.3,  # 挖矿 - 中高风险
            4: 0.5,  # 机枪池 - 高风险
            5: 0.2,  # 质押 - 中低风险
            6: 0.3,  # 借贷 - 中高风险
        }

        # 投资类型名称映射
        self.invest_type_map = {
            1: "存币",
            2: "流动性池",
            3: "挖矿",
            4: "机枪池",
            5: "质押",
            6: "借贷",
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

                # 尝试获取资产的历史数据并使用AI分析市场趋势
                try:
                    # 使用新方法获取历史数据
                    historical_data = self._get_asset_historical_data(asset)

                    if historical_data is not None and not historical_data.empty:
                        market_analysis = self.ai_predictor.analyze_market_trend(
                            historical_data, asset
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
                except Exception as e:
                    logger.error(f"获取{asset}历史数据或分析市场趋势时出错: {e}")

        # 根据波动性风险提供建议
        if volatility_risk > 0.7:
            recommendations.append("当前市场波动较大，建议增加稳定币比例")
        elif volatility_risk < 0.3:
            recommendations.append("当前市场稳定，可以考虑适当增加收益率较高的资产配置")

        return recommendations

    def analyze_investment_type_risk(self, position: Position) -> Dict:
        """
        根据投资类型分析风险

        Args:
            position: 投资头寸

        Returns:
            Dict: 包含风险分析结果的字典
        """
        try:
            # 如果没有投资类型，默认为存币(1)
            invest_type = (
                position.invest_type if position.invest_type is not None else 1
            )
            invest_type_name = self.invest_type_map.get(invest_type, "未知类型")

            # 基础风险评分 (0-1范围)
            base_risk = self.invest_type_risk_weights.get(invest_type, 0.3)

            # 初始化风险分析结果
            risk_analysis = {
                "invest_type": invest_type,
                "invest_type_name": invest_type_name,
                "base_risk_score": base_risk,
                "risk_factors": [],
                "recommendations": [],
                "monitoring_points": [],
            }

            # 根据不同投资类型进行特定分析
            if invest_type == 1:  # 存币
                risk_analysis["risk_factors"].append(
                    "存币通常风险较低，但仍需关注平台安全性"
                )
                risk_analysis["recommendations"].append(
                    f"定期检查{position.protocol}平台的安全状态"
                )
                risk_analysis["monitoring_points"].append("平台安全审计状态")

            elif invest_type == 2:  # 流动性池
                risk_analysis["risk_factors"].extend(
                    [
                        "流动性池面临无常损失风险",
                        "价格波动可能导致资产比例变化",
                        "流动性池合约可能存在安全漏洞",
                    ]
                )
                risk_analysis["recommendations"].extend(
                    [
                        f"关注{position.asset}的价格波动",
                        "设置止损策略以防止无常损失过大",
                        "分散投资于多个流动性池",
                    ]
                )
                risk_analysis["monitoring_points"].extend(
                    ["资产价格相对变化", "池子总流动性变化", "交易费收益率"]
                )

                # 流动性池特有的风险调整
                # 检查是否包含小市值代币
                if "-" in position.asset:
                    tokens = position.asset.split("-")
                    for token in tokens:
                        if token not in ["ETH", "WETH", "BTC", "USDC", "USDT", "DAI"]:
                            risk_analysis["risk_factors"].append(
                                f"{token}可能是小市值代币，存在较高波动风险"
                            )
                            risk_analysis["base_risk_score"] += 0.1  # 增加风险评分

            elif invest_type == 3:  # 挖矿
                risk_analysis["risk_factors"].extend(
                    [
                        "挖矿收益可能随时间降低",
                        "代币价格波动可能影响总收益",
                        "智能合约风险",
                    ]
                )
                risk_analysis["recommendations"].extend(
                    [
                        "定期评估挖矿收益与风险",
                        "关注代币价格趋势",
                        "设置自动复投或提取策略",
                    ]
                )
                risk_analysis["monitoring_points"].extend(
                    ["挖矿APY变化", "奖励代币价格", "协议TVL变化"]
                )

            elif invest_type == 4:  # 机枪池
                risk_analysis["risk_factors"].extend(
                    [
                        "机枪池涉及复杂的自动化策略，风险较高",
                        "可能涉及杠杆操作",
                        "依赖第三方协议，存在协议组合风险",
                        "智能合约风险更为复杂",
                    ]
                )
                risk_analysis["recommendations"].extend(
                    [
                        "限制在机枪池中的资金比例",
                        "选择经过多次审计的机枪池",
                        "关注机枪池策略的变更",
                    ]
                )
                risk_analysis["monitoring_points"].extend(
                    ["机枪池策略变更", "底层协议安全状态", "收益率变化趋势"]
                )

            elif invest_type == 5:  # 质押
                risk_analysis["risk_factors"].extend(
                    [
                        "质押锁定期可能影响流动性",
                        "质押奖励可能随时间变化",
                        "解质押可能需要等待期",
                    ]
                )
                risk_analysis["recommendations"].extend(
                    [
                        "评估质押锁定期与预期投资周期",
                        "关注质押奖励变化",
                        "分散质押到不同协议",
                    ]
                )
                risk_analysis["monitoring_points"].extend(
                    ["质押APY变化", "解质押条件变更", "协议治理变化"]
                )

            elif invest_type == 6:  # 借贷
                risk_analysis["risk_factors"].extend(
                    ["利率波动风险", "清算风险", "抵押品价值波动风险"]
                )
                risk_analysis["recommendations"].extend(
                    ["保持健康的抵押率", "设置清算预警", "关注借贷市场利率变化"]
                )
                risk_analysis["monitoring_points"].extend(
                    ["借贷利率变化", "抵押率变化", "清算阈值距离"]
                )

            # 使用AI预测器进行更深入的分析
            try:
                # 调用AI预测器的投资类型风险分析方法
                ai_analysis = self.ai_predictor.analyze_investment_type_risk(
                    protocol=position.protocol,
                    asset=position.asset,
                    invest_type=invest_type,
                    amount=position.amount,
                    invest_type_name=invest_type_name,
                )

                if ai_analysis:
                    # 整合AI分析结果
                    if "risk_score" in ai_analysis:
                        # 将AI风险评分(0-100)转换为0-1范围
                        ai_risk_score = ai_analysis["risk_score"] / 100
                        # 综合基础风险和AI风险评分
                        risk_analysis["risk_score"] = (base_risk + ai_risk_score) / 2
                    else:
                        risk_analysis["risk_score"] = base_risk

                    if "risk_factors" in ai_analysis:
                        risk_analysis["risk_factors"].extend(
                            ai_analysis["risk_factors"]
                        )

                    if "recommendations" in ai_analysis:
                        risk_analysis["recommendations"].extend(
                            ai_analysis["recommendations"]
                        )

                    if "monitoring_points" in ai_analysis:
                        risk_analysis["monitoring_points"].extend(
                            ai_analysis["monitoring_points"]
                        )

                    if "risk_level" in ai_analysis:
                        risk_analysis["risk_level"] = ai_analysis["risk_level"]
                else:
                    # 如果AI分析失败，使用基础风险评分
                    risk_analysis["risk_score"] = base_risk
            except Exception as e:
                logger.error(f"使用AI分析投资类型风险时出错: {e}")
                # 出错时使用基础风险评分
                risk_analysis["risk_score"] = base_risk

            # 去重
            risk_analysis["risk_factors"] = list(set(risk_analysis["risk_factors"]))
            risk_analysis["recommendations"] = list(
                set(risk_analysis["recommendations"])
            )
            risk_analysis["monitoring_points"] = list(
                set(risk_analysis["monitoring_points"])
            )

            return risk_analysis

        except Exception as e:
            logger.error(f"分析投资类型风险时出错: {e}")
            return {
                "invest_type": (
                    position.invest_type if position.invest_type is not None else 1
                ),
                "invest_type_name": (
                    self.invest_type_map.get(position.invest_type, "未知类型")
                    if position.invest_type is not None
                    else "存币"
                ),
                "base_risk_score": 0.5,  # 默认中等风险
                "risk_score": 0.5,
                "risk_factors": ["风险分析过程中出错"],
                "recommendations": ["建议手动评估风险"],
                "monitoring_points": ["系统错误修复状态"],
            }

    def assess_portfolio_risk(
        self,
        positions: List[Position],
    ) -> RiskAssessment:
        """评估整个投资组合的风险，包含多个维度的风险分析"""
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(positions)

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
            risk_scores = {}  # 原始风险评分（0-1范围）
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

                    # 分析投资类型风险
                    investment_risk = self.analyze_investment_type_risk(pos)
                    investment_type_analysis[f"{pos.protocol}_{pos.asset}"] = (
                        investment_risk
                    )

                    # 添加投资类型风险因素
                    risk_factors["investment_type_risk"]["factors"].extend(
                        investment_risk["risk_factors"]
                    )

                    # 添加投资类型相关建议
                    recommendations.extend(investment_risk["recommendations"])

                    # 添加投资类型相关监控点
                    monitoring_points.extend(investment_risk["monitoring_points"])

                    # 添加高风险警告
                    if investment_risk.get("risk_score", 0) > 0.7:
                        warnings.append(
                            f"{pos.protocol}的{investment_risk['invest_type_name']}投资风险较高"
                        )

                except Exception as e:
                    logger.warning(f"获取{pos.protocol}的分析时出错: {e}")

            # 1. 计算市场风险
            position_market_risks = []
            for pos in positions:
                try:
                    # 使用新方法获取历史数据
                    historical_data = self._get_asset_historical_data(pos.asset)

                    # 计算市场风险
                    risk = self.calculate_market_volatility_risk(pos, historical_data)
                    position_market_risks.append((pos, risk))
                except Exception as e:
                    logger.error(f"计算{pos.asset}市场风险时出错: {e}")
                    # 使用默认风险值
                    position_market_risks.append((pos, 0.5))

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

            weighted_protocol_risk = 0
            for protocol, risk in protocol_risks.items():
                # 查找属于该协议的所有头寸
                protocol_positions = [p for p in positions if p.protocol == protocol]
                # 计算该协议的加权风险
                protocol_value = sum(p.amount for p in protocol_positions)
                if protocol_value > 0:
                    weighted_protocol_risk += risk * protocol_value / total_value

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

            # 从历史数据中分析趋势
            trend_analysis = {
                "short_term": "无数据",
                "medium_term": "无数据",
                "key_indicators": {
                    "macd_signal": "无数据",
                    "rsi_signal": "无数据",
                    "volume_analysis": "无数据",
                },
            }

            # 计算投资类型风险
            investment_type_risks = []
            for pos in positions:
                key = f"{pos.protocol}_{pos.asset}"
                if key in investment_type_analysis:
                    risk_score = investment_type_analysis[key].get("risk_score", 0.5)
                    investment_type_risks.append((pos, risk_score))
                else:
                    # 使用默认风险值
                    default_risk = (
                        self.invest_type_risk_weights.get(pos.invest_type, 0.3)
                        if pos.invest_type
                        else 0.3
                    )
                    investment_type_risks.append((pos, default_risk))

            # 计算加权投资类型风险
            weighted_investment_type_risk = sum(
                risk * pos.amount / total_value for pos, risk in investment_type_risks
            )

            # 更新投资类型风险因素
            risk_factors["investment_type_risk"]["score"] = int(
                weighted_investment_type_risk * 100
            )

            # 添加投资类型分布分析
            invest_type_distribution = {}
            for pos in positions:
                invest_type = pos.invest_type if pos.invest_type is not None else 1
                invest_type_name = self.invest_type_map.get(invest_type, "未知类型")
                if invest_type_name in invest_type_distribution:
                    invest_type_distribution[invest_type_name] += pos.amount
                else:
                    invest_type_distribution[invest_type_name] = pos.amount

            # 计算投资类型集中度
            for invest_type, amount in invest_type_distribution.items():
                percentage = amount / total_value * 100
                risk_factors["investment_type_risk"]["factors"].append(
                    f"{invest_type}占比{percentage:.1f}%"
                )

                # 添加高集中度警告
                if percentage > 60:
                    warnings.append(
                        f"{invest_type}投资占比过高({percentage:.1f}%)，建议分散投资类型"
                    )
                    recommendations.append(f"减少{invest_type}投资比例，分散到其他类型")

            # 计算综合风险分数（整合AI分析和投资类型风险）
            # 更新风险权重，加入投资类型风险
            updated_risk_weights = self.risk_weights.copy()
            # 调整权重以包含投资类型风险
            for risk_type in updated_risk_weights:
                updated_risk_weights[risk_type] *= 0.9  # 减少原有权重
            investment_type_risk_weight = 0.1  # 投资类型风险权重

            # 计算综合风险分数
            total_risk_score = (
                sum(
                    score * updated_risk_weights[risk_type]
                    for risk_type, score in risk_scores.items()
                )
                + weighted_investment_type_risk * investment_type_risk_weight
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

    async def _get_asset_historical_data(self, asset: str) -> Optional[pd.DataFrame]:
        """异步获取资产历史数据"""
        try:
            if not self.blockchain_service:
                logger.warning(f"blockchain_service未初始化，无法获取{asset}的历史数据")
                return None

            historical_data = await self.blockchain_service.get_asset_historical_data(
                asset
            )

            if historical_data is not None and not historical_data.empty:
                logger.info(
                    f"成功获取{asset}的历史数据，共{len(historical_data)}条记录"
                )
            else:
                logger.warning(f"未能获取{asset}的历史数据")

            return historical_data
        except Exception as e:
            logger.error(f"获取{asset}历史数据时出错: {e}")
            return None
