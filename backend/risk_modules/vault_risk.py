"""
机枪池风险分析模块 - 用于分析机枪池类型投资的风险
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger("defi_risk.vault_risk")


class VaultRiskAnalyzer:
    """机枪池风险分析器"""

    def __init__(self, ai_predictor=None, blockchain_service=None):
        """
        初始化机枪池风险分析器

        Args:
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service

    def monitor_vault_risk(self, vault_data: Dict) -> Dict:
        """
        监测机枪池风险

        Args:
            vault_data: 机枪池投资数据

        Returns:
            Dict: 风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_analysis = {
                "invest_type": 4,  # 机枪池
                "invest_type_name": "机枪池",
                "pool_name": vault_data.get("investmentName", "未知机枪池"),
                "risk_score": 0,
                "risk_level": "",
                "risk_factors": [],
                "recommendations": [],
                "monitoring_points": [],
                "detailed_risks": {},
            }

            # 提取基础信息
            assets = vault_data.get("assetsTokenList", [])
            total_value = float(vault_data.get("totalValue", "0"))
            protocol_name = self._extract_protocol_name(vault_data)

            # 提取机枪池特有信息
            strategy = vault_data.get("strategy", "")  # 策略描述
            leverage = vault_data.get("leverage", 1)  # 杠杆倍数
            apy = vault_data.get("apy", 0)  # 年化收益率
            underlying_protocols = vault_data.get("underlyingProtocols", [])  # 底层协议

            if not assets:
                risk_analysis["risk_factors"].append("无法获取资产信息，风险评估不完整")
                risk_analysis["risk_score"] = 0.7  # 信息不完整，默认较高风险
                risk_analysis["risk_level"] = "HIGH"
                return risk_analysis

            # 1. 资产风险分析
            asset_risk = self._analyze_vault_asset_risk(assets)
            risk_analysis["detailed_risks"]["asset_risk"] = asset_risk
            risk_analysis["risk_factors"].extend(asset_risk["risk_factors"])
            risk_analysis["recommendations"].extend(asset_risk["recommendations"])

            # 2. 策略风险分析
            strategy_risk = self._analyze_strategy_risk(strategy, leverage)
            risk_analysis["detailed_risks"]["strategy_risk"] = strategy_risk
            risk_analysis["risk_factors"].extend(strategy_risk["risk_factors"])
            risk_analysis["recommendations"].extend(strategy_risk["recommendations"])

            # 3. 协议安全风险分析
            protocol_risk = self._analyze_protocol_risk(
                vault_data, underlying_protocols
            )
            risk_analysis["detailed_risks"]["protocol_risk"] = protocol_risk
            risk_analysis["risk_factors"].extend(protocol_risk["risk_factors"])
            risk_analysis["recommendations"].extend(protocol_risk["recommendations"])

            # 4. 收益风险分析
            yield_risk = self._analyze_yield_risk(apy)
            risk_analysis["detailed_risks"]["yield_risk"] = yield_risk
            risk_analysis["risk_factors"].extend(yield_risk["risk_factors"])
            risk_analysis["recommendations"].extend(yield_risk["recommendations"])

            # 5. 智能合约风险分析
            contract_risk = {
                "score": 0.6,  # 机枪池合约通常风险较高
                "risk_factors": [
                    "机枪池智能合约风险较高",
                    "复杂的自动化策略增加了漏洞风险",
                    "多协议交互增加了攻击面",
                ],
                "recommendations": [
                    "关注协议安全审计状态",
                    "了解机枪池的紧急提款机制",
                    "关注社区对该机枪池的评价",
                ],
            }
            risk_analysis["detailed_risks"]["contract_risk"] = contract_risk
            risk_analysis["risk_factors"].extend(contract_risk["risk_factors"])
            risk_analysis["recommendations"].extend(contract_risk["recommendations"])

            # 计算综合风险分数（加权平均）
            weights = {
                "asset_risk": 0.15,
                "strategy_risk": 0.3,
                "protocol_risk": 0.2,
                "yield_risk": 0.15,
                "contract_risk": 0.2,
            }

            total_score = sum(
                risk_analysis["detailed_risks"][risk_type]["score"] * weight
                for risk_type, weight in weights.items()
            )

            risk_analysis["risk_score"] = round(total_score, 2)

            # 确定风险等级
            if risk_analysis["risk_score"] >= 0.65:
                risk_analysis["risk_level"] = "HIGH"
            elif risk_analysis["risk_score"] <= 0.35:
                risk_analysis["risk_level"] = "LOW"
            else:
                risk_analysis["risk_level"] = "MEDIUM"

            # 添加监控点
            risk_analysis["monitoring_points"] = [
                "机枪池策略变更",
                "底层协议安全状态",
                "收益率变化趋势",
                "资产价格波动",
                "杠杆率变化",
                "TVL变化",
            ]

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
            logger.error(f"监测机枪池风险时出错: {e}")
            return {
                "invest_type": 4,
                "invest_type_name": "机枪池",
                "pool_name": vault_data.get("investmentName", "未知机枪池"),
                "risk_score": 0.7,  # 出错时默认较高风险
                "risk_level": "HIGH",
                "risk_factors": ["风险分析过程中出错"],
                "recommendations": ["建议手动评估风险"],
                "monitoring_points": ["系统错误修复状态"],
                "error": str(e),
            }

    def _analyze_vault_asset_risk(self, assets: List[Dict]) -> Dict:
        """
        分析机枪池资产风险

        Args:
            assets: 资产列表

        Returns:
            Dict: 资产风险分析结果
        """
        try:
            if not assets:
                return {
                    "score": 0.7,
                    "risk_factors": ["无法获取资产信息"],
                    "recommendations": ["建议手动评估资产风险"],
                }

            # 初始化风险分析结果
            risk_score = 0.0
            risk_factors = []
            recommendations = []

            # 分析每个资产
            for asset in assets:
                token_symbol = asset.get("tokenSymbol", "未知资产")
                token_amount = float(asset.get("tokenAmount", "0"))

                # 根据资产类型评估风险
                if token_symbol in ["ETH", "WETH", "BTC", "WBTC"]:
                    # 主流资产，波动性较高
                    asset_risk = 0.4
                    risk_factors.append(f"{token_symbol}价格波动可能影响机枪池策略效果")
                elif token_symbol in ["USDC", "USDT", "DAI"]:
                    # 稳定币，风险较低
                    asset_risk = 0.2
                    risk_factors.append(f"{token_symbol}是稳定币，价格风险较低")
                else:
                    # 其他资产，风险较高
                    asset_risk = 0.7
                    risk_factors.append(
                        f"{token_symbol}可能是小市值代币，价格波动风险高"
                    )
                    recommendations.append(f"密切关注{token_symbol}的价格波动")

                # 累加风险评分
                risk_score += asset_risk

            # 计算平均风险评分
            avg_risk_score = risk_score / len(assets) if assets else 0.5

            # 根据风险评分生成建议
            if avg_risk_score > 0.5:
                recommendations.append("机枪池资产风险较高，建议限制投资金额")
                recommendations.append("设置价格预警，及时关注资产价格变化")
            elif avg_risk_score > 0.3:
                recommendations.append("定期监控机枪池资产组合变化")
            else:
                recommendations.append("当前机枪池资产风险较低，但仍需关注策略变化")

            return {
                "score": avg_risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析机枪池资产风险时出错: {e}")
            return {
                "score": 0.5,
                "risk_factors": ["资产风险分析过程中出错"],
                "recommendations": ["建议手动评估资产风险"],
            }

    def _analyze_strategy_risk(self, strategy: str, leverage: float) -> Dict:
        """
        分析机枪池策略风险

        Args:
            strategy: 策略描述
            leverage: 杠杆倍数

        Returns:
            Dict: 策略风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            # 根据策略描述评估风险
            strategy_risk = 0.5  # 默认中等风险

            # 检查策略描述中的关键词
            strategy_lower = strategy.lower() if strategy else ""

            # 高风险策略关键词
            high_risk_keywords = [
                "leverage",
                "杠杆",
                "short",
                "做空",
                "delta-neutral",
                "delta中性",
                "options",
                "期权",
            ]
            # 中等风险策略关键词
            medium_risk_keywords = [
                "yield farming",
                "收益耕作",
                "liquidity",
                "流动性",
                "lending",
                "借贷",
            ]
            # 低风险策略关键词
            low_risk_keywords = ["stable", "稳定", "保守", "conservative"]

            # 检查高风险关键词
            high_risk_count = sum(
                1 for keyword in high_risk_keywords if keyword in strategy_lower
            )
            # 检查中等风险关键词
            medium_risk_count = sum(
                1 for keyword in medium_risk_keywords if keyword in strategy_lower
            )
            # 检查低风险关键词
            low_risk_count = sum(
                1 for keyword in low_risk_keywords if keyword in strategy_lower
            )

            # 根据关键词出现次数调整风险评分
            if high_risk_count > 0:
                strategy_risk = 0.7
                risk_factors.append("策略包含高风险操作，如杠杆或做空")
                recommendations.append("限制在此类高风险机枪池中的投资比例")
            elif medium_risk_count > 0:
                strategy_risk = 0.5
                risk_factors.append("策略包含中等风险操作，如收益耕作或流动性挖矿")
            elif low_risk_count > 0:
                strategy_risk = 0.3
                risk_factors.append("策略相对保守，风险较低")
            else:
                risk_factors.append("无法从策略描述中确定具体风险等级")
                recommendations.append("进一步了解机枪池策略细节")

            # 分析杠杆风险
            if leverage > 1:
                leverage_risk = min(
                    0.3 + (leverage - 1) * 0.2, 0.9
                )  # 杠杆每增加1倍，风险增加0.2，最高0.9
                risk_factors.append(f"使用了{leverage}倍杠杆，大幅增加了风险")
                recommendations.append("密切关注杠杆头寸的清算风险")
                recommendations.append("考虑减少投资金额或选择低杠杆策略")

                # 综合策略风险和杠杆风险
                strategy_risk = max(strategy_risk, leverage_risk)

            # 如果策略描述为空
            if not strategy:
                risk_factors.append("缺乏策略描述，无法准确评估风险")
                recommendations.append("在投资前了解机枪池的具体策略")
                strategy_risk = 0.6  # 信息不足，风险较高

            return {
                "score": strategy_risk,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析机枪池策略风险时出错: {e}")
            return {
                "score": 0.6,
                "risk_factors": ["策略风险分析过程中出错"],
                "recommendations": ["建议手动评估策略风险"],
            }

    def _analyze_protocol_risk(
        self, vault_data: Dict, underlying_protocols: List[str]
    ) -> Dict:
        """
        分析机枪池协议风险

        Args:
            vault_data: 机枪池数据
            underlying_protocols: 底层协议列表

        Returns:
            Dict: 协议风险分析结果
        """
        try:
            # 提取协议信息
            protocol_name = self._extract_protocol_name(vault_data)

            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            # 主流机枪池协议风险评估
            mainstream_protocols = [
                "Yearn",
                "Convex",
                "Beefy",
                "Harvest",
                "Pickle",
                "Badger",
                "Idle",
                "Alpha",
                "Vesper",
            ]

            if protocol_name in mainstream_protocols:
                protocol_risk = 0.3
                risk_factors.append(f"{protocol_name}是主流机枪池协议，相对安全")
            else:
                # 非主流协议，风险较高
                protocol_risk = 0.7
                risk_factors.append(
                    f"{protocol_name}可能是小型机枪池协议，安全性需评估"
                )
                recommendations.append(f"研究{protocol_name}的安全审计历史")
                recommendations.append("关注社区对该协议的评价")

            # 分析底层协议风险
            if underlying_protocols:
                underlying_risk = 0.0
                high_risk_protocols = []

                for up in underlying_protocols:
                    if up in mainstream_protocols:
                        underlying_risk += 0.3
                    else:
                        underlying_risk += 0.7
                        high_risk_protocols.append(up)

                avg_underlying_risk = underlying_risk / len(underlying_protocols)

                if high_risk_protocols:
                    risk_factors.append(
                        f"底层协议包含较小型协议: {', '.join(high_risk_protocols)}"
                    )
                    recommendations.append("评估底层协议的安全性")

                # 综合主协议和底层协议风险
                protocol_risk = (protocol_risk + avg_underlying_risk) / 2

                # 多协议组合风险
                if len(underlying_protocols) > 2:
                    risk_factors.append(
                        f"使用了{len(underlying_protocols)}个底层协议，增加了组合风险"
                    )
                    protocol_risk = min(
                        protocol_risk + 0.1, 0.9
                    )  # 增加组合风险，但不超过0.9
            else:
                risk_factors.append("缺乏底层协议信息，无法评估组合风险")

            # 使用AI预测器进行更深入的协议分析
            if self.ai_predictor:
                try:
                    protocol_analysis = self.ai_predictor.analyze_protocol_security(
                        protocol_name
                    )
                    if protocol_analysis:
                        # 整合AI分析结果
                        if "risk_score" in protocol_analysis:
                            ai_risk_score = protocol_analysis["risk_score"] / 100
                            # 综合基础风险和AI风险评分
                            protocol_risk = (protocol_risk + ai_risk_score) / 2

                        if "risk_factors" in protocol_analysis:
                            risk_factors.extend(protocol_analysis["risk_factors"])

                        if "recommendations" in protocol_analysis:
                            recommendations.extend(protocol_analysis["recommendations"])
                except Exception as e:
                    logger.error(f"使用AI分析协议风险时出错: {e}")

            return {
                "score": protocol_risk,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析协议风险时出错: {e}")
            return {
                "score": 0.6,
                "risk_factors": ["协议风险分析过程中出错"],
                "recommendations": ["建议手动评估协议风险"],
            }

    def _analyze_yield_risk(self, apy: float) -> Dict:
        """
        分析收益风险

        Args:
            apy: 年化收益率

        Returns:
            Dict: 收益风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            # 根据APY评估风险
            if apy <= 0:
                # 无收益信息
                risk_score = 0.5
                risk_factors.append("无法获取收益率信息，使用默认风险评估")
            elif apy <= 10:
                # 低收益，风险较低
                risk_score = 0.3
                risk_factors.append(f"APY较低({apy}%)，收益风险较低")
            elif apy <= 30:
                # 中等收益，风险中等
                risk_score = 0.5
                risk_factors.append(f"APY中等({apy}%)，收益风险中等")
                recommendations.append("关注收益率变化趋势")
            elif apy <= 100:
                # 高收益，风险较高
                risk_score = 0.7
                risk_factors.append(f"APY较高({apy}%)，收益风险较高")
                recommendations.append("高收益通常伴随高风险，建议谨慎投资")
                recommendations.append("定期检查收益来源的可持续性")
            else:
                # 超高收益，风险极高
                risk_score = 0.9
                risk_factors.append(f"APY极高({apy}%)，收益风险极高")
                recommendations.append("极高收益可能不可持续，建议极度谨慎")
                recommendations.append("限制投资金额，做好资金损失的准备")
                recommendations.append("密切关注收益率变化，及时调整策略")

            return {
                "score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析收益风险时出错: {e}")
            return {
                "score": 0.6,
                "risk_factors": ["收益风险分析过程中出错"],
                "recommendations": ["建议手动评估收益风险"],
            }

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

    def monitor_vault_risk_with_ai(self, vault_data: Dict) -> Dict:
        """
        使用AI增强的机枪池风险监测

        Args:
            vault_data: 机枪池投资数据

        Returns:
            Dict: 增强的风险分析结果，包含AI预测
        """
        # 获取基础风险分析
        base_risk = self.monitor_vault_risk(vault_data)

        # 如果没有AI预测器，直接返回基础分析
        if not self.ai_predictor:
            return base_risk

        try:
            # 提取资产信息
            asset = vault_data.get("assetsTokenList", [{}])[0].get("tokenSymbol", "")
            protocol_name = self._extract_protocol_name(vault_data)
            amount = float(vault_data.get("totalValue", 0))

            # 创建临时Position对象用于AI分析
            from risk_modules.portfolio_risk import Position

            temp_position = Position(
                protocol=protocol_name,
                asset=asset,
                amount=amount,
                invest_type=4,  # 机枪池类型
            )

            # 使用AI分析协议风险
            protocol_analysis = self.ai_predictor.analyze_protocol_risk_from_position(
                temp_position
            )
            if protocol_analysis:
                # 整合AI分析结果
                base_risk["ai_analysis"] = protocol_analysis

                # 更新风险评分
                if (
                    "ai_risk_analysis" in protocol_analysis
                    and "risk_score" in protocol_analysis["ai_risk_analysis"]
                ):
                    ai_risk_score = (
                        protocol_analysis["ai_risk_analysis"]["risk_score"] / 100
                    )
                    # 综合基础风险和AI风险评分
                    base_risk["risk_score"] = (
                        base_risk["risk_score"] + ai_risk_score
                    ) / 2

                # 添加AI建议
                if (
                    "ai_risk_analysis" in protocol_analysis
                    and "recommendations" in protocol_analysis["ai_risk_analysis"]
                ):
                    base_risk["recommendations"].extend(
                        protocol_analysis["ai_risk_analysis"]["recommendations"]
                    )

                # 添加风险因素
                if (
                    "ai_risk_analysis" in protocol_analysis
                    and "risk_factors" in protocol_analysis["ai_risk_analysis"]
                ):
                    for risk_type, risk_info in protocol_analysis["ai_risk_analysis"][
                        "risk_factors"
                    ].items():
                        if "factors" in risk_info:
                            base_risk["risk_factors"].extend(risk_info["factors"])

                # 添加监控点
                if (
                    "ai_risk_analysis" in protocol_analysis
                    and "monitoring_points" in protocol_analysis["ai_risk_analysis"]
                ):
                    base_risk["monitoring_points"].extend(
                        protocol_analysis["ai_risk_analysis"]["monitoring_points"]
                    )

            # 获取AI市场预测
            historical_data = None
            if self.blockchain_service:
                try:
                    historical_data = self.blockchain_service.get_asset_price_history(
                        asset, days=30
                    )
                except Exception as e:
                    logger.error(f"获取{asset}历史数据时出错: {e}")

            if historical_data is not None and not historical_data.empty:
                market_analysis = self.ai_predictor.analyze_market_trend(
                    historical_data=historical_data, asset=asset
                )

                if market_analysis:
                    # 添加市场分析
                    base_risk["market_analysis"] = market_analysis

                    # 更新风险因素
                    if "risk_factors" in market_analysis:
                        base_risk["risk_factors"].extend(
                            market_analysis["risk_factors"]
                        )

                    # 添加交易信号
                    if "trading_signals" in market_analysis:
                        base_risk["trading_signals"] = market_analysis[
                            "trading_signals"
                        ]

            # 去重
            base_risk["risk_factors"] = list(set(base_risk["risk_factors"]))
            base_risk["recommendations"] = list(set(base_risk["recommendations"]))
            base_risk["monitoring_points"] = list(set(base_risk["monitoring_points"]))

            return base_risk

        except Exception as e:
            logger.error(f"使用AI增强机枪池风险分析时出错: {e}")
            return base_risk
