"""
流动性风险分析模块 - 用于分析DeFi投资组合的流动性风险
"""

from typing import Dict, List, Any, Optional
import logging
from app.models.domain.risk import RiskFactor, RiskType, RiskAnalysisResult
from app.risk_modules.base import RiskAnalyzerBase


class LiquidityRiskAnalyzer(RiskAnalyzerBase):
    """流动性风险分析器"""

    async def analyze(self, data: Dict[str, Any]) -> RiskAnalysisResult:
        """
        分析流动性风险

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        self.logger.info("开始分析流动性风险")

        try:
            # 获取风险因子
            risk_factors = await self.get_risk_factors(data)

            # 如果没有收集到任何风险因素，返回默认风险分析结果
            if not risk_factors:
                self.logger.warning("未能收集到任何流动性风险因素")
                return RiskAnalysisResult(
                    risk_type=RiskType.LIQUIDITY.value,
                    target="投资组合",
                    score=50,  # 默认中等风险
                    factors=[],
                    recommendations=[],
                    monitoring_points=[],
                )

            # 计算总体风险评分（加权平均）
            total_weight = sum(factor.weight for factor in risk_factors)
            if total_weight > 0:
                weighted_score = (
                    sum(factor.score * factor.weight for factor in risk_factors)
                    / total_weight
                )
            else:
                weighted_score = 50  # 默认中等风险

            # 确保评分在0-100范围内
            weighted_score = max(0, min(100, weighted_score))

            # 生成建议和监控点
            recommendations = await self.get_recommendations(risk_factors)
            monitoring_points = await self.get_monitoring_points(risk_factors)

            # 创建风险分析结果
            result = RiskAnalysisResult(
                risk_type=RiskType.LIQUIDITY.value,
                target="投资组合流动性",
                score=weighted_score,
                factors=risk_factors,
                recommendations=recommendations,
                monitoring_points=monitoring_points,
            )

            self.logger.info(f"完成流动性风险分析，总体风险评分: {weighted_score:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"分析流动性风险时出错: {str(e)}")
            # 返回默认风险分析结果
            return RiskAnalysisResult(
                risk_type=RiskType.LIQUIDITY.value,
                target="投资组合",
                score=50,  # 默认中等风险
                factors=[],
                recommendations=[
                    "无法完成流动性风险分析，请检查输入数据是否正确",
                    "确保区块链服务正常运行",
                    "尝试稍后再次分析",
                ],
                monitoring_points=[
                    "监控系统日志以排查风险分析失败的原因",
                ],
            )

    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取流动性风险因子

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

        # 分析资产流动性风险
        asset_liquidity_risk = await self._analyze_asset_liquidity(positions)
        if asset_liquidity_risk:
            risk_factors.append(asset_liquidity_risk)

        # 分析协议流动性风险
        protocol_liquidity_risk = await self._analyze_protocol_liquidity(positions)
        if protocol_liquidity_risk:
            risk_factors.append(protocol_liquidity_risk)

        # 分析投资类型流动性风险
        investment_type_liquidity_risk = await self._analyze_investment_type_liquidity(
            positions
        )
        if investment_type_liquidity_risk:
            risk_factors.append(investment_type_liquidity_risk)

        # 分析流动性池风险
        liquidity_pool_risk = await self._analyze_liquidity_pool_risk(positions)
        if liquidity_pool_risk:
            risk_factors.append(liquidity_pool_risk)

        return risk_factors

    async def _analyze_asset_liquidity(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析资产流动性风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取资产流动性数据")
                return None

            # 计算总价值
            total_value = sum(pos.get("amount", 0) for pos in positions)
            if total_value == 0:
                return None

            # 提取资产列表和权重
            assets = {}
            for pos in positions:
                # 尝试从tokenList获取更精确的代币信息
                if pos.get("tokenList"):
                    for token in pos.get("tokenList", []):
                        token_symbol = token.get("tokenSymbol", "")
                        if token_symbol:
                            if token_symbol not in assets:
                                assets[token_symbol] = 0
                            # 使用代币在池中的比例分配价值
                            token_value = pos.get("amount", 0) * (
                                1 / len(pos.get("tokenList", []))
                            )
                            assets[token_symbol] += token_value
                else:
                    # 如果没有tokenList，使用资产名称
                    asset = pos.get("asset", "Unknown").split("/")[
                        0
                    ]  # 处理流动性池资产格式
                    if asset not in assets:
                        assets[asset] = 0
                    assets[asset] += pos.get("amount", 0)

            # 尝试使用AI服务进行资产流动性分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "assets": list(assets.keys()),
                        "weights": {
                            asset: (value / total_value)
                            for asset, value in assets.items()
                        },
                        "analysis_type": "asset_liquidity",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="asset_liquidity", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get("description", "资产流动性分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.LIQUIDITY.value,
                            factor_name="资产流动性风险",
                            score=risk_score,
                            weight=0.4,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "assets": assets,
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析资产流动性风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 如果AI分析失败或不可用，使用区块链服务获取流动性数据
            assets_data = []
            weighted_liquidity_score = 0

            for asset, amount in assets.items():
                # 尝试从区块链服务获取资产流动性数据
                liquidity_data = await self.blockchain_service.get_asset_liquidity(
                    asset
                )

                # 如果获取到流动性数据，使用它计算风险评分
                if liquidity_data:
                    # 根据交易量、市值等因素计算流动性评分
                    volume_24h = liquidity_data.get("volume_24h", 0)
                    market_cap = liquidity_data.get("market_cap", 0)

                    # 流动性评分计算 (0-100，越高风险越大)
                    if market_cap > 0 and volume_24h > 0:
                        # 交易量/市值比率，越高流动性越好
                        volume_to_mcap = volume_24h / market_cap
                        if volume_to_mcap > 0.2:
                            liquidity_score = 20  # 高流动性，低风险
                        elif volume_to_mcap > 0.1:
                            liquidity_score = 40  # 中高流动性
                        elif volume_to_mcap > 0.05:
                            liquidity_score = 60  # 中等流动性
                        else:
                            liquidity_score = 80  # 低流动性，高风险
                    else:
                        liquidity_score = 80  # 数据不足，假设高风险
                else:
                    # 如果没有获取到数据，使用默认评分
                    # 主流代币流动性较高，风险较低
                    if asset.upper() in ["BTC", "ETH", "USDT", "USDC", "BNB", "DAI"]:
                        liquidity_score = 20  # 低风险
                    elif asset.upper() in [
                        "LINK",
                        "UNI",
                        "AAVE",
                        "MATIC",
                        "SOL",
                        "DOT",
                    ]:
                        liquidity_score = 40  # 中低风险
                    else:
                        liquidity_score = 70  # 默认高风险

                # 计算加权评分
                weight = amount / total_value
                weighted_liquidity_score += liquidity_score * weight

                assets_data.append(
                    {
                        "asset": asset,
                        "amount": amount,
                        "liquidity_score": liquidity_score,
                        "weight": weight,
                        "liquidity_data": liquidity_data,
                    }
                )

            # 根据加权评分生成描述
            if weighted_liquidity_score > 70:
                description = "投资组合中包含大量低流动性资产，可能面临流动性风险"
                trend = "上升"
            elif weighted_liquidity_score > 50:
                description = "投资组合中包含一定比例的低流动性资产，流动性风险中等"
                trend = "稳定"
            elif weighted_liquidity_score > 30:
                description = "投资组合中大部分为高流动性资产，流动性风险较低"
                trend = "稳定"
            else:
                description = "投资组合中几乎全部为高流动性资产，流动性风险低"
                trend = "下降"

            return self.create_risk_factor(
                risk_type=RiskType.LIQUIDITY.value,
                factor_name="资产流动性风险",
                score=weighted_liquidity_score,
                weight=0.4,
                description=description,
                trend=trend,
                data_points=assets_data,
                metadata={"assets": assets},
            )
        except Exception as e:
            self.logger.error(f"分析资产流动性风险时出错: {str(e)}")
            return None

    async def _analyze_protocol_liquidity(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析协议流动性风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取协议流动性数据")
                return None

            # 按协议分组
            protocol_values = {}
            for pos in positions:
                protocol = pos.get("protocol", "Unknown")
                amount = pos.get("amount", 0)

                if protocol not in protocol_values:
                    protocol_values[protocol] = 0
                protocol_values[protocol] += amount

            # 计算总价值
            total_value = sum(protocol_values.values())
            if total_value == 0:
                return None

            # 尝试使用AI服务进行协议流动性分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "protocols": list(protocol_values.keys()),
                        "weights": {
                            protocol: (value / total_value)
                            for protocol, value in protocol_values.items()
                        },
                        "analysis_type": "protocol_liquidity",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="protocol_liquidity", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get("description", "协议流动性分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.LIQUIDITY.value,
                            factor_name="协议流动性风险",
                            score=risk_score,
                            weight=0.3,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "protocols": protocol_values,
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析协议流动性风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 如果AI分析失败或不可用，使用区块链服务获取协议流动性数据
            protocols_data = []
            weighted_protocol_liquidity_score = 0

            for protocol, amount in protocol_values.items():
                # 尝试从区块链服务获取协议流动性数据
                protocol_data = await self.blockchain_service.get_protocol_data(
                    protocol
                )

                # 如果获取到协议数据，使用它计算风险评分
                if protocol_data:
                    # 根据TVL、交易量等因素计算流动性评分
                    tvl = protocol_data.get("tvl", 0)
                    volume_24h = protocol_data.get("volume_24h", 0)

                    # 流动性评分计算 (0-100，越高风险越大)
                    if tvl > 0:
                        if tvl > 1000000000:  # > 10亿美元
                            liquidity_score = 20  # 高流动性，低风险
                        elif tvl > 100000000:  # > 1亿美元
                            liquidity_score = 40  # 中高流动性
                        elif tvl > 10000000:  # > 1000万美元
                            liquidity_score = 60  # 中等流动性
                        else:
                            liquidity_score = 80  # 低流动性，高风险
                    else:
                        liquidity_score = 70  # 数据不足，假设高风险
                else:
                    # 如果没有获取到数据，使用默认评分
                    # 主流协议流动性较高，风险较低
                    if protocol.lower() in [
                        "aave",
                        "compound",
                        "uniswap",
                        "curve",
                        "makerdao",
                    ]:
                        liquidity_score = 20  # 低风险
                    elif protocol.lower() in [
                        "sushiswap",
                        "balancer",
                        "yearn",
                        "pancakeswap",
                    ]:
                        liquidity_score = 40  # 中低风险
                    else:
                        liquidity_score = 60  # 默认中高风险

                # 计算加权评分
                weight = amount / total_value
                weighted_protocol_liquidity_score += liquidity_score * weight

                protocols_data.append(
                    {
                        "protocol": protocol,
                        "amount": amount,
                        "liquidity_score": liquidity_score,
                        "weight": weight,
                        "protocol_data": protocol_data,
                    }
                )

            # 根据加权评分生成描述
            if weighted_protocol_liquidity_score > 70:
                description = "投资组合中使用的协议流动性风险较高"
                trend = "上升"
            elif weighted_protocol_liquidity_score > 50:
                description = "投资组合中使用的协议流动性风险中等"
                trend = "稳定"
            elif weighted_protocol_liquidity_score > 30:
                description = "投资组合中使用的协议流动性风险较低"
                trend = "稳定"
            else:
                description = "投资组合中使用的协议流动性风险低"
                trend = "下降"

            return self.create_risk_factor(
                risk_type=RiskType.LIQUIDITY.value,
                factor_name="协议流动性风险",
                score=weighted_protocol_liquidity_score,
                weight=0.3,
                description=description,
                trend=trend,
                data_points=protocols_data,
                metadata={"protocols": protocol_values},
            )
        except Exception as e:
            self.logger.error(f"分析协议流动性风险时出错: {str(e)}")
            return None

    async def _analyze_investment_type_liquidity(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析投资类型流动性风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取投资类型流动性数据")
                return None

            # 计算总价值
            total_value = sum(pos.get("amount", 0) for pos in positions)
            if total_value == 0:
                return None

            # 按投资类型分组
            investment_type_values = {}
            for pos in positions:
                invest_type = pos.get("invest_type", 0)
                invest_type_name = pos.get("invest_type_name", "未知类型")
                amount = pos.get("amount", 0)

                if invest_type not in investment_type_values:
                    investment_type_values[invest_type] = {
                        "amount": 0,
                        "name": invest_type_name,
                    }
                investment_type_values[invest_type]["amount"] += amount

            # 尝试使用AI服务进行投资类型流动性分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "investment_types": {
                            str(k): {
                                "name": v["name"],
                                "weight": v["amount"] / total_value,
                                "amount": v["amount"],
                            }
                            for k, v in investment_type_values.items()
                        },
                        "analysis_type": "investment_type_liquidity",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="investment_type_liquidity", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get(
                            "description", "投资类型流动性分析"
                        )
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.LIQUIDITY.value,
                            factor_name="投资类型流动性风险",
                            score=risk_score,
                            weight=0.2,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "investment_types": investment_type_values,
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析投资类型流动性风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 如果AI分析失败或不可用，使用传统方法
            # 投资类型流动性评分映射（0-100，越高风险越大）
            investment_type_liquidity_scores = {
                1: 20,  # 存币 - 低风险
                2: 50,  # 流动性池 - 中高风险
                3: 60,  # 挖矿 - 中高风险
                4: 70,  # 机枪池 - 高风险
                5: 40,  # 质押 - 中等风险
                6: 30,  # 借贷 - 中低风险
                0: 60,  # 未知 - 中高风险
            }

            weighted_investment_type_liquidity_score = 0
            investment_types_data = []

            for invest_type, data in investment_type_values.items():
                amount = data["amount"]
                name = data["name"]

                # 获取投资类型流动性评分
                liquidity_score = investment_type_liquidity_scores.get(
                    invest_type, 60
                )  # 默认中高风险

                # 计算加权评分
                weight = amount / total_value
                weighted_investment_type_liquidity_score += liquidity_score * weight

                investment_types_data.append(
                    {
                        "invest_type": invest_type,
                        "name": name,
                        "amount": amount,
                        "liquidity_score": liquidity_score,
                        "weight": weight,
                    }
                )

            # 根据加权评分生成描述
            if weighted_investment_type_liquidity_score > 70:
                description = "投资组合中包含大量低流动性投资类型，流动性风险高"
                trend = "上升"
            elif weighted_investment_type_liquidity_score > 50:
                description = "投资组合中包含一定比例的低流动性投资类型，流动性风险中等"
                trend = "稳定"
            elif weighted_investment_type_liquidity_score > 30:
                description = "投资组合中大部分为高流动性投资类型，流动性风险较低"
                trend = "稳定"
            else:
                description = "投资组合中几乎全部为高流动性投资类型，流动性风险低"
                trend = "下降"

            return self.create_risk_factor(
                risk_type=RiskType.LIQUIDITY.value,
                factor_name="投资类型流动性风险",
                score=weighted_investment_type_liquidity_score,
                weight=0.2,
                description=description,
                trend=trend,
                data_points=investment_types_data,
                metadata={"investment_types": investment_type_values},
            )
        except Exception as e:
            self.logger.error(f"分析投资类型流动性风险时出错: {str(e)}")
            return None

    async def _analyze_liquidity_pool_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析流动性池风险"""
        try:
            # 筛选出流动性池类型的头寸
            lp_positions = [
                pos
                for pos in positions
                if pos.get("invest_type") == 2
                or "LP" in pos.get("asset", "")
                or "/" in pos.get("asset", "")
            ]

            if not lp_positions:
                return None

            # 计算流动性池总价值
            total_lp_value = sum(pos.get("amount", 0) for pos in lp_positions)

            # 如果总价值为0，返回None
            if total_lp_value == 0:
                return None

            # 尝试使用AI服务进行流动性池风险分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    pools_data = []
                    for pos in lp_positions:
                        protocol = pos.get("protocol", "Unknown")
                        asset = pos.get("asset", "Unknown")
                        amount = pos.get("amount", 0)
                        weight = amount / total_lp_value if total_lp_value > 0 else 0

                        # 提取代币列表
                        token_list = pos.get("tokenList", [])
                        tokens = []
                        if token_list:
                            for token in token_list:
                                token_symbol = token.get("tokenSymbol", "")
                                tokens.append(token_symbol)
                        else:
                            # 尝试从资产名称解析
                            tokens = asset.split("/")

                        pools_data.append(
                            {
                                "protocol": protocol,
                                "asset": asset,
                                "tokens": tokens,
                                "weight": weight,
                                "amount": amount,
                            }
                        )

                    ai_input_data = {
                        "liquidity_pools": pools_data,
                        "analysis_type": "liquidity_pool_risk",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="liquidity_pool_risk", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get("description", "流动性池风险分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.LIQUIDITY.value,
                            factor_name="流动性池风险",
                            score=risk_score,
                            weight=0.25,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "liquidity_pools": pools_data,
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析流动性池风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 分析每个流动性池
            pool_risks = []
            for pos in lp_positions:
                protocol = pos.get("protocol", "Unknown")
                asset = pos.get("asset", "Unknown")
                amount = pos.get("amount", 0)
                weight = amount / total_lp_value if total_lp_value > 0 else 0

                # 提取代币列表
                token_list = pos.get("tokenList", [])

                # 计算池子风险
                pool_risk = 50  # 默认中等风险

                # 如果有代币列表，分析代币组合风险
                if token_list:
                    # 检查是否为稳定币池
                    stablecoin_count = 0
                    volatile_count = 0
                    tokens = []

                    for token in token_list:
                        token_symbol = token.get("tokenSymbol", "")
                        tokens.append(token_symbol)

                        # 判断是否为稳定币
                        if token_symbol in [
                            "USDT",
                            "USDC",
                            "DAI",
                            "BUSD",
                            "TUSD",
                            "USDP",
                            "GUSD",
                        ]:
                            stablecoin_count += 1
                        else:
                            volatile_count += 1

                    # 根据代币组合评估风险
                    if stablecoin_count > 0 and volatile_count == 0:
                        # 纯稳定币池风险较低
                        pool_risk = 20
                    elif stablecoin_count > 0 and volatile_count > 0:
                        # 稳定币+波动币混合池风险中等
                        pool_risk = 50
                    elif volatile_count > 1:
                        # 多种波动币池风险较高
                        pool_risk = 70

                    # 添加代币信息
                    pool_risks.append(
                        {
                            "protocol": protocol,
                            "asset": asset,
                            "tokens": tokens,
                            "risk": pool_risk,
                            "weight": weight,
                            "amount": amount,
                            "token_count": len(token_list),
                        }
                    )
                else:
                    # 没有代币列表，尝试从资产名称解析
                    tokens = asset.split("/")

                    # 判断是否为稳定币池
                    stablecoin_count = 0
                    for token in tokens:
                        if token in [
                            "USDT",
                            "USDC",
                            "DAI",
                            "BUSD",
                            "TUSD",
                            "USDP",
                            "GUSD",
                        ]:
                            stablecoin_count += 1

                    if len(tokens) > 1:
                        if stablecoin_count == len(tokens):
                            # 纯稳定币池风险较低
                            pool_risk = 20
                        elif stablecoin_count > 0:
                            # 稳定币+波动币混合池风险中等
                            pool_risk = 50
                        else:
                            # 多种波动币池风险较高
                            pool_risk = 70

                    pool_risks.append(
                        {
                            "protocol": protocol,
                            "asset": asset,
                            "tokens": tokens,
                            "risk": pool_risk,
                            "weight": weight,
                            "amount": amount,
                            "token_count": len(tokens),
                        }
                    )

            # 计算加权平均风险
            weighted_risk = sum(pool["risk"] * pool["weight"] for pool in pool_risks)

            # 构建描述
            if weighted_risk > 70:
                description = "流动性池风险较高，主要由波动性资产组成，可能面临无常损失"
                trend = "上升"
            elif weighted_risk > 40:
                description = "流动性池风险中等，包含一定比例的稳定币和波动性资产"
                trend = "稳定"
            else:
                description = "流动性池风险较低，主要由稳定币组成，无常损失风险较小"
                trend = "下降"

            # 添加池子数量信息
            description += f"，共有{len(pool_risks)}个流动性池头寸"

            # 构建数据点
            data_points = []
            for pool in pool_risks:
                data_points.append(
                    {
                        "protocol": pool["protocol"],
                        "asset": pool["asset"],
                        "tokens": pool["tokens"],
                        "risk": pool["risk"],
                        "weight": pool["weight"],
                        "amount": pool["amount"],
                        "token_count": pool["token_count"],
                    }
                )

            return self.create_risk_factor(
                risk_type=RiskType.LIQUIDITY.value,
                factor_name="流动性池风险",
                score=weighted_risk,
                weight=0.25,
                description=description,
                trend=trend,
                data_points=data_points,
            )
        except Exception as e:
            self.logger.error(f"分析流动性池风险时出错: {str(e)}")
            return None

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取流动性风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        recommendations = []

        # 根据风险因子生成建议
        for factor in risk_factors:
            if factor.factor_name == "资产流动性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合中低流动性资产比例过高，建议大幅减少这些资产的配置"
                    )
                    recommendations.append(
                        "考虑增加主流代币和稳定币等高流动性资产的比例"
                    )
                    recommendations.append("避免在小型交易所或低交易量市场进行交易")
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合中低流动性资产比例较高，建议适当减少这些资产的配置"
                    )
                    recommendations.append(
                        "关注低流动性资产的市场深度变化，设置止损策略"
                    )
                else:
                    recommendations.append(
                        "投资组合资产流动性状况良好，继续保持当前的资产配置策略"
                    )

                # 检查是否有特别低流动性的资产
                low_liquidity_assets = []
                for data_point in factor.data_points:
                    if data_point.get("liquidity_score", 0) > 70:
                        low_liquidity_assets.append(data_point.get("asset", ""))

                if low_liquidity_assets:
                    assets_str = ", ".join(low_liquidity_assets[:3])
                    if len(low_liquidity_assets) > 3:
                        assets_str += f" 等{len(low_liquidity_assets)}个资产"
                    recommendations.append(
                        f"特别关注以下低流动性资产: {assets_str}，考虑减少其配置比例"
                    )

            elif factor.factor_name == "协议流动性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合中使用的协议流动性风险较高，建议减少在这些协议中的投资"
                    )
                    recommendations.append("考虑将资金转移到TVL更高、更成熟的协议中")
                    recommendations.append("密切关注小型协议的TVL变化和用户活跃度")
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合中使用的部分协议流动性风险中等，建议关注这些协议的发展"
                    )
                    recommendations.append("确保在高风险协议中的投资比例不要过高")
                else:
                    recommendations.append(
                        "投资组合使用的协议流动性状况良好，继续关注这些协议的发展"
                    )

                # 检查是否有特别低流动性的协议
                low_liquidity_protocols = []
                for data_point in factor.data_points:
                    if data_point.get("liquidity_score", 0) > 70:
                        low_liquidity_protocols.append(data_point.get("protocol", ""))

                if low_liquidity_protocols:
                    protocols_str = ", ".join(low_liquidity_protocols[:3])
                    if len(low_liquidity_protocols) > 3:
                        protocols_str += f" 等{len(low_liquidity_protocols)}个协议"
                    recommendations.append(
                        f"特别关注以下低流动性协议: {protocols_str}，考虑减少在这些协议中的投资"
                    )

            elif factor.factor_name == "投资类型流动性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合中低流动性投资类型比例过高，建议调整投资类型配置"
                    )
                    recommendations.append("增加高流动性投资类型的比例，如存币和借贷")
                    recommendations.append(
                        "减少锁仓期长的投资，如长期质押和某些挖矿项目"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合中低流动性投资类型比例较高，建议适当调整"
                    )
                    recommendations.append("关注不同投资类型的锁仓期和提取条件")
                else:
                    recommendations.append(
                        "投资组合投资类型流动性状况良好，继续保持当前的配置策略"
                    )

            elif factor.factor_name == "流动性池风险":
                if factor.score > 70:
                    recommendations.append(
                        "流动性池投资风险较高，建议降低流动性池投资的总体比例"
                    )
                    recommendations.append("特别是减少波动性大的代币对流动性池的投资")
                    recommendations.append(
                        "考虑增加稳定币对流动性池的比例，降低无常损失风险"
                    )
                elif factor.score > 50:
                    recommendations.append("流动性池投资风险中等，建议关注无常损失情况")
                    recommendations.append("选择交易量大、深度好的流动性池进行投资")
                else:
                    recommendations.append(
                        "流动性池投资风险较低，继续关注市场波动对流动性池的影响"
                    )

                # 检查是否有高风险的流动性池
                high_risk_pools = []
                for data_point in factor.data_points:
                    if data_point.get("risk", 0) > 70:
                        high_risk_pools.append(data_point.get("asset", ""))

                if high_risk_pools:
                    pools_str = ", ".join(high_risk_pools[:3])
                    if len(high_risk_pools) > 3:
                        pools_str += f" 等{len(high_risk_pools)}个池子"
                    recommendations.append(
                        f"特别关注以下高风险流动性池: {pools_str}，考虑减少在这些池子中的投资"
                    )

        # 添加一般性建议
        if not recommendations:
            recommendations.append(
                "定期评估投资组合的流动性状况，确保在需要时能够快速退出"
            )
            recommendations.append("关注市场整体流动性变化，特别是在市场波动时期")
            recommendations.append("建立分层流动性策略，确保部分资产可以快速变现")

        return recommendations

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取流动性风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        monitoring_points = []

        # 根据风险因子生成监控点
        for factor in risk_factors:
            if factor.factor_name == "资产流动性风险":
                if factor.score > 70:
                    monitoring_points.append("密切监控低流动性资产的交易量和价格波动")
                    monitoring_points.append(
                        "设置流动性阈值警报，当资产流动性下降到特定水平时发出提醒"
                    )
                    monitoring_points.append("跟踪低流动性资产的市场深度变化")
                elif factor.score > 50:
                    monitoring_points.append("定期监控投资组合中资产的流动性变化")
                    monitoring_points.append("关注市场波动对资产流动性的影响")
                else:
                    monitoring_points.append(
                        "定期检查资产流动性状况，确保维持良好的流动性水平"
                    )

                # 检查是否有特别低流动性的资产
                low_liquidity_assets = []
                for data_point in factor.data_points:
                    if data_point.get("liquidity_score", 0) > 70:
                        low_liquidity_assets.append(data_point.get("asset", ""))

                if low_liquidity_assets:
                    assets_str = ", ".join(low_liquidity_assets[:3])
                    if len(low_liquidity_assets) > 3:
                        assets_str += f" 等{len(low_liquidity_assets)}个资产"
                    monitoring_points.append(f"重点监控以下低流动性资产: {assets_str}")

            elif factor.factor_name == "协议流动性风险":
                if factor.score > 70:
                    monitoring_points.append("密切关注高风险协议的TVL变化和用户活跃度")
                    monitoring_points.append("监控协议的治理变更和重大更新")
                    monitoring_points.append(
                        "设置TVL变化警报，当协议TVL大幅下降时发出提醒"
                    )
                elif factor.score > 50:
                    monitoring_points.append("定期关注协议的TVL和用户活跃度变化")
                    monitoring_points.append("监控协议的重大更新和安全事件")
                else:
                    monitoring_points.append(
                        "定期检查协议的TVL和用户活跃度，确保维持良好的流动性水平"
                    )

            elif factor.factor_name == "投资类型流动性风险":
                if factor.score > 70:
                    monitoring_points.append("密切跟踪各类投资的锁仓期和提取条件变化")
                    monitoring_points.append("监控高风险投资类型的市场流动性变化")
                    monitoring_points.append("关注可能影响投资类型流动性的协议变更")
                elif factor.score > 50:
                    monitoring_points.append("定期评估不同投资类型的流动性状况")
                    monitoring_points.append("关注市场环境变化对投资类型流动性的影响")
                else:
                    monitoring_points.append(
                        "定期检查投资类型的流动性状况，确保维持良好的流动性水平"
                    )

            elif factor.factor_name == "流动性池风险":
                if factor.score > 70:
                    monitoring_points.append(
                        "密切监控高风险流动性池的深度和无常损失情况"
                    )
                    monitoring_points.append("跟踪流动性池中代币价格的相对变化")
                    monitoring_points.append("关注可能影响流动性池的市场事件和协议更新")
                elif factor.score > 50:
                    monitoring_points.append("定期评估流动性池的深度和无常损失情况")
                    monitoring_points.append("监控流动性池的交易量和费用收入变化")
                else:
                    monitoring_points.append(
                        "定期检查流动性池的状况，确保维持良好的流动性水平"
                    )

                # 检查是否有高风险的流动性池
                high_risk_pools = []
                for data_point in factor.data_points:
                    if data_point.get("risk", 0) > 70:
                        high_risk_pools.append(data_point.get("asset", ""))

                if high_risk_pools:
                    pools_str = ", ".join(high_risk_pools[:3])
                    if len(high_risk_pools) > 3:
                        pools_str += f" 等{len(high_risk_pools)}个池子"
                    monitoring_points.append(f"重点监控以下高风险流动性池: {pools_str}")

        # 添加一般性监控点
        if not monitoring_points:
            monitoring_points.append("定期检查市场整体流动性状况和极端情况下的退出成本")
            monitoring_points.append("关注宏观经济因素对DeFi市场流动性的影响")
            monitoring_points.append("监控流动性危机的早期警示信号")

        return monitoring_points
