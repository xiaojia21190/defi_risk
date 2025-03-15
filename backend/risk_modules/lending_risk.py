"""
借贷风险分析模块 - 用于分析借贷类型投资的风险
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger("defi_risk.lending_risk")


class LendingRiskAnalyzer:
    """借贷风险分析器"""

    def __init__(self, ai_predictor=None, blockchain_service=None):
        """
        初始化借贷风险分析器

        Args:
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service

    def monitor_lending_risk(self, lending_data: Dict) -> Dict:
        """
        监测借贷风险

        Args:
            lending_data: 借贷投资数据

        Returns:
            Dict: 风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_analysis = {
                "invest_type": 6,  # 借贷
                "invest_type_name": "借贷",
                "pool_name": lending_data.get("investmentName", "未知借贷池"),
                "risk_score": 0,
                "risk_level": "",
                "risk_factors": [],
                "recommendations": [],
                "monitoring_points": [],
                "detailed_risks": {},
            }

            # 提取基础信息
            assets = lending_data.get("assetsTokenList", [])
            total_value = float(lending_data.get("totalValue", "0"))
            protocol_name = self._extract_protocol_name(lending_data)

            # 提取借贷特有信息
            collateral_ratio = lending_data.get("collateralRatio", 0)  # 抵押率
            liquidation_threshold = lending_data.get(
                "liquidationThreshold", 0
            )  # 清算阈值
            borrow_apy = lending_data.get("borrowApy", 0)  # 借款利率
            supply_apy = lending_data.get("supplyApy", 0)  # 存款利率
            is_borrowing = lending_data.get("isBorrowing", False)  # 是否为借款

            if not assets:
                risk_analysis["risk_factors"].append("无法获取资产信息，风险评估不完整")
                risk_analysis["risk_score"] = 0.7  # 信息不完整，默认较高风险
                risk_analysis["risk_level"] = "HIGH"
                return risk_analysis

            # 1. 资产风险分析
            asset_risk = self._analyze_lending_asset_risk(assets, is_borrowing)
            risk_analysis["detailed_risks"]["asset_risk"] = asset_risk
            risk_analysis["risk_factors"].extend(asset_risk["risk_factors"])
            risk_analysis["recommendations"].extend(asset_risk["recommendations"])

            # 2. 抵押率风险分析（如果是借款）
            if is_borrowing and collateral_ratio > 0:
                collateral_risk = self._analyze_collateral_risk(
                    collateral_ratio, liquidation_threshold
                )
                risk_analysis["detailed_risks"]["collateral_risk"] = collateral_risk
                risk_analysis["risk_factors"].extend(collateral_risk["risk_factors"])
                risk_analysis["recommendations"].extend(
                    collateral_risk["recommendations"]
                )

            # 3. 利率风险分析
            interest_risk = self._analyze_interest_risk(
                borrow_apy, supply_apy, is_borrowing
            )
            risk_analysis["detailed_risks"]["interest_risk"] = interest_risk
            risk_analysis["risk_factors"].extend(interest_risk["risk_factors"])
            risk_analysis["recommendations"].extend(interest_risk["recommendations"])

            # 4. 协议安全风险分析
            protocol_risk = self._analyze_protocol_risk(lending_data)
            risk_analysis["detailed_risks"]["protocol_risk"] = protocol_risk
            risk_analysis["risk_factors"].extend(protocol_risk["risk_factors"])
            risk_analysis["recommendations"].extend(protocol_risk["recommendations"])

            # 5. 智能合约风险分析
            contract_risk = {
                "score": 0.3,  # 借贷合约通常风险中等
                "risk_factors": [
                    "借贷智能合约固有风险",
                    "清算机制可能存在延迟或错误",
                ],
                "recommendations": [
                    "关注协议安全审计状态",
                    "了解清算机制和条件",
                    "关注社区对该借贷项目的评价",
                ],
            }
            risk_analysis["detailed_risks"]["contract_risk"] = contract_risk
            risk_analysis["risk_factors"].extend(contract_risk["risk_factors"])
            risk_analysis["recommendations"].extend(contract_risk["recommendations"])

            # 计算综合风险分数（加权平均）
            weights = {}
            if is_borrowing:
                weights = {
                    "asset_risk": 0.2,
                    "collateral_risk": 0.3,
                    "interest_risk": 0.2,
                    "protocol_risk": 0.15,
                    "contract_risk": 0.15,
                }
            else:
                weights = {
                    "asset_risk": 0.3,
                    "interest_risk": 0.2,
                    "protocol_risk": 0.25,
                    "contract_risk": 0.25,
                }

            # 计算总风险分数
            total_score = 0
            for risk_type, weight in weights.items():
                if risk_type in risk_analysis["detailed_risks"]:
                    total_score += (
                        risk_analysis["detailed_risks"][risk_type]["score"] * weight
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
            if is_borrowing:
                risk_analysis["monitoring_points"] = [
                    "抵押资产价格变化",
                    "抵押率变化",
                    "清算阈值距离",
                    "借款利率变化",
                    "协议治理变更",
                ]
            else:
                risk_analysis["monitoring_points"] = [
                    "存款资产价格变化",
                    "存款利率变化",
                    "协议总借款量变化",
                    "协议治理变更",
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
            logger.error(f"监测借贷风险时出错: {e}")
            return {
                "invest_type": 6,
                "invest_type_name": "借贷",
                "pool_name": lending_data.get("investmentName", "未知借贷池"),
                "risk_score": 0.5,  # 出错时默认中等风险
                "risk_level": "MEDIUM",
                "risk_factors": ["风险分析过程中出错"],
                "recommendations": ["建议手动评估风险"],
                "monitoring_points": ["系统错误修复状态"],
                "error": str(e),
            }

    def _analyze_lending_asset_risk(
        self, assets: List[Dict], is_borrowing: bool
    ) -> Dict:
        """
        分析借贷资产风险

        Args:
            assets: 资产列表
            is_borrowing: 是否为借款

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
                    asset_risk = 0.4 if is_borrowing else 0.2
                    if is_borrowing:
                        risk_factors.append(
                            f"{token_symbol}价格波动较大，作为抵押品存在清算风险"
                        )
                        recommendations.append(
                            f"保持较高的抵押率，避免{token_symbol}价格下跌导致清算"
                        )
                    else:
                        risk_factors.append(f"{token_symbol}作为存款资产，风险较低")
                elif token_symbol in ["USDC", "USDT", "DAI"]:
                    # 稳定币，风险较低
                    asset_risk = 0.1
                    if is_borrowing:
                        risk_factors.append(
                            f"{token_symbol}是稳定币，作为借款资产风险较低"
                        )
                    else:
                        risk_factors.append(
                            f"{token_symbol}是稳定币，作为存款资产风险极低"
                        )
                else:
                    # 其他资产，风险较高
                    asset_risk = 0.7 if is_borrowing else 0.5
                    if is_borrowing:
                        risk_factors.append(
                            f"{token_symbol}可能是小市值代币，作为抵押品风险极高"
                        )
                        recommendations.append(
                            f"谨慎使用{token_symbol}作为抵押品，保持极高的抵押率"
                        )
                    else:
                        risk_factors.append(
                            f"{token_symbol}可能是小市值代币，作为存款资产风险较高"
                        )
                        recommendations.append(
                            f"密切关注{token_symbol}的价格波动和协议状态"
                        )

                # 累加风险评分
                risk_score += asset_risk

            # 计算平均风险评分
            avg_risk_score = risk_score / len(assets) if assets else 0.5

            # 根据风险评分生成建议
            if is_borrowing:
                if avg_risk_score > 0.5:
                    recommendations.append("建议使用更稳定的资产作为抵押品")
                    recommendations.append("保持较高的抵押率，避免清算风险")
                elif avg_risk_score > 0.3:
                    recommendations.append("定期监控抵押率，避免接近清算阈值")
            else:
                if avg_risk_score > 0.5:
                    recommendations.append("建议减少高风险资产的存款比例")
                    recommendations.append("分散存款到多个协议，降低单一协议风险")
                elif avg_risk_score > 0.3:
                    recommendations.append("保持对资产价格和协议状态的关注")

            return {
                "score": avg_risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析借贷资产风险时出错: {e}")
            return {
                "score": 0.5,
                "risk_factors": ["资产风险分析过程中出错"],
                "recommendations": ["建议手动评估资产风险"],
            }

    def _analyze_collateral_risk(
        self, collateral_ratio: float, liquidation_threshold: float
    ) -> Dict:
        """
        分析抵押率风险

        Args:
            collateral_ratio: 当前抵押率
            liquidation_threshold: 清算阈值

        Returns:
            Dict: 抵押率风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            # 计算清算安全距离
            if liquidation_threshold > 0:
                safety_margin = collateral_ratio - liquidation_threshold
                safety_percentage = (safety_margin / liquidation_threshold) * 100
            else:
                safety_margin = 0
                safety_percentage = 0

            # 根据抵押率和安全距离评估风险
            if collateral_ratio <= 0:
                # 无抵押率信息
                risk_score = 0.7
                risk_factors.append("无法获取抵押率信息，无法评估清算风险")
                recommendations.append("手动检查抵押率和清算阈值")
            elif safety_margin <= 0:
                # 已经低于清算阈值
                risk_score = 1.0
                risk_factors.append("当前抵押率已低于清算阈值，面临立即清算风险")
                recommendations.append("立即增加抵押品或偿还部分借款")
            elif safety_percentage < 10:
                # 极高风险，接近清算
                risk_score = 0.9
                risk_factors.append(
                    f"抵押率({collateral_ratio:.2f}%)接近清算阈值({liquidation_threshold:.2f}%)，清算风险极高"
                )
                recommendations.append("尽快增加抵押品或偿还部分借款")
                recommendations.append("设置价格预警，密切关注抵押品价格变化")
            elif safety_percentage < 20:
                # 高风险
                risk_score = 0.7
                risk_factors.append(
                    f"抵押率({collateral_ratio:.2f}%)与清算阈值({liquidation_threshold:.2f}%)较近，清算风险较高"
                )
                recommendations.append("考虑增加抵押品或偿还部分借款")
                recommendations.append("密切关注抵押品价格变化")
            elif safety_percentage < 50:
                # 中等风险
                risk_score = 0.4
                risk_factors.append(
                    f"抵押率({collateral_ratio:.2f}%)高于清算阈值({liquidation_threshold:.2f}%)，清算风险中等"
                )
                recommendations.append("定期检查抵押率变化")
            else:
                # 低风险
                risk_score = 0.2
                risk_factors.append(
                    f"抵押率({collateral_ratio:.2f}%)远高于清算阈值({liquidation_threshold:.2f}%)，清算风险较低"
                )
                recommendations.append("保持当前抵押率，定期检查")

            return {
                "score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析抵押率风险时出错: {e}")
            return {
                "score": 0.6,
                "risk_factors": ["抵押率风险分析过程中出错"],
                "recommendations": ["建议手动评估抵押率风险"],
            }

    def _analyze_interest_risk(
        self, borrow_apy: float, supply_apy: float, is_borrowing: bool
    ) -> Dict:
        """
        分析利率风险

        Args:
            borrow_apy: 借款年利率
            supply_apy: 存款年利率
            is_borrowing: 是否为借款

        Returns:
            Dict: 利率风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            if is_borrowing:
                # 分析借款利率风险
                if borrow_apy <= 0:
                    risk_score = 0.3
                    risk_factors.append("无法获取借款利率信息，使用默认风险评估")
                elif borrow_apy <= 3:
                    risk_score = 0.2
                    risk_factors.append(
                        f"借款利率较低({borrow_apy:.2f}%)，利率风险较低"
                    )
                elif borrow_apy <= 8:
                    risk_score = 0.4
                    risk_factors.append(
                        f"借款利率中等({borrow_apy:.2f}%)，利率风险中等"
                    )
                    recommendations.append(
                        "关注利率变化趋势，考虑在利率上升前偿还部分借款"
                    )
                elif borrow_apy <= 15:
                    risk_score = 0.6
                    risk_factors.append(
                        f"借款利率较高({borrow_apy:.2f}%)，利率风险较高"
                    )
                    recommendations.append("考虑寻找利率更低的借款平台")
                    recommendations.append("制定还款计划，避免长期高利率借款")
                else:
                    risk_score = 0.8
                    risk_factors.append(
                        f"借款利率极高({borrow_apy:.2f}%)，利率风险极高"
                    )
                    recommendations.append("尽快偿还部分或全部借款")
                    recommendations.append("评估高利率借款的必要性")
            else:
                # 分析存款利率风险
                if supply_apy <= 0:
                    risk_score = 0.3
                    risk_factors.append("无法获取存款利率信息，使用默认风险评估")
                elif supply_apy <= 2:
                    risk_score = 0.2
                    risk_factors.append(
                        f"存款利率较低({supply_apy:.2f}%)，收益有限但风险较低"
                    )
                    recommendations.append("考虑探索收益更高的存款选项")
                elif supply_apy <= 8:
                    risk_score = 0.3
                    risk_factors.append(
                        f"存款利率中等({supply_apy:.2f}%)，收益与风险平衡"
                    )
                elif supply_apy <= 15:
                    risk_score = 0.5
                    risk_factors.append(
                        f"存款利率较高({supply_apy:.2f}%)，可能存在潜在风险"
                    )
                    recommendations.append("研究高利率背后的原因，评估协议安全性")
                else:
                    risk_score = 0.7
                    risk_factors.append(
                        f"存款利率极高({supply_apy:.2f}%)，可能存在重大风险"
                    )
                    recommendations.append("谨慎评估高利率背后的风险因素")
                    recommendations.append("考虑减少存款金额或分散到多个协议")

            return {
                "score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析利率风险时出错: {e}")
            return {
                "score": 0.4,
                "risk_factors": ["利率风险分析过程中出错"],
                "recommendations": ["建议手动评估利率风险"],
            }

    def _analyze_protocol_risk(self, lending_data: Dict) -> Dict:
        """
        分析协议风险

        Args:
            lending_data: 借贷数据

        Returns:
            Dict: 协议风险分析结果
        """
        try:
            # 提取协议信息
            protocol_name = self._extract_protocol_name(lending_data)

            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            # 主流借贷协议风险评估
            mainstream_protocols = [
                "Aave",
                "Compound",
                "MakerDAO",
                "Curve",
                "dYdX",
                "Euler",
                "JustLend",
                "Venus",
                "Benqi",
            ]

            if protocol_name in mainstream_protocols:
                risk_score = 0.2
                risk_factors.append(f"{protocol_name}是主流借贷协议，安全性较高")
            else:
                # 非主流协议，风险较高
                risk_score = 0.6
                risk_factors.append(f"{protocol_name}可能是小型借贷协议，安全性需评估")
                recommendations.append(f"研究{protocol_name}的安全审计历史")
                recommendations.append("关注社区对该协议的评价")

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
                            risk_score = (risk_score + ai_risk_score) / 2

                        if "risk_factors" in protocol_analysis:
                            risk_factors.extend(protocol_analysis["risk_factors"])

                        if "recommendations" in protocol_analysis:
                            recommendations.extend(protocol_analysis["recommendations"])
                except Exception as e:
                    logger.error(f"使用AI分析协议风险时出错: {e}")

            return {
                "score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析协议风险时出错: {e}")
            return {
                "score": 0.5,
                "risk_factors": ["协议风险分析过程中出错"],
                "recommendations": ["建议手动评估协议风险"],
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

    def monitor_lending_risk_with_ai(self, lending_data: Dict) -> Dict:
        """
        使用AI增强的借贷风险监测

        Args:
            lending_data: 借贷投资数据

        Returns:
            Dict: 增强的风险分析结果，包含AI预测
        """
        # 获取基础风险分析
        base_risk = self.monitor_lending_risk(lending_data)

        # 如果没有AI预测器，直接返回基础分析
        if not self.ai_predictor:
            return base_risk

        try:
            # 提取资产信息
            asset = lending_data.get("assetsTokenList", [{}])[0].get("tokenSymbol", "")
            protocol_name = self._extract_protocol_name(lending_data)
            amount = float(lending_data.get("totalValue", 0))
            is_borrowing = lending_data.get("isBorrowing", False)

            # 创建临时Position对象用于AI分析
            from risk_modules.portfolio_risk import Position

            temp_position = Position(
                protocol=protocol_name,
                asset=asset,
                amount=amount,
                invest_type=6,  # 借贷类型
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
            logger.error(f"使用AI增强借贷风险分析时出错: {e}")
            return base_risk
