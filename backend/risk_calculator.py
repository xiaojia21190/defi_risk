from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import pandas as pd
from datetime import datetime
import json
import hashlib
import asyncio
from cachetools import TTLCache, LRUCache

# 导入风险模块
from risk_modules.market_risk import MarketRiskAnalyzer
from risk_modules.investment_type_risk import InvestmentTypeRiskAnalyzer
from risk_modules.liquidity_pool_risk import LiquidityPoolRiskAnalyzer
from risk_modules.mining_risk import MiningRiskAnalyzer
from risk_modules.save_risk import SaveRiskAnalyzer
from risk_modules.vault_risk import VaultRiskAnalyzer
from risk_modules.staking_risk import StakingRiskAnalyzer
from risk_modules.lending_risk import LendingRiskAnalyzer
from risk_modules.portfolio_risk import (
    PortfolioRiskAnalyzer,
    Position,
    RiskAssessment,
    RiskLevel,
    RiskType,
)

from ai_predictor import AiPredictor

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


@dataclass
class LiquidityMetrics:
    depth_score: float  # 0-1
    volume_24h: float
    slippage_impact: float
    withdrawal_limits: Optional[Dict[str, float]]


class RiskCalculator:
    def __init__(self, blockchain_service=None):
        # 风险阈值配置
        self.high_volatility_threshold = 0.5  # 50% 的价格波动作为高波动性阈值

        # 风险等级定义
        self.RISK_LEVELS = {"LOW": "低风险", "MEDIUM": "中等风险", "HIGH": "高风险"}

        # 初始化AI预测器
        self.ai_predictor = AiPredictor()

        # 初始化风险分析器
        self.market_risk_analyzer = MarketRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )
        self.investment_type_risk_analyzer = InvestmentTypeRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )
        self.liquidity_pool_risk_analyzer = LiquidityPoolRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )
        self.mining_risk_analyzer = MiningRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )
        self.save_risk_analyzer = SaveRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )
        self.vault_risk_analyzer = VaultRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )
        self.staking_risk_analyzer = StakingRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )
        self.lending_risk_analyzer = LendingRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )
        self.portfolio_risk_analyzer = PortfolioRiskAnalyzer(
            self.ai_predictor, blockchain_service
        )

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

        使用市场风险分析器计算
        """
        return self.market_risk_analyzer.calculate_market_volatility_risk(
            position, historical_data
        )

    def analyze_market_trend(
        self, asset: str, historical_data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        分析市场趋势

        使用市场风险分析器分析
        """
        return self.market_risk_analyzer.analyze_market_trend(asset, historical_data)

    def analyze_correlation_risk(self, assets: List[str]) -> Dict:
        """
        分析资产相关性风险

        使用市场风险分析器分析
        """
        return self.market_risk_analyzer.analyze_correlation_risk(assets)

    def analyze_investment_type_risk(
        self, protocol: str, asset: str, invest_type: int, amount: float
    ) -> Dict:
        """
        分析投资类型风险

        使用投资类型风险分析器分析
        """
        return self.investment_type_risk_analyzer.analyze_investment_type_risk(
            protocol, asset, invest_type, amount
        )

    def monitor_liquidity_pool_risk(self, pool_data: Dict) -> Dict:
        """
        监测流动性池风险

        使用流动性池风险分析器监测
        """
        return self.liquidity_pool_risk_analyzer.monitor_liquidity_pool_risk(pool_data)

    def monitor_mining_risk(self, mining_data: Dict) -> Dict:
        """
        监测挖矿风险

        使用挖矿风险分析器监测
        """
        return self.mining_risk_analyzer.monitor_mining_risk(mining_data)

    def monitor_save_risk(self, save_data: Dict) -> Dict:
        """
        监测存币风险

        使用存币风险分析器监测
        """
        return self.save_risk_analyzer.monitor_save_risk(save_data)

    def monitor_vault_risk(self, vault_data: Dict) -> Dict:
        """
        监测机枪池风险

        使用机枪池风险分析器监测
        """
        return self.vault_risk_analyzer.monitor_vault_risk(vault_data)

    def monitor_staking_risk(self, staking_data: Dict) -> Dict:
        """
        监测质押风险

        使用质押风险分析器监测
        """
        return self.staking_risk_analyzer.monitor_staking_risk(staking_data)

    def monitor_lending_risk(self, lending_data: Dict) -> Dict:
        """
        监测借贷风险

        使用借贷风险分析器监测
        """
        return self.lending_risk_analyzer.monitor_lending_risk(lending_data)

    def assess_portfolio_risk(
        self,
        positions: List[Position],
    ) -> RiskAssessment:
        """
        评估整个投资组合的风险，包含多个维度的风险分析

        使用投资组合风险分析器评估
        """
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

            # 使用投资组合风险分析器评估风险
            risk_assessment = self.portfolio_risk_analyzer.assess_portfolio_risk(
                positions
            )

            # 缓存结果
            self.portfolio_cache[cache_key] = risk_assessment

            return risk_assessment

        except Exception as e:
            logger.error(f"评估投资组合风险时出错: {e}")
            # 返回默认风险评估
            return self.portfolio_risk_analyzer.get_default_risk_assessment(str(e))

    def generate_ai_portfolio_recommendations(
        self, all_investments: List[Dict]
    ) -> Dict:
        """生成AI驱动的投资组合优化建议"""

        # 分析当前投资组合风险
        portfolio_risks = {}
        positions = []

        # 将投资转换为Position对象
        for investment in all_investments:
            invest_type = investment.get("investType")
            protocol = self._extract_protocol_name(investment)

            # 提取资产信息
            asset = ""
            amount = 0
            if (
                "assetsTokenList" in investment
                and len(investment["assetsTokenList"]) > 0
            ):
                asset = investment["assetsTokenList"][0].get("tokenSymbol", "")
                amount = float(investment["assetsTokenList"][0].get("tokenAmount", 0))
            else:
                asset = investment.get("asset", "")
                amount = float(investment.get("amount", 0))

            if not asset or amount <= 0:
                continue

            # 创建Position对象
            position = Position(
                protocol=protocol,
                asset=asset,
                amount=amount,
                invest_type=invest_type,
            )
            positions.append(position)

            # 根据投资类型获取风险分析
            if invest_type == 1:  # 存币
                risk_analysis = self.monitor_save_risk(investment)
            elif invest_type == 2:  # 流动性池
                risk_analysis = self.monitor_liquidity_pool_risk(investment)
            elif invest_type == 3:  # 挖矿
                risk_analysis = self.monitor_mining_risk(investment)
            elif invest_type == 4:  # 机枪池
                risk_analysis = self.monitor_vault_risk(investment)
            elif invest_type == 5:  # 质押
                risk_analysis = self.monitor_staking_risk(investment)
            elif invest_type == 6:  # 借贷
                risk_analysis = self.monitor_lending_risk(investment)
            else:
                # 默认使用投资类型风险分析
                risk_analysis = self.analyze_investment_type_risk(
                    protocol, asset, invest_type or 0, amount
                )

            # 存储风险分析结果
            investment_name = investment.get("investmentName", f"{protocol}-{asset}")
            portfolio_risks[investment_name] = risk_analysis

        # 如果没有有效投资，返回空结果
        if not positions:
            return {
                "portfolio_risk": {
                    "risk_score": 0,
                    "risk_level": "LOW",
                    "risk_factors": [],
                },
                "recommendations": ["开始投资以获取收益"],
                "rebalancing_suggestions": [],
                "risk_reduction_strategies": [],
            }

        # 评估整体投资组合风险
        portfolio_risk = self.assess_portfolio_risk(positions)

        # 分析资产相关性
        assets = [p.asset for p in positions]
        correlation_analysis = self.analyze_correlation_risk(assets)

        # 生成再平衡建议
        rebalancing_suggestions = self._generate_rebalancing_recommendations(
            portfolio_risks, correlation_analysis
        )

        # 生成风险降低策略
        risk_reduction_strategies = self._generate_risk_reduction_strategies(
            portfolio_risks
        )

        # 整合所有建议
        all_recommendations = []
        if hasattr(portfolio_risk, "recommendations"):
            all_recommendations.extend(portfolio_risk.recommendations)

        # 添加再平衡建议
        all_recommendations.extend(rebalancing_suggestions)

        # 添加风险降低策略
        all_recommendations.extend(risk_reduction_strategies[:3])  # 只取前三个策略

        # 去重
        all_recommendations = list(set(all_recommendations))

        return {
            "portfolio_risk": {
                "risk_score": portfolio_risk.risk_score,
                "risk_level": portfolio_risk.risk_level.value,
                "risk_factors": portfolio_risk.risk_factors,
            },
            "recommendations": all_recommendations,
            "rebalancing_suggestions": rebalancing_suggestions,
            "risk_reduction_strategies": risk_reduction_strategies,
        }

    def _generate_rebalancing_recommendations(
        self, portfolio_risks: Dict[str, Dict], correlation_matrix: Dict
    ) -> List[str]:
        """
        生成投资组合再平衡建议

        Args:
            portfolio_risks: 每个投资的风险分析结果
            correlation_matrix: 相关性矩阵分析结果

        Returns:
            List[str]: 再平衡建议列表
        """
        try:
            recommendations = []

            # 1. 风险评分基础建议
            high_risk_investments = []
            for investment_name, risk_analysis in portfolio_risks.items():
                risk_score = 0

                # 尝试从不同格式中提取风险评分
                if isinstance(risk_analysis, dict):
                    if "risk_score" in risk_analysis:
                        risk_score = risk_analysis["risk_score"]
                    elif (
                        "ai_risk_analysis" in risk_analysis
                        and "risk_score" in risk_analysis["ai_risk_analysis"]
                    ):
                        risk_score = risk_analysis["ai_risk_analysis"]["risk_score"]
                    elif "score" in risk_analysis:
                        # 将0-1范围转换为0-100
                        if 0 <= risk_score <= 1:
                            risk_score = risk_score * 100
                        else:
                            risk_score = risk_score

                if risk_score > 70:  # 高风险阈值
                    high_risk_investments.append(investment_name)

            if high_risk_investments:
                recommendations.append(
                    f"减少高风险投资: {', '.join(high_risk_investments)}"
                )

            # 2. 相关性基础建议
            high_correlation_pairs = self._identify_high_correlation_pairs(
                correlation_matrix
            )
            if high_correlation_pairs:
                for pair in high_correlation_pairs[:3]:  # 只取前三对
                    recommendations.append(
                        f"减少相关资产集中度: {pair['asset1']}和{pair['asset2']}的相关性为{pair['correlation']:.2f}"
                    )

            # 3. 多样化评分基础建议
            diversification_score = correlation_matrix.get("diversification_score", 0)
            if diversification_score < 50:
                recommendations.append("增加资产类型多样性以降低整体风险")

            # 4. 添加一般性建议
            if not recommendations:
                recommendations.extend(
                    [
                        "定期重新平衡投资组合以维持目标风险水平",
                        "考虑增加不同类型的DeFi投资以提高多样性",
                        "关注高收益投资的风险暴露",
                    ]
                )

            return recommendations
        except Exception as e:
            logger.error(f"生成再平衡建议时出错: {e}")
            return ["定期重新平衡投资组合以维持目标风险水平"]

    def _identify_high_correlation_pairs(self, correlation_matrix: Dict) -> List[Dict]:
        """识别高相关性资产对"""
        try:
            high_correlation_pairs = []

            if "matrix" not in correlation_matrix:
                return high_correlation_pairs

            matrix = correlation_matrix["matrix"]
            assets = correlation_matrix.get("assets", [])

            if not matrix or not assets:
                return high_correlation_pairs

            # 遍历相关性矩阵
            for i in range(len(assets)):
                for j in range(i + 1, len(assets)):
                    correlation = matrix[i][j]
                    if correlation > 0.7:  # 高相关性阈值
                        high_correlation_pairs.append(
                            {
                                "asset1": assets[i],
                                "asset2": assets[j],
                                "correlation": correlation,
                            }
                        )

            # 按相关性降序排序
            high_correlation_pairs.sort(key=lambda x: x["correlation"], reverse=True)

            return high_correlation_pairs
        except Exception as e:
            logger.error(f"识别高相关性资产对时出错: {e}")
            return []

    def _generate_risk_reduction_strategies(
        self, portfolio_risks: Dict[str, Dict]
    ) -> List[str]:
        """生成风险降低策略"""
        try:
            strategies = []
            all_risk_factors = []
            all_recommendations = []

            # 收集所有风险因素和建议
            for investment_name, risk_analysis in portfolio_risks.items():
                if isinstance(risk_analysis, dict):
                    if "risk_factors" in risk_analysis:
                        all_risk_factors.extend(risk_analysis["risk_factors"])
                    if "recommendations" in risk_analysis:
                        all_recommendations.extend(risk_analysis["recommendations"])
                    elif (
                        "ai_risk_analysis" in risk_analysis
                        and "recommendations" in risk_analysis["ai_risk_analysis"]
                    ):
                        all_recommendations.extend(
                            risk_analysis["ai_risk_analysis"]["recommendations"]
                        )

            # 去重
            unique_risk_factors = list(set(all_risk_factors))
            unique_recommendations = list(set(all_recommendations))

            # 生成风险降低策略
            if unique_risk_factors:
                for factor in unique_risk_factors[:5]:  # 只取前五个
                    strategies.append(f"解决风险因素: {factor}")

            if unique_recommendations:
                for recommendation in unique_recommendations[:5]:  # 只取前五个
                    strategies.append(f"遵循建议: {recommendation}")

            # 添加一般性策略
            if not strategies:
                strategies.extend(
                    [
                        "定期监控投资组合风险",
                        "设置止损策略以控制下行风险",
                        "在不同资产类型间分散投资",
                        "关注市场趋势并相应调整策略",
                    ]
                )

            return strategies
        except Exception as e:
            logger.error(f"生成风险降低策略时出错: {e}")
            return [
                "定期监控投资组合风险",
                "设置止损策略以控制下行风险",
            ]

    def monitor_save_risk_with_ai(self, save_data: Dict) -> Dict:
        """
        使用AI增强的存币风险监测

        使用存币风险分析器的AI增强监测
        """
        return self.save_risk_analyzer.monitor_save_risk_with_ai(save_data)

    def monitor_liquidity_pool_risk_with_ai(self, pool_data: Dict) -> Dict:
        """
        使用AI增强的流动性池风险监测

        使用流动性池风险分析器的AI增强监测
        """
        return self.liquidity_pool_risk_analyzer.monitor_liquidity_pool_risk_with_ai(
            pool_data
        )

    def monitor_mining_risk_with_ai(self, mining_data: Dict) -> Dict:
        """
        使用AI增强的挖矿风险监测

        使用挖矿风险分析器的AI增强监测
        """
        return self.mining_risk_analyzer.monitor_mining_risk_with_ai(mining_data)

    def monitor_vault_risk_with_ai(self, vault_data: Dict) -> Dict:
        """
        使用AI增强的机枪池风险监测

        使用机枪池风险分析器的AI增强监测
        """
        return self.vault_risk_analyzer.monitor_vault_risk_with_ai(vault_data)

    def _extract_protocol_name(self, investment_data: Dict) -> str:
        """
        从投资数据中提取协议名称

        Args:
            investment_data: 投资数据

        Returns:
            str: 协议名称
        """
        # 尝试从不同字段提取协议名称
        protocol = investment_data.get("protocol", "")
        if protocol:
            return protocol

        platform = investment_data.get("platform", "")
        if platform:
            return platform

        # 从投资名称中提取
        investment_name = investment_data.get("investmentName", "")
        if investment_name:
            # 简单处理：取第一个单词作为协议名
            return investment_name.split()[0]

        return "未知协议"
