from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
from app.models.domain.risk import (
    RiskFactor,
    RiskAnalysisResult,
)


class RiskAnalyzerBase(ABC):
    """风险分析器基类"""

    def __init__(self, ai_service=None, ai_predictor=None, blockchain_service=None):
        """
        初始化风险分析器

        Args:
            ai_service: AI服务实例
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.ai_service = ai_service
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service
        self.logger = logging.getLogger(f"defi_risk.{self.__class__.__name__}")
        self.name = self.__class__.__name__

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

        # 检查是否为yt代币或pt代币
        if "yt" in token_symbol_lower or "pt" in token_symbol_lower:
            self.logger.info(f"排除代币{token_symbol}，因为它是yt或pt代币")
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
        for token in token_list:
            # 忽略奖励代币
            if token.get("tokenType") == "reward":
                continue

            token_symbol = token.get("tokenSymbol", "")

            # 检查是否应排除该代币
            if self.is_excluded_token(token_symbol):
                continue

            filtered_tokens.append(token)

        return filtered_tokens
