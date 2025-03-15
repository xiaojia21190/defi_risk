"""
质押风险分析模块 - 用于分析质押类型投资的风险
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger("defi_risk.staking_risk")


class StakingRiskAnalyzer:
    """质押风险分析器"""

    def __init__(self, ai_predictor=None, blockchain_service=None):
        """
        初始化质押风险分析器

        Args:
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service

    def monitor_staking_risk(self, staking_data: Dict) -> Dict:
        """
        监测质押风险

        Args:
            staking_data: 质押投资数据

        Returns:
            Dict: 风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_analysis = {
                "invest_type": 5,  # 质押
                "invest_type_name": "质押",
                "pool_name": staking_data.get("investmentName", "未知质押池"),
                "risk_score": 0,
                "risk_level": "",
                "risk_factors": [],
                "recommendations": [],
                "monitoring_points": [],
                "detailed_risks": {},
            }

            # 提取基础信息
            assets = staking_data.get("assetsTokenList", [])
            total_value = float(staking_data.get("totalValue", "0"))
            protocol_name = self._extract_protocol_name(staking_data)

            if not assets:
                risk_analysis["risk_factors"].append("无法获取资产信息，风险评估不完整")
                risk_analysis["risk_score"] = 0.7  # 信息不完整，默认较高风险
                risk_analysis["risk_level"] = "HIGH"
                return risk_analysis

            # 1. 资产风险分析
            asset_risk = self._analyze_staking_asset_risk(assets)
            risk_analysis["detailed_risks"]["asset_risk"] = asset_risk
            risk_analysis["risk_factors"].extend(asset_risk["risk_factors"])
            risk_analysis["recommendations"].extend(asset_risk["recommendations"])

            # 2. 锁定期风险分析
            lock_risk = self._analyze_lock_period_risk(staking_data)
            risk_analysis["detailed_risks"]["lock_risk"] = lock_risk
            risk_analysis["risk_factors"].extend(lock_risk["risk_factors"])
            risk_analysis["recommendations"].extend(lock_risk["recommendations"])

            # 3. 协议安全风险分析
            protocol_risk = self._analyze_protocol_risk(staking_data)
            risk_analysis["detailed_risks"]["protocol_risk"] = protocol_risk
            risk_analysis["risk_factors"].extend(protocol_risk["risk_factors"])
            risk_analysis["recommendations"].extend(protocol_risk["recommendations"])

            # 4. 收益风险分析
            yield_risk = self._analyze_yield_risk(staking_data)
            risk_analysis["detailed_risks"]["yield_risk"] = yield_risk
            risk_analysis["risk_factors"].extend(yield_risk["risk_factors"])
            risk_analysis["recommendations"].extend(yield_risk["recommendations"])

            # 5. 智能合约风险分析
            contract_risk = {
                "score": 0.3,  # 质押合约通常风险中等
                "risk_factors": [
                    "质押智能合约固有风险",
                    "解质押机制可能存在延迟或限制",
                ],
                "recommendations": [
                    "关注协议安全审计状态",
                    "了解解质押机制和条件",
                    "关注社区对该质押项目的评价",
                ],
            }
            risk_analysis["detailed_risks"]["contract_risk"] = contract_risk
            risk_analysis["risk_factors"].extend(contract_risk["risk_factors"])
            risk_analysis["recommendations"].extend(contract_risk["recommendations"])

            # 计算综合风险分数（加权平均）
            weights = {
                "asset_risk": 0.25,
                "lock_risk": 0.25,
                "protocol_risk": 0.2,
                "yield_risk": 0.15,
                "contract_risk": 0.15,
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
                "质押资产价格变化",
                "质押APY变化趋势",
                "解质押条件变更",
                "协议治理变更",
                "锁定期变更",
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
            logger.error(f"监测质押风险时出错: {e}")
            return {
                "invest_type": 5,
                "invest_type_name": "质押",
                "pool_name": staking_data.get("investmentName", "未知质押池"),
                "risk_score": 0.5,  # 出错时默认中等风险
                "risk_level": "MEDIUM",
                "risk_factors": ["风险分析过程中出错"],
                "recommendations": ["建议手动评估风险"],
                "monitoring_points": ["系统错误修复状态"],
                "error": str(e),
            }

    def _analyze_staking_asset_risk(self, assets: List[Dict]) -> Dict:
        """
        分析质押资产风险

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
                    # 主流资产，风险较低
                    asset_risk = 0.2
                    if token_symbol in ["ETH", "WETH"]:
                        risk_factors.append(f"{token_symbol}质押通常风险较低")
                    else:
                        risk_factors.append(f"{token_symbol}质押通常风险较低")
                elif token_symbol in ["USDC", "USDT", "DAI"]:
                    # 稳定币，风险较低
                    asset_risk = 0.1
                    risk_factors.append(f"{token_symbol}是稳定币，质押风险较低")
                else:
                    # 其他资产，风险较高
                    asset_risk = 0.6
                    risk_factors.append(f"{token_symbol}可能是小市值代币，质押风险较高")
                    recommendations.append(f"密切关注{token_symbol}的价格波动")

                # 累加风险评分
                risk_score += asset_risk

            # 计算平均风险评分
            avg_risk_score = risk_score / len(assets) if assets else 0.5

            # 根据风险评分生成建议
            if avg_risk_score > 0.5:
                recommendations.append("建议减少高风险资产的质押比例")
                recommendations.append("设置价格预警，及时关注资产价格变化")
            elif avg_risk_score > 0.3:
                recommendations.append("保持对资产价格的关注")
            else:
                recommendations.append("当前质押资产风险较低，可以继续持有")

            return {
                "score": avg_risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析质押资产风险时出错: {e}")
            return {
                "score": 0.5,
                "risk_factors": ["资产风险分析过程中出错"],
                "recommendations": ["建议手动评估资产风险"],
            }

    def _analyze_lock_period_risk(self, staking_data: Dict) -> Dict:
        """
        分析锁定期风险

        Args:
            staking_data: 质押数据

        Returns:
            Dict: 锁定期风险分析结果
        """
        try:
            # 提取锁定期信息
            lock_period = staking_data.get("lockPeriod", 0)  # 锁定期（天）
            lock_end_time = staking_data.get("lockEndTime", None)  # 锁定结束时间

            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            # 根据锁定期评估风险
            if lock_period == 0 or not lock_period:
                # 无锁定期
                risk_score = 0.1
                risk_factors.append("无锁定期，可随时解质押，流动性风险低")
            elif lock_period <= 7:
                # 短期锁定
                risk_score = 0.2
                risk_factors.append(f"短期锁定（{lock_period}天），流动性风险较低")
            elif lock_period <= 30:
                # 中期锁定
                risk_score = 0.4
                risk_factors.append(f"中期锁定（{lock_period}天），存在一定流动性风险")
                recommendations.append("确保有足够的流动资金应对短期需求")
            elif lock_period <= 90:
                # 长期锁定
                risk_score = 0.6
                risk_factors.append(f"长期锁定（{lock_period}天），流动性风险较高")
                recommendations.append("确保有足够的流动资金应对中长期需求")
                recommendations.append("考虑分批质押，避免所有资金同时锁定")
            else:
                # 超长期锁定
                risk_score = 0.8
                risk_factors.append(f"超长期锁定（{lock_period}天），流动性风险极高")
                recommendations.append("仅使用长期闲置资金进行质押")
                recommendations.append("确保有其他流动性来源应对紧急需求")

            # 添加锁定期相关建议
            if lock_period > 0:
                recommendations.append("记录锁定结束时间，提前规划资金使用")
                if lock_end_time:
                    recommendations.append(f"锁定将于{lock_end_time}结束，请提前规划")

            return {
                "score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析锁定期风险时出错: {e}")
            return {
                "score": 0.5,
                "risk_factors": ["锁定期风险分析过程中出错"],
                "recommendations": ["建议手动评估锁定期风险"],
            }

    def _analyze_protocol_risk(self, staking_data: Dict) -> Dict:
        """
        分析协议风险

        Args:
            staking_data: 质押数据

        Returns:
            Dict: 协议风险分析结果
        """
        try:
            # 提取协议信息
            protocol_name = self._extract_protocol_name(staking_data)

            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            # 主流协议风险评估
            mainstream_protocols = [
                "Lido",
                "Rocket Pool",
                "Coinbase",
                "Binance",
                "Kraken",
                "Ethereum",
                "Polkadot",
                "Cosmos",
                "Solana",
            ]

            if protocol_name in mainstream_protocols:
                risk_score = 0.2
                risk_factors.append(f"{protocol_name}是主流质押协议，安全性较高")
            else:
                # 非主流协议，风险较高
                risk_score = 0.6
                risk_factors.append(f"{protocol_name}可能是小型质押协议，安全性需评估")
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

    def _analyze_yield_risk(self, staking_data: Dict) -> Dict:
        """
        分析收益风险

        Args:
            staking_data: 质押数据

        Returns:
            Dict: 收益风险分析结果
        """
        try:
            # 提取收益信息
            apy = float(staking_data.get("apy", "0"))
            reward_token = staking_data.get("rewardTokenSymbol", "")

            # 初始化风险分析结果
            risk_factors = []
            recommendations = []

            # 根据APY评估风险
            if apy <= 5:
                # 低收益，风险较低
                risk_score = 0.2
                risk_factors.append(f"APY较低({apy}%)，收益风险较低")
            elif apy <= 15:
                # 中等收益，风险中等
                risk_score = 0.4
                risk_factors.append(f"APY中等({apy}%)，收益风险中等")
            elif apy <= 30:
                # 高收益，风险较高
                risk_score = 0.6
                risk_factors.append(f"APY较高({apy}%)，收益风险较高")
                recommendations.append("高收益通常伴随高风险，建议谨慎投资")
            else:
                # 超高收益，风险极高
                risk_score = 0.8
                risk_factors.append(f"APY极高({apy}%)，收益风险极高")
                recommendations.append("极高收益可能不可持续，建议谨慎投资")
                recommendations.append("考虑分散投资，降低单一项目风险")

            # 分析奖励代币风险
            if reward_token:
                if reward_token in [
                    "ETH",
                    "WETH",
                    "BTC",
                    "WBTC",
                    "USDC",
                    "USDT",
                    "DAI",
                ]:
                    # 主流代币奖励，风险较低
                    risk_factors.append(f"奖励代币{reward_token}是主流代币，风险较低")
                else:
                    # 非主流代币奖励，风险较高
                    risk_score = min(risk_score + 0.2, 1.0)  # 增加风险，但不超过1
                    risk_factors.append(
                        f"奖励代币{reward_token}可能是小市值代币，存在价格波动风险"
                    )
                    recommendations.append(f"关注{reward_token}的价格走势和流动性")
                    recommendations.append("考虑定期将奖励兑换为主流代币")

            return {
                "score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"分析收益风险时出错: {e}")
            return {
                "score": 0.5,
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

    def monitor_staking_risk_with_ai(self, staking_data: Dict) -> Dict:
        """
        使用AI增强的质押风险监测

        Args:
            staking_data: 质押投资数据

        Returns:
            Dict: 增强的风险分析结果，包含AI预测
        """
        # 获取基础风险分析
        base_risk = self.monitor_staking_risk(staking_data)

        # 如果没有AI预测器，直接返回基础分析
        if not self.ai_predictor:
            return base_risk

        try:
            # 提取资产信息
            asset = staking_data.get("assetsTokenList", [{}])[0].get("tokenSymbol", "")
            protocol_name = self._extract_protocol_name(staking_data)
            amount = float(staking_data.get("totalValue", 0))

            # 创建临时Position对象用于AI分析
            from risk_modules.portfolio_risk import Position

            temp_position = Position(
                protocol=protocol_name,
                asset=asset,
                amount=amount,
                invest_type=5,  # 质押类型
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
            logger.error(f"使用AI增强质押风险分析时出错: {e}")
            return base_risk
