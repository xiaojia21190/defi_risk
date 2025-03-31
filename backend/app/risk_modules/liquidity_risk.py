"""
流动性风险分析模块 - 用于分析DeFi投资组合的流动性风险
"""

from typing import Dict, List, Any, Optional
import logging
from app.models.domain.risk import RiskFactor, RiskType, RiskAnalysisResult
from app.risk_modules.base import RiskAnalyzerBase
from app.services.recommendation_service import RecommendationService
from app.core.utility import safe_get  # 导入safe_get函数
import copy


class LiquidityRiskAnalyzer(RiskAnalyzerBase):
    """流动性风险分析器"""

    def __init__(self, ai_service=None, ai_predictor=None, blockchain_service=None):
        """初始化流动性风险分析器"""
        super().__init__(ai_service, ai_predictor, blockchain_service)
        self.recommendation_service = RecommendationService()

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
                return self.create_default_risk_result(
                    RiskType.LIQUIDITY.value, "投资组合"
                )

            # 计算总体风险评分（加权平均）
            weighted_score = self.calculate_weighted_score(risk_factors)

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
            return self.create_default_risk_result(
                RiskType.LIQUIDITY.value, "投资组合", str(e)
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
        self, positions: List[Any]
    ) -> Optional[RiskFactor]:
        """分析资产流动性风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取资产流动性数据")
                return None

            # 处理嵌套的positions结构
            assets = {}
            total_value = 0

            # 遍历协议positions
            for protocol_position in positions:
                inner_positions = safe_get(protocol_position, "positions", [])

                # 遍历每个协议中的具体资产positions
                for pos in inner_positions:
                    position_amount = safe_get(pos, "amount", 0)
                    total_value += position_amount

                    # 优先从tokenList获取更精确的代币信息
                    if safe_get(pos, "tokenList"):
                        # 使用基类方法过滤代币列表
                        filtered_tokens = self.filter_token_list(
                            safe_get(pos, "tokenList", [])
                        )

                        for token in filtered_tokens:
                            token_symbol = safe_get(token, "tokenSymbol", "")
                            if not token_symbol:
                                continue

                            # 计算代币价值
                            if safe_get(token, "currencyAmount"):
                                token_value = float(
                                    safe_get(token, "currencyAmount", "0")
                                )
                            else:
                                # 如果没有明确的价值，按比例分配
                                token_value = (
                                    position_amount / len(filtered_tokens)
                                    if filtered_tokens
                                    else 0
                                )

                            # 累加到资产映射中
                            if token_symbol not in assets:
                                assets[token_symbol] = 0
                            assets[token_symbol] += token_value
                    else:
                        # 如果没有tokenList，使用资产名称
                        asset = safe_get(pos, "asset", "Unknown").split("/")[
                            0
                        ]  # 处理流动性池资产格式

                        # 使用基类方法检查是否应排除该资产
                        if self.is_excluded_token(asset):
                            self.logger.info(
                                f"排除资产{asset}，因为它是被排除的资产类型"
                            )
                            continue

                        if asset not in assets:
                            assets[asset] = 0
                        assets[asset] += position_amount

            if total_value == 0:
                self.logger.warning("投资组合总价值为0，无法分析资产流动性风险")
                return None

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
            )

        except Exception as e:
            self.logger.error(f"分析资产流动性风险时出错: {str(e)}")
            return None

    async def _analyze_protocol_liquidity(
        self, positions: List[Any]
    ) -> Optional[RiskFactor]:
        """分析协议流动性风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取协议流动性数据")
                return None

            # 按协议分组
            protocol_values = {}

            # 处理嵌套的positions结构
            for protocol_position in positions:
                protocol = safe_get(protocol_position, "protocol", "Unknown")
                inner_positions = safe_get(protocol_position, "positions", [])

                if protocol not in protocol_values:
                    protocol_values[protocol] = 0

                # 累加该协议下所有position的金额
                for pos in inner_positions:
                    amount = safe_get(pos, "amount", 0)
                    protocol_values[protocol] += amount

            # 计算总价值
            total_value = sum(protocol_values.values())
            if total_value == 0:
                self.logger.warning("投资组合总价值为0，无法分析协议流动性风险")
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
                protocol_data = await self.blockchain_service.get_protocol(protocol)

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
            )
        except Exception as e:
            self.logger.error(f"分析协议流动性风险时出错: {str(e)}")
            return None

    async def _analyze_investment_type_liquidity(
        self, positions: List[Any]
    ) -> Optional[RiskFactor]:
        """分析投资类型流动性风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取投资类型流动性数据")
                return None

            # 处理嵌套的positions结构
            investment_type_values = {}
            total_value = 0

            # 遍历协议positions
            for protocol_position in positions:
                inner_positions = safe_get(protocol_position, "positions", [])

                # 遍历每个协议中的具体资产positions
                for pos in inner_positions:
                    # 获取投资类型，默认为"spot"（现货）
                    invest_type = safe_get(pos, "invest_type", 1)

                    # 将数字类型转换为可读的类型名称
                    if isinstance(invest_type, int):
                        if invest_type == 1:
                            invest_type_name = "spot"
                        elif invest_type == 2:
                            invest_type_name = "liquidity_pool"
                        elif invest_type == 3:
                            invest_type_name = "lending"
                        elif invest_type == 4:
                            invest_type_name = "staking"
                        elif invest_type == 5:
                            invest_type_name = "leveraged"
                        elif invest_type == 6:
                            invest_type_name = "borrowed"
                        else:
                            invest_type_name = "other"
                    else:
                        invest_type_name = str(invest_type)

                    # 获取资产价值
                    amount = safe_get(pos, "amount", 0)

                    # 累加到投资类型映射中
                    if invest_type_name not in investment_type_values:
                        investment_type_values[invest_type_name] = 0
                    investment_type_values[invest_type_name] += amount
                    total_value += amount

            if total_value == 0:
                self.logger.warning("投资组合总价值为0，无法分析投资类型流动性风险")
                return None

            # 尝试使用AI服务进行投资类型流动性分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "investment_types": {
                            invest_type_name: {
                                "name": invest_type_name,
                                "weight": investment_type_values[invest_type_name]
                                / total_value,
                                "amount": investment_type_values[invest_type_name],
                            }
                            for invest_type_name in investment_type_values
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
            weighted_investment_type_liquidity_score = 0
            investment_types_data = []

            # 投资类型流动性评分映射（0-100，越高风险越大）
            investment_type_liquidity_scores = {
                "spot": 20,  # 现货 - 低风险
                "liquidity_pool": 50,  # 流动性池 - 中高风险
                "lending": 30,  # 借贷 - 中低风险
                "staking": 40,  # 质押 - 中等风险
                "leveraged": 70,  # 杠杆 - 高风险
                "borrowed": 60,  # 借入 - 中高风险
                "other": 60,  # 其他 - 中高风险
            }

            for invest_type_name, amount in investment_type_values.items():
                # 获取投资类型流动性评分
                liquidity_score = investment_type_liquidity_scores.get(
                    invest_type_name, 60  # 默认中高风险
                )

                # 计算加权评分
                weight = amount / total_value
                weighted_investment_type_liquidity_score += liquidity_score * weight

                investment_types_data.append(
                    {
                        "invest_type": invest_type_name,
                        "name": invest_type_name,
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
        self, positions: List[Any]
    ) -> Optional[RiskFactor]:
        """分析流动性池风险"""
        try:
            # 处理嵌套的positions结构，筛选出流动性池类型的头寸
            lp_positions = []

            # 遍历协议positions
            for protocol_position in positions:
                protocol = safe_get(protocol_position, "protocol", "Unknown")
                inner_positions = safe_get(protocol_position, "positions", [])

                # 遍历每个协议中的具体资产positions
                for pos in inner_positions:
                    # 创建新的字典，添加protocol信息（如果pos中没有）
                    if isinstance(pos, dict):
                        lp_pos = pos.copy()
                    else:
                        # 处理PlatformAsset对象，创建新的dict
                        lp_pos = {
                            "protocol": safe_get(pos, "protocol", protocol),
                            "asset": safe_get(pos, "asset", "Unknown"),
                            "amount": safe_get(pos, "amount", 0),
                            "invest_type": safe_get(pos, "invest_type", 1),
                            "apy": safe_get(pos, "apy", None),
                            "tokenList": safe_get(pos, "tokenList", []),
                        }

                    if "protocol" not in lp_pos:
                        lp_pos["protocol"] = protocol

                    lp_positions.append(lp_pos)

            if not lp_positions:
                self.logger.info("未检测到头寸，跳过流动性池风险分析")
                return None

            # 计算流动性池总价值
            total_lp_value = sum(safe_get(pos, "amount", 0) for pos in lp_positions)

            # 如果总价值为0，返回None
            if total_lp_value == 0:
                self.logger.warning("检测到的流动性池总价值为0，无法分析流动性池风险")
                return None

            # 尝试使用AI服务进行流动性池风险分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    pools_data = []
                    for pos in lp_positions:
                        protocol = safe_get(pos, "protocol", "Unknown")
                        asset = safe_get(pos, "asset", "Unknown")
                        amount = safe_get(pos, "amount", 0)
                        weight = amount / total_lp_value if total_lp_value > 0 else 0

                        # 提取代币列表
                        token_list = safe_get(pos, "tokenList", [])
                        tokens = []
                        valid_tokens = []  # 用于风险计算的有效代币

                        if token_list:
                            for token in token_list:
                                token_symbol = safe_get(token, "tokenSymbol", "")
                                tokens.append(token_symbol)  # 保留所有代币用于显示

                                # 使用基类方法检查是否应排除该代币
                                if self.is_excluded_token(token_symbol):
                                    self.logger.info(
                                        f"风险计算中排除代币{token_symbol}，因为它是被排除的代币类型"
                                    )
                                    continue

                                valid_tokens.append(token_symbol)
                        else:
                            # 尝试从资产名称解析
                            tokens = asset.split("/")
                            # 使用基类方法过滤代币
                            valid_tokens = [
                                token
                                for token in tokens
                                if not self.is_excluded_token(token)
                            ]

                        pools_data.append(
                            {
                                "protocol": protocol,
                                "asset": asset,
                                "tokens": tokens,  # 显示所有代币，包括yt和pt
                                "valid_tokens": valid_tokens,  # 仅用于风险计算的代币
                                "weight": weight,
                                "amount": amount,
                            }
                        )

                    ai_input_data = {
                        "liquidity_pools": pools_data,
                        "analysis_type": "liquidity_pool_risk",
                    }

                    # 确保AI服务使用valid_tokens进行分析
                    # 创建一个新的数据副本，将tokens替换为valid_tokens用于分析
                    ai_pools_data = []
                    for pool in pools_data:
                        ai_pool = pool.copy()
                        ai_pool["tokens"] = pool[
                            "valid_tokens"
                        ]  # 用有效代币替换所有代币
                        ai_pools_data.append(ai_pool)

                    ai_input_data["liquidity_pools"] = ai_pools_data

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
                protocol = safe_get(pos, "protocol", "Unknown")
                asset = safe_get(pos, "asset", "Unknown")
                amount = safe_get(pos, "amount", 0)
                weight = amount / total_lp_value if total_lp_value > 0 else 0

                # 提取代币列表
                token_list = safe_get(pos, "tokenList", [])

                # 计算池子风险
                pool_risk = 50  # 默认中等风险

                # 如果有代币列表，分析代币组合风险
                if token_list:
                    # 检查是否为稳定币池
                    stablecoin_count = 0
                    volatile_count = 0
                    tokens = []
                    valid_tokens = []  # 用于风险计算的有效代币

                    for token in token_list:
                        token_symbol = token.get("tokenSymbol", "")
                        tokens.append(token_symbol)  # 保留所有代币用于显示

                        # 使用基类方法检查是否应排除该代币
                        if self.is_excluded_token(token_symbol):
                            self.logger.info(
                                f"风险计算中排除代币{token_symbol}，因为它是被排除的代币类型"
                            )
                            continue

                        valid_tokens.append(token_symbol)

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

                    # 根据代币组合评估风险，只使用有效代币
                    if len(valid_tokens) > 0:  # 确保有有效代币
                        if stablecoin_count > 0 and volatile_count == 0:
                            # 纯稳定币池风险较低
                            pool_risk = 20
                        elif stablecoin_count > 0 and volatile_count > 0:
                            # 稳定币+波动币混合池风险中等
                            pool_risk = 50
                        elif volatile_count > 1:
                            # 多种波动币池风险较高
                            pool_risk = 70
                    # 没有有效代币时使用默认风险

                    # 添加代币信息，显示所有代币但在metadata中指明有效代币
                    pool_risks.append(
                        {
                            "protocol": protocol,
                            "asset": asset,
                            "tokens": tokens,
                            "valid_tokens": valid_tokens,
                            "risk": pool_risk,
                            "weight": weight,
                            "amount": amount,
                            "token_count": len(valid_tokens),  # 使用有效代币数量
                        }
                    )
                else:
                    # 如果没有tokenList，尝试从资产名称解析
                    all_tokens = asset.split("/")
                    tokens = all_tokens  # 保留所有代币用于显示

                    # 使用基类方法过滤代币
                    valid_tokens = [
                        token
                        for token in all_tokens
                        if not self.is_excluded_token(token)
                    ]

                    # 判断是否为稳定币池
                    stablecoin_count = 0
                    for token in valid_tokens:  # 只考虑有效代币
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

                    if len(valid_tokens) > 1:  # 确保有多个有效代币
                        if stablecoin_count == len(valid_tokens):
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
                            "valid_tokens": valid_tokens,
                            "risk": pool_risk,
                            "weight": weight,
                            "amount": amount,
                            "token_count": len(valid_tokens),  # 使用有效代币数量
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
        # 使用推荐服务生成建议
        return self.recommendation_service.get_liquidity_risk_recommendations(
            risk_factors
        )

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取流动性风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        # 使用推荐服务生成监控点
        return self.recommendation_service.get_monitoring_points(
            "LIQUIDITY", risk_factors
        )
