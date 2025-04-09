"""
市场风险分析模块 - 用于分析市场相关的风险
"""

from typing import Dict, List, Any, Optional
import logging
import asyncio
from app.models.domain.risk import RiskFactor, RiskType, RiskAnalysisResult
from app.risk_modules.base import RiskAnalyzerBase
from app.services.recommendation_service import RecommendationService
import numpy as np
from app.core.utility import safe_get


class MarketRiskAnalyzer(RiskAnalyzerBase):
    """市场风险分析器"""

    def __init__(self, ai_service=None, ai_predictor=None, blockchain_service=None):
        """初始化市场风险分析器"""
        super().__init__(ai_service, ai_predictor, blockchain_service)
        self.recommendation_service = RecommendationService()

    async def analyze(self, data: Dict[str, Any]) -> RiskAnalysisResult:
        """
        分析市场风险

        Args:
            data: 分析数据

        Returns:
            分析结果
        """
        self.logger.info("开始分析市场风险")

        # 检查AI服务可用性
        await self._check_ai_services()

        try:
            # 获取风险因子
            risk_factors = await self.get_risk_factors(data)

            # 如果没有收集到任何风险因素，返回默认风险分析结果
            if not risk_factors:
                self.logger.warning("未能收集到任何市场风险因素")
                return self.create_default_risk_result(
                    RiskType.MARKET.value, "投资组合"
                )

            # 计算总体风险评分（加权平均）
            weighted_score = self.calculate_weighted_score(risk_factors)

            # 生成建议和监控点
            recommendations = await self.get_recommendations(risk_factors)
            monitoring_points = await self.get_monitoring_points(risk_factors)

            # 创建风险分析结果
            result = RiskAnalysisResult(
                risk_type=RiskType.MARKET.value,
                target="投资组合市场风险",
                score=weighted_score,
                factors=risk_factors,
                recommendations=recommendations,
                monitoring_points=monitoring_points,
            )

            self.logger.info(f"完成市场风险分析，总体风险评分: {weighted_score:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"分析市场风险时出错: {str(e)}")
            # 返回默认风险分析结果
            return self.create_default_risk_result(
                RiskType.MARKET.value, "投资组合", str(e)
            )

    async def _check_ai_services(self) -> None:
        """检查AI服务和预测器的可用性"""
        if self.ai_service:
            try:
                # 简单检查AI服务是否可用
                self.logger.info("检查AI服务可用性...")
                is_available = await self.ai_service.is_available()
                if is_available:
                    self.logger.info("AI服务可用，将用于风险分析")
                else:
                    self.logger.warning("AI服务不可用，将使用传统方法进行风险分析")
            except Exception as e:
                self.logger.error(f"检查AI服务可用性时出错: {str(e)}")
                self.logger.warning("AI服务检查失败，将使用传统方法进行风险分析")
        else:
            self.logger.info("未配置AI服务，将使用传统方法进行风险分析")

        if self.ai_predictor:
            try:
                # 简单检查AI预测器是否可用
                self.logger.info("检查AI预测器可用性...")
                is_available = await self.ai_predictor.is_available()
                if is_available:
                    self.logger.info("AI预测器可用，将用于市场趋势分析")
                else:
                    self.logger.warning(
                        "AI预测器不可用，将使用传统方法进行市场趋势分析"
                    )
            except Exception as e:
                self.logger.error(f"检查AI预测器可用性时出错: {str(e)}")
                self.logger.warning("AI预测器检查失败，将使用传统方法进行市场趋势分析")
        else:
            self.logger.info("未配置AI预测器，将使用传统方法进行市场趋势分析")

    async def get_risk_factors(self, data: Dict[str, Any]) -> List[RiskFactor]:
        """
        获取市场风险因子

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

        # 分析资产集中度风险
        concentration_risk = await self._analyze_concentration_risk(positions)
        if concentration_risk:
            risk_factors.append(concentration_risk)

        # 分析市场波动性风险
        volatility_risk = await self._analyze_volatility_risk(positions)
        if volatility_risk:
            risk_factors.append(volatility_risk)

        # 分析市场趋势风险
        trend_risk = await self._analyze_trend_risk(positions)
        if trend_risk:
            risk_factors.append(trend_risk)

        # 分析市场相关性风险
        correlation_risk = await self._analyze_correlation_risk(positions)
        if correlation_risk:
            risk_factors.append(correlation_risk)

        return risk_factors

    async def _analyze_concentration_risk(
        self, positions: List[Any]
    ) -> Optional[RiskFactor]:
        """分析市场集中度风险"""
        try:
            # 使用HHI指数分析资产和协议集中度
            # HHI指数=各实体占比的平方和，范围0-10000，越大表示越集中

            assets = {}
            protocols = {}
            total_value = 0

            # 处理嵌套的positions结构
            for protocol_position in positions:
                protocol = safe_get(protocol_position, "protocol", "Unknown")
                inner_positions = safe_get(protocol_position, "positions", [])

                # 初始化协议价值
                if protocol not in protocols:
                    protocols[protocol] = 0

                # 遍历每个协议中的具体资产positions
                for pos in inner_positions:
                    # 获取资产价值
                    position_amount = safe_get(pos, "amount", 0)
                    total_value += position_amount
                    protocols[protocol] += position_amount

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
                self.logger.warning("投资组合总价值为0，无法分析市场集中度风险")
                return None

            # 尝试使用AI服务进行集中度分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "assets": {
                            asset: value / total_value
                            for asset, value in assets.items()
                        },
                        "protocols": {
                            protocol: value / total_value
                            for protocol, value in protocols.items()
                        },
                        "analysis_type": "concentration_risk",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="concentration_risk", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get("description", "市场集中度分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.MARKET.value,
                            factor_name="市场集中度风险",
                            score=risk_score,
                            weight=0.3,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "asset_weights": {
                                    asset: value / total_value
                                    for asset, value in assets.items()
                                },
                                "protocol_weights": {
                                    protocol: value / total_value
                                    for protocol, value in protocols.items()
                                },
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析市场集中度风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 如果AI分析失败或不可用，使用传统方法
            # 计算资产集中度（赫芬达尔指数）
            if assets:
                asset_weights = [value / total_value for value in assets.values()]
                asset_hhi = sum(weight**2 for weight in asset_weights)
            else:
                asset_hhi = 0

            # 计算协议集中度
            if protocols:
                protocol_weights = [value / total_value for value in protocols.values()]
                protocol_hhi = sum(weight**2 for weight in protocol_weights)
            else:
                protocol_hhi = 0

            # 综合集中度
            concentration_score = max(asset_hhi, protocol_hhi) * 100

            # 调整到0-100范围
            if concentration_score > 100:
                concentration_score = 100
            elif concentration_score < 0:
                concentration_score = 0

            # 根据分数判断风险级别
            if concentration_score > 70:  # 高集中度
                description = "投资组合高度集中，存在显著的集中度风险"
                trend = "上升"
            elif concentration_score > 40:  # 中等集中度
                description = "投资组合集中度中等，存在一定的集中度风险"
                trend = "稳定"
            else:  # 低集中度
                description = "投资组合分散良好，集中度风险较低"
                trend = "下降"

            # 创建数据点
            data_points = [
                {"name": "资产集中度HHI", "value": asset_hhi},
                {"name": "协议集中度HHI", "value": protocol_hhi},
            ]

            # 添加排名前三的资产和协议数据
            sorted_assets = sorted(assets.items(), key=lambda x: x[1], reverse=True)[:3]
            sorted_protocols = sorted(
                protocols.items(), key=lambda x: x[1], reverse=True
            )[:3]

            for asset, amount in sorted_assets:
                data_points.append(
                    {
                        "name": "主要资产",
                        "asset": asset,
                        "value": amount / total_value,
                        "amount": amount,
                    }
                )

            for protocol, amount in sorted_protocols:
                data_points.append(
                    {
                        "name": "主要协议",
                        "protocol": protocol,
                        "value": amount / total_value,
                        "amount": amount,
                    }
                )

            return self.create_risk_factor(
                risk_type=RiskType.MARKET.value,
                factor_name="市场集中度风险",
                score=concentration_score,
                weight=0.3,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "assets": assets,
                    "protocols": protocols,
                    "asset_hhi": asset_hhi,
                    "protocol_hhi": protocol_hhi,
                    "total_value": total_value,
                },
            )
        except Exception as e:
            self.logger.error(f"分析市场集中度风险时出错: {str(e)}")
            return None

    async def _analyze_volatility_risk(
        self, positions: List[Any]
    ) -> Optional[RiskFactor]:
        """分析市场波动性风险"""
        try:
            # 使用区块链服务获取资产波动性数据
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取资产波动性数据")
                return None

            # 提取资产列表和权重
            assets = {}
            total_value = 0

            # 处理嵌套的positions结构
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

            if not assets:
                self.logger.warning("没有检测到任何资产，无法分析波动性风险")
                return None

            # 获取每个资产的24小时波动性数据
            volatility_data = {}

            for asset in assets:
                # 获取24小时数据
                data_24h = await self.blockchain_service._get_24h_data(asset)

                if data_24h:
                    volatility = data_24h.get("volatility", 0)
                    volatility_data[asset] = {
                        "volatility": volatility,
                        "weight": (
                            assets[asset] / total_value if total_value > 0 else 0
                        ),
                        "price_change_percent": data_24h.get("price_change_percent", 0),
                    }
                else:
                    # 如果没有获取到数据，使用历史数据估算波动性
                    historical_data = (
                        await self.blockchain_service.get_asset_historical_data(asset)
                    )
                    if historical_data is not None and not historical_data.empty:
                        # 计算价格波动率
                        prices = historical_data["price"].values
                        if len(prices) > 1:
                            daily_returns = np.diff(prices) / prices[:-1]
                            volatility = np.std(daily_returns) * 100  # 转换为百分比
                        else:
                            volatility = 0
                    else:
                        volatility = 0

                    volatility_data[asset] = {
                        "volatility": volatility,
                        "weight": (
                            assets[asset] / total_value if total_value > 0 else 0
                        ),
                        "price_change_percent": 0,
                    }

            # 计算加权平均波动性
            if not volatility_data:
                self.logger.warning("无法获取任何资产的波动性数据")
                return None

            weighted_volatility = sum(
                data["volatility"] * data["weight"] for data in volatility_data.values()
            )

            # 计算风险评分 (0-100)
            # 波动性越高，风险越大
            # 假设波动性在0-30%之间，线性映射到0-100的风险评分
            risk_score = min(100, weighted_volatility * 100 / 30)

            # 确定趋势
            avg_price_change = sum(
                data["price_change_percent"] * data["weight"]
                for data in volatility_data.values()
            )

            if avg_price_change > 2:
                trend = "上升"
            elif avg_price_change < -2:
                trend = "下降"
            else:
                trend = "稳定"

            # 构建数据点
            data_points = [
                {
                    "name": asset,
                    "value": data["volatility"],
                    "weight": data["weight"],
                    "price_change": data["price_change_percent"],
                }
                for asset, data in volatility_data.items()
            ]

            # 构建描述
            description = f"投资组合的加权平均波动性为{weighted_volatility:.2f}%，"
            if weighted_volatility > 20:
                description += "波动性极高，市场风险显著。"
            elif weighted_volatility > 10:
                description += "波动性较高，市场风险中等。"
            else:
                description += "波动性较低，市场风险可控。"

            return self.create_risk_factor(
                risk_type=RiskType.MARKET.value,
                factor_name="市场波动性风险",
                score=risk_score,
                weight=0.3,
                description=description,
                trend=trend,
                data_points=data_points,
            )
        except Exception as e:
            self.logger.error(f"分析市场波动性风险时出错: {str(e)}")
            return None

    async def _analyze_trend_risk(self, positions: List[Any]) -> Optional[RiskFactor]:
        """分析市场趋势风险"""
        try:
            # 使用区块链服务获取资产趋势数据
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取资产趋势数据")
                return None

            # 提取资产列表和权重
            assets = {}
            total_value = 0

            # 处理嵌套的positions结构
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

            if not assets:
                self.logger.warning("未检测到任何资产，无法分析市场趋势风险")
                return None

            if total_value == 0:
                self.logger.warning("投资组合总价值为0，无法分析市场趋势风险")
                return None

            # 获取市场趋势数据
            market_trends = {}
            weighted_trend_score = 0
            total_weight = 0

            # 对资产按价值排序，只分析占比较大的资产
            sorted_assets = sorted(
                [(asset, value) for asset, value in assets.items()],
                key=lambda x: x[1],
                reverse=True,
            )

            # 只分析总价值占比前80%的资产或者前10个资产
            top_assets = []
            cumulative_value = 0

            for asset, value in sorted_assets:
                top_assets.append(asset)
                cumulative_value += value
                if cumulative_value / total_value > 0.8 or len(top_assets) >= 10:
                    break

            # 获取主要资产的趋势数据
            for asset in top_assets:
                weight = assets[asset] / total_value
                try:
                    # 获取资产的市场趋势数据
                    token_data = await self.blockchain_service.get_token_trend(asset)
                    if token_data:
                        # 计算趋势分数：正面趋势为低风险，负面趋势为高风险
                        trend_direction = token_data.get("trend_direction", 0)
                        trend_strength = token_data.get("trend_strength", 0.5)

                        # 趋势分数，0为最佳(上升趋势)，100为最差(下降趋势)
                        if trend_direction > 0:  # 上升趋势
                            trend_score = 30 * (
                                1 - trend_strength
                            )  # 较强上升趋势得分更低
                        elif trend_direction < 0:  # 下降趋势
                            trend_score = (
                                70 + 30 * trend_strength
                            )  # 较强下降趋势得分更高
                        else:  # 横盘
                            trend_score = 50

                        market_trends[asset] = {
                            "trend_direction": trend_direction,
                            "trend_strength": trend_strength,
                            "trend_score": trend_score,
                            "price_change_1d": token_data.get("price_change_1d", 0),
                            "price_change_7d": token_data.get("price_change_7d", 0),
                            "price_change_30d": token_data.get("price_change_30d", 0),
                            "weight": weight,
                        }

                        # 累加加权趋势分数
                        weighted_trend_score += trend_score * weight
                        total_weight += weight
                except Exception as e:
                    self.logger.warning(f"获取{asset}趋势数据时出错: {str(e)}")

            # 如果没有获取到任何趋势数据
            if total_weight == 0:
                self.logger.warning(
                    "未能获取到任何资产的趋势数据，无法分析市场趋势风险"
                )
                return None

            # 尝试使用AI服务进行趋势风险分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "assets": {
                            asset: {
                                "weight": assets[asset] / total_value,
                                "trend_data": market_trends.get(asset, {}),
                            }
                            for asset in top_assets
                        },
                        "analysis_type": "trend_risk",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="trend_risk", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get("description", "市场趋势分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.MARKET.value,
                            factor_name="市场趋势风险",
                            score=risk_score,
                            weight=0.2,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "market_trends": market_trends,
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析市场趋势风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 如果AI分析失败或不可用，使用传统方法
            # 计算最终的趋势风险分数
            final_trend_score = weighted_trend_score / total_weight

            # 根据趋势分数判断风险
            if final_trend_score > 80:
                description = "多数主要资产呈强烈下降趋势，市场趋势风险极高"
                trend = "上升"
            elif final_trend_score > 65:
                description = "多数主要资产呈下降趋势，市场趋势风险较高"
                trend = "上升"
            elif final_trend_score > 55:
                description = "部分主要资产呈下降趋势，市场趋势风险中等偏高"
                trend = "稳定"
            elif final_trend_score > 45:
                description = "主要资产趋势混合，市场趋势风险中等"
                trend = "稳定"
            elif final_trend_score > 35:
                description = "部分主要资产呈上升趋势，市场趋势风险中等偏低"
                trend = "稳定"
            elif final_trend_score > 20:
                description = "多数主要资产呈上升趋势，市场趋势风险较低"
                trend = "下降"
            else:
                description = "多数主要资产呈强烈上升趋势，市场趋势风险极低"
                trend = "下降"

            # 创建数据点
            data_points = [
                {
                    "name": "整体趋势风险",
                    "value": final_trend_score,
                    "description": "整体市场趋势风险评分，越高风险越大",
                }
            ]

            # 添加主要资产的趋势数据
            for asset, data in market_trends.items():
                if data["weight"] > 0.05:  # 只添加权重超过5%的资产
                    data_points.append(
                        {
                            "name": "资产趋势",
                            "asset": asset,
                            "trend_score": data["trend_score"],
                            "price_change_7d": data.get("price_change_7d", 0),
                            "weight": data["weight"],
                        }
                    )

            return self.create_risk_factor(
                risk_type=RiskType.MARKET.value,
                factor_name="市场趋势风险",
                score=final_trend_score,
                weight=0.2,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={"market_trends": market_trends},
            )
        except Exception as e:
            self.logger.error(f"分析市场趋势风险时出错: {str(e)}")
            return None

    async def _analyze_correlation_risk(
        self, positions: List[Any]
    ) -> Optional[RiskFactor]:
        """分析市场相关性风险"""
        try:
            # 使用区块链服务获取资产相关性数据
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取资产相关性数据")
                return None

            # 提取资产列表和权重
            assets = {}
            total_value = 0

            # 处理嵌套的positions结构
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

            # 如果检测到的资产少于2种，无法计算相关性
            if len(assets) < 2:
                self.logger.warning("检测到的资产少于2种，无法进行相关性分析")
                return None

            if total_value == 0:
                self.logger.warning("投资组合总价值为0，无法分析市场相关性风险")
                return None

            # 尝试使用AI服务进行相关性分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    asset_weights = {
                        asset: amount / total_value for asset, amount in assets.items()
                    }

                    # 获取资产历史价格数据
                    asset_price_data = {}
                    for asset in assets:
                        try:
                            historical_prices = await self.blockchain_service.get_token_historical_prices(
                                asset, days=30
                            )
                            if historical_prices:
                                asset_price_data[asset] = historical_prices
                        except Exception as e:
                            self.logger.warning(
                                f"获取{asset}历史价格数据时出错: {str(e)}"
                            )

                    ai_input_data = {
                        "assets": list(assets.keys()),
                        "weights": asset_weights,
                        "price_data": asset_price_data,
                        "analysis_type": "correlation_risk",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="correlation_risk", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get("description", "市场相关性分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.MARKET.value,
                            factor_name="市场相关性风险",
                            score=risk_score,
                            weight=0.2,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "assets": assets,
                                "asset_weights": asset_weights,
                                "price_data": asset_price_data,
                                "ai_analysis": ai_analysis,
                            },
                        )
                except Exception as e:
                    self.logger.error(f"使用AI分析市场相关性风险时出错: {str(e)}")
                    # 如果AI分析失败，继续使用传统方法

            # 如果AI分析失败或不可用，使用传统方法
            # 简单评估相关性风险
            # 如果主要资产（占比>20%）个数小于2
            significant_assets = sum(
                1 for amount in assets.values() if amount / total_value > 0.2
            )

            if significant_assets <= 1:
                score = 30  # 低相关性风险
                description = "投资组合中无多个主要资产，相关性风险较低"
                trend = "稳定"
            else:
                # 获取主要资产类型（如货币、DeFi代币等）
                asset_types = set()
                for asset in [a for a, v in assets.items() if v / total_value > 0.2]:
                    asset_type = "未知"
                    try:
                        token_info = await self.blockchain_service.get_token_info(asset)
                        if token_info:
                            asset_type = token_info.get("category", "未知")
                    except Exception:
                        pass
                    asset_types.add(asset_type)

                if len(asset_types) <= 1:
                    score = 70  # 高相关性风险
                    description = (
                        f"主要资产属于同一类别({list(asset_types)[0]})，相关性风险较高"
                    )
                    trend = "上升"
                else:
                    score = 40  # 中等相关性风险
                    description = "主要资产分布于不同类别，存在一定相关性风险"
                    trend = "稳定"

            data_points = []
            for asset, amount in assets.items():
                weight = amount / total_value
                if weight > 0.1:  # 只显示占比超过10%的资产
                    data_points.append(
                        {
                            "name": "主要资产",
                            "asset": asset,
                            "weight": weight,
                            "amount": amount,
                        }
                    )

            return self.create_risk_factor(
                risk_type=RiskType.MARKET.value,
                factor_name="市场相关性风险",
                score=score,
                weight=0.2,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={
                    "assets": assets,
                    "significant_assets": significant_assets,
                    "total_value": total_value,
                },
            )
        except Exception as e:
            self.logger.error(f"分析市场相关性风险时出错: {str(e)}")
            return None

    async def get_recommendations(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取市场风险建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            建议列表
        """
        # 使用推荐服务生成建议
        recommendations = self.recommendation_service.get_market_risk_recommendations(
            risk_factors
        )

        return recommendations

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取市场风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        try:
            # 检查是否存在recommendation_service
            if hasattr(self, "recommendation_service") and self.recommendation_service:
                # 使用推荐服务生成监控点 - 使用中文风险类型
                monitoring_points = self.recommendation_service.get_monitoring_points(
                    self.get_chinese_risk_type("MARKET"), risk_factors
                )
            else:
                # 如果没有推荐服务，生成默认监控点
                monitoring_points = []
                # 根据风险因子生成基本监控点
                for factor in risk_factors:
                    if "集中度" in factor.name:
                        monitoring_points.append("监控投资组合中主要资产的占比变化")
                    elif "波动性" in factor.name:
                        monitoring_points.append("监控市场波动性指标（如VIX）的变化")
                    elif "趋势" in factor.name:
                        monitoring_points.append("监控市场趋势指标和移动平均线交叉")
                    elif "相关性" in factor.name:
                        monitoring_points.append(
                            "定期计算投资组合中主要资产对的相关系数"
                        )

                # 如果通过风险因子没有生成监控点，添加默认监控点
                if not monitoring_points:
                    monitoring_points = [
                        "定期监控主要加密资产价格走势",
                        "关注市场总体波动性变化",
                        "跟踪重要资产的相关性变化",
                        "监控投资组合的集中度风险",
                        "关注市场情绪指标如恐惧与贪婪指数",
                    ]

            # 尝试添加AI生成的监控点
            try:
                if self.ai_predictor and hasattr(
                    self.ai_predictor, "generate_market_risk_monitoring_points"
                ):
                    # 准备风险因子数据
                    risk_data = {
                        "risk_factors": [
                            {
                                "name": factor.name,
                                "score": factor.score,
                                "description": factor.description,
                                "trend": factor.trend,
                                "data_points": factor.data_points,
                            }
                            for factor in risk_factors
                        ],
                    }

                    # 获取AI监控点
                    ai_result = (
                        self.ai_predictor.generate_market_risk_monitoring_points(
                            risk_data
                        )
                    )
                    if ai_result and "monitoring_points" in ai_result:
                        monitoring_points.extend(ai_result["monitoring_points"])
            except Exception as e:
                self.logger.error(f"获取AI市场风险监控点时出错: {str(e)}")

            return list(set(monitoring_points))  # 去重

        except Exception as e:
            self.logger.error(f"生成市场风险监控点时出错: {str(e)}")
            # 发生错误时返回基本监控点
            return [
                "监控主要资产的价格波动",
                "关注投资组合的整体风险",
                "定期评估市场趋势变化",
            ]

    async def _get_ai_recommendations(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """获取AI生成的建议"""
        if not self.ai_predictor:
            return []

        try:
            # 准备风险因子数据
            risk_data = {
                "risk_factors": [
                    {
                        "name": factor.name,
                        "score": factor.score,
                        "description": factor.description,
                        "trend": factor.trend,
                        "data_points": factor.data_points,
                    }
                    for factor in risk_factors
                ],
            }

            # 获取AI建议
            result = self.ai_predictor.generate_market_risk_recommendations(risk_data)
            if result and "recommendations" in result:
                return result["recommendations"]
        except Exception as e:
            self.logger.error(f"获取AI市场风险建议时出错: {str(e)}")

        return []
