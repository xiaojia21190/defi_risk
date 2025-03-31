"""
协议风险分析模块 - 用于分析DeFi协议相关的风险
"""

from typing import Dict, List, Any, Optional
import logging
from app.models.domain.risk import RiskFactor, RiskType, RiskAnalysisResult
from app.risk_modules.base import RiskAnalyzerBase
import time
import numpy as np
from datetime import datetime
from app.services.recommendation_service import RecommendationService
from app.core.utility import safe_get  # 导入safe_get函数
import copy


class ProtocolRiskAnalyzer(RiskAnalyzerBase):
    """协议风险分析器"""

    def __init__(
        self,
        ai_service=None,
        ai_predictor=None,
        blockchain_service=None,
        risk_engine=None,
    ):
        """初始化协议风险分析器"""
        super().__init__(ai_service, ai_predictor, blockchain_service)
        self.recommendation_service = RecommendationService()
        self.risk_engine = risk_engine

    async def analyze(self, protocol: str) -> RiskAnalysisResult:
        """分析协议风险"""
        self.logger.info(f"开始分析协议 {protocol} 的风险")

        try:
            # 确保区块链服务已初始化
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，使用有限的风险分析")

            # 收集所有风险因素
            risk_factors = []

            # 分析协议安全风险
            security_risk = await self._analyze_protocol_security(protocol)
            if security_risk:
                risk_factors.append(security_risk)

            # 分析协议治理风险
            governance_risk = await self._analyze_protocol_governance(protocol)
            if governance_risk:
                risk_factors.append(governance_risk)

            # 分析协议历史风险
            history_risk = await self._analyze_protocol_history(protocol)
            if history_risk:
                risk_factors.append(history_risk)

            # 分析协议复杂性风险
            complexity_risk = await self._analyze_protocol_complexity(protocol)
            if complexity_risk:
                risk_factors.append(complexity_risk)

            # 如果没有收集到任何风险因素，返回默认风险分析结果
            if not risk_factors:
                self.logger.warning(f"未能收集到协议 {protocol} 的任何风险因素")
                return self.create_default_risk_result(
                    RiskType.PROTOCOL.value, protocol
                )

            # 计算总体风险评分（加权平均）
            weighted_score = self.calculate_weighted_score(risk_factors)

            # 获取协议名称（如果可能）
            protocol_name = protocol
            if self.blockchain_service:
                try:
                    protocol_data = await self.blockchain_service.get_protocol(protocol)
                    if protocol_data and "name" in protocol_data:
                        protocol_name = protocol_data["name"]
                except Exception as e:
                    self.logger.error(f"获取协议名称时出错: {str(e)}")

            # 生成建议和监控点
            recommendations = await self.get_recommendations(risk_factors)
            monitoring_points = await self.get_monitoring_points(risk_factors)

            # 创建风险分析结果
            result = RiskAnalysisResult(
                risk_type=RiskType.PROTOCOL.value,
                target=protocol_name,
                score=weighted_score,
                factors=risk_factors,
                recommendations=recommendations,
                monitoring_points=monitoring_points,
            )

            self.logger.info(
                f"完成协议 {protocol} 的风险分析，总体风险评分: {weighted_score:.2f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"分析协议 {protocol} 风险时出错: {str(e)}")
            # 返回默认风险分析结果
            return RiskAnalysisResult(
                risk_type=RiskType.PROTOCOL.value,
                target=protocol,
                score=50,  # 默认中等风险
                factors=[
                    "无法完成风险分析，请检查输入的协议名称是否正确",
                    "确保区块链服务正常运行",
                    "尝试稍后再次分析",
                ],
                recommendations=[
                    "无法完成风险分析，请检查输入的协议名称是否正确",
                    "确保区块链服务正常运行",
                    "尝试稍后再次分析",
                ],
                monitoring_points=[
                    "监控系统日志以排查风险分析失败的原因",
                ],
            )

    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取协议风险因子

        Args:
            data: 分析数据

        Returns:
            风险因子列表
        """
        risk_factors = []
        positions = data.get("positions", [])

        # 如果没有头寸，返回空列表
        if not positions:
            return []

        # 按协议分组
        protocols = {}
        for pos in positions:
            protocol = safe_get(pos, "protocol", "unknown")
            if protocol not in protocols:
                protocols[protocol] = []
            protocols[protocol].append(pos)

        # 分析每个协议的风险
        for protocol, protocol_positions in protocols.items():
            # 分析协议安全风险
            security_risk = await self._analyze_protocol_security(protocol)
            if security_risk:
                risk_factors.append(security_risk)

            # 分析协议治理风险
            governance_risk = await self._analyze_protocol_governance(protocol)
            if governance_risk:
                risk_factors.append(governance_risk)

            # 分析协议历史风险
            history_risk = await self._analyze_protocol_history(protocol)
            if history_risk:
                risk_factors.append(history_risk)

            # 分析协议复杂性风险
            complexity_risk = await self._analyze_protocol_complexity(protocol)
            if complexity_risk:
                risk_factors.append(complexity_risk)

        return risk_factors

    async def _analyze_protocol_security(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议安全风险"""
        try:
            # 直接调用RiskEngine的安全风险分析方法
            # 注意：这要求ProtocolRiskAnalyzer实例化时能访问RiskEngine实例
            if hasattr(self, "risk_engine") and self.risk_engine:
                return await self.risk_engine._analyze_protocol_security(protocol)

            # 如果没有访问RiskEngine的权限，使用现有的分析逻辑
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取协议安全数据")
                return None

            # 使用区块链服务获取协议数据（从DefiLlama）
            protocol_data = await self.blockchain_service.get_protocol(protocol)

            if not protocol_data:
                self.logger.warning(f"获取协议 {protocol} 的数据失败")
                return None

            # 提取关键安全指标
            protocol_name = protocol_data.get("name", protocol)
            audit_count = int(protocol_data.get("audits", 0))
            audit_links = protocol_data.get("audit_links", [])
            is_open_source = protocol_data.get("openSource", False)
            github_repos = protocol_data.get("github", [])
            category = protocol_data.get("category", "未知")
            chains = protocol_data.get("chains", [])
            tvl = sum(protocol_data.get("currentChainTvls", {}).values())

            # 准备AI分析的数据
            ai_input_data = {
                "protocol_name": protocol_name,
                "audit_count": audit_count,
                "audit_links": audit_links,
                "is_open_source": is_open_source,
                "github_repos": github_repos,
                "category": category,
                "chains": chains,
                "tvl": tvl,
                "analysis_type": "security_risk",
            }

            # 使用AI服务进行分析
            if self.ai_service:
                try:
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="protocol_security", data=ai_input_data
                    )

                    # 提取AI分析结果
                    risk_score = ai_analysis.get("risk_score", 50)
                    risk_level = ai_analysis.get("risk_level", "中")
                    description = ai_analysis.get(
                        "description", f"对{protocol_name}协议的安全风险分析"
                    )
                    trend = ai_analysis.get("trend", "稳定")
                    data_points = ai_analysis.get("data_points", [])

                except Exception as e:
                    self.logger.error(f"使用AI分析协议安全风险时出错: {str(e)}")
                    # 如果AI分析失败，使用基于规则的分析
                    return await self._rule_based_security_analysis(protocol_data)
            else:
                # 如果没有AI服务，使用基于规则的分析
                return await self._rule_based_security_analysis(protocol_data)

            return self.create_risk_factor(
                risk_type=RiskType.PROTOCOL.value,
                factor_name="协议安全风险",
                score=risk_score,
                weight=0.4,  # 安全风险权重较高
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "protocol": protocol_name,
                    "protocol_data": protocol_data,
                    "ai_analysis": ai_analysis,
                },
            )
        except Exception as e:
            self.logger.error(f"分析协议 {protocol} 安全风险时出错: {str(e)}")
            return None

    async def _rule_based_security_analysis(
        self, protocol_data: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """基于规则的协议安全风险分析"""
        try:
            # 提取关键安全指标
            protocol_name = protocol_data.get("name", "未知协议")
            audit_count = int(protocol_data.get("audits", 0))
            audit_links = protocol_data.get("audit_links", [])
            is_open_source = protocol_data.get("openSource", False)
            github_repos = protocol_data.get("github", [])
            category = protocol_data.get("category", "未知")
            chains = protocol_data.get("chains", [])
            tvl = sum(protocol_data.get("currentChainTvls", {}).values())

            # 计算基础安全评分
            base_score = 50  # 默认中等风险

            # 审计因素 (每次审计-10分，最多-30分)
            audit_factor = min(30, audit_count * 10)

            # 开源因素 (-20分)
            open_source_factor = 20 if is_open_source else 0

            # GitHub活跃度 (-10分)
            github_factor = 10 if github_repos else 0

            # TVL因素 (TVL越高，风险越低，最多-20分)
            tvl_factor = 0
            if tvl > 1000000000:  # > 10亿
                tvl_factor = 20
            elif tvl > 100000000:  # > 1亿
                tvl_factor = 15
            elif tvl > 10000000:  # > 1000万
                tvl_factor = 10
            elif tvl > 1000000:  # > 100万
                tvl_factor = 5

            # 多链部署因素 (部署在多条链上可能增加风险面，每条链+2分，最多+10分)
            chain_factor = min(10, len(chains) * 2)

            # 计算最终风险评分 (0-100，越高风险越大)
            risk_score = (
                base_score
                - audit_factor
                - open_source_factor
                - github_factor
                - tvl_factor
                + chain_factor
            )
            risk_score = max(0, min(100, risk_score))  # 确保在0-100范围内

            # 确定风险等级
            if risk_score < 20:
                risk_level = "极低"
            elif risk_score < 40:
                risk_level = "低"
            elif risk_score < 60:
                risk_level = "中"
            elif risk_score < 80:
                risk_level = "高"
            else:
                risk_level = "极高"

            # 构建描述
            description = f"{protocol_name}协议的安全风险等级为{risk_level}，"

            if audit_count > 0:
                description += f"已通过{audit_count}次专业审计，"
            else:
                description += "未经专业审计或缺乏审计信息，"

            if is_open_source:
                description += "代码已开源。"
            else:
                description += "代码未开源。"

            # 添加TVL信息
            if tvl > 0:
                description += f" 当前锁仓量(TVL)为{tvl:.2f}美元，"
                if tvl > 100000000:
                    description += "锁仓量较大，表明市场对协议有较高信任度。"
                elif tvl > 10000000:
                    description += "锁仓量中等，市场信任度适中。"
                else:
                    description += "锁仓量较小，市场信任度有限。"

            # 确定趋势
            if risk_score > 70:
                trend = "上升"
            elif risk_score > 40:
                trend = "稳定"
            else:
                trend = "下降"

            # 构建数据点
            data_points = [
                {"name": "风险评分", "value": risk_score},
                {"name": "风险等级", "value": risk_level},
                {"name": "审计次数", "value": audit_count},
                {"name": "是否开源", "value": "是" if is_open_source else "否"},
                {"name": "TVL", "value": tvl},
                {"name": "链数量", "value": len(chains)},
            ]

            # 添加审计链接
            if audit_links:
                data_points.append({"name": "审计链接", "value": audit_links})

            # 添加GitHub仓库
            if github_repos:
                data_points.append({"name": "GitHub仓库", "value": github_repos})

            return self.create_risk_factor(
                risk_type=RiskType.PROTOCOL.value,
                factor_name="协议安全风险",
                score=risk_score,
                weight=0.4,  # 安全风险权重较高
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "protocol": protocol_name,
                    "protocol_data": protocol_data,
                },
            )
        except Exception as e:
            self.logger.error(f"基于规则分析协议安全风险时出错: {str(e)}")
            return None

    async def _analyze_protocol_governance(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议治理风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取协议治理数据")
                return None

            # 使用区块链服务获取协议数据（从DefiLlama）
            protocol_data = await self.blockchain_service.get_protocol(protocol)

            if not protocol_data:
                self.logger.warning(f"获取协议 {protocol} 的数据失败")
                return None

            # 提取关键治理指标
            protocol_name = protocol_data.get("name", protocol)
            category = protocol_data.get("category", "未知")
            twitter = protocol_data.get("twitter", "")
            github_repos = protocol_data.get("github", [])
            token_symbol = protocol_data.get("symbol", "")

            # 准备AI分析的数据
            ai_input_data = {
                "protocol_name": protocol_name,
                "category": category,
                "twitter": twitter,
                "github_repos": github_repos,
                "token_symbol": token_symbol,
                "analysis_type": "governance_risk",
            }

            # 使用AI服务进行分析
            if self.ai_service:
                try:
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="protocol_governance", data=ai_input_data
                    )

                    # 提取AI分析结果
                    risk_score = ai_analysis.get("risk_score", 50)
                    description = ai_analysis.get(
                        "description", f"对{protocol_name}协议的治理风险分析"
                    )
                    trend = ai_analysis.get("trend", "稳定")
                    data_points = ai_analysis.get("data_points", [])

                except Exception as e:
                    self.logger.error(f"使用AI分析协议治理风险时出错: {str(e)}")
                    # 如果AI分析失败，使用基于规则的分析
                    return await self._rule_based_governance_analysis(protocol_data)
            else:
                # 如果没有AI服务，使用基于规则的分析
                return await self._rule_based_governance_analysis(protocol_data)

            return self.create_risk_factor(
                risk_type=RiskType.PROTOCOL.value,
                factor_name="协议治理风险",
                score=risk_score,
                weight=0.3,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "protocol": protocol_name,
                    "protocol_data": protocol_data,
                    "ai_analysis": ai_analysis,
                },
            )
        except Exception as e:
            self.logger.error(f"分析协议 {protocol} 治理风险时出错: {str(e)}")
            return None

    async def _rule_based_governance_analysis(
        self, protocol_data: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """基于规则的协议治理风险分析"""
        try:
            # 提取关键治理指标
            protocol_name = protocol_data.get("name", "未知协议")
            category = protocol_data.get("category", "未知")
            twitter = protocol_data.get("twitter", "")
            github_repos = protocol_data.get("github", [])
            token_symbol = protocol_data.get("symbol", "")

            # 计算基础治理评分
            base_score = 50  # 默认中等风险

            # 社区因素 (有活跃社区降低风险)
            community_factor = 0
            if twitter:
                community_factor += 10  # 有Twitter账号减10分

            # 开发活跃度因素 (GitHub活跃度降低风险)
            github_factor = 0
            if github_repos:
                github_factor = min(
                    20, len(github_repos) * 10
                )  # 每个GitHub仓库减10分，最多减20分

            # 代币因素 (有治理代币可能降低中心化风险)
            token_factor = 10 if token_symbol else 0  # 有代币减10分

            # 协议类别因素 (某些类别的协议治理风险更高)
            category_risk = {
                "Dexes": -10,  # DEX通常治理较为去中心化
                "Lending": 0,  # 借贷协议治理中等
                "Yield": 5,  # 收益聚合器治理风险略高
                "Derivatives": 10,  # 衍生品协议治理风险较高
                "Options": 10,  # 期权协议治理风险较高
                "Staking": -5,  # 质押协议治理风险较低
                "Bridges": 15,  # 跨链桥治理风险高
                "Yield Aggregator": 10,  # 收益聚合器治理风险较高
                "Insurance": 5,  # 保险协议治理风险中等
                "Payments": 0,  # 支付协议治理风险中等
                "Privacy": 10,  # 隐私协议治理风险较高
            }

            category_factor = category_risk.get(category, 0)

            # 计算最终治理风险评分 (0-100，越高风险越大)
            governance_score = (
                base_score
                - community_factor
                - github_factor
                - token_factor
                + category_factor
            )
            governance_score = max(0, min(100, governance_score))  # 确保在0-100范围内

            # 构建描述
            if governance_score > 70:
                description = f"{protocol_name}协议治理高度中心化，决策透明度低"
                trend = "上升"
            elif governance_score > 50:
                description = f"{protocol_name}协议治理相对中心化，决策透明度有限"
                trend = "稳定"
            elif governance_score > 30:
                description = f"{protocol_name}协议治理较为去中心化，决策透明度中等"
                trend = "稳定"
            else:
                description = f"{protocol_name}协议治理高度去中心化，决策透明度高"
                trend = "下降"

            # 添加社区信息
            if twitter:
                description += " 协议拥有活跃的社区，"
            else:
                description += " 协议社区活跃度有限，"

            # 添加开发活跃度信息
            if github_repos:
                description += f"有{len(github_repos)}个GitHub仓库，开发较为活跃。"
            else:
                description += "缺乏公开的代码仓库，开发透明度低。"

            # 添加代币信息
            if token_symbol:
                description += f" 协议拥有治理代币{token_symbol}，可能支持社区治理。"

            # 构建数据点
            data_points = [
                {"name": "治理风险评分", "value": governance_score},
                {"name": "协议类别", "value": category},
                {"name": "Twitter", "value": twitter if twitter else "无"},
                {"name": "GitHub仓库数", "value": len(github_repos)},
                {"name": "治理代币", "value": token_symbol if token_symbol else "无"},
            ]

            # 添加GitHub仓库
            if github_repos:
                data_points.append({"name": "GitHub仓库", "value": github_repos})

            return self.create_risk_factor(
                risk_type=RiskType.PROTOCOL.value,
                factor_name="协议治理风险",
                score=governance_score,
                weight=0.3,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "protocol": protocol_name,
                    "protocol_data": protocol_data,
                },
            )
        except Exception as e:
            self.logger.error(f"基于规则分析协议治理风险时出错: {str(e)}")
            return None

    async def _analyze_protocol_history(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议历史风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取协议历史数据")
                return None

            # 使用区块链服务获取协议数据（从DefiLlama）
            protocol_data = await self.blockchain_service.get_protocol(protocol)

            if not protocol_data:
                self.logger.warning(f"获取协议 {protocol} 的数据失败")
                return None

            # 提取关键历史指标
            protocol_name = protocol_data.get("name", protocol)
            tvl_data = protocol_data.get("tvl", [])
            category = protocol_data.get("category", "未知")

            # 计算协议年龄（如果有tvl历史数据）
            protocol_age_days = 0
            if tvl_data and len(tvl_data) > 0:
                try:
                    # 假设tvl数据是按时间排序的，第一个是最早的数据点
                    first_data_point = tvl_data[0]
                    if (
                        isinstance(first_data_point, dict)
                        and "date" in first_data_point
                    ):
                        first_date = datetime.fromtimestamp(first_data_point["date"])
                        protocol_age_days = (datetime.now() - first_date).days
                    elif isinstance(tvl_data[0], list) and len(tvl_data[0]) >= 2:
                        # 如果是[timestamp, value]格式
                        first_timestamp = tvl_data[0][0]
                        first_date = datetime.fromtimestamp(first_timestamp)
                        protocol_age_days = (datetime.now() - first_date).days
                except Exception as e:
                    self.logger.error(f"计算协议年龄时出错: {str(e)}")

            # 准备AI分析的数据
            ai_input_data = {
                "protocol_name": protocol_name,
                "category": category,
                "protocol_age_days": protocol_age_days,
                "tvl_data": tvl_data,
                "analysis_type": "history_risk",
            }

            # 使用AI服务进行分析
            if self.ai_service:
                try:
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="protocol_history", data=ai_input_data
                    )

                    # 提取AI分析结果
                    risk_score = ai_analysis.get("risk_score", 50)
                    description = ai_analysis.get(
                        "description", f"对{protocol_name}协议的历史风险分析"
                    )
                    trend = ai_analysis.get("trend", "稳定")
                    data_points = ai_analysis.get("data_points", [])

                except Exception as e:
                    self.logger.error(f"使用AI分析协议历史风险时出错: {str(e)}")
                    # 如果AI分析失败，使用基于规则的分析
                    return await self._rule_based_history_analysis(protocol_data)
            else:
                # 如果没有AI服务，使用基于规则的分析
                return await self._rule_based_history_analysis(protocol_data)

            return self.create_risk_factor(
                risk_type=RiskType.PROTOCOL.value,
                factor_name="协议历史风险",
                score=risk_score,
                weight=0.2,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "protocol": protocol_name,
                    "protocol_data": protocol_data,
                    "ai_analysis": ai_analysis,
                },
            )
        except Exception as e:
            self.logger.error(f"分析协议 {protocol} 历史风险时出错: {str(e)}")
            return None

    async def _rule_based_history_analysis(
        self, protocol_data: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """基于规则的协议历史风险分析"""
        try:
            # 提取关键历史指标
            protocol_name = protocol_data.get("name", "未知协议")
            tvl_data = protocol_data.get("tvl", [])
            category = protocol_data.get("category", "未知")

            # 计算协议年龄（如果有tvl历史数据）
            protocol_age_days = 0
            if tvl_data and len(tvl_data) > 0:
                try:
                    # 假设tvl数据是按时间排序的，第一个是最早的数据点
                    first_data_point = tvl_data[0]
                    if (
                        isinstance(first_data_point, dict)
                        and "date" in first_data_point
                    ):
                        first_date = datetime.fromtimestamp(first_data_point["date"])
                        protocol_age_days = (datetime.now() - first_date).days
                    elif isinstance(tvl_data[0], list) and len(tvl_data[0]) >= 2:
                        # 如果是[timestamp, value]格式
                        first_timestamp = tvl_data[0][0]
                        first_date = datetime.fromtimestamp(first_timestamp)
                        protocol_age_days = (datetime.now() - first_date).days
                except Exception as e:
                    self.logger.error(f"计算协议年龄时出错: {str(e)}")

            # 计算TVL稳定性（如果有足够的历史数据）
            tvl_stability = 50  # 默认中等稳定性
            tvl_trend = "稳定"
            current_tvl = 0

            if tvl_data and len(tvl_data) > 30:  # 至少需要30个数据点
                try:
                    # 提取TVL值
                    tvl_values = []
                    if (
                        isinstance(tvl_data[0], dict)
                        and "totalLiquidityUSD" in tvl_data[0]
                    ):
                        tvl_values = [
                            point.get("totalLiquidityUSD", 0) for point in tvl_data
                        ]
                    elif isinstance(tvl_data[0], list) and len(tvl_data[0]) >= 2:
                        tvl_values = [point[1] for point in tvl_data]

                    if tvl_values:
                        # 计算当前TVL
                        current_tvl = tvl_values[-1]

                        # 计算TVL波动率（标准差/平均值）
                        if len(tvl_values) > 0 and sum(tvl_values) > 0:
                            avg_tvl = sum(tvl_values) / len(tvl_values)
                            std_dev = (
                                sum((x - avg_tvl) ** 2 for x in tvl_values)
                                / len(tvl_values)
                            ) ** 0.5
                            volatility = std_dev / avg_tvl if avg_tvl > 0 else 1

                            # 波动率越高，稳定性越低
                            tvl_stability = max(0, min(100, 100 - volatility * 100))

                            # 计算TVL趋势（最近30天与之前相比）
                            recent_avg = sum(tvl_values[-30:]) / 30
                            previous_avg = (
                                sum(tvl_values[-60:-30]) / 30
                                if len(tvl_values) >= 60
                                else recent_avg
                            )

                            if recent_avg > previous_avg * 1.1:
                                tvl_trend = "上升"
                            elif recent_avg < previous_avg * 0.9:
                                tvl_trend = "下降"
                            else:
                                tvl_trend = "稳定"
                except Exception as e:
                    self.logger.error(f"计算TVL稳定性时出错: {str(e)}")

            # 计算历史风险评分
            # 1. 协议年龄因素（越老风险越低）
            age_factor = 0
            if protocol_age_days > 730:  # 2年以上
                age_factor = 30
            elif protocol_age_days > 365:  # 1-2年
                age_factor = 20
            elif protocol_age_days > 180:  # 6个月-1年
                age_factor = 10
            elif protocol_age_days > 90:  # 3-6个月
                age_factor = 5

            # 2. TVL稳定性因素
            stability_factor = (100 - tvl_stability) / 2  # 转换为0-50的风险分数

            # 3. 协议类别历史风险因素
            category_risk = {
                "Dexes": 10,  # DEX历史相对稳定
                "Lending": 15,  # 借贷协议历史风险中等
                "Yield": 25,  # 收益聚合器历史风险较高
                "Derivatives": 30,  # 衍生品协议历史风险高
                "Options": 30,  # 期权协议历史风险高
                "Staking": 10,  # 质押协议历史风险较低
                "Bridges": 35,  # 跨链桥历史风险高
                "Yield Aggregator": 25,  # 收益聚合器历史风险较高
                "Insurance": 15,  # 保险协议历史风险中等
                "Payments": 10,  # 支付协议历史风险较低
                "Privacy": 20,  # 隐私协议历史风险中等
            }

            category_factor = category_risk.get(category, 20)  # 默认中等风险

            # 计算最终历史风险评分 (0-100，越高风险越大)
            # 基础分50，减去年龄因素（越老越安全），加上稳定性风险和类别风险
            history_score = 50 - age_factor + stability_factor + category_factor
            history_score = max(0, min(100, history_score))  # 确保在0-100范围内

            # 构建描述
            age_description = ""
            if protocol_age_days > 730:
                age_description = f"{protocol_name}是一个成熟的协议，已运行超过2年"
            elif protocol_age_days > 365:
                age_description = f"{protocol_name}是一个相对成熟的协议，已运行超过1年"
            elif protocol_age_days > 180:
                age_description = f"{protocol_name}是一个发展中的协议，已运行超过6个月"
            elif protocol_age_days > 90:
                age_description = f"{protocol_name}是一个较新的协议，已运行超过3个月"
            else:
                age_description = f"{protocol_name}是一个新兴协议，运行时间不足3个月"

            tvl_description = ""
            if tvl_stability > 70:
                tvl_description = "，TVL非常稳定"
            elif tvl_stability > 50:
                tvl_description = "，TVL相对稳定"
            elif tvl_stability > 30:
                tvl_description = "，TVL波动较大"
            else:
                tvl_description = "，TVL波动剧烈"

            trend_description = ""
            if tvl_trend == "上升":
                trend_description = "，呈上升趋势"
            elif tvl_trend == "下降":
                trend_description = "，呈下降趋势"
            else:
                trend_description = "，保持稳定"

            description = f"{age_description}{tvl_description}{trend_description}。"

            if current_tvl > 0:
                description += f" 当前锁仓价值约为{current_tvl/1000000:.2f}百万美元。"

            # 添加类别信息
            description += f" 作为{category}类别的协议，"

            if category_factor > 25:
                description += "该类别历史上风险较高。"
            elif category_factor > 15:
                description += "该类别历史上风险中等。"
            else:
                description += "该类别历史上风险相对较低。"

            # 构建数据点
            data_points = [
                {"name": "历史风险评分", "value": history_score},
                {"name": "协议年龄(天)", "value": protocol_age_days},
                {"name": "TVL稳定性", "value": tvl_stability},
                {"name": "TVL趋势", "value": tvl_trend},
                {"name": "当前TVL(USD)", "value": current_tvl},
                {"name": "协议类别", "value": category},
            ]

            return self.create_risk_factor(
                risk_type=RiskType.PROTOCOL.value,
                factor_name="协议历史风险",
                score=history_score,
                weight=0.2,
                description=description,
                trend=tvl_trend,
                data_points=data_points,
                metadata={
                    "protocol": protocol_name,
                    "protocol_data": protocol_data,
                },
            )
        except Exception as e:
            self.logger.error(f"基于规则分析协议历史风险时出错: {str(e)}")
            return None

    async def _analyze_protocol_complexity(self, protocol: str) -> Optional[RiskFactor]:
        """分析协议复杂性风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取协议复杂性数据")
                return None

            # 使用区块链服务获取协议数据（从DefiLlama）
            protocol_data = await self.blockchain_service.get_protocol(protocol)

            if not protocol_data:
                self.logger.warning(f"获取协议 {protocol} 的数据失败")
                return None

            # 提取关键复杂性指标
            protocol_name = protocol_data.get("name", protocol)
            category = protocol_data.get("category", "未知")
            chains = protocol_data.get("chains", [])
            github_repos = protocol_data.get("github", [])

            # 准备AI分析的数据
            ai_input_data = {
                "protocol_name": protocol_name,
                "category": category,
                "chains": chains,
                "github_repos": github_repos,
                "analysis_type": "complexity_risk",
            }

            # 使用AI服务进行分析
            if self.ai_service:
                try:
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="protocol_complexity", data=ai_input_data
                    )

                    # 提取AI分析结果
                    risk_score = ai_analysis.get("risk_score", 50)
                    description = ai_analysis.get(
                        "description", f"对{protocol_name}协议的复杂性风险分析"
                    )
                    trend = ai_analysis.get("trend", "稳定")
                    data_points = ai_analysis.get("data_points", [])

                except Exception as e:
                    self.logger.error(f"使用AI分析协议复杂性风险时出错: {str(e)}")
                    # 如果AI分析失败，使用基于规则的分析
                    return await self._rule_based_complexity_analysis(protocol_data)
            else:
                # 如果没有AI服务，使用基于规则的分析
                return await self._rule_based_complexity_analysis(protocol_data)

            return self.create_risk_factor(
                risk_type=RiskType.PROTOCOL.value,
                factor_name="协议复杂性风险",
                score=risk_score,
                weight=0.2,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "protocol": protocol_name,
                    "protocol_data": protocol_data,
                    "ai_analysis": ai_analysis,
                },
            )
        except Exception as e:
            self.logger.error(f"分析协议 {protocol} 复杂性风险时出错: {str(e)}")
            return None

    async def _rule_based_complexity_analysis(
        self, protocol_data: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """基于规则的协议复杂性风险分析"""
        try:
            # 提取关键复杂性指标
            protocol_name = protocol_data.get("name", "未知协议")
            category = protocol_data.get("category", "未知")
            chains = protocol_data.get("chains", [])
            github_repos = protocol_data.get("github", [])

            # 计算基础复杂性评分
            base_score = 50  # 默认中等复杂性

            # 1. 多链因素（支持的链越多，复杂性越高）
            chain_factor = min(30, len(chains) * 5)  # 每条链增加5分，最多30分

            # 2. 协议类别复杂性因素
            category_complexity = {
                "Dexes": 15,  # DEX复杂性中等
                "Lending": 20,  # 借贷协议复杂性较高
                "Yield": 25,  # 收益聚合器复杂性高
                "Derivatives": 30,  # 衍生品协议复杂性高
                "Options": 35,  # 期权协议复杂性很高
                "Staking": 10,  # 质押协议复杂性较低
                "Bridges": 25,  # 跨链桥复杂性高
                "Yield Aggregator": 30,  # 收益聚合器复杂性高
                "Insurance": 20,  # 保险协议复杂性较高
                "Payments": 15,  # 支付协议复杂性中等
                "Privacy": 25,  # 隐私协议复杂性高
            }

            category_factor = category_complexity.get(category, 20)  # 默认中等复杂性

            # 3. 代码库因素（有公开代码库可能降低复杂性风险）
            github_factor = -10 if github_repos else 0  # 有GitHub仓库减10分

            # 计算最终复杂性风险评分 (0-100，越高风险越大)
            complexity_score = (
                base_score + chain_factor + category_factor + github_factor
            )
            complexity_score = max(0, min(100, complexity_score))  # 确保在0-100范围内

            # 构建描述
            if complexity_score > 70:
                description = f"{protocol_name}协议复杂性非常高，"
                trend = "上升"
            elif complexity_score > 50:
                description = f"{protocol_name}协议复杂性较高，"
                trend = "稳定"
            elif complexity_score > 30:
                description = f"{protocol_name}协议复杂性中等，"
                trend = "稳定"
            else:
                description = f"{protocol_name}协议复杂性较低，"
                trend = "下降"

            # 添加多链信息
            if len(chains) > 1:
                description += (
                    f"支持{len(chains)}条区块链（{', '.join(chains[:3])}等），"
                )
                if len(chains) > 5:
                    description += "多链操作增加了协议的复杂性和风险。"
                elif len(chains) > 2:
                    description += "跨链操作增加了一定的复杂性。"
                else:
                    description += "有限的跨链支持。"
            elif len(chains) == 1:
                description += f"仅支持{chains[0]}链，复杂性相对较低。"
            else:
                description += "未明确支持的区块链，可能增加使用复杂性。"

            # 添加类别信息
            description += f" 作为{category}类别的协议，"

            if category_factor > 25:
                description += "该类别通常具有较高的复杂性。"
            elif category_factor > 15:
                description += "该类别具有中等复杂性。"
            else:
                description += "该类别复杂性相对较低。"

            # 添加代码库信息
            if github_repos:
                description += (
                    f" 协议有{len(github_repos)}个公开的GitHub仓库，增加了透明度。"
                )
            else:
                description += " 协议缺乏公开的代码仓库，可能增加了理解和审计的难度。"

            # 构建数据点
            data_points = [
                {"name": "复杂性风险评分", "value": complexity_score},
                {"name": "支持的区块链数量", "value": len(chains)},
                {"name": "支持的区块链", "value": chains},
                {"name": "协议类别", "value": category},
                {"name": "GitHub仓库数", "value": len(github_repos)},
            ]

            # 添加GitHub仓库
            if github_repos:
                data_points.append({"name": "GitHub仓库", "value": github_repos})

            return self.create_risk_factor(
                risk_type=RiskType.PROTOCOL.value,
                factor_name="协议复杂性风险",
                score=complexity_score,
                weight=0.2,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "protocol": protocol_name,
                    "protocol_data": protocol_data,
                },
            )
        except Exception as e:
            self.logger.error(f"基于规则分析协议复杂性风险时出错: {str(e)}")
            return None

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取协议风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        # 从风险因子中提取协议名称，如果不存在则使用通用名称
        protocol_name = "未知协议"
        if risk_factors and risk_factors[0].metadata:
            protocol_name = risk_factors[0].metadata.get("protocol_name", "未知协议")

        recommendations = []

        # 根据风险因子生成建议
        for factor in risk_factors:
            # 协议安全风险建议
            if factor.name == "协议安全风险":
                if factor.score > 70:
                    recommendations.append(
                        f"建议避免投资{protocol_name}，该协议安全风险极高"
                    )
                    recommendations.append(
                        f"密切关注{protocol_name}的安全审计报告和漏洞披露"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        f"谨慎投资{protocol_name}，该协议存在一定安全风险"
                    )
                    recommendations.append(
                        f"关注{protocol_name}的安全审计状态和历史安全事件"
                    )
                else:
                    recommendations.append(
                        f"{protocol_name}的安全风险相对较低，但仍需保持警惕"
                    )

                # 检查审计信息
                audit_info = False
                for data_point in factor.data_points:
                    if (
                        data_point.get("name") == "审计状态"
                        and data_point.get("value") == "已审计"
                    ):
                        audit_info = True
                        recommendations.append(
                            f"查阅{protocol_name}的审计报告，了解潜在风险点"
                        )

        # 返回去重后的建议
        return list(set(recommendations))

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取协议风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        # 从风险因子中提取协议名称，如果不存在则使用通用名称
        protocol_name = "未知协议"
        if risk_factors and risk_factors[0].metadata:
            protocol_name = risk_factors[0].metadata.get("protocol_name", "未知协议")

        monitoring_points = []

        # 根据风险因子生成监控点
        for factor in risk_factors:
            if factor.name == "协议安全风险" and factor.score > 40:
                monitoring_points.append(f"关注{protocol_name}的安全审计状态和更新")
                monitoring_points.append(f"监控{protocol_name}的安全事件和漏洞报告")

            if factor.name == "协议治理风险" and factor.score > 40:
                monitoring_points.append(f"关注{protocol_name}的治理提案和投票情况")
                monitoring_points.append(f"监控{protocol_name}的治理结构变化")

            if factor.name == "协议历史风险" and factor.score > 40:
                monitoring_points.append(f"跟踪{protocol_name}的TVL变化趋势")
                monitoring_points.append(f"监控{protocol_name}的用户增长情况")

            if factor.name == "协议复杂性风险" and factor.score > 40:
                monitoring_points.append(f"关注{protocol_name}的合约升级和功能变更")
                monitoring_points.append(f"监控{protocol_name}的技术架构变化")

        # 如果没有生成监控点，添加通用监控点
        if not monitoring_points:
            monitoring_points.append(f"定期检查{protocol_name}的运行状态和性能指标")
            monitoring_points.append(f"关注{protocol_name}的官方公告和社区动态")

        return monitoring_points
