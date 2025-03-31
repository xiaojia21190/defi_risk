"""
相关性风险分析模块 - 用于分析DeFi投资组合的资产相关性风险
"""

from typing import Dict, List, Any, Optional
import logging
import numpy as np
import pandas as pd
from app.models.domain.risk import RiskFactor, RiskType, RiskAnalysisResult
from app.risk_modules.base import RiskAnalyzerBase
from app.services.recommendation_service import RecommendationService


class CorrelationRiskAnalyzer(RiskAnalyzerBase):
    """相关性风险分析器"""

    def __init__(self, ai_service=None, ai_predictor=None, blockchain_service=None):
        """初始化相关性风险分析器"""
        super().__init__(ai_service, ai_predictor, blockchain_service)
        self.recommendation_service = RecommendationService()

        # 确保区块链服务可用
        self._ensure_blockchain_service_available("初始化")

    def _ensure_blockchain_service_available(self, context=""):
        """
        确保区块链服务可用，如果不可用则尝试初始化

        Args:
            context: 调用上下文，用于日志记录

        Returns:
            bool: 区块链服务是否可用
        """
        if not self.blockchain_service:
            try:
                # 尝试导入并初始化区块链服务
                from app.services.blockchain import BlockchainService

                self.blockchain_service = BlockchainService()
                self.logger.info(f"已自动初始化区块链服务 [{context}]")
                return True
            except Exception as e:
                self.logger.error(f"无法自动初始化区块链服务 [{context}]: {str(e)}")
                return False
        return True

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
            # 确保区块链服务可用，并检查其健康状态
            if self._ensure_blockchain_service_available("开始相关性风险分析"):
                # 检查区块链服务健康状态
                if hasattr(self.blockchain_service, "check_health") and callable(
                    getattr(self.blockchain_service, "check_health")
                ):
                    try:
                        health_status = await self.blockchain_service.check_health()
                        if not health_status.get("is_healthy", False):
                            self.logger.warning(
                                f"区块链服务健康检查失败: {health_status.get('message', '未知原因')}"
                            )
                            # 尝试重新初始化
                            self.blockchain_service = None
                            self._ensure_blockchain_service_available(
                                "重新初始化区块链服务"
                            )
                    except Exception as e:
                        self.logger.warning(f"区块链服务健康检查异常: {str(e)}")

            # 获取风险因子
            risk_factors = await self.get_risk_factors(data)

            # 如果没有收集到任何风险因素，返回默认风险分析结果
            if not risk_factors:
                self.logger.warning("未能收集到任何相关性风险因素")
                return self.create_default_risk_result(
                    RiskType.CORRELATION.value, "投资组合"
                )

            # 计算总体风险评分（加权平均）
            weighted_score = self.calculate_weighted_score(risk_factors)

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
            return self.create_default_risk_result(
                RiskType.CORRELATION.value, "投资组合", str(e)
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
            # 提取资产列表和权重
            assets = {}
            reward_assets = {}  # 单独跟踪奖励代币
            total_value = 0

            # 处理嵌套的positions结构
            for protocol_position in positions:
                # 安全获取内部positions，支持字典和对象类型
                inner_positions = self._safe_get_attr(
                    protocol_position, "positions", []
                )

                # 遍历每个协议中的具体资产positions
                for pos in inner_positions:
                    # 安全获取数值属性，支持字典和对象类型
                    position_amount = self._safe_get_attr(pos, "amount", 0)
                    total_value += float(position_amount) if position_amount else 0

                    # 优先从tokenList获取更精确的代币信息
                    token_list = self._safe_get_attr(pos, "tokenList", None)
                    if token_list:
                        # 计算非奖励代币且非排除代币的数量
                        regular_tokens = self.filter_token_list(token_list)
                        regular_token_count = len(regular_tokens) or 1  # 避免除以零

                        for token in token_list:
                            token_symbol = self._safe_get_attr(token, "tokenSymbol", "")
                            if not token_symbol:
                                continue

                            # 排除应该被排除的代币不参与相关性分析
                            if self.is_excluded_token(token_symbol):
                                self.logger.info(
                                    f"相关性分析中排除代币{token_symbol}，因为它是被排除的代币类型"
                                )
                                continue

                            # 使用代币实际金额(currencyAmount)而不是平均分配，如果可用
                            token_value = 0
                            currency_amount = self._safe_get_attr(
                                token, "currencyAmount", 0
                            )

                            if currency_amount and float(currency_amount) > 0:
                                try:
                                    token_value = float(currency_amount)
                                except (ValueError, TypeError):
                                    # 如果无法转换为float，使用估计值
                                    token_value = (
                                        float(position_amount) / regular_token_count
                                    )
                            else:
                                token_value = (
                                    float(position_amount) / regular_token_count
                                )

                            # 根据代币类型分别处理
                            token_type = self._safe_get_attr(token, "tokenType", "")
                            if token_type == "reward":
                                if token_symbol not in reward_assets:
                                    reward_assets[token_symbol] = 0
                                reward_assets[token_symbol] += token_value
                            else:
                                if token_symbol not in assets:
                                    assets[token_symbol] = 0
                                assets[token_symbol] += token_value
                    else:
                        # 如果没有tokenList，使用资产名称
                        asset_name = self._safe_get_attr(pos, "asset", "Unknown")
                        if isinstance(asset_name, str) and "/" in asset_name:
                            asset = asset_name.split("/")[0]  # 处理流动性池资产格式
                        else:
                            asset = str(asset_name)

                        # 排除应该被排除的资产
                        if self.is_excluded_token(asset):
                            self.logger.info(
                                f"相关性分析中排除资产{asset}，因为它是被排除的资产类型"
                            )
                            continue

                        if asset not in assets:
                            assets[asset] = 0
                        assets[asset] += (
                            float(position_amount) if position_amount else 0
                        )

            # 如果资产不足，无法进行相关性分析
            if len(assets) < 2:
                self.logger.warning("检测到的非奖励资产少于2个，无法进行相关性分析")
                return None

            # 尝试使用AI服务进行资产相关性分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "assets": list(assets.keys()),
                        "weights": {
                            asset: (value / total_value if total_value > 0 else 0)
                            for asset, value in assets.items()
                        },
                        "analysis_type": "asset_correlation",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="asset_correlation", data=ai_input_data
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
                            weight=0.4,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "assets": assets,
                                "reward_assets": reward_assets,
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析资产相关性风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 如果AI分析失败或不可用，使用区块链服务获取历史数据计算相关性
            # 确保区块链服务可用
            if not self._ensure_blockchain_service_available("资产相关性分析"):
                # 使用默认的估计值
                return self.create_risk_factor(
                    risk_type=RiskType.CORRELATION.value,
                    factor_name="资产相关性风险",
                    score=50,  # 默认中等风险
                    weight=0.4,
                    description="无法初始化区块链服务获取资产历史数据，使用默认的相关性风险评估",
                    trend="稳定",
                    data_points=[],
                    metadata={
                        "assets": assets,
                        "reward_assets": reward_assets,
                        "estimation_method": "default",
                    },
                )

            # 获取所有资产对的相关性数据
            asset_list = list(assets.keys())
            correlation_matrix = {}
            high_correlation_pairs = []
            num_stablecoin_pairs = 0

            for i in range(len(asset_list)):
                for j in range(i + 1, len(asset_list)):
                    asset1 = asset_list[i]
                    asset2 = asset_list[j]

                    # 如果两个资产都是稳定币，跳过计算（它们应该高度相关）
                    if self._is_stablecoin(asset1) and self._is_stablecoin(asset2):
                        # 将稳定币对的相关性设为1.0
                        correlation = 1.0
                        num_stablecoin_pairs += 1
                    else:
                        # 计算两个资产之间的相关性
                        correlation = await self._estimate_asset_correlation(
                            asset1, asset2
                        )

                    # 存储相关性数据
                    if asset1 not in correlation_matrix:
                        correlation_matrix[asset1] = {}
                    correlation_matrix[asset1][asset2] = correlation

                    # 记录高相关性对（绝对值超过0.7的相关性被视为高）
                    if abs(correlation) > 0.7:
                        high_correlation_pairs.append(
                            {
                                "asset1": asset1,
                                "asset2": asset2,
                                "correlation": correlation,
                            }
                        )

            # 计算高相关性对数量和总对数
            num_high_corr_pairs = len(high_correlation_pairs)
            total_pairs = (len(asset_list) * (len(asset_list) - 1)) / 2

            # 排除稳定币对之间的关系
            adjusted_total_pairs = (
                total_pairs - num_stablecoin_pairs
                if total_pairs > num_stablecoin_pairs
                else 1
            )

            # 计算高相关性对的百分比
            high_corr_percentage = (
                num_high_corr_pairs / adjusted_total_pairs
                if adjusted_total_pairs > 0
                else 0
            )

            # 创建数据点
            data_points = []
            for pair in high_correlation_pairs:
                data_points.append(
                    {
                        "asset_pair": f"{pair['asset1']}-{pair['asset2']}",
                        "correlation": round(pair["correlation"], 2),
                    }
                )

            # 根据高相关性对的百分比计算相关性风险评分
            if high_corr_percentage >= 0.75:
                correlation_score = 80  # 高风险
                description = f"投资组合中{num_high_corr_pairs}对资产({high_corr_percentage:.1%})高度相关，多样化效果差"
                trend = "上升"
            elif high_corr_percentage >= 0.5:
                correlation_score = 60  # 中高风险
                description = f"投资组合中{num_high_corr_pairs}对资产({high_corr_percentage:.1%})高度相关，多样化效果有限"
                trend = "稳定"
            elif high_corr_percentage >= 0.25:
                correlation_score = 40  # 中低风险
                description = f"投资组合中{num_high_corr_pairs}对资产({high_corr_percentage:.1%})高度相关，仍有多样化空间"
                trend = "稳定"
            else:
                correlation_score = 20  # 低风险
                description = f"投资组合中只有{num_high_corr_pairs}对资产({high_corr_percentage:.1%})高度相关，多样化效果好"
                trend = "下降"

            return self.create_risk_factor(
                risk_type=RiskType.CORRELATION.value,
                factor_name="资产相关性风险",
                score=correlation_score,
                weight=0.4,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "correlation_matrix": correlation_matrix,
                    "high_correlation_pairs": high_correlation_pairs,
                    "assets": assets,
                    "reward_assets": reward_assets,
                },
            )
        except Exception as e:
            self.logger.error(f"分析资产相关性风险时出错: {str(e)}")
            return None

    async def _estimate_asset_correlation(self, asset1: str, asset2: str) -> float:
        """估计两个资产之间的相关性，优先使用AI服务"""
        # 标准化资产名称
        asset1_upper = asset1.upper()
        asset2_upper = asset2.upper()

        # 尝试使用AI服务获取相关性
        if self.ai_service:
            try:
                # 准备AI分析的数据
                ai_input_data = {
                    "assets": [asset1_upper, asset2_upper],  # 修改为assets列表
                    "weights": {asset1_upper: 0.5, asset2_upper: 0.5},  # 添加权重信息
                    "analysis_type": "asset_pair_correlation",  # 分析子类型
                    "pair_analysis": True,  # 标识这是一个资产对分析
                }

                # 使用AI服务进行分析
                ai_result = await self.ai_service.analyze_with_predictor(
                    analysis_type="asset_correlation",  # 使用现有的分析类型
                    data=ai_input_data,
                )

                # 提取相关性结果
                if ai_result and "correlation_matrix" in ai_result:
                    # 从相关性矩阵中提取这两个资产的相关性
                    if (
                        isinstance(ai_result["correlation_matrix"], dict)
                        and asset1_upper in ai_result["correlation_matrix"]
                    ):
                        correlation = (
                            ai_result["correlation_matrix"]
                            .get(asset1_upper, {})
                            .get(asset2_upper)
                        )
                        if correlation is not None:
                            self.logger.info(
                                f"使用AI估计资产 {asset1} 和 {asset2} 的相关性: {correlation:.2f}"
                            )
                            return float(correlation)

                    # 如果没有找到特定的相关性数据，但有平均相关性
                    if "avg_correlation" in ai_result:
                        correlation = float(ai_result["avg_correlation"])
                        self.logger.info(
                            f"使用AI估计资产 {asset1} 和 {asset2} 的平均相关性: {correlation:.2f}"
                        )
                        return correlation

                # 如果在correlation_matrix中找不到，尝试在其他可能的字段中查找
                if ai_result and "correlation" in ai_result:
                    correlation = float(ai_result["correlation"])
                    self.logger.info(
                        f"使用AI估计资产 {asset1} 和 {asset2} 的相关性: {correlation:.2f}"
                    )
                    return correlation

                self.logger.warning(f"AI返回的结果中没有找到相关性数据: {ai_result}")
            except Exception as e:
                self.logger.warning(
                    f"使用AI估计资产相关性时出错: {str(e)}，将使用后备方法"
                )

        # 如果AI调用失败或未配置AI服务，确保区块链服务可用再继续
        self._ensure_blockchain_service_available(
            f"估计资产 {asset1} 和 {asset2} 的相关性"
        )

        # 使用后备方法
        # 检查是否为稳定币
        if self._is_stablecoin(asset1_upper) and self._is_stablecoin(asset2_upper):
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

        # 查找相关性
        key = (
            (asset1_upper, asset2_upper)
            if asset1_upper < asset2_upper
            else (asset2_upper, asset1_upper)
        )
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
        try:
            # 确保区块链服务可用
            self._ensure_blockchain_service_available("协议相关性分析")

            # 处理嵌套的positions结构
            protocols = {}
            total_value = 0

            # 遍历协议positions
            for protocol_position in positions:
                protocol = self._safe_get_attr(protocol_position, "protocol", "Unknown")
                inner_positions = self._safe_get_attr(
                    protocol_position, "positions", []
                )

                if protocol not in protocols:
                    protocols[protocol] = 0

                # 累加该协议下所有position的金额
                for pos in inner_positions:
                    amount = self._safe_get_attr(pos, "amount", 0)
                    try:
                        amount = float(amount)
                    except (ValueError, TypeError):
                        amount = 0
                    protocols[protocol] += amount
                    total_value += amount

            # 如果协议数量少于2，无法计算相关性
            if len(protocols) < 2:
                self.logger.warning("检测到的协议少于2个，无法进行协议相关性分析")
                return None

            # 计算协议集中度
            if total_value == 0:
                self.logger.warning("投资组合总价值为0，无法分析协议相关性风险")
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
        except Exception as e:
            self.logger.error(f"分析协议相关性风险时出错: {str(e)}")
            return None

    async def _analyze_investment_type_correlation(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析投资类型相关性风险"""
        try:
            # 确保区块链服务可用
            self._ensure_blockchain_service_available("投资类型相关性分析")

            # 处理嵌套的positions结构
            investment_types = {}
            total_value = 0

            # 遍历协议positions
            for protocol_position in positions:
                inner_positions = self._safe_get_attr(
                    protocol_position, "positions", []
                )

                # 遍历每个协议中的具体资产positions
                for pos in inner_positions:
                    invest_type = self._safe_get_attr(pos, "invest_type", 0)
                    invest_type_name = self._safe_get_attr(
                        pos, "invest_type_name", "未知类型"
                    )
                    amount = self._safe_get_attr(pos, "amount", 0)
                    try:
                        amount = float(amount)
                    except (ValueError, TypeError):
                        amount = 0
                    total_value += amount

                    if invest_type not in investment_types:
                        investment_types[invest_type] = {
                            "name": invest_type_name,
                            "amount": 0,
                        }
                    investment_types[invest_type]["amount"] += amount

            # 如果投资类型数量少于2，无法计算相关性
            if len(investment_types) < 2:
                self.logger.warning(
                    "检测到的投资类型少于2种，无法进行投资类型相关性分析"
                )
                return None

            # 计算投资类型集中度
            if total_value == 0:
                self.logger.warning("投资组合总价值为0，无法分析投资类型相关性风险")
                return None

            # 尝试使用AI服务进行投资类型相关性分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "investment_types": {
                            str(k): {
                                "name": v["name"],
                                "weight": v["amount"] / total_value,
                            }
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
                        description = ai_analysis.get(
                            "description", "投资类型相关性分析"
                        )
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
                (data["amount"] / total_value) ** 2
                for data in investment_types.values()
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
        except Exception as e:
            self.logger.error(f"分析投资类型相关性风险时出错: {str(e)}")
            return None

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取相关性风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        # 确保区块链服务可用
        self._ensure_blockchain_service_available("获取相关性风险建议")

        # 使用推荐服务生成建议
        return self.recommendation_service.get_correlation_risk_recommendations(
            risk_factors
        )

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取相关性风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        # 确保区块链服务可用
        self._ensure_blockchain_service_available("获取相关性风险监控点")

        # 使用推荐服务生成监控点
        return self.recommendation_service.get_monitoring_points(
            "CORRELATION", risk_factors
        )

    def _safe_get_attr(self, obj, attr_name, default=None):
        """
        安全获取对象属性或字典值

        Args:
            obj: 对象或字典
            attr_name: 属性或键名
            default: 默认值

        Returns:
            属性值或默认值
        """
        if obj is None:
            return default

        # 如果是字典类型
        if isinstance(obj, dict):
            return obj.get(attr_name, default)

        # 如果是对象类型
        try:
            return getattr(obj, attr_name, default)
        except (AttributeError, TypeError):
            return default

    def filter_token_list(self, token_list):
        """
        过滤代币列表，排除奖励代币和应该被排除的代币

        Args:
            token_list: 代币列表

        Returns:
            过滤后的代币列表
        """
        if not token_list:
            return []

        filtered_tokens = []
        for token in token_list:
            token_symbol = self._safe_get_attr(token, "tokenSymbol", "")
            token_type = self._safe_get_attr(token, "tokenType", "")

            # 排除奖励代币和应该被排除的代币
            if (
                not token_symbol
                or token_type == "reward"
                or self.is_excluded_token(token_symbol)
            ):
                continue

            filtered_tokens.append(token)

        return filtered_tokens

    def is_excluded_token(self, token_symbol):
        """
        检查代币是否应该被排除在相关性分析之外

        Args:
            token_symbol: 代币符号

        Returns:
            bool: 是否应该被排除
        """
        excluded_tokens = [
            # 稳定币通常不参与相关性分析，因为它们的价格波动很小
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
            # 包装代币通常与其底层资产高度相关
            "WETH",
            "WBTC",
            "WBNB",
            "WAVAX",
            # 流动性代币或治理代币，通常不参与相关性分析
            "LP",
            "FARM",
            "XVS",
            "CAKE",
        ]

        if not token_symbol:
            return True

        token_upper = token_symbol.upper()

        # 检查精确匹配
        if token_upper in excluded_tokens:
            return True

        # 检查部分匹配（如USDT-3CRV这样的代币名称）
        for excluded in excluded_tokens:
            if excluded in token_upper:
                return True

        return False
