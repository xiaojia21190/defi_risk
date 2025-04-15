from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
from app.models.domain.risk import (
    RiskFactor,
    RiskAnalysisResult,
)


class RiskAnalyzerBase(ABC):
    """风险分析器基类"""

    def __init__(
        self,
        ai_service=None,
        ai_predictor=None,
        blockchain_service=None,
        risk_engine=None,
    ):
        """
        初始化风险分析器

        Args:
            ai_service: AI服务实例
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
            risk_engine: 风险引擎实例，用于委托复杂计算和跨域风险分析
        """
        self.ai_service = ai_service
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service
        self.risk_engine = risk_engine
        self.logger = logging.getLogger(f"defi_risk.{self.__class__.__name__}")
        self.name = self.__class__.__name__

        # 风险类型映射表，用于在调用推荐服务等场景下转换风险类型
        self.risk_type_map = {
            "MARKET": "市场风险",
            "PROTOCOL": "协议风险",
            "LIQUIDITY": "流动性风险",
            "CORRELATION": "相关性风险",
            "SMART_CONTRACT": "智能合约风险",
        }

    def calculate_weighted_score(self, risk_factors: List[RiskFactor]) -> float:
        """
        计算风险因子的加权平均分数

        Args:
            risk_factors: 风险因子列表

        Returns:
            加权平均分数
        """
        if not risk_factors:
            return 50  # 默认中等风险

        total_weight = sum(factor.weight for factor in risk_factors)
        if total_weight > 0:
            weighted_score = (
                sum(factor.score * factor.weight for factor in risk_factors)
                / total_weight
            )
        else:
            weighted_score = 50  # 默认中等风险

        # 确保评分在0-100范围内
        return max(0, min(100, weighted_score))

    def create_default_risk_result(
        self, risk_type: str, target: str, error_message: str = None
    ) -> RiskAnalysisResult:
        """
        创建默认的风险分析结果

        Args:
            risk_type: 风险类型
            target: 目标对象
            error_message: 错误信息

        Returns:
            默认风险分析结果
        """
        recommendations = []
        monitoring_points = []

        if error_message:
            recommendations = [
                f"无法完成{risk_type}风险分析：{error_message}",
                "请检查输入数据是否正确",
                "确保区块链服务正常运行",
                "尝试稍后再次分析",
            ]
            monitoring_points = [
                "监控系统日志以排查风险分析失败的原因",
            ]

        return RiskAnalysisResult(
            risk_type=risk_type,
            target=target,
            score=50,  # 默认中等风险
            factors=[],
            recommendations=recommendations,
            monitoring_points=monitoring_points,
        )

    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行风险分析

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        pass

    @abstractmethod
    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取风险因子

        Args:
            data: 分析数据

        Returns:
            风险因子列表
        """
        pass

    @abstractmethod
    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        pass

    @abstractmethod
    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        pass

    def create_risk_factor(
        self,
        risk_type: str,
        factor_name: str,
        score: float,
        weight: float,
        description: str,
        trend: str,
        data_points: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None,
    ) -> RiskFactor:
        """
        创建风险因子

        Args:
            risk_type: 风险类型
            factor_name: 因子名称
            score: 评分(0-100)
            weight: 权重
            description: 描述
            trend: 趋势
            data_points: 数据点
            metadata: 元数据

        Returns:
            风险因子
        """
        if data_points is None:
            data_points = []

        if metadata is None:
            metadata = {}

        return RiskFactor(
            id=f"{risk_type}.{factor_name}",
            name=factor_name,
            score=score,
            weight=weight,
            description=description,
            trend=trend,
            data_points=data_points,
            metadata=metadata,
        )

    def is_excluded_token(self, token_symbol: str) -> bool:
        """
        检查代币是否应该被排除在风险计算之外

        Args:
            token_symbol: 代币符号

        Returns:
            如果代币应该被排除则返回True，否则返回False
        """
        if not token_symbol:
            return True

        # 将代币符号转换为小写进行检查
        token_symbol_lower = token_symbol.lower()

        # 特殊处理：Pendle V2 的 PT 和 YT 代币不应被排除
        if token_symbol.startswith("PT-") or token_symbol.startswith("YT-"):
            self.logger.info(f"不排除 Pendle V2 代币 {token_symbol}")
            return False

        # 检查是否为其他应被排除的代币类型
        # 注意：这里不再使用简单的字符串包含检查，而是更精确的模式匹配
        excluded_patterns = [
            # 添加需要排除的特定代币模式
            # 例如可以添加一些测试代币、包装代币等
        ]

        for pattern in excluded_patterns:
            if pattern in token_symbol_lower:
                self.logger.info(
                    f"排除代币 {token_symbol}，因为它匹配排除模式: {pattern}"
                )
                return True

        return False

    def filter_token_list(
        self, token_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        过滤代币列表，排除不应参与风险计算的代币

        Args:
            token_list: 代币列表

        Returns:
            过滤后的代币列表
        """
        if not token_list:
            return []

        filtered_tokens = []
        pendle_reward_tokens = []  # 专门用于存储 Pendle 的奖励代币
        valuable_reward_tokens = []  # 存储所有有价值的奖励代币

        for token in token_list:
            token_symbol = token.get("tokenSymbol", "")
            is_reward = token.get("tokenType") == "reward"

            # 检查代币是否有价值（currencyAmount > 0）
            has_value = False
            if token.get("currencyAmount"):
                try:
                    currency_amount = float(token.get("currencyAmount", "0"))
                    has_value = currency_amount > 0
                except (ValueError, TypeError):
                    has_value = False

            # Pendle V2 的 PT 和 YT 代币特殊处理
            is_pendle_token = token_symbol.startswith("PT-") or token_symbol.startswith(
                "YT-"
            )

            # 如果是 Pendle 的奖励代币，单独收集
            if is_reward and is_pendle_token:
                pendle_reward_tokens.append(token)
                continue

            # 如果是有价值的奖励代币，也单独收集
            if is_reward and has_value:
                valuable_reward_tokens.append(token)
                self.logger.info(
                    f"收集到有价值的奖励代币 {token_symbol}，价值: {token.get('currencyAmount')}"
                )
                # 常规奖励代币还是被排除，但我们已经收集了它们
                continue
            # 常规奖励代币仍然被排除
            elif is_reward and not is_pendle_token:
                continue

            # 检查是否应排除该代币
            if self.is_excluded_token(token_symbol):
                continue

            filtered_tokens.append(token)

        # 检查是否有任何有价值的正常代币
        has_valuable_normal_tokens = any(
            float(token.get("currencyAmount", "0")) > 0
            for token in filtered_tokens
            if token.get("currencyAmount")
        )

        # 如果没有常规代币但有 Pendle 奖励代币，则将 Pendle 奖励代币添加到结果中
        if not filtered_tokens and pendle_reward_tokens:
            self.logger.info(
                f"没有常规代币但有 Pendle 奖励代币，将 {len(pendle_reward_tokens)} 个 Pendle 奖励代币添加到风险计算中"
            )
            filtered_tokens.extend(pendle_reward_tokens)

        # 如果没有有价值的常规代币但有其他有价值的奖励代币，则将这些奖励代币也添加到结果中
        if not has_valuable_normal_tokens and valuable_reward_tokens:
            self.logger.info(
                f"常规代币没有价值但有 {len(valuable_reward_tokens)} 个有价值的奖励代币，将它们添加到风险计算中"
            )
            filtered_tokens.extend(valuable_reward_tokens)

        return filtered_tokens

    def get_chinese_risk_type(self, risk_type: str) -> str:
        """
        将英文大写风险类型转换为中文风险类型

        Args:
            risk_type: 英文大写风险类型

        Returns:
            中文风险类型
        """
        return self.risk_type_map.get(risk_type, risk_type)

    def analyze_reward_tokens_impact(
        self,
        assets: Dict[str, float],
        reward_assets: Dict[str, float],
        total_value: float,
        risk_context: str = "风险",
    ) -> Dict[str, Any]:
        """
        分析奖励代币对风险的影响并记录日志

        Args:
            assets: 资产及其价值的字典
            reward_assets: 奖励代币及其价值的字典
            total_value: 投资组合总价值
            risk_context: 风险上下文描述（如"流动性风险"、"相关性风险"等）

        Returns:
            包含奖励代币影响分析结果的字典
        """
        if not reward_assets:
            return {
                "has_reward_tokens": False,
                "reward_percentage": 0,
                "reward_tokens_count": 0,
                "significant_impact": False,
                "impact_level": "无",
                "reward_included_in_assets": False,
            }

        # 筛选有价值的奖励代币
        valuable_rewards = {
            symbol: value for symbol, value in reward_assets.items() if value > 0
        }

        # 计算奖励代币在总价值中的占比
        reward_total = sum(valuable_rewards.values())
        reward_percentage = (reward_total / total_value * 100) if total_value > 0 else 0

        # 检查有价值的奖励代币是否已包含在资产列表中
        reward_included = bool(set(valuable_rewards.keys()) & set(assets.keys()))

        # 确定影响级别
        impact_level = "低"
        significant_impact = False

        if reward_percentage > 30:
            impact_level = "高"
            significant_impact = True
        elif reward_percentage > 10:
            impact_level = "中"
            significant_impact = True

        # 记录日志
        if valuable_rewards:
            if significant_impact:
                self.logger.warning(
                    f"奖励代币占总价值的{reward_percentage:.2f}%，对{risk_context}有{impact_level}影响"
                )
                for symbol, value in valuable_rewards.items():
                    percentage = (value / total_value * 100) if total_value > 0 else 0
                    self.logger.info(
                        f"奖励代币 {symbol} 价值: {value:.2f}，占比: {percentage:.2f}%"
                    )
            else:
                self.logger.info(
                    f"奖励代币占总价值的{reward_percentage:.2f}%，对{risk_context}影响较小"
                )

            if reward_included:
                self.logger.info("有价值的奖励代币已包含在风险计算中")
            else:
                self.logger.warning(
                    "有价值的奖励代币未包含在风险计算中，可能导致风险评估不完整"
                )

        return {
            "has_reward_tokens": bool(valuable_rewards),
            "reward_percentage": reward_percentage,
            "reward_tokens_count": len(valuable_rewards),
            "significant_impact": significant_impact,
            "impact_level": impact_level,
            "reward_included_in_assets": reward_included,
            "valuable_rewards": valuable_rewards,
        }
