"""
市场风险分析模块 - 用于分析市场相关的风险
"""

from typing import Dict, List, Any, Optional
import logging
import asyncio
from app.models.domain.risk import RiskFactor, RiskType, RiskAnalysisResult
from app.risk_modules.base import RiskAnalyzerBase
import numpy as np


class MarketRiskAnalyzer(RiskAnalyzerBase):
    """市场风险分析器"""

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
                return RiskAnalysisResult(
                    risk_type=RiskType.MARKET.value,
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
            return RiskAnalysisResult(
                risk_type=RiskType.MARKET.value,
                target="投资组合",
                score=50,  # 默认中等风险
                factors=[],
                recommendations=[
                    "无法完成市场风险分析，请检查输入数据是否正确",
                    "确保区块链服务正常运行",
                    "尝试稍后再次分析",
                ],
                monitoring_points=[
                    "监控系统日志以排查风险分析失败的原因",
                ],
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
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析资产集中度风险"""
        try:
            # 计算总价值
            total_value = sum(pos.get("amount", 0) for pos in positions)

            if total_value == 0:
                return None

            # 按资产分组
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
                    asset = pos.get("asset", "unknown")
                    if asset not in assets:
                        assets[asset] = 0
                    assets[asset] += pos.get("amount", 0)

            # 尝试使用AI服务进行资产集中度分析
            if self.ai_service:
                try:
                    # 准备AI分析的数据
                    ai_input_data = {
                        "assets": {
                            asset: amount / total_value
                            for asset, amount in assets.items()
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
                        description = ai_analysis.get("description", "资产集中度分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        return self.create_risk_factor(
                            risk_type=RiskType.MARKET.value,
                            factor_name="资产集中度风险",
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
                    self.logger.error(f"使用AI分析资产集中度风险时出错: {str(e)}")
                    self.logger.info("将使用传统方法进行资产集中度风险分析")
                    # 如果AI分析失败，继续使用传统方法
            else:
                self.logger.info("AI服务不可用，使用传统方法进行资产集中度风险分析")

            # 如果AI分析失败或不可用，使用传统方法
            # 计算最大资产占比
            max_asset = max(assets.items(), key=lambda x: x[1])
            max_concentration = max_asset[1] / total_value

            # 计算赫芬达尔-赫希曼指数 (HHI)
            hhi = sum((amount / total_value) ** 2 for amount in assets.values()) * 10000

            # 根据集中度评分
            if max_concentration > 0.7 or hhi > 6000:
                score = 80  # 高风险
                description = f"投资组合过于集中在{max_asset[0]}，占比{max_concentration:.1%}，HHI={hhi:.0f}"
                trend = "上升"
            elif max_concentration > 0.5 or hhi > 3000:
                score = 60  # 中高风险
                description = f"投资组合在{max_asset[0]}上的集中度较高，占比{max_concentration:.1%}，HHI={hhi:.0f}"
                trend = "稳定"
            elif max_concentration > 0.3 or hhi > 1500:
                score = 40  # 中等风险
                description = f"投资组合在{max_asset[0]}上有一定集中度，占比{max_concentration:.1%}，HHI={hhi:.0f}"
                trend = "稳定"
            else:
                score = 20  # 低风险
                description = f"投资组合分散良好，最大资产{max_asset[0]}占比{max_concentration:.1%}，HHI={hhi:.0f}"
                trend = "下降"

            # 构建数据点
            data_points = [
                {
                    "asset": asset,
                    "amount": amount,
                    "percentage": amount / total_value,
                    "is_max_asset": asset == max_asset[0],
                }
                for asset, amount in assets.items()
            ]

            return self.create_risk_factor(
                risk_type=RiskType.MARKET.value,
                factor_name="资产集中度风险",
                score=score,
                weight=0.4,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={"hhi": hhi, "max_concentration": max_concentration},
            )
        except Exception as e:
            self.logger.error(f"分析资产集中度风险时出错: {str(e)}")
            return None

    async def _analyze_volatility_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析市场波动性风险"""
        try:
            # 使用区块链服务获取资产波动性数据
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取资产波动性数据")
                return None

            # 提取资产列表
            assets = []
            asset_values = {}
            for pos in positions:
                asset = pos.get("asset", "Unknown").split("/")[
                    0
                ]  # 处理流动性池资产格式
                if asset not in assets:
                    assets.append(asset)
                    asset_values[asset] = 0
                asset_values[asset] += pos.get("amount", 0)

            # 获取每个资产的24小时波动性数据
            volatility_data = {}
            total_value = sum(asset_values.values())

            for asset in assets:
                # 尝试从tokenList中获取更精确的代币符号
                token_symbol = asset
                for pos in positions:
                    if pos.get("asset") == asset and pos.get("tokenList"):
                        for token in pos.get("tokenList", []):
                            if token.get("tokenSymbol"):
                                token_symbol = token.get("tokenSymbol")
                                break
                        break

                # 获取24小时数据
                data_24h = await self.blockchain_service._get_24h_data(token_symbol)

                if data_24h:
                    volatility = data_24h.get("volatility", 0)
                    volatility_data[asset] = {
                        "volatility": volatility,
                        "weight": (
                            asset_values[asset] / total_value if total_value > 0 else 0
                        ),
                        "price_change_percent": data_24h.get("price_change_percent", 0),
                    }
                else:
                    # 如果没有获取到数据，使用历史数据估算波动性
                    historical_data = (
                        await self.blockchain_service.get_asset_historical_data(
                            token_symbol
                        )
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
                            asset_values[asset] / total_value if total_value > 0 else 0
                        ),
                        "price_change_percent": 0,
                    }

            # 计算加权平均波动性
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

    async def _analyze_trend_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析市场趋势风险"""
        try:
            # 如果没有头寸，返回None
            if not positions:
                return None

            # 提取资产
            assets = set()
            for pos in positions:
                asset = pos.get("asset", "").split("/")[0]
                if asset:
                    assets.add(asset)

            # 如果没有资产，返回None
            if not assets:
                return None

            # 计算总体趋势风险
            trend_risk_score = 0
            asset_trends = {}

            # 使用AI预测器分析每个资产的市场趋势
            if self.ai_predictor:
                self.logger.info(f"使用AI预测器分析{len(assets)}个资产的市场趋势")
                for asset in assets:
                    try:
                        # 使用AI预测器分析市场趋势
                        trend_analysis = await self.ai_predictor.analyze_market_trend(
                            asset=asset
                        )

                        # 提取趋势信息
                        trend = trend_analysis.get("trend", "neutral")
                        trend_strength = trend_analysis.get(
                            "trend_strength", "moderate"
                        )
                        risk_level = trend_analysis.get("risk_level", "MEDIUM")

                        # 计算趋势风险评分
                        if trend == "bearish":
                            if trend_strength == "strong":
                                asset_score = 80
                            elif trend_strength == "moderate":
                                asset_score = 60
                            else:
                                asset_score = 40
                        elif trend == "bullish":
                            if trend_strength == "strong":
                                asset_score = 20
                            elif trend_strength == "moderate":
                                asset_score = 30
                            else:
                                asset_score = 40
                        else:  # neutral
                            asset_score = 50

                        # 保存资产趋势信息
                        asset_trends[asset] = {
                            "trend": trend,
                            "strength": trend_strength,
                            "risk_level": risk_level,
                            "score": asset_score,
                        }

                        # 累加趋势风险评分
                        trend_risk_score += asset_score
                        self.logger.debug(
                            f"资产{asset}的趋势分析结果: {trend} ({trend_strength}), 风险评分: {asset_score}"
                        )
                    except Exception as e:
                        self.logger.error(f"分析{asset}市场趋势时出错: {str(e)}")
                        # 使用默认评分
                        asset_trends[asset] = {
                            "trend": "neutral",
                            "strength": "moderate",
                            "risk_level": "MEDIUM",
                            "score": 50,
                        }
                        trend_risk_score += 50
                        self.logger.debug(
                            f"资产{asset}使用默认趋势分析结果: neutral (moderate), 风险评分: 50"
                        )
            else:
                self.logger.info("AI预测器不可用，使用默认市场趋势分析")
                # 如果AI预测器不可用，为每个资产使用默认评分
                for asset in assets:
                    asset_trends[asset] = {
                        "trend": "neutral",
                        "strength": "moderate",
                        "risk_level": "MEDIUM",
                        "score": 50,
                    }
                    trend_risk_score += 50

            # 计算平均趋势风险评分
            if assets:
                trend_risk_score /= len(assets)

            # 生成描述
            if trend_risk_score > 70:
                description = "投资组合中的资产整体呈现强烈下跌趋势，市场风险较高"
                trend = "上升"
            elif trend_risk_score > 50:
                description = "投资组合中的资产整体呈现轻微下跌趋势，市场风险中等"
                trend = "稳定"
            elif trend_risk_score > 30:
                description = "投资组合中的资产整体呈现轻微上涨趋势，市场风险中等"
                trend = "稳定"
            else:
                description = "投资组合中的资产整体呈现强烈上涨趋势，市场风险较低"
                trend = "下降"

            return self.create_risk_factor(
                risk_type="MARKET",
                factor_name="市场趋势",
                score=trend_risk_score,
                weight=0.3,
                description=description,
                trend=trend,
                data_points=[
                    {"asset": asset, **data} for asset, data in asset_trends.items()
                ],
            )

        except Exception as e:
            self.logger.error(f"分析市场趋势风险时出错: {str(e)}")
            # 返回默认风险因子
            return self.create_risk_factor(
                risk_type="MARKET",
                factor_name="市场趋势",
                score=50,  # 默认中等风险
                weight=0.3,
                description="市场趋势分析失败，使用默认中等风险评分",
                trend="稳定",
                data_points=[],
            )

    async def _analyze_correlation_risk(
        self, positions: List[Dict[str, Any]]
    ) -> Optional[RiskFactor]:
        """分析市场相关性风险"""
        try:
            if not self.blockchain_service:
                self.logger.warning("区块链服务未初始化，无法获取资产相关性数据")
                return None

            # 提取资产列表
            assets = []
            asset_values = {}
            for pos in positions:
                # 尝试从tokenList获取更精确的代币信息
                if pos.get("tokenList"):
                    for token in pos.get("tokenList", []):
                        token_symbol = token.get("tokenSymbol", "")
                        if token_symbol and token_symbol not in assets:
                            assets.append(token_symbol)
                            asset_values[token_symbol] = 0
                        if token_symbol:
                            # 使用代币在池中的比例分配价值
                            token_value = pos.get("amount", 0) * (
                                1 / len(pos.get("tokenList", []))
                            )
                            asset_values[token_symbol] = (
                                asset_values.get(token_symbol, 0) + token_value
                            )
                else:
                    # 如果没有tokenList，使用资产名称
                    asset = pos.get("asset", "Unknown").split("/")[
                        0
                    ]  # 处理流动性池资产格式
                    if asset not in assets:
                        assets.append(asset)
                        asset_values[asset] = 0
                    asset_values[asset] += pos.get("amount", 0)

            # 如果资产数量少于2，无法计算相关性
            if len(assets) < 2:
                return None

            # 尝试使用AI服务进行资产相关性分析
            if self.ai_service:
                try:
                    self.logger.info(f"使用AI服务分析{len(assets)}个资产的相关性风险")
                    # 准备AI分析的数据
                    total_value = sum(asset_values.values())
                    ai_input_data = {
                        "assets": list(assets),
                        "weights": {
                            asset: (value / total_value if total_value > 0 else 0)
                            for asset, value in asset_values.items()
                        },
                        "analysis_type": "correlation_risk",
                    }

                    # 使用AI服务进行分析
                    ai_analysis = await self.ai_service.analyze_with_predictor(
                        analysis_type="correlation_risk", data=ai_input_data
                    )

                    # 提取AI分析结果
                    if ai_analysis and "risk_score" in ai_analysis:
                        risk_score = ai_analysis.get("risk_score", 50)
                        description = ai_analysis.get("description", "资产相关性分析")
                        trend = ai_analysis.get("trend", "稳定")
                        data_points = ai_analysis.get("data_points", [])

                        self.logger.info(f"AI相关性分析完成，风险评分: {risk_score}")
                        return self.create_risk_factor(
                            risk_type=RiskType.MARKET.value,
                            factor_name="资产相关性风险",
                            score=risk_score,
                            weight=0.2,
                            description=description,
                            trend=trend,
                            data_points=data_points,
                            metadata={
                                "assets": assets,
                                "ai_analysis": ai_analysis,
                            },
                        )
                    else:
                        self.logger.warning("AI相关性分析结果不完整，将使用传统方法")
                except Exception as e:
                    self.logger.error(f"使用AI分析资产相关性风险时出错: {str(e)}")
                    self.logger.info("将使用传统方法进行资产相关性风险分析")
                    # 如果AI分析失败，继续使用传统方法
            else:
                self.logger.info("AI服务不可用，使用传统方法进行资产相关性风险分析")

            # 如果AI分析失败或不可用，尝试使用区块链服务获取历史数据计算相关性
            correlation_matrix = {}
            high_correlation_pairs = []
            avg_correlation = 0
            correlation_count = 0

            # 获取历史价格数据并计算相关性
            for i in range(len(assets)):
                for j in range(i + 1, len(assets)):
                    asset1 = assets[i]
                    asset2 = assets[j]

                    try:
                        # 获取资产1的历史数据
                        historical_data1 = (
                            await self.blockchain_service.get_asset_historical_data(
                                asset1
                            )
                        )
                        # 获取资产2的历史数据
                        historical_data2 = (
                            await self.blockchain_service.get_asset_historical_data(
                                asset2
                            )
                        )

                        if (
                            historical_data1 is not None
                            and not historical_data1.empty
                            and historical_data2 is not None
                            and not historical_data2.empty
                        ):
                            # 确保两个数据集有相同的日期
                            common_dates = set(historical_data1.index).intersection(
                                set(historical_data2.index)
                            )
                            if len(common_dates) > 5:  # 至少需要5个共同的数据点
                                # 提取共同日期的价格数据
                                prices1 = [
                                    historical_data1.loc[date, "price"]
                                    for date in common_dates
                                ]
                                prices2 = [
                                    historical_data2.loc[date, "price"]
                                    for date in common_dates
                                ]

                                # 计算相关系数
                                correlation = np.corrcoef(prices1, prices2)[0, 1]

                                # 存储相关系数
                                if asset1 not in correlation_matrix:
                                    correlation_matrix[asset1] = {}
                                correlation_matrix[asset1][asset2] = correlation

                                # 累加相关系数
                                avg_correlation += abs(correlation)
                                correlation_count += 1

                                # 检查高相关性对
                                if abs(correlation) > 0.7:
                                    high_correlation_pairs.append(
                                        {
                                            "asset1": asset1,
                                            "asset2": asset2,
                                            "correlation": correlation,
                                        }
                                    )
                    except Exception as e:
                        self.logger.error(
                            f"计算{asset1}和{asset2}的相关性时出错: {str(e)}"
                        )

            # 如果没有计算出任何相关系数，使用默认评分
            if correlation_count == 0:
                correlation_score = 50  # 默认中等风险
                description = "无法计算资产间的相关性，使用默认中等风险评分"
                trend = "稳定"
            else:
                # 计算平均相关系数
                avg_correlation = avg_correlation / correlation_count

                # 根据平均相关系数计算风险评分 (0-100)
                # 相关性越高，风险越大
                correlation_score = min(100, avg_correlation * 100)

                # 生成描述
                if correlation_score > 75:
                    description = "投资组合中资产高度相关，缺乏多样性保护"
                    trend = "上升"
                elif correlation_score > 50:
                    description = "投资组合中资产相关性较高，多样化效果有限"
                    trend = "稳定"
                elif correlation_score > 25:
                    description = "投资组合中资产相关性适中，有一定多样化效果"
                    trend = "稳定"
                else:
                    description = "投资组合中资产相关性低，多样化效果良好"
                    trend = "下降"

                # 添加高相关性对的信息
                if high_correlation_pairs:
                    description += f"，发现{len(high_correlation_pairs)}对高相关性资产"

            # 构建数据点
            data_points = [
                {
                    "asset_pair": f"{pair['asset1']}-{pair['asset2']}",
                    "correlation": pair["correlation"],
                }
                for pair in high_correlation_pairs
            ]
            data_points.append({"avg_correlation": avg_correlation})

            return self.create_risk_factor(
                risk_type=RiskType.MARKET.value,
                factor_name="资产相关性风险",
                score=correlation_score,
                weight=0.2,
                description=description,
                trend=trend,
                data_points=data_points,
                metadata={"correlation_matrix": correlation_matrix},
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
        # 尝试使用AI服务生成个性化建议
        ai_recommendations = await self._get_ai_recommendations(risk_factors)
        if ai_recommendations:
            return ai_recommendations

        recommendations = []

        # 根据风险因子生成建议
        for factor in risk_factors:
            if factor.factor_name == "资产集中度风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合资产过于集中，建议大幅分散投资到更多不同的资产，降低单一资产风险"
                    )
                    recommendations.append(
                        "考虑设置单一资产最大持仓比例限制，如不超过总资产的20%"
                    )
                    recommendations.append(
                        "增加不同类别的资产，如稳定币、大型代币、中小型代币的组合配置"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合资产集中度较高，建议适当分散投资，降低主要资产的配置比例"
                    )
                    recommendations.append(
                        "关注主要持仓资产的市场风险，考虑逐步调整资产配置"
                    )
                else:
                    recommendations.append(
                        "投资组合资产分散度良好，继续保持当前的多元化投资策略"
                    )

                # 检查是否有特别集中的资产
                high_concentration_assets = []
                for data_point in factor.data_points:
                    if data_point.get("percentage", 0) > 0.3:  # 占比超过30%
                        high_concentration_assets.append(data_point.get("asset", ""))

                if high_concentration_assets:
                    assets_str = ", ".join(high_concentration_assets[:3])
                    if len(high_concentration_assets) > 3:
                        assets_str += f" 等{len(high_concentration_assets)}个资产"
                    recommendations.append(
                        f"特别关注以下高集中度资产: {assets_str}，考虑降低其配置比例"
                    )

            elif factor.factor_name == "市场波动性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合波动性风险较高，建议增加稳定币比例或使用对冲策略"
                    )
                    recommendations.append("考虑设置止损策略，限制单次下跌的最大损失")
                    recommendations.append(
                        "关注高波动性资产的市场动态，在极端波动时考虑减仓"
                    )
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合波动性风险中等，建议关注市场波动指标，适时调整仓位"
                    )
                    recommendations.append(
                        "考虑增加低波动性资产的比例，平衡投资组合风险"
                    )
                else:
                    recommendations.append(
                        "投资组合波动性风险较低，继续保持当前的风险管理策略"
                    )

                # 检查是否有特别波动的资产
                high_volatility_assets = []
                for data_point in factor.data_points:
                    if data_point.get("value", 0) > 15:  # 波动率超过15%
                        high_volatility_assets.append(data_point.get("name", ""))

                if high_volatility_assets:
                    assets_str = ", ".join(high_volatility_assets[:3])
                    if len(high_volatility_assets) > 3:
                        assets_str += f" 等{len(high_volatility_assets)}个资产"
                    recommendations.append(
                        f"特别关注以下高波动性资产: {assets_str}，考虑降低其配置比例或设置更严格的止损"
                    )

            elif factor.factor_name == "市场趋势":
                if factor.score > 70:
                    recommendations.append(
                        "市场下跌趋势明显，建议减少风险敞口或设置止损"
                    )
                    recommendations.append("考虑增加稳定币比例，等待更好的入场时机")
                    recommendations.append("关注市场反转信号，避免在下跌趋势中追加投资")
                elif factor.score > 50:
                    recommendations.append(
                        "市场趋势偏弱，建议谨慎投资，关注技术指标变化"
                    )
                    recommendations.append("考虑分批建仓策略，避免一次性投入过多资金")
                elif factor.score > 30:
                    recommendations.append(
                        "市场趋势偏强，可以考虑适度增加仓位，但仍需关注风险"
                    )
                    recommendations.append("设置止盈策略，锁定部分收益")
                else:
                    recommendations.append(
                        "市场上涨趋势明显，可以考虑适度增加仓位，但注意设置止盈"
                    )

                # 检查是否有特别强的下跌趋势资产
                bearish_assets = []
                for data_point in factor.data_points:
                    if (
                        data_point.get("trend") == "bearish"
                        and data_point.get("strength") == "strong"
                    ):
                        bearish_assets.append(data_point.get("asset", ""))

                if bearish_assets:
                    assets_str = ", ".join(bearish_assets[:3])
                    if len(bearish_assets) > 3:
                        assets_str += f" 等{len(bearish_assets)}个资产"
                    recommendations.append(
                        f"特别关注以下强下跌趋势资产: {assets_str}，考虑减仓或设置止损"
                    )

            elif factor.factor_name == "资产相关性风险":
                if factor.score > 70:
                    recommendations.append(
                        "投资组合中资产高度相关，建议增加低相关性资产，如不同类别或不同链上的资产"
                    )
                    recommendations.append(
                        "考虑引入对冲策略，降低整体投资组合的系统性风险"
                    )
                    recommendations.append("关注宏观经济因素对高相关性资产的共同影响")
                elif factor.score > 50:
                    recommendations.append(
                        "投资组合中资产相关性较高，建议适当增加低相关性资产"
                    )
                    recommendations.append("关注市场波动对相关性高的资产组合的影响")
                else:
                    recommendations.append(
                        "投资组合资产相关性适中或较低，继续保持当前的多元化策略"
                    )

                # 检查是否有高相关性对
                high_correlation_pairs = []
                for data_point in factor.data_points:
                    if "asset_pair" in data_point and "correlation" in data_point:
                        if abs(data_point.get("correlation", 0)) > 0.8:  # 相关性超过0.8
                            high_correlation_pairs.append(
                                data_point.get("asset_pair", "")
                            )

                if high_correlation_pairs:
                    pairs_str = ", ".join(high_correlation_pairs[:3])
                    if len(high_correlation_pairs) > 3:
                        pairs_str += f" 等{len(high_correlation_pairs)}对资产"
                    recommendations.append(
                        f"特别关注以下高相关性资产对: {pairs_str}，考虑减少其中一个资产的配置"
                    )

        # 添加一般性建议
        if not recommendations:
            recommendations.append("定期检查市场状况，及时调整投资策略")
            recommendations.append("关注宏观经济因素对加密货币市场的影响")
            recommendations.append("建立系统性的风险管理策略，包括止损和止盈计划")

        return recommendations

    async def _get_ai_recommendations(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """
        使用AI服务生成个性化建议

        Args:
            risk_factors: 风险因子列表

        Returns:
            AI生成的建议列表，如果AI服务不可用或失败则返回空列表
        """
        if not self.ai_service:
            return []

        try:
            self.logger.info("尝试使用AI服务生成个性化市场风险建议")

            # 准备输入数据
            risk_data = {
                "risk_factors": [
                    {
                        "factor_name": factor.factor_name,
                        "score": factor.score,
                        "description": factor.description,
                        "trend": factor.trend,
                        "data_points": factor.data_points,
                    }
                    for factor in risk_factors
                ],
                "analysis_type": "market_risk_recommendations",
            }

            # 调用AI服务
            ai_result = await self.ai_service.analyze_with_predictor(
                analysis_type="market_risk_recommendations", data=risk_data
            )

            # 提取建议
            if ai_result and "recommendations" in ai_result:
                recommendations = ai_result.get("recommendations", [])
                if recommendations:
                    self.logger.info(
                        f"AI服务成功生成{len(recommendations)}条市场风险建议"
                    )
                    return recommendations
                else:
                    self.logger.warning("AI服务返回的建议列表为空")
            else:
                self.logger.warning("AI服务返回的结果不包含建议")

            return []
        except Exception as e:
            self.logger.error(f"使用AI服务生成市场风险建议时出错: {str(e)}")
            return []

    async def get_monitoring_points(self, risk_factors: List[RiskFactor]) -> List[str]:
        """
        获取市场风险监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            监控点列表
        """
        # 尝试使用AI服务生成个性化监控点
        ai_monitoring_points = await self._get_ai_monitoring_points(risk_factors)
        if ai_monitoring_points:
            return ai_monitoring_points

        monitoring_points = []

        # 根据风险因子生成监控点
        for factor in risk_factors:
            if factor.factor_name == "资产集中度风险":
                if factor.score > 70:
                    monitoring_points.append(
                        "密切监控主要资产的价格波动和市场消息，设置价格预警"
                    )
                    monitoring_points.append("定期评估资产集中度，确保不超过设定的阈值")
                    monitoring_points.append(
                        "关注主要资产的流动性变化，确保在需要时能够快速调整仓位"
                    )
                elif factor.score > 40:
                    monitoring_points.append("定期监控主要资产的价格波动和市场消息")
                    monitoring_points.append("关注资产集中度的变化趋势")
                else:
                    monitoring_points.append(
                        "定期检查资产分布情况，确保维持良好的分散度"
                    )

            elif factor.factor_name == "市场波动性风险":
                if factor.score > 70:
                    monitoring_points.append(
                        "密切关注市场波动指标，如VIX或加密货币恐惧与贪婪指数"
                    )
                    monitoring_points.append(
                        "监控高波动性资产的价格变化，设置波动率预警"
                    )
                    monitoring_points.append("关注市场流动性变化，特别是在极端波动时期")
                elif factor.score > 40:
                    monitoring_points.append("定期关注市场波动指标和主要资产的波动率")
                    monitoring_points.append("监控投资组合的整体波动性变化")
                else:
                    monitoring_points.append(
                        "定期检查市场波动性状况，确保风险在可控范围内"
                    )

            elif factor.factor_name == "市场趋势":
                if factor.score > 70:
                    monitoring_points.append(
                        "密切跟踪主要技术指标，如移动平均线和RSI，关注趋势反转信号"
                    )
                    monitoring_points.append("监控市场情绪指标，如交易量和持仓比例变化")
                    monitoring_points.append("关注宏观经济事件对市场趋势的影响")
                elif factor.score > 40:
                    monitoring_points.append("定期跟踪主要技术指标和市场趋势变化")
                    monitoring_points.append("关注重要支撑位和阻力位的突破情况")
                else:
                    monitoring_points.append(
                        "定期检查市场趋势状况，关注潜在的趋势变化信号"
                    )

            elif factor.factor_name == "资产相关性风险":
                if factor.score > 70:
                    monitoring_points.append(
                        "密切关注投资组合的相关性矩阵变化，特别是在市场波动时期"
                    )
                    monitoring_points.append(
                        "监控高相关性资产对的价格变动，关注相关性突变"
                    )
                    monitoring_points.append("关注可能影响多个资产的系统性风险因素")
                elif factor.score > 40:
                    monitoring_points.append("定期评估投资组合的相关性矩阵")
                    monitoring_points.append("关注市场环境变化对资产相关性的影响")
                else:
                    monitoring_points.append(
                        "定期检查资产相关性状况，确保维持良好的多元化效果"
                    )

        # 添加一般性监控点
        if not monitoring_points:
            monitoring_points.append("定期检查市场整体状况和宏观经济指标")
            monitoring_points.append("关注重要的市场事件和政策变化")
            monitoring_points.append("定期评估投资组合的风险收益特征")

        return monitoring_points

    async def _get_ai_monitoring_points(
        self, risk_factors: List[RiskFactor]
    ) -> List[str]:
        """
        使用AI服务生成个性化监控点

        Args:
            risk_factors: 风险因子列表

        Returns:
            AI生成的监控点列表，如果AI服务不可用或失败则返回空列表
        """
        if not self.ai_service:
            return []

        try:
            self.logger.info("尝试使用AI服务生成个性化市场风险监控点")

            # 准备输入数据
            risk_data = {
                "risk_factors": [
                    {
                        "factor_name": factor.factor_name,
                        "score": factor.score,
                        "description": factor.description,
                        "trend": factor.trend,
                        "data_points": factor.data_points,
                    }
                    for factor in risk_factors
                ],
                "analysis_type": "market_risk_monitoring_points",
            }

            # 调用AI服务
            ai_result = await self.ai_service.analyze_with_predictor(
                analysis_type="market_risk_monitoring_points", data=risk_data
            )

            # 提取监控点
            if ai_result and "monitoring_points" in ai_result:
                monitoring_points = ai_result.get("monitoring_points", [])
                if monitoring_points:
                    self.logger.info(
                        f"AI服务成功生成{len(monitoring_points)}条市场风险监控点"
                    )
                    return monitoring_points
                else:
                    self.logger.warning("AI服务返回的监控点列表为空")
            else:
                self.logger.warning("AI服务返回的结果不包含监控点")

            return []
        except Exception as e:
            self.logger.error(f"使用AI服务生成市场风险监控点时出错: {str(e)}")
            return []
