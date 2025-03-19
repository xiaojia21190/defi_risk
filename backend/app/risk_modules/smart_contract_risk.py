"""
智能合约风险分析模块 - 用于分析DeFi协议的智能合约风险
"""

from typing import Dict, List, Any, Optional
from app.models.domain.risk import RiskFactor, RiskType
from app.risk_modules.base import RiskAnalyzerBase


class SmartContractRiskAnalyzer(RiskAnalyzerBase):
    """智能合约风险分析器"""

    def __init__(self, ai_service=None, ai_predictor=None, blockchain_service=None):
        """初始化智能合约风险分析器"""
        super().__init__(ai_service, ai_predictor, blockchain_service)
        from app.services.recommendation_service import RecommendationService

        self.recommendation_service = RecommendationService()

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析智能合约风险

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        self.logger.info("开始分析智能合约风险")

        # 获取风险因子
        risk_factors = await self.get_risk_factors(data)

        # 计算总体风险评分
        if not risk_factors:
            total_score = 0
        else:
            total_score = sum(f.score * f.weight for f in risk_factors) / sum(
                f.weight for f in risk_factors
            )

        # 获取建议
        recommendations = await self.get_recommendations(risk_factors)

        # 获取监控点
        monitoring_points = await self.get_monitoring_points(risk_factors)

        self.logger.info(f"智能合约风险分析完成: 评分={total_score}")

        return {
            "risk_score": total_score,
            "risk_factors": [f.__dict__ for f in risk_factors],
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
        }

    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取智能合约风险因子

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
            protocol = pos.get("protocol", "Unknown")
            if protocol not in protocols:
                protocols[protocol] = 0
            protocols[protocol] += pos.get("amount", 0)

        # 分析审计风险
        audit_risk = await self._analyze_audit_risk(protocols)
        if audit_risk:
            risk_factors.append(audit_risk)

        # 分析代码质量风险
        code_quality_risk = await self._analyze_code_quality_risk(protocols)
        if code_quality_risk:
            risk_factors.append(code_quality_risk)

        # 分析漏洞历史风险
        vulnerability_risk = await self._analyze_vulnerability_risk(protocols)
        if vulnerability_risk:
            risk_factors.append(vulnerability_risk)

        # 分析合约复杂性风险
        complexity_risk = await self._analyze_complexity_risk(protocols)
        if complexity_risk:
            risk_factors.append(complexity_risk)

        return risk_factors

    async def _analyze_audit_risk(
        self, protocols: Dict[str, float]
    ) -> Optional[RiskFactor]:
        """分析审计风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取协议审计数据")
                return None

            # 获取每个协议的审计状态
            audit_data = {}
            total_value = sum(protocols.values())

            for protocol, value in protocols.items():
                weight = value / total_value if total_value > 0 else 0

                # 获取协议审计状态
                audit_status = await self.blockchain_service.get_protocol_audit_status(
                    protocol
                )

                # 提取审计信息
                is_audited = audit_status.get("audited", False)
                audit_count = audit_status.get("audit_count", 0)
                audit_score = audit_status.get("audit_score", 0)
                is_open_source = audit_status.get("is_open_source", False)
                audit_firms = audit_status.get("audit_firms", [])

                # 计算审计风险评分 (0-100，越高风险越大)
                # 审计评分越高，风险越低，需要转换为风险分数
                audit_risk = 100 - audit_score

                # 存储数据
                audit_data[protocol] = {
                    "is_audited": is_audited,
                    "audit_count": audit_count,
                    "audit_score": audit_score,
                    "is_open_source": is_open_source,
                    "audit_firms": audit_firms,
                    "audit_risk": audit_risk,
                    "weight": weight,
                    "value": value,
                }

            # 计算加权平均审计风险
            weighted_audit_risk = sum(
                data["audit_risk"] * data["weight"] for data in audit_data.values()
            )

            # 计算未审计协议的占比
            unaudited_protocols = [
                p for p, data in audit_data.items() if not data["is_audited"]
            ]
            unaudited_value = sum(audit_data[p]["value"] for p in unaudited_protocols)
            unaudited_ratio = unaudited_value / total_value if total_value > 0 else 0

            # 构建描述
            if weighted_audit_risk > 80:
                description = "智能合约审计风险极高，大部分协议缺乏专业审计"
                trend = "上升"
            elif weighted_audit_risk > 60:
                description = "智能合约审计风险较高，部分协议缺乏足够的审计"
                trend = "上升"
            elif weighted_audit_risk > 40:
                description = "智能合约审计风险中等，主要协议已有基本审计"
                trend = "稳定"
            elif weighted_audit_risk > 20:
                description = "智能合约审计风险较低，大部分协议已经过多次审计"
                trend = "下降"
            else:
                description = "智能合约审计风险很低，所有协议都经过了充分审计"
                trend = "下降"

            # 添加未审计协议信息
            if unaudited_protocols:
                description += f"，有{len(unaudited_protocols)}个协议（占比{unaudited_ratio:.1%}）缺乏审计"

            # 构建数据点
            data_points = []
            for protocol, data in audit_data.items():
                data_points.append(
                    {
                        "protocol": protocol,
                        "is_audited": data["is_audited"],
                        "audit_count": data["audit_count"],
                        "audit_score": data["audit_score"],
                        "is_open_source": data["is_open_source"],
                        "audit_firms": data["audit_firms"],
                        "audit_risk": data["audit_risk"],
                        "weight": data["weight"],
                    }
                )

            return self.create_risk_factor(
                risk_type=RiskType.SMART_CONTRACT.value,
                factor_name="智能合约审计风险",
                score=weighted_audit_risk,
                weight=0.4,  # 审计风险权重较高
                description=description,
                trend=trend,
                data_points=data_points,
            )
        except Exception as e:
            self.logger.error(f"分析审计风险时出错: {str(e)}")
            return None

    async def _analyze_code_quality_risk(
        self, protocols: Dict[str, float]
    ) -> Optional[RiskFactor]:
        """分析代码质量风险"""
        # 预定义的代码质量评分（0-100，越低越好）
        code_quality_scores = {
            "Aave": 15,  # 高质量代码
            "Compound": 15,  # 高质量代码
            "Uniswap": 10,  # 高质量代码
            "Curve": 20,  # 高质量代码
            "MakerDAO": 25,  # 高质量代码
            "SushiSwap": 35,  # 中等质量代码
            "Balancer": 30,  # 中等质量代码
            "Yearn": 40,  # 中等质量代码
            "PancakeSwap": 45,  # 中等质量代码
            "dYdX": 30,  # 中等质量代码
            "Synthetix": 35,  # 中等质量代码
            "1inch": 40,  # 中等质量代码
            "Bancor": 50,  # 中低质量代码
            "Cream": 55,  # 中低质量代码
            "Alpha": 60,  # 中低质量代码
            "BarnBridge": 65,  # 低质量代码
            "Harvest": 70,  # 低质量代码
            "Badger": 60,  # 中低质量代码
            "ForTube": 75,  # 低质量代码
            "AnySwap": 80,  # 低质量代码
        }

        # 计算加权代码质量评分
        total_value = sum(protocols.values())
        if total_value == 0:
            return None

        weighted_score = 0
        for protocol, amount in protocols.items():
            score = code_quality_scores.get(protocol, 60)  # 默认为中低质量
            weighted_score += score * (amount / total_value)

        # 根据加权评分评估风险
        if weighted_score > 70:
            description = "投资组合中的协议代码质量普遍较低，增加了安全风险"
            trend = "上升"
        elif weighted_score > 50:
            description = "投资组合中的部分协议代码质量不佳，存在一定安全风险"
            trend = "稳定"
        elif weighted_score > 30:
            description = "投资组合中的协议代码质量中等，安全风险适中"
            trend = "稳定"
        else:
            description = "投资组合中的协议代码质量普遍较高，安全风险相对较低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="SMART_CONTRACT",
            factor_name="代码质量",
            score=weighted_score,
            weight=0.3,
            description=description,
            trend=trend,
            data_points=[
                {
                    "protocol": protocol,
                    "amount": amount,
                    "code_quality_score": code_quality_scores.get(protocol, 60),
                }
                for protocol, amount in protocols.items()
            ],
        )

    async def _analyze_vulnerability_risk(
        self, protocols: Dict[str, float]
    ) -> Optional[RiskFactor]:
        """分析漏洞历史风险"""
        # 预定义的漏洞历史评分（0-100，越低越好）
        vulnerability_scores = {
            "Aave": 20,  # 很少漏洞
            "Compound": 25,  # 很少漏洞
            "Uniswap": 15,  # 很少漏洞
            "Curve": 30,  # 很少漏洞
            "MakerDAO": 35,  # 少量漏洞
            "SushiSwap": 45,  # 中等漏洞
            "Balancer": 50,  # 中等漏洞
            "Yearn": 55,  # 中等漏洞
            "PancakeSwap": 40,  # 中等漏洞
            "dYdX": 35,  # 少量漏洞
            "Synthetix": 45,  # 中等漏洞
            "1inch": 40,  # 中等漏洞
            "Bancor": 60,  # 较多漏洞
            "Cream": 70,  # 较多漏洞
            "Alpha": 65,  # 较多漏洞
            "BarnBridge": 55,  # 中等漏洞
            "Harvest": 75,  # 较多漏洞
            "Badger": 60,  # 较多漏洞
            "ForTube": 80,  # 多次漏洞
            "AnySwap": 85,  # 多次漏洞
        }

        # 计算加权漏洞历史评分
        total_value = sum(protocols.values())
        if total_value == 0:
            return None

        weighted_score = 0
        for protocol, amount in protocols.items():
            score = vulnerability_scores.get(protocol, 60)  # 默认为中等漏洞
            weighted_score += score * (amount / total_value)

        # 根据加权评分评估风险
        if weighted_score > 70:
            description = "投资组合中的协议历史上存在多次漏洞，安全风险高"
            trend = "上升"
        elif weighted_score > 50:
            description = "投资组合中的部分协议历史上有漏洞记录，存在一定安全风险"
            trend = "稳定"
        elif weighted_score > 30:
            description = "投资组合中的协议历史上漏洞较少，安全风险适中"
            trend = "稳定"
        else:
            description = "投资组合中的协议历史上几乎没有漏洞，安全风险相对较低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="SMART_CONTRACT",
            factor_name="漏洞历史",
            score=weighted_score,
            weight=0.2,
            description=description,
            trend=trend,
            data_points=[
                {
                    "protocol": protocol,
                    "amount": amount,
                    "vulnerability_score": vulnerability_scores.get(protocol, 60),
                }
                for protocol, amount in protocols.items()
            ],
        )

    async def _analyze_complexity_risk(
        self, protocols: Dict[str, float]
    ) -> Optional[RiskFactor]:
        """分析合约复杂性风险"""
        # 预定义的复杂性评分（0-100，越低越好）
        complexity_scores = {
            "Aave": 60,  # 较复杂
            "Compound": 55,  # 较复杂
            "Uniswap": 40,  # 中等复杂度
            "Curve": 70,  # 复杂
            "MakerDAO": 75,  # 复杂
            "SushiSwap": 45,  # 中等复杂度
            "Balancer": 65,  # 较复杂
            "Yearn": 80,  # 非常复杂
            "PancakeSwap": 40,  # 中等复杂度
            "dYdX": 70,  # 复杂
            "Synthetix": 75,  # 复杂
            "1inch": 60,  # 较复杂
            "Bancor": 65,  # 较复杂
            "Cream": 60,  # 较复杂
            "Alpha": 55,  # 较复杂
            "BarnBridge": 70,  # 复杂
            "Harvest": 65,  # 较复杂
            "Badger": 60,  # 较复杂
            "ForTube": 50,  # 中等复杂度
            "AnySwap": 45,  # 中等复杂度
        }

        # 计算加权复杂性评分
        total_value = sum(protocols.values())
        if total_value == 0:
            return None

        weighted_score = 0
        for protocol, amount in protocols.items():
            score = complexity_scores.get(protocol, 60)  # 默认为较复杂
            weighted_score += score * (amount / total_value)

        # 根据加权评分评估风险
        if weighted_score > 70:
            description = "投资组合中的协议合约普遍较为复杂，增加了潜在风险"
            trend = "上升"
        elif weighted_score > 60:
            description = "投资组合中的协议合约复杂度较高，存在一定风险"
            trend = "稳定"
        elif weighted_score > 50:
            description = "投资组合中的协议合约复杂度中等，风险适中"
            trend = "稳定"
        else:
            description = "投资组合中的协议合约相对简单，风险较低"
            trend = "下降"

        return self.create_risk_factor(
            risk_type="SMART_CONTRACT",
            factor_name="合约复杂性",
            score=weighted_score,
            weight=0.1,
            description=description,
            trend=trend,
            data_points=[
                {
                    "protocol": protocol,
                    "amount": amount,
                    "complexity_score": complexity_scores.get(protocol, 60),
                }
                for protocol, amount in protocols.items()
            ],
        )

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取智能合约风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        # 根据风险因子生成建议
        for factor in risk_factors:
            if factor.id == "SMART_CONTRACT.审计状态" and factor.score > 60:
                recommendations.append("优先选择经过多次安全审计的协议进行投资")
                recommendations.append("考虑购买智能合约保险以降低安全风险")

            if factor.id == "SMART_CONTRACT.代码质量" and factor.score > 60:
                recommendations.append("关注协议的代码质量和开发团队的技术实力")
                recommendations.append("避免投资代码质量较差的新兴协议")

            if factor.id == "SMART_CONTRACT.漏洞历史" and factor.score > 60:
                recommendations.append("研究协议的漏洞历史和安全事件处理能力")
                recommendations.append("减少在历史上多次出现漏洞的协议中的投资")

            if factor.id == "SMART_CONTRACT.合约复杂性" and factor.score > 60:
                recommendations.append("了解协议的合约架构和复杂度")
                recommendations.append("对于复杂协议，建议分散投资以降低风险")

        # 添加一般性建议
        if not recommendations:
            recommendations.append("定期关注协议的安全审计报告和代码更新")

        return recommendations

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取智能合约风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        monitoring_points = []

        # 根据风险因子生成监控点
        for factor in risk_factors:
            if factor.id == "SMART_CONTRACT.审计状态" and factor.score > 40:
                monitoring_points.append("关注协议的最新安全审计报告和审计机构的声誉")

            if factor.id == "SMART_CONTRACT.代码质量" and factor.score > 40:
                monitoring_points.append("监控协议的GitHub活动和代码更新频率")

            if factor.id == "SMART_CONTRACT.漏洞历史" and factor.score > 40:
                monitoring_points.append("关注安全漏洞公告和协议的安全事件响应")

            if factor.id == "SMART_CONTRACT.合约复杂性" and factor.score > 40:
                monitoring_points.append("跟踪协议的合约升级和架构变化")

        # 添加一般性监控点
        if not monitoring_points:
            monitoring_points.append("定期检查协议的安全状态和社区反馈")

        return monitoring_points
