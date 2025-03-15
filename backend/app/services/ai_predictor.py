# AI预测器服务

import httpx
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
from app.core.config import settings
from openai import OpenAI

logger = logging.getLogger("defi_risk.ai_predictor")


class AiPredictor:
    """AI预测器服务，提供高级风险分析和预测功能"""

    def __init__(self):
        """初始化AI预测器"""
        self.logger = logger
        # 初始化OpenAI客户端
        self.client = None
        try:
            client_http = httpx.Client(proxy="http://127.0.0.1:7890")
            if settings.OPENAI_API_KEY:
                self.client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_API_URL,
                    http_client=client_http,
                )
                self.logger.info("OpenAI客户端初始化成功")
            else:
                self.logger.warning("未设置OpenAI API密钥，AI预测功能将受限")
        except Exception as e:
            self.logger.error(f"初始化OpenAI客户端失败: {str(e)}")
        # 可以在这里添加模型加载或其他初始化逻辑

    def analyze_defi_protocol_risk(
        self, protocol_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析DeFi协议风险

        Args:
            protocol_data: 协议数据，包含基本分析和历史数据

        Returns:
            Dict: 风险分析结果
        """
        try:
            # 提取基本信息
            basic_analysis = protocol_data.get("basic_analysis", {})
            historical_tvl = protocol_data.get("historical_tvl", [])
            protocol_metadata = protocol_data.get("protocol_metadata", {})
            chain_distribution = protocol_data.get("chain_distribution", {})

            # 处理TVL数据
            tvl_df = self._process_tvl_data(historical_tvl)

            # 分析链分布
            chain_df = self._analyze_chain_distribution(chain_distribution)

            # 计算风险指标
            risk_metrics = self._calculate_risk_metrics(tvl_df, chain_df)

            # 分析TVL趋势
            tvl_trend = self._analyze_trend(tvl_df)

            # 计算最终风险评分
            risk_score = self._calculate_risk_score(risk_metrics)

            # 生成风险等级
            risk_level = self._get_risk_level(risk_score)

            # 生成建议
            recommendations = self._generate_recommendations(
                risk_score, risk_metrics, protocol_metadata
            )

            # 构建完整分析结果
            analysis_result = {
                "protocol_name": protocol_metadata.get("name", "未知协议"),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_metrics": risk_metrics,
                "tvl_trend": tvl_trend,
                "chain_analysis": chain_df.to_dict() if not chain_df.empty else {},
                "recommendations": recommendations,
                "confidence": 0.85,  # 置信度，可以根据数据质量动态调整
                "analysis_timestamp": datetime.now().isoformat(),
            }

            return analysis_result
        except Exception as e:
            self.logger.error(f"分析DeFi协议风险失败: {str(e)}")
            return {
                "error": f"分析失败: {str(e)}",
                "risk_score": 0,
                "risk_level": "未知",
                "recommendations": ["无法完成风险分析，请检查输入数据"],
            }

    def _process_tvl_data(self, tvl_history: List[Dict]) -> pd.DataFrame:
        """
        处理TVL历史数据

        Args:
            tvl_history: TVL历史数据列表

        Returns:
            pd.DataFrame: 处理后的TVL数据
        """
        try:
            if not tvl_history:
                return pd.DataFrame()

            # 创建DataFrame
            df = pd.DataFrame(tvl_history)

            # 确保日期列是datetime类型
            if "date" in df.columns:
                if not isinstance(df["date"].iloc[0], datetime):
                    df["date"] = pd.to_datetime(df["date"])

            # 排序
            df = df.sort_values("date")

            # 计算日变化率
            if "tvl" in df.columns and len(df) > 1:
                df["tvl_change"] = df["tvl"].pct_change()

                # 计算7日和30日移动平均
                df["tvl_ma7"] = df["tvl"].rolling(window=7, min_periods=1).mean()
                df["tvl_ma30"] = df["tvl"].rolling(window=30, min_periods=1).mean()

                # 计算波动率 (30日标准差)
                df["volatility"] = (
                    df["tvl_change"].rolling(window=30, min_periods=5).std()
                )

            return df
        except Exception as e:
            self.logger.error(f"处理TVL数据失败: {str(e)}")
            return pd.DataFrame()

    def _analyze_chain_distribution(self, chain_tvls: Dict) -> pd.DataFrame:
        """
        分析链分布

        Args:
            chain_tvls: 各链上的TVL数据

        Returns:
            pd.DataFrame: 链分布分析结果
        """
        try:
            if not chain_tvls:
                return pd.DataFrame()

            # 创建DataFrame
            chains = []
            tvls = []

            for chain, tvl in chain_tvls.items():
                chains.append(chain)
                tvls.append(tvl)

            df = pd.DataFrame({"chain": chains, "tvl": tvls})

            if not df.empty:
                # 计算总TVL
                total_tvl = df["tvl"].sum()

                # 计算各链占比
                df["percentage"] = df["tvl"] / total_tvl * 100

                # 计算集中度 (前两条链的占比)
                df = df.sort_values("tvl", ascending=False)
                top_chains_pct = (
                    df.iloc[0:2]["percentage"].sum() if len(df) >= 2 else 100
                )

                # 添加集中度指标
                df["concentration"] = top_chains_pct

            return df
        except Exception as e:
            self.logger.error(f"分析链分布失败: {str(e)}")
            return pd.DataFrame()

    def _calculate_risk_metrics(
        self, tvl_df: pd.DataFrame, chain_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        计算风险指标

        Args:
            tvl_df: TVL数据
            chain_df: 链分布数据

        Returns:
            Dict: 风险指标
        """
        metrics = {}

        try:
            # TVL相关指标
            if not tvl_df.empty and "tvl" in tvl_df.columns:
                # 当前TVL
                current_tvl = tvl_df["tvl"].iloc[-1] if len(tvl_df) > 0 else 0
                metrics["current_tvl"] = current_tvl

                # TVL增长率 (30日)
                if len(tvl_df) >= 30:
                    tvl_30d_ago = (
                        tvl_df["tvl"].iloc[-30]
                        if len(tvl_df) >= 30
                        else tvl_df["tvl"].iloc[0]
                    )
                    tvl_growth_30d = (
                        ((current_tvl / tvl_30d_ago) - 1) * 100
                        if tvl_30d_ago > 0
                        else 0
                    )
                    metrics["tvl_growth_30d"] = tvl_growth_30d

                # TVL波动率
                if "volatility" in tvl_df.columns:
                    recent_volatility = (
                        tvl_df["volatility"].iloc[-1]
                        if not pd.isna(tvl_df["volatility"].iloc[-1])
                        else 0
                    )
                    metrics["tvl_volatility"] = recent_volatility * 100  # 转为百分比

                # TVL趋势 (7日MA vs 30日MA)
                if "tvl_ma7" in tvl_df.columns and "tvl_ma30" in tvl_df.columns:
                    ma7 = tvl_df["tvl_ma7"].iloc[-1]
                    ma30 = tvl_df["tvl_ma30"].iloc[-1]

                    if ma30 > 0:
                        trend_strength = (ma7 / ma30 - 1) * 100
                        metrics["trend_strength"] = trend_strength

                        if trend_strength > 5:
                            metrics["trend_direction"] = "强势上升"
                        elif trend_strength > 0:
                            metrics["trend_direction"] = "上升"
                        elif trend_strength > -5:
                            metrics["trend_direction"] = "下降"
                        else:
                            metrics["trend_direction"] = "强势下降"
                    else:
                        metrics["trend_direction"] = "无法确定"

            # 链分布指标
            if not chain_df.empty:
                # 链数量
                metrics["chain_count"] = len(chain_df)

                # 链集中度
                if "concentration" in chain_df.columns:
                    metrics["chain_concentration"] = (
                        chain_df["concentration"].iloc[0] if len(chain_df) > 0 else 100
                    )

                # 主链依赖度
                if len(chain_df) > 0:
                    metrics["main_chain_dependency"] = (
                        chain_df["percentage"].iloc[0]
                        if "percentage" in chain_df.columns
                        else 100
                    )

            # 综合风险指标
            tvl_risk = self._calculate_tvl_risk(metrics.get("current_tvl", 0))
            volatility_risk = self._calculate_volatility_risk(
                metrics.get("tvl_volatility", 0)
            )
            concentration_risk = self._calculate_concentration_risk(
                metrics.get("chain_concentration", 100)
            )

            metrics["tvl_risk"] = tvl_risk
            metrics["volatility_risk"] = volatility_risk
            metrics["concentration_risk"] = concentration_risk

            return metrics
        except Exception as e:
            self.logger.error(f"计算风险指标失败: {str(e)}")
            return {"error": str(e)}

    def _calculate_tvl_risk(self, tvl: float) -> float:
        """计算基于TVL的风险分数 (0-100，越低风险越小)"""
        if tvl <= 0:
            return 100  # 最高风险

        # TVL越高，风险越低
        # 使用对数尺度，避免线性关系导致的偏差
        log_tvl = np.log10(max(tvl, 1))

        # 1百万以下: 高风险
        # 1千万: 中等风险
        # 1亿以上: 低风险
        if log_tvl >= 8:  # 1亿以上
            return max(0, 100 - (log_tvl - 8) * 20)
        elif log_tvl >= 7:  # 1千万以上
            return max(20, 100 - (log_tvl - 6) * 20)
        else:
            return min(100, 100 - (log_tvl - 5) * 20)

    def _calculate_volatility_risk(self, volatility: float) -> float:
        """计算基于波动率的风险分数 (0-100，越低风险越小)"""
        # 波动率越高，风险越高
        if volatility <= 1:
            return 10  # 非常稳定
        elif volatility <= 3:
            return 30  # 稳定
        elif volatility <= 7:
            return 50  # 中等波动
        elif volatility <= 15:
            return 70  # 高波动
        else:
            return 90  # 极高波动

    def _calculate_concentration_risk(self, concentration: float) -> float:
        """计算基于链集中度的风险分数 (0-100，越低风险越小)"""
        # 集中度越高，风险越高
        if concentration <= 60:
            return 20  # 分散部署
        elif concentration <= 80:
            return 50  # 中等集中
        elif concentration <= 95:
            return 70  # 高度集中
        else:
            return 90  # 单链依赖

    def _calculate_risk_score(self, metrics: Dict[str, Any]) -> float:
        """
        计算综合风险评分

        Args:
            metrics: 风险指标

        Returns:
            float: 风险评分 (0-100，越高风险越大)
        """
        try:
            # 权重设置
            weights = {
                "tvl_risk": 0.4,
                "volatility_risk": 0.3,
                "concentration_risk": 0.3,
            }

            # 计算加权风险分数
            risk_score = 0
            total_weight = 0

            for metric, weight in weights.items():
                if metric in metrics:
                    risk_score += metrics[metric] * weight
                    total_weight += weight

            # 归一化
            if total_weight > 0:
                risk_score = risk_score / total_weight
            else:
                risk_score = 50  # 默认中等风险

            return round(risk_score, 2)
        except Exception as e:
            self.logger.error(f"计算风险评分失败: {str(e)}")
            return 50  # 默认中等风险

    def _get_risk_level(self, risk_score: float) -> str:
        """
        根据风险评分获取风险等级

        Args:
            risk_score: 风险评分

        Returns:
            str: 风险等级
        """
        if risk_score < 20:
            return "极低"
        elif risk_score < 40:
            return "低"
        elif risk_score < 60:
            return "中"
        elif risk_score < 80:
            return "高"
        else:
            return "极高"

    def _analyze_trend(self, tvl_df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析TVL趋势

        Args:
            tvl_df: TVL数据

        Returns:
            Dict: 趋势分析结果
        """
        trend_analysis = {}

        try:
            if tvl_df.empty or "tvl" not in tvl_df.columns:
                return {"trend": "无法确定", "confidence": 0}

            # 获取最近的数据点
            recent_data = tvl_df.iloc[-30:] if len(tvl_df) >= 30 else tvl_df

            if len(recent_data) < 7:
                return {"trend": "数据不足", "confidence": 0}

            # 计算7日和30日移动平均线
            if "tvl_ma7" not in recent_data.columns:
                recent_data["tvl_ma7"] = (
                    recent_data["tvl"].rolling(window=7, min_periods=1).mean()
                )

            if "tvl_ma30" not in recent_data.columns and len(tvl_df) >= 30:
                recent_data["tvl_ma30"] = (
                    recent_data["tvl"].rolling(window=30, min_periods=1).mean()
                )

            # 获取最新值
            latest_tvl = recent_data["tvl"].iloc[-1]
            latest_ma7 = recent_data["tvl_ma7"].iloc[-1]
            latest_ma30 = (
                recent_data["tvl_ma30"].iloc[-1]
                if "tvl_ma30" in recent_data.columns
                else None
            )

            # 计算7日变化率
            if len(recent_data) >= 7:
                tvl_7d_ago = recent_data["tvl"].iloc[-7]
                change_7d = (
                    ((latest_tvl / tvl_7d_ago) - 1) * 100 if tvl_7d_ago > 0 else 0
                )
                trend_analysis["change_7d"] = round(change_7d, 2)

            # 计算30日变化率
            if len(recent_data) >= 30:
                tvl_30d_ago = recent_data["tvl"].iloc[-30]
                change_30d = (
                    ((latest_tvl / tvl_30d_ago) - 1) * 100 if tvl_30d_ago > 0 else 0
                )
                trend_analysis["change_30d"] = round(change_30d, 2)

            # 判断趋势
            if latest_ma30 and latest_ma30 > 0:
                # 使用MA7和MA30的关系判断趋势
                ma_ratio = latest_ma7 / latest_ma30

                if ma_ratio > 1.1:
                    trend = "强势上升"
                    confidence = 0.9
                elif ma_ratio > 1.02:
                    trend = "上升"
                    confidence = 0.8
                elif ma_ratio > 0.98:
                    trend = "稳定"
                    confidence = 0.7
                elif ma_ratio > 0.9:
                    trend = "下降"
                    confidence = 0.8
                else:
                    trend = "强势下降"
                    confidence = 0.9
            else:
                # 仅使用最近7天数据判断趋势
                if "change_7d" in trend_analysis:
                    change_7d = trend_analysis["change_7d"]

                    if change_7d > 10:
                        trend = "强势上升"
                        confidence = 0.7
                    elif change_7d > 2:
                        trend = "上升"
                        confidence = 0.6
                    elif change_7d > -2:
                        trend = "稳定"
                        confidence = 0.5
                    elif change_7d > -10:
                        trend = "下降"
                        confidence = 0.6
                    else:
                        trend = "强势下降"
                        confidence = 0.7
                else:
                    trend = "无法确定"
                    confidence = 0

            trend_analysis["trend"] = trend
            trend_analysis["confidence"] = confidence

            return trend_analysis
        except Exception as e:
            self.logger.error(f"分析TVL趋势失败: {str(e)}")
            return {"trend": "分析失败", "error": str(e), "confidence": 0}

    def _generate_recommendations(
        self,
        risk_score: float,
        metrics: Dict[str, Any],
        protocol_metadata: Dict[str, Any],
    ) -> List[str]:
        """
        生成投资建议

        Args:
            risk_score: 风险评分
            metrics: 风险指标
            protocol_metadata: 协议元数据

        Returns:
            List[str]: 投资建议列表
        """
        recommendations = []
        protocol_name = protocol_metadata.get("name", "该协议")

        # 基于风险评分的一般建议
        if risk_score < 20:
            recommendations.append(
                f"{protocol_name}风险极低，适合作为投资组合的核心配置。"
            )
        elif risk_score < 40:
            recommendations.append(f"{protocol_name}风险较低，可以考虑适量配置。")
        elif risk_score < 60:
            recommendations.append(f"{protocol_name}风险中等，建议谨慎参与并控制仓位。")
        elif risk_score < 80:
            recommendations.append(
                f"{protocol_name}风险较高，建议仅小额参与或等待风险降低。"
            )
        else:
            recommendations.append(
                f"{protocol_name}风险极高，建议避免参与或严格控制仓位。"
            )

        # 基于TVL的建议
        tvl = metrics.get("current_tvl", 0)
        if tvl < 1000000:  # 小于100万
            recommendations.append(
                f"协议TVL较小 (${tvl:,.2f})，流动性风险高，建议限制投资规模。"
            )
        elif tvl < 10000000:  # 小于1000万
            recommendations.append(f"协议TVL适中 (${tvl:,.2f})，建议关注流动性变化。")

        # 基于波动率的建议
        volatility = metrics.get("tvl_volatility", 0)
        if volatility > 10:
            recommendations.append(
                f"TVL波动率较高 ({volatility:.2f}%)，表明协议可能存在不稳定因素，建议密切关注。"
            )

        # 基于链分布的建议
        chain_concentration = metrics.get("chain_concentration", 0)
        if chain_concentration > 90:
            recommendations.append(
                "协议高度依赖单一链，存在较高的链风险，建议关注链安全性。"
            )

        # 基于趋势的建议
        trend_direction = metrics.get("trend_direction", "")
        if trend_direction == "强势上升":
            recommendations.append(
                "TVL呈强势上升趋势，表明用户信任度提高，可能是增加配置的好时机。"
            )
        elif trend_direction == "强势下降":
            recommendations.append(
                "TVL呈强势下降趋势，表明用户可能在撤离，建议谨慎观望。"
            )

        # 确保至少有3条建议
        if len(recommendations) < 3:
            recommendations.append(
                "建议定期关注协议更新和治理提案，及时了解潜在风险变化。"
            )
            recommendations.append(
                "考虑分散投资于多个不同类型的DeFi协议，降低单一协议风险。"
            )

        return recommendations

    def analyze_market_trend(
        self,
        historical_data: pd.DataFrame = None,
        asset: str = None,
        asset_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        分析市场趋势并预测价格走势，结合AI模型进行智能预测

        支持两种调用方式：
        1. 传入historical_data和asset参数，直接分析历史数据
        2. 传入asset_data参数，从中提取历史数据进行分析

        Args:
            historical_data: 资产历史价格数据DataFrame，包含price、volume等列
            asset: 资产名称或符号
            asset_data: 资产数据字典，包含历史价格等信息

        Returns:
            Dict: 市场趋势分析结果，包含AI预测
        """
        try:
            self.logger.info(
                f"开始分析{'未指定' if asset is None else asset}的市场趋势"
            )

            # 处理输入参数，确保有可用的历史数据
            if historical_data is None and asset_data is not None:
                if "historical_data" in asset_data:
                    historical_data = pd.DataFrame(asset_data["historical_data"])
                    if asset is None and "asset" in asset_data:
                        asset = asset_data["asset"]

            # 如果没有历史数据，返回基本分析结果
            if historical_data is None or historical_data.empty:
                self.logger.warning("没有提供历史数据，返回基本分析结果")
                return self._get_basic_market_analysis(asset)

            # 确保历史数据包含必要的列
            required_columns = ["price", "timestamp"]
            if not all(col in historical_data.columns for col in required_columns):
                self.logger.warning(f"历史数据缺少必要的列: {required_columns}")
                return self._get_basic_market_analysis(asset)

            # 准备市场数据
            prices, volumes, current_price, price_change_24h, volatility, rsi = (
                self._prepare_market_data(historical_data)
            )

            # 计算技术指标
            ma7 = np.mean(prices[-7:]) if len(prices) >= 7 else current_price
            ma30 = np.mean(prices[-30:]) if len(prices) >= 30 else current_price
            ma50 = np.mean(prices[-50:]) if len(prices) >= 50 else current_price
            ma200 = np.mean(prices[-200:]) if len(prices) >= 200 else current_price

            # 计算MACD
            macd, signal, hist = self.calculate_macd(prices)
            macd_trend = "看涨" if macd[-1] > signal[-1] else "看跌"

            # 计算布林带
            upper, middle, lower = self.calculate_bollinger_bands(prices)
            bb_position = self._get_bollinger_band_position(
                current_price, upper[-1], middle[-1], lower[-1]
            )

            # 分析成交量趋势
            volume_trend, volume_strength = (
                self._analyze_volume_trend(volumes)
                if len(volumes) > 0
                else ("未知", "未知")
            )

            # 计算支撑位和阻力位
            support_levels = self._calculate_support_levels(prices, current_price)
            resistance_levels = self._calculate_resistance_levels(prices, current_price)

            # 使用传统方法预测价格
            traditional_prediction_24h = self._predict_price(
                prices, 1, current_price, volatility
            )
            traditional_prediction_7d = self._predict_price(
                prices, 7, current_price, volatility
            )

            # 使用AI服务进行市场分析和预测
            ai_analysis = self._predict_with_ai_service(
                asset=asset if asset else "未知资产",
                current_price=current_price,
                price_change_24h=price_change_24h,
                volatility=volatility,
                rsi=rsi,
                ma7=ma7,
                ma30=ma30,
                macd_trend=macd_trend,
                bb_position=bb_position,
                volume_trend=volume_trend,
                volume_strength=volume_strength,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
            )

            # 确定整体趋势
            trend, confidence = self._determine_trend(
                current_price,
                ma7,
                ma30,
                ma50,
                ma200,
                rsi,
                macd_trend,
                bb_position,
                price_change_24h,
            )

            # 从AI分析中提取预测价格
            ai_prediction_24h = {
                "price": np.mean(ai_analysis["predicted_price_range"]["24h"]),
                "range": ai_analysis["predicted_price_range"]["24h"],
                "change_percent": (
                    np.mean(ai_analysis["predicted_price_range"]["24h"]) / current_price
                    - 1
                )
                * 100,
                "confidence": 0.8 if ai_analysis["trend_strength"] == "strong" else 0.6,
            }

            ai_prediction_7d = {
                "price": np.mean(ai_analysis["predicted_price_range"]["7d"]),
                "range": ai_analysis["predicted_price_range"]["7d"],
                "change_percent": (
                    np.mean(ai_analysis["predicted_price_range"]["7d"]) / current_price
                    - 1
                )
                * 100,
                "confidence": 0.7 if ai_analysis["trend_strength"] == "strong" else 0.5,
            }

            # 构建分析结果
            result = {
                "asset": asset,
                "current_price": current_price,
                "price_change_24h": price_change_24h,
                "trend": trend,
                "confidence": confidence,
                "volatility": volatility,
                "rsi": rsi,
                "technical_indicators": {
                    "ma7": ma7,
                    "ma30": ma30,
                    "ma50": ma50,
                    "ma200": ma200,
                    "macd": {
                        "value": macd[-1],
                        "signal": signal[-1],
                        "histogram": hist[-1],
                        "trend": macd_trend,
                    },
                    "bollinger_bands": {
                        "upper": upper[-1],
                        "middle": middle[-1],
                        "lower": lower[-1],
                        "position": bb_position,
                    },
                    "volume": {"trend": volume_trend, "strength": volume_strength},
                },
                "support_levels": support_levels,
                "resistance_levels": resistance_levels,
                "prediction": {
                    "traditional": {
                        "24h": traditional_prediction_24h,
                        "7d": traditional_prediction_7d,
                    },
                    "ai": {
                        "24h": ai_prediction_24h,
                        "7d": ai_prediction_7d,
                        "analysis": ai_analysis,
                    },
                    "combined": {
                        "24h": self._combine_predictions(
                            traditional_prediction_24h, ai_prediction_24h
                        ),
                        "7d": self._combine_predictions(
                            traditional_prediction_7d, ai_prediction_7d
                        ),
                    },
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "recommendations": ai_analysis["recommendations"],
            }

            self.logger.info(
                f"完成{asset}的市场趋势分析: {trend}, 置信度: {confidence}"
            )
            return result

        except Exception as e:
            self.logger.error(f"分析市场趋势时出错: {str(e)}")
            return self._get_basic_market_analysis(asset)

    def _get_basic_market_analysis(self, asset: str = None) -> Dict[str, Any]:
        """
        在没有足够数据时返回基本市场分析

        Args:
            asset: 资产名称

        Returns:
            Dict: 基本市场分析结果
        """
        return {
            "asset": asset if asset else "未知资产",
            "trend": "未知",
            "confidence": 0.0,
            "support_levels": [],
            "resistance_levels": [],
            "prediction_24h": {"price": 0, "range": [0, 0]},
            "prediction_7d": {"price": 0, "range": [0, 0]},
            "analysis_timestamp": datetime.now().isoformat(),
            "error": "没有足够的历史数据进行分析",
            "recommendations": ["需要更多历史数据才能提供准确的市场分析"],
        }

    def _get_bollinger_band_position(
        self, price: float, upper: float, middle: float, lower: float
    ) -> str:
        """
        确定价格在布林带中的位置

        Args:
            price: 当前价格
            upper: 上轨
            middle: 中轨
            lower: 下轨

        Returns:
            str: 价格位置描述
        """
        if price >= upper:
            return "超买"
        elif price <= lower:
            return "超卖"
        elif price > middle:
            return "上行区间"
        else:
            return "下行区间"

    def _analyze_volume_trend(self, volumes: np.ndarray) -> Tuple[str, str]:
        """
        分析成交量趋势

        Args:
            volumes: 成交量数据

        Returns:
            Tuple[str, str]: 成交量趋势和强度
        """
        if len(volumes) < 7:
            return "未知", "未知"

        # 计算近期成交量变化
        recent_volumes = volumes[-7:]
        avg_volume = np.mean(recent_volumes)
        latest_volume = recent_volumes[-1]

        # 判断趋势
        if latest_volume > avg_volume * 1.2:
            trend = "上升"
        elif latest_volume < avg_volume * 0.8:
            trend = "下降"
        else:
            trend = "稳定"

        # 判断强度
        volume_std = np.std(recent_volumes)
        volume_cv = volume_std / avg_volume if avg_volume > 0 else 0

        if volume_cv > 0.5:
            strength = "强"
        elif volume_cv > 0.2:
            strength = "中"
        else:
            strength = "弱"

        return trend, strength

    def _determine_trend(
        self,
        price: float,
        ma7: float,
        ma30: float,
        ma50: float,
        ma200: float,
        rsi: float,
        macd_trend: str,
        bb_position: str,
        price_change_24h: float,
    ) -> Tuple[str, float]:
        """
        综合各项指标确定整体趋势

        Args:
            price: 当前价格
            ma7: 7日均线
            ma30: 30日均线
            ma50: 50日均线
            ma200: 200日均线
            rsi: 相对强弱指标
            macd_trend: MACD趋势
            bb_position: 布林带位置
            price_change_24h: 24小时价格变化百分比

        Returns:
            Tuple[str, float]: 趋势和置信度
        """
        # 初始化得分和权重
        bullish_score = 0
        bearish_score = 0
        total_weight = 0

        # 均线权重
        ma_weight = 3
        total_weight += ma_weight

        # 均线交叉判断
        if price > ma7 > ma30:
            bullish_score += ma_weight
        elif price < ma7 < ma30:
            bearish_score += ma_weight

        # 长期趋势判断
        if ma50 > 0 and ma200 > 0:
            long_term_weight = 2
            total_weight += long_term_weight

            if ma50 > ma200:
                bullish_score += long_term_weight  # 金叉
            else:
                bearish_score += long_term_weight  # 死叉

        # RSI判断
        rsi_weight = 2
        total_weight += rsi_weight

        if rsi > 70:
            bearish_score += rsi_weight  # 超买
        elif rsi < 30:
            bullish_score += rsi_weight  # 超卖
        elif rsi > 50:
            bullish_score += rsi_weight * 0.5  # 偏强
        else:
            bearish_score += rsi_weight * 0.5  # 偏弱

        # MACD判断
        macd_weight = 2.5
        total_weight += macd_weight

        if macd_trend == "看涨":
            bullish_score += macd_weight
        else:
            bearish_score += macd_weight

        # 布林带判断
        bb_weight = 1.5
        total_weight += bb_weight

        if bb_position == "超卖":
            bullish_score += bb_weight
        elif bb_position == "超买":
            bearish_score += bb_weight
        elif bb_position == "上行区间":
            bullish_score += bb_weight * 0.7
        elif bb_position == "下行区间":
            bearish_score += bb_weight * 0.7

        # 24小时价格变化
        price_change_weight = 1
        total_weight += price_change_weight

        if price_change_24h > 5:
            bullish_score += price_change_weight
        elif price_change_24h < -5:
            bearish_score += price_change_weight

        # 计算最终得分和置信度
        if total_weight > 0:
            bullish_percentage = bullish_score / total_weight
            bearish_percentage = bearish_score / total_weight

            confidence = max(bullish_percentage, bearish_percentage)

            if bullish_percentage > bearish_percentage:
                if bullish_percentage > 0.7:
                    trend = "强势上升"
                else:
                    trend = "上升"
            else:
                if bearish_percentage > 0.7:
                    trend = "强势下降"
                else:
                    trend = "下降"
        else:
            trend = "未知"
            confidence = 0.0

        return trend, round(confidence, 2)

    def _predict_price(
        self, prices: np.ndarray, days: int, current_price: float, volatility: float
    ) -> Dict[str, Any]:
        """
        基于历史数据和波动率预测未来价格

        Args:
            prices: 历史价格数据
            days: 预测天数
            current_price: 当前价格
            volatility: 波动率

        Returns:
            Dict: 预测结果，包含预测价格和范围
        """
        if len(prices) < 7:
            return {"price": current_price, "range": [current_price, current_price]}

        # 计算价格趋势
        recent_prices = prices[-7:]
        price_trend = (recent_prices[-1] / recent_prices[0] - 1) / 7  # 日均变化率

        # 预测价格
        predicted_change = price_trend * days
        predicted_price = current_price * (1 + predicted_change)

        # 计算预测范围
        range_factor = volatility * np.sqrt(days) / 100
        lower_bound = predicted_price * (1 - range_factor)
        upper_bound = predicted_price * (1 + range_factor)

        return {
            "price": round(predicted_price, 2),
            "range": [round(lower_bound, 2), round(upper_bound, 2)],
            "change_percent": round(predicted_change * 100, 2),
        }

    def _generate_market_recommendations(
        self,
        trend: str,
        rsi: float,
        macd_trend: str,
        bb_position: str,
        volatility: float,
        asset: str = None,
    ) -> List[str]:
        """
        基于市场分析生成投资建议

        Args:
            trend: 整体趋势
            rsi: RSI值
            macd_trend: MACD趋势
            bb_position: 布林带位置
            volatility: 波动率
            asset: 资产名称

        Returns:
            List[str]: 投资建议列表
        """
        asset_name = asset if asset else "该资产"
        recommendations = []

        # 基于趋势的建议
        if trend == "强势上升":
            recommendations.append(
                f"{asset_name}呈强势上升趋势，可考虑适量买入或持有。"
            )
        elif trend == "上升":
            recommendations.append(f"{asset_name}呈上升趋势，可考虑分批买入策略。")
        elif trend == "下降":
            recommendations.append(
                f"{asset_name}呈下降趋势，建议谨慎，可考虑减仓或观望。"
            )
        elif trend == "强势下降":
            recommendations.append(
                f"{asset_name}呈强势下降趋势，建议暂时避险或考虑对冲策略。"
            )

        # 基于RSI的建议
        if rsi > 70:
            recommendations.append(
                f"RSI值为{rsi:.1f}，处于超买区间，短期可能面临回调风险。"
            )
        elif rsi < 30:
            recommendations.append(
                f"RSI值为{rsi:.1f}，处于超卖区间，可能出现技术性反弹。"
            )

        # 基于MACD的建议
        if macd_trend == "看涨" and trend.endswith("上升"):
            recommendations.append(
                "MACD指标显示看涨信号，与整体趋势一致，增强买入信心。"
            )
        elif macd_trend == "看跌" and trend.endswith("下降"):
            recommendations.append(
                "MACD指标显示看跌信号，与整体趋势一致，增强卖出信心。"
            )
        elif macd_trend == "看涨" and trend.endswith("下降"):
            recommendations.append(
                "MACD指标显示看涨信号，但与整体趋势不一致，建议等待更明确的信号。"
            )
        elif macd_trend == "看跌" and trend.endswith("上升"):
            recommendations.append(
                "MACD指标显示看跌信号，但与整体趋势不一致，建议保持谨慎。"
            )

        # 基于布林带的建议
        if bb_position == "超买":
            recommendations.append("价格处于布林带上轨以上，超买状态，注意回调风险。")
        elif bb_position == "超卖":
            recommendations.append("价格处于布林带下轨以下，超卖状态，可能出现反弹。")

        # 基于波动率的建议
        if volatility > 10:
            recommendations.append(
                f"波动率较高({volatility:.1f}%)，建议使用限价单而非市价单，并考虑设置止损。"
            )
        elif volatility < 3:
            recommendations.append(
                f"波动率较低({volatility:.1f}%)，市场相对稳定，适合长期持有策略。"
            )

        # 确保至少有3条建议
        if len(recommendations) < 3:
            recommendations.append(
                "建议关注重要的市场新闻和事件，它们可能对价格产生重大影响。"
            )
            recommendations.append("考虑使用分批买入/卖出策略，以分散市场时机风险。")

        return recommendations

    def calculate_macd(
        self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算MACD指标

        Args:
            prices: 价格数据
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: MACD线、信号线和柱状图
        """
        if len(prices) < max(fast, slow, signal):
            # 返回空数组
            empty = np.array([0])
            return empty, empty, empty

        # 计算EMA
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)

        # 计算MACD线
        macd_line = ema_fast - ema_slow

        # 计算信号线
        signal_line = self._calculate_ema(macd_line, signal)

        # 计算柱状图
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def calculate_bollinger_bands(
        self, prices: np.ndarray, window: int = 20, num_std: float = 2
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算布林带

        Args:
            prices: 价格数据
            window: 移动平均窗口
            num_std: 标准差倍数

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: 上轨、中轨和下轨
        """
        if len(prices) < window:
            # 返回空数组
            empty = np.array([prices[-1] if len(prices) > 0 else 0])
            return empty, empty, empty

        # 计算移动平均线
        middle_band = np.array(
            [
                np.mean(prices[max(0, i - window + 1) : i + 1])
                for i in range(len(prices))
            ]
        )

        # 计算标准差
        std = np.array(
            [np.std(prices[max(0, i - window + 1) : i + 1]) for i in range(len(prices))]
        )

        # 计算上下轨
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)

        return upper_band, middle_band, lower_band

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """
        计算指数移动平均

        Args:
            data: 数据
            period: 周期

        Returns:
            np.ndarray: EMA值
        """
        if len(data) < period:
            return np.array([np.mean(data)])

        ema = np.zeros_like(data)
        ema[0] = data[0]

        multiplier = 2 / (period + 1)

        for i in range(1, len(data)):
            ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]

        return ema

    def _calculate_support_levels(
        self, prices: np.ndarray, current_price: float
    ) -> List[float]:
        """
        计算支撑位

        Args:
            prices: 价格数据
            current_price: 当前价格

        Returns:
            List[float]: 支撑位列表
        """
        if len(prices) < 10:
            return []

        # 找出局部最低点
        local_mins = []
        for i in range(2, len(prices) - 2):
            if (
                prices[i] < prices[i - 1]
                and prices[i] < prices[i - 2]
                and prices[i] < prices[i + 1]
                and prices[i] < prices[i + 2]
            ):
                local_mins.append(prices[i])

        # 过滤出低于当前价格的支撑位
        support_levels = [price for price in local_mins if price < current_price]

        # 如果没有找到支撑位，使用简单的百分比方法
        if not support_levels:
            support_levels = [
                current_price * 0.95,
                current_price * 0.9,
                current_price * 0.85,
            ]

        # 排序并取前3个
        support_levels = sorted(support_levels, reverse=True)[:3]

        return [round(level, 2) for level in support_levels]

    def _calculate_resistance_levels(
        self, prices: np.ndarray, current_price: float
    ) -> List[float]:
        """
        计算阻力位

        Args:
            prices: 价格数据
            current_price: 当前价格

        Returns:
            List[float]: 阻力位列表
        """
        if len(prices) < 10:
            return []

        # 找出局部最高点
        local_maxs = []
        for i in range(2, len(prices) - 2):
            if (
                prices[i] > prices[i - 1]
                and prices[i] > prices[i - 2]
                and prices[i] > prices[i + 1]
                and prices[i] > prices[i + 2]
            ):
                local_maxs.append(prices[i])

        # 过滤出高于当前价格的阻力位
        resistance_levels = [price for price in local_maxs if price > current_price]

        # 如果没有找到阻力位，使用简单的百分比方法
        if not resistance_levels:
            resistance_levels = [
                current_price * 1.05,
                current_price * 1.1,
                current_price * 1.15,
            ]

        # 排序并取前3个
        resistance_levels = sorted(resistance_levels)[:3]

        return [round(level, 2) for level in resistance_levels]

    def analyze_portfolio_risk(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析投资组合风险

        Args:
            portfolio_data: 投资组合数据

        Returns:
            Dict: 投资组合风险分析结果
        """
        # 这里可以实现投资组合风险分析逻辑
        # 暂时返回一个示例结果
        return {
            "risk_score": 65,
            "risk_level": "中等",
            "diversification_score": 70,
            "concentration_risk": "中等",
            "volatility_exposure": "中等",
            "recommendations": [
                "考虑增加稳定币比例以降低整体波动性",
                "减少单一资产集中度，特别是高风险资产",
                "关注借贷头寸的健康因子，避免清算风险",
            ],
        }

    def _predict_with_ai_service(
        self,
        asset: str,
        current_price: float,
        price_change_24h: float,
        volatility: float,
        rsi: float,
        ma7: float,
        ma30: float,
        macd_trend: str,
        bb_position: str,
        volume_trend: str,
        volume_strength: str,
        support_levels: List[float],
        resistance_levels: List[float],
    ) -> Dict[str, Any]:
        """
        使用OpenAI服务进行市场分析和预测

        Args:
            asset: 资产名称
            current_price: 当前价格
            price_change_24h: 24小时价格变化百分比
            volatility: 波动率
            rsi: 相对强弱指标
            ma7: 7日均线
            ma30: 30日均线
            macd_trend: MACD趋势
            bb_position: 布林带位置
            volume_trend: 成交量趋势
            volume_strength: 成交量强度
            support_levels: 支撑位列表
            resistance_levels: 阻力位列表

        Returns:
            Dict: AI分析结果
        """
        try:
            # 构建市场分析提示
            prompt = f"""
分析以下{asset}资产的市场数据，并提供详细的趋势分析和预测：

基本指标：
- 当前价格: ${current_price:.2f}
- 24小时价格变化: {price_change_24h:.2f}%
- 波动率: {volatility:.2f}%
- RSI指标: {rsi:.2f}（超买>70，超卖<30）

技术指标：
- 7日均价: ${ma7:.2f}
- 30日均价: ${ma30:.2f}
- MACD趋势: {macd_trend}
- 布林带位置: {bb_position}

成交量分析：
- 成交量趋势: {volume_trend}
- 成交量强度: {volume_strength}

支撑位: {', '.join([f'${level:.2f}' for level in support_levels])}
阻力位: {', '.join([f'${level:.2f}' for level in resistance_levels])}

请提供以下JSON格式的分析结果：
{{
    "trend": "bullish/bearish/neutral",
    "trend_strength": "strong/moderate/weak",
    "risk_level": "HIGH/MEDIUM/LOW",
    "predicted_price_range": {{
        "24h": [最低预期价格, 最高预期价格],
        "7d": [最低预期价格, 最高预期价格]
    }},
    "technical_analysis": {{
        "ma_trend": "上升/下降/盘整",
        "macd_signal": "买入/卖出/观望",
        "bollinger_signal": "超买/超卖/中性",
        "volume_analysis": "放量/缩量/平稳"
    }},
    "risk_factors": [
        "主要风险因素1",
        "主要风险因素2",
        ...
    ],
    "trading_signals": [
        "交易信号1",
        "交易信号2",
        ...
    ],
    "key_levels": {{
        "support": [主要支撑位1, 主要支撑位2],
        "resistance": [主要阻力位1, 主要阻力位2],
        "stop_loss": 建议止损价格,
        "take_profit": [目标获利价格1, 目标获利价格2]
    }},
    "analysis_summary": "详细的市场分析总结",
    "recommendations": [
        "具体建议1",
        "具体建议2",
        ...
    ]
}}

注意：
1. 基于所有技术指标提供综合分析
2. 考虑价格、成交量和技术指标的配合
3. 给出明确的交易建议和风险控制措施
4. 分析要客观且有数据支持
5. 建议要具体且可操作
"""
            if self.client is not None:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个专业的DeFi风险分析师，擅长评估协议安全性、流动性和去中心化程度。请基于详细的数据指标和深度分析结果，提供全面的风险评估。重点关注技术指标和多维度风险因素。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                ai_analysis = json.loads(response.choices[0].message.content)
                self.logger.info(f"AI分析完成: {asset}")
                return ai_analysis

            return self._get_basic_ai_analysis(
                asset, current_price, price_change_24h, volatility, rsi
            )
        except Exception as e:
            self.logger.error(f"AI服务分析出错: {str(e)}")
            return self._get_basic_ai_analysis(
                asset, current_price, price_change_24h, volatility, rsi
            )

    def _get_basic_ai_analysis(
        self,
        asset: str,
        current_price: float,
        price_change_24h: float,
        volatility: float,
        rsi: float,
    ) -> Dict[str, Any]:
        """
        在AI服务不可用时提供基本分析

        Args:
            asset: 资产名称
            current_price: 当前价格
            price_change_24h: 24小时价格变化百分比
            volatility: 波动率
            rsi: 相对强弱指标

        Returns:
            Dict: 基本分析结果
        """
        # 根据基本指标确定趋势
        if price_change_24h > 5:
            trend = "bullish"
            trend_strength = "strong" if price_change_24h > 10 else "moderate"
        elif price_change_24h < -5:
            trend = "bearish"
            trend_strength = "strong" if price_change_24h < -10 else "moderate"
        else:
            trend = "neutral"
            trend_strength = "weak"

        # 根据RSI确定风险水平
        if rsi > 70:
            risk_level = "HIGH"
        elif rsi < 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # 预测价格范围
        range_factor_24h = volatility * 0.01
        range_factor_7d = volatility * 0.03

        return {
            "trend": trend,
            "trend_strength": trend_strength,
            "risk_level": risk_level,
            "predicted_price_range": {
                "24h": [
                    round(current_price * (1 - range_factor_24h), 2),
                    round(current_price * (1 + range_factor_24h), 2),
                ],
                "7d": [
                    round(current_price * (1 - range_factor_7d), 2),
                    round(current_price * (1 + range_factor_7d), 2),
                ],
            },
            "technical_analysis": {
                "ma_trend": "盘整",
                "macd_signal": "观望",
                "bollinger_signal": "中性",
                "volume_analysis": "平稳",
            },
            "risk_factors": ["AI服务不可用，分析有限", "仅基于基本指标进行预测"],
            "trading_signals": ["建议等待更多信号确认"],
            "key_levels": {
                "support": [
                    round(current_price * 0.95, 2),
                    round(current_price * 0.9, 2),
                ],
                "resistance": [
                    round(current_price * 1.05, 2),
                    round(current_price * 1.1, 2),
                ],
                "stop_loss": round(current_price * 0.93, 2),
                "take_profit": [
                    round(current_price * 1.07, 2),
                    round(current_price * 1.15, 2),
                ],
            },
            "analysis_summary": f"{asset}当前价格${current_price:.2f}，24小时变化{price_change_24h:.2f}%，波动率{volatility:.2f}%，RSI为{rsi:.2f}。由于AI服务不可用，此分析基于有限指标，建议谨慎参考。",
            "recommendations": [
                "建议等待更多技术确认",
                "控制仓位，设置止损",
                "关注市场新闻和事件",
            ],
        }

    def _prepare_market_data(
        self, historical_data: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, float, float, float, float]:
        """
        从历史数据中提取市场数据

        Args:
            historical_data: 历史价格数据DataFrame

        Returns:
            Tuple: 价格数组、成交量数组、当前价格、24小时价格变化、波动率、RSI
        """
        try:
            # 确保数据按时间排序
            if "timestamp" in historical_data.columns:
                historical_data = historical_data.sort_values("timestamp")

            # 提取价格数据
            prices = historical_data["price"].values

            # 提取成交量数据（如果有）
            volumes = (
                historical_data["volume"].values
                if "volume" in historical_data.columns
                else np.array([])
            )

            # 获取当前价格（最新价格）
            current_price = prices[-1]

            # 计算24小时价格变化
            if len(prices) >= 24:
                price_24h_ago = prices[-24] if len(prices) >= 24 else prices[0]
                price_change_24h = ((current_price / price_24h_ago) - 1) * 100
            else:
                # 如果没有足够的数据，使用可用数据计算
                first_price = prices[0]
                price_change_24h = ((current_price / first_price) - 1) * 100

            # 计算波动率（20日标准差）
            if len(prices) >= 20:
                returns = np.diff(prices) / prices[:-1]
                volatility = np.std(returns[-20:]) * 100 * np.sqrt(365)  # 年化波动率
            else:
                returns = (
                    np.diff(prices) / prices[:-1] if len(prices) > 1 else np.array([0])
                )
                volatility = np.std(returns) * 100 * np.sqrt(365)

            # 计算RSI
            rsi = self._calculate_rsi(prices)[-1] if len(prices) >= 14 else 50.0

            return prices, volumes, current_price, price_change_24h, volatility, rsi

        except Exception as e:
            self.logger.error(f"准备市场数据时出错: {str(e)}")
            # 返回基本数据
            if len(historical_data) > 0:
                prices = historical_data["price"].values
                return prices, np.array([]), prices[-1], 0.0, 5.0, 50.0
            else:
                return np.array([0]), np.array([]), 0.0, 0.0, 0.0, 50.0

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """
        计算相对强弱指标(RSI)

        Args:
            prices: 价格数组
            period: 计算周期

        Returns:
            np.ndarray: RSI值数组
        """
        if len(prices) <= period:
            return np.array([50.0])  # 默认中性值

        # 计算价格变化
        deltas = np.diff(prices)

        # 分离上涨和下跌
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # 初始化平均值
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        # 如果没有损失，RSI为100
        if avg_loss == 0:
            return np.array([100.0])

        # 计算初始RS和RSI
        rs = avg_gain / avg_loss
        rsi = np.zeros(len(prices))
        rsi[period] = 100 - (100 / (1 + rs))

        # 计算剩余的RSI值
        for i in range(period + 1, len(prices)):
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

            if avg_loss == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))

        return rsi
