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

    async def is_available(self) -> bool:
        """
        检查AI预测器是否可用

        Returns:
            bool: 预测器是否可用
        """
        try:
            # 检查OpenAI客户端是否初始化
            if self.client is None:
                self.logger.warning("OpenAI客户端未初始化")
                return False

            # 尝试发送一个简单的请求来测试连接
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个AI助手。"},
                    {"role": "user", "content": "测试连接"},
                ],
                max_tokens=5,
            )

            # 如果能获取到响应，说明服务可用
            if response and hasattr(response, "choices") and len(response.choices) > 0:
                self.logger.info("AI预测器可用")
                return True
            else:
                self.logger.warning("AI预测器测试失败，响应不完整")
                return False
        except Exception as e:
            self.logger.error(f"检查AI预测器可用性时出错: {str(e)}")
            return False

    def analyze_concentration_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析资产集中度风险

        Args:
            data: 包含资产分布的数据，格式为 {"assets": {"BTC": 0.4, "ETH": 0.3, ...}}

        Returns:
            Dict: 集中度风险分析结果
        """
        try:
            self.logger.info("开始分析资产集中度风险")

            # 提取资产分布
            assets = data.get("assets", {})
            if not assets:
                return {
                    "risk_score": 50,
                    "description": "无法分析资产集中度风险，未提供资产数据",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 计算赫芬达尔-赫希曼指数 (HHI)
            hhi = sum(value**2 for value in assets.values()) * 10000

            # 找出最大资产及其占比
            max_asset = max(assets.items(), key=lambda x: x[1])
            max_concentration = max_asset[1]

            # 计算风险评分
            if max_concentration > 0.7 or hhi > 6000:
                risk_score = 80  # 高风险
                description = f"投资组合过于集中在{max_asset[0]}，占比{max_concentration:.1%}，HHI={hhi:.0f}"
                trend = "上升"
            elif max_concentration > 0.5 or hhi > 3000:
                risk_score = 60  # 中高风险
                description = f"投资组合在{max_asset[0]}上的集中度较高，占比{max_concentration:.1%}，HHI={hhi:.0f}"
                trend = "稳定"
            elif max_concentration > 0.3 or hhi > 1500:
                risk_score = 40  # 中等风险
                description = f"投资组合在{max_asset[0]}上有一定集中度，占比{max_concentration:.1%}，HHI={hhi:.0f}"
                trend = "稳定"
            else:
                risk_score = 20  # 低风险
                description = f"投资组合分散良好，最大资产{max_asset[0]}占比{max_concentration:.1%}，HHI={hhi:.0f}"
                trend = "下降"

            # 构建数据点
            data_points = [
                {
                    "asset": asset,
                    "percentage": percentage,
                    "is_max_asset": asset == max_asset[0],
                }
                for asset, percentage in assets.items()
            ]

            return {
                "risk_score": risk_score,
                "description": description,
                "trend": trend,
                "data_points": data_points,
                "hhi": hhi,
                "max_concentration": max_concentration,
            }
        except Exception as e:
            self.logger.error(f"分析资产集中度风险时出错: {str(e)}")
            return {
                "risk_score": 50,
                "description": f"分析资产集中度风险时出错: {str(e)}",
                "trend": "稳定",
                "data_points": [],
            }

    def analyze_correlation_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析相关性风险

        Args:
            data: 包含资产相关性数据的字典

        Returns:
            Dict: 相关性风险分析结果
        """
        try:
            self.logger.info(f"开始分析相关性风险")

            # 提取相关类型
            correlation_type = data.get("correlation_type", "asset_correlation")

            if correlation_type == "asset_correlation":
                return self._analyze_asset_correlation(data)
            elif correlation_type == "protocol_correlation":
                return self._analyze_protocol_correlation(data)
            elif correlation_type == "investment_type_correlation":
                return self._analyze_investment_type_correlation(data)
            else:
                return self._analyze_asset_correlation(data)  # 默认分析资产相关性

        except Exception as e:
            self.logger.error(f"分析相关性风险失败: {str(e)}")
            return {
                "risk_score": 50,
                "description": f"相关性分析过程中出错: {str(e)}",
                "trend": "未知",
                "data_points": [],
            }

    def analyze_portfolio_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析投资组合风险，生成投资组合洞察

        Args:
            data: 包含钱包地址、头寸列表、风险分析结果的字典

        Returns:
            Dict: 包含洞察、建议和警告的分析结果
        """
        try:
            self.logger.info(f"开始分析投资组合风险和生成洞察")

            # 提取关键数据
            wallet_address = data.get("wallet_address", "未知钱包")
            positions = data.get("positions", [])
            risk_score = data.get("risk_score", 0)
            risk_level = data.get("risk_level", "未知")
            risk_metrics = data.get("risk_metrics", {})
            risk_factors = data.get("risk_factors", [])

            if not positions:
                return {
                    "insights": ["投资组合为空，无法进行分析"],
                    "recommendations": [
                        "开始投资以获取收益",
                        "从小额投资开始，逐步了解DeFi生态",
                    ],
                    "warnings": [],
                    "confidence": 0.9,
                }

            # 计算资产分布
            assets = {}
            protocols = {}
            investment_types = {}
            total_value = 0
            high_risk_positions = []
            liquidation_risk_positions = []

            for position in positions:
                asset = position.get("asset", "未知资产")
                protocol = position.get("protocol", "未知协议")
                invest_type = position.get("invest_type", 0)
                usd_value = float(position.get("usd_value", 0))

                # 累计资产价值
                if asset in assets:
                    assets[asset] += usd_value
                else:
                    assets[asset] = usd_value

                # 累计协议价值
                if protocol in protocols:
                    protocols[protocol] += usd_value
                else:
                    protocols[protocol] = usd_value

                # 累计投资类型价值
                invest_type_name = self._get_invest_type_name(invest_type)
                if invest_type_name in investment_types:
                    investment_types[invest_type_name] += usd_value
                else:
                    investment_types[invest_type_name] = usd_value

                total_value += usd_value

                # 检查高风险和清算风险头寸
                risk_score = position.get("risk_score", 0)
                health_factor = position.get("health_factor", 10)

                if risk_score > 70:
                    high_risk_positions.append(position)

                if health_factor < 1.5 and invest_type in [1, 2]:  # 借贷和杠杆头寸
                    liquidation_risk_positions.append(position)

            # 计算投资组合的关键指标
            insights = []
            recommendations = []
            warnings = []

            # 1. 资产集中度分析
            if total_value > 0:
                assets_sorted = sorted(
                    [(k, v) for k, v in assets.items()],
                    key=lambda x: x[1],
                    reverse=True,
                )
                if assets_sorted and assets_sorted[0][1] / total_value > 0.5:
                    top_asset = assets_sorted[0][0]
                    top_pct = assets_sorted[0][1] / total_value * 100
                    insights.append(
                        f"您的投资组合过于集中在{top_asset}，占总资产的{top_pct:.1f}%，增加了单一资产风险"
                    )
                    recommendations.append(
                        f"考虑将部分{top_asset}转换为其他资产，降低集中度至40%以下"
                    )

            # 2. 协议分散度分析
            if len(protocols) == 1:
                protocol_name = list(protocols.keys())[0]
                insights.append(
                    f"您的投资全部集中在{protocol_name}协议，缺乏协议多样性"
                )
                recommendations.append("考虑分散投资到2-3个不同的协议，降低协议风险")
            elif len(protocols) > 5:
                insights.append(
                    f"您的投资分散在{len(protocols)}个协议，管理成本可能较高"
                )
                recommendations.append("考虑合并部分小额投资，减少管理复杂度")

            # 3. 投资类型分析
            if (
                "借贷" in investment_types
                and investment_types.get("借贷", 0) / total_value > 0.4
            ):
                insights.append("借贷头寸占比过高，增加了清算风险")
                recommendations.append("减少借贷头寸的比例，确保不超过总资产的30%")

            if (
                "流动性挖矿" in investment_types
                and investment_types.get("流动性挖矿", 0) / total_value > 0.5
            ):
                insights.append("流动性挖矿占比较高，面临无常损失风险")
                recommendations.append(
                    "关注流动性池资产的相关性，选择相关性低的资产对提供流动性"
                )

            # 4. 风险警告
            if len(high_risk_positions) > 0:
                warnings.append(
                    f"检测到{len(high_risk_positions)}个高风险头寸，建议密切关注"
                )

            if len(liquidation_risk_positions) > 0:
                protocol_names = ", ".join(
                    set([p.get("protocol", "未知") for p in liquidation_risk_positions])
                )
                warnings.append(
                    f"{protocol_names}上的借贷头寸健康因子低于1.5，存在清算风险"
                )
                recommendations.append(
                    "立即补充抵押品或偿还部分债务，提高健康因子至2.0以上"
                )

            # 5. 基于风险指标的一般性建议
            market_risk = risk_metrics.get("market_risk", 0)
            liquidity_risk = risk_metrics.get("liquidity_risk", 0)

            if market_risk > 70:
                insights.append("当前市场风险较高，投资组合波动可能加剧")
                recommendations.append("考虑增加稳定币比例，对冲市场下行风险")

            if liquidity_risk > 70:
                insights.append("投资组合流动性风险较高，可能面临兑现困难")
                recommendations.append("增加高流动性资产的比例，确保资金灵活性")

            # 6. 稳定币分析
            stablecoin_assets = [
                "USDT",
                "USDC",
                "DAI",
                "BUSD",
                "TUSD",
                "USDP",
                "GUSD",
                "USDD",
                "FRAX",
                "sUSD",
            ]
            stablecoin_value = sum(assets.get(coin, 0) for coin in stablecoin_assets)
            stablecoin_ratio = stablecoin_value / total_value if total_value > 0 else 0

            if stablecoin_ratio < 0.1:
                insights.append(
                    f"稳定币比例较低({stablecoin_ratio:.1%})，缺乏市场波动缓冲"
                )
                recommendations.append("增加稳定币比例至少20%，作为市场波动的缓冲")
            elif stablecoin_ratio > 0.7:
                insights.append(
                    f"稳定币比例过高({stablecoin_ratio:.1%})，可能错过市场上涨机会"
                )
                recommendations.append("考虑将部分稳定币投入到收益较高的资产中")

            # 确保至少有三条洞察和三条建议
            if len(insights) < 3:
                default_insights = [
                    "投资组合综合风险评分处于中等水平，有优化空间",
                    "当前仓位分布相对均衡，但可进一步优化",
                    "考虑根据风险承受能力调整投资策略",
                ]
                insights.extend(default_insights[: 3 - len(insights)])

            if len(recommendations) < 3:
                default_recommendations = [
                    "定期检查投资组合风险，每月至少一次",
                    "关注市场趋势变化，及时调整投资策略",
                    "探索新的DeFi机会，但控制在总资产的10%以内",
                ]
                recommendations.extend(
                    default_recommendations[: 3 - len(recommendations)]
                )

            return {
                "insights": insights,
                "recommendations": recommendations,
                "warnings": warnings,
                "confidence": 0.85,
                "supporting_data": {
                    "asset_distribution": [
                        {"name": k, "value": v} for k, v in assets.items()
                    ],
                    "protocol_distribution": [
                        {"name": k, "value": v} for k, v in protocols.items()
                    ],
                    "investment_type_distribution": [
                        {"name": k, "value": v} for k, v in investment_types.items()
                    ],
                    "stablecoin_ratio": stablecoin_ratio,
                    "risk_level": risk_level,
                },
            }

        except Exception as e:
            self.logger.error(f"生成投资组合洞察失败: {str(e)}")
            return {
                "insights": [f"分析投资组合时出错: {str(e)}"],
                "recommendations": ["建议重新分析或联系技术支持"],
                "warnings": [],
                "confidence": 0.3,
            }

    def _get_invest_type_name(self, invest_type: int) -> str:
        """获取投资类型名称"""
        type_names = {
            0: "普通持有",
            1: "借贷",
            2: "杠杆",
            3: "流动性挖矿",
            4: "质押",
            5: "衍生品",
            6: "收益农场",
            7: "保险",
            8: "预言机",
            9: "跨链桥",
            10: "期权",
            11: "合成资产",
            12: "预测市场",
            13: "借贷池",
            14: "算法稳定币",
        }
        return type_names.get(invest_type, "其他")

    def generate_market_risk_recommendations(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据风险因子生成市场风险建议

        Args:
            data: 包含风险因子的数据，格式为 {"risk_factors": [{"factor_name": "...", "score": 75, ...}, ...]}

        Returns:
            Dict: 包含建议列表的结果
        """
        try:
            self.logger.info("开始生成市场风险建议")

            # 提取风险因子
            risk_factors = data.get("risk_factors", [])
            if not risk_factors:
                return {
                    "recommendations": [
                        "定期检查市场状况，及时调整投资策略",
                        "关注宏观经济因素对加密货币市场的影响",
                        "建立系统性的风险管理策略，包括止损和止盈计划",
                    ]
                }

            recommendations = []
            priority_recommendations = []

            # 根据风险因子生成建议
            for factor in risk_factors:
                factor_name = factor.get("factor_name", "")
                score = factor.get("score", 50)

                if "集中度" in factor_name:
                    if score > 70:
                        rec = "投资组合资产过于集中，建议大幅分散投资到更多不同的资产，降低单一资产风险"
                        recommendations.append(rec)
                        priority_recommendations.append(
                            {
                                "recommendation": rec,
                                "priority": "高",
                                "rationale": f"当前集中度风险评分为{score}，远高于安全阈值",
                            }
                        )

                        recommendations.append(
                            "考虑设置单一资产最大持仓比例限制，如不超过总资产的20%"
                        )
                        recommendations.append(
                            "增加不同类别的资产，如稳定币、大型代币、中小型代币的组合配置"
                        )
                    elif score > 50:
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

                elif "波动性" in factor_name:
                    if score > 70:
                        rec = "投资组合波动性风险较高，建议增加稳定币比例或使用对冲策略"
                        recommendations.append(rec)
                        priority_recommendations.append(
                            {
                                "recommendation": rec,
                                "priority": "高",
                                "rationale": f"当前波动性风险评分为{score}，市场波动加剧",
                            }
                        )

                        recommendations.append(
                            "考虑设置止损策略，限制单次下跌的最大损失"
                        )
                        recommendations.append(
                            "关注高波动性资产的市场动态，在极端波动时考虑减仓"
                        )
                    elif score > 50:
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

                elif "趋势" in factor_name:
                    if score > 70:
                        rec = "市场下跌趋势明显，建议减少风险敞口或设置止损"
                        recommendations.append(rec)
                        priority_recommendations.append(
                            {
                                "recommendation": rec,
                                "priority": "高",
                                "rationale": f"当前市场趋势风险评分为{score}，下跌趋势明显",
                            }
                        )

                        recommendations.append("考虑增加稳定币比例，等待更好的入场时机")
                        recommendations.append(
                            "关注市场反转信号，避免在下跌趋势中追加投资"
                        )
                    elif score > 50:
                        recommendations.append(
                            "市场趋势偏弱，建议谨慎投资，关注技术指标变化"
                        )
                        recommendations.append(
                            "考虑分批建仓策略，避免一次性投入过多资金"
                        )
                    elif score > 30:
                        recommendations.append(
                            "市场趋势偏强，可以考虑适度增加仓位，但仍需关注风险"
                        )
                        recommendations.append("设置止盈策略，锁定部分收益")
                    else:
                        recommendations.append(
                            "市场上涨趋势明显，可以考虑适度增加仓位，但注意设置止盈"
                        )

                elif "相关性" in factor_name:
                    if score > 70:
                        rec = "投资组合中资产高度相关，建议增加低相关性资产，如不同类别或不同链上的资产"
                        recommendations.append(rec)
                        priority_recommendations.append(
                            {
                                "recommendation": rec,
                                "priority": "中",
                                "rationale": f"当前相关性风险评分为{score}，资产多样化效果有限",
                            }
                        )

                        recommendations.append(
                            "考虑引入对冲策略，降低整体投资组合的系统性风险"
                        )
                        recommendations.append(
                            "关注宏观经济因素对高相关性资产的共同影响"
                        )
                    elif score > 50:
                        recommendations.append(
                            "投资组合中资产相关性较高，建议适当增加低相关性资产"
                        )
                        recommendations.append("关注市场波动对相关性高的资产组合的影响")
                    else:
                        recommendations.append(
                            "投资组合资产相关性适中或较低，继续保持当前的多元化策略"
                        )

            # 如果没有生成任何建议，添加一般性建议
            if not recommendations:
                recommendations = [
                    "定期检查市场状况，及时调整投资策略",
                    "关注宏观经济因素对加密货币市场的影响",
                    "建立系统性的风险管理策略，包括止损和止盈计划",
                ]

            # 确保建议不重复
            recommendations = list(set(recommendations))

            return {
                "recommendations": recommendations,
                "priority_recommendations": priority_recommendations,
            }
        except Exception as e:
            self.logger.error(f"生成市场风险建议时出错: {str(e)}")
            return {
                "recommendations": [
                    "定期检查市场状况，及时调整投资策略",
                    "关注宏观经济因素对加密货币市场的影响",
                    "建立系统性的风险管理策略，包括止损和止盈计划",
                ]
            }

    def generate_market_risk_monitoring_points(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据风险因子生成市场风险监控点

        Args:
            data: 包含风险因子的数据，格式为 {"risk_factors": [{"factor_name": "...", "score": 75, ...}, ...]}

        Returns:
            Dict: 包含监控点列表的结果
        """
        try:
            self.logger.info("开始生成市场风险监控点")

            # 提取风险因子
            risk_factors = data.get("risk_factors", [])
            if not risk_factors:
                return {
                    "monitoring_points": [
                        "定期检查市场整体状况和宏观经济指标",
                        "关注重要的市场事件和政策变化",
                        "定期评估投资组合的风险收益特征",
                    ]
                }

            monitoring_points = []
            priority_monitoring_points = []

            # 根据风险因子生成监控点
            for factor in risk_factors:
                factor_name = factor.get("factor_name", "")
                score = factor.get("score", 50)
                data_points = factor.get("data_points", [])

                if "集中度" in factor_name:
                    if score > 70:
                        # 提取主要资产
                        main_assets = []
                        for dp in data_points:
                            if dp.get("percentage", 0) > 0.2:  # 占比超过20%
                                main_assets.append(dp.get("asset", ""))

                        asset_str = (
                            "主要资产"
                            if not main_assets
                            else "、".join(main_assets[:2])
                        )

                        point = f"密切监控{asset_str}的价格波动和市场消息，设置价格预警"
                        monitoring_points.append(point)
                        priority_monitoring_points.append(
                            {
                                "point": point,
                                "priority": "高",
                                "frequency": "每日",
                                "threshold": "10%价格波动",
                            }
                        )

                        monitoring_points.append(
                            "定期评估资产集中度，确保不超过设定的阈值"
                        )
                        monitoring_points.append(
                            "关注主要资产的流动性变化，确保在需要时能够快速调整仓位"
                        )
                    elif score > 40:
                        monitoring_points.append("定期监控主要资产的价格波动和市场消息")
                        monitoring_points.append("关注资产集中度的变化趋势")
                    else:
                        monitoring_points.append(
                            "定期检查资产分布情况，确保维持良好的分散度"
                        )

                elif "波动性" in factor_name:
                    if score > 70:
                        point = "密切关注市场波动指标，如VIX或加密货币恐惧与贪婪指数"
                        monitoring_points.append(point)
                        priority_monitoring_points.append(
                            {
                                "point": point,
                                "priority": "高",
                                "frequency": "每日",
                                "threshold": "指数低于20或高于80",
                            }
                        )

                        # 提取高波动性资产
                        volatile_assets = []
                        for dp in data_points:
                            if dp.get("value", 0) > 15:  # 波动率超过15%
                                volatile_assets.append(dp.get("name", ""))

                        if volatile_assets:
                            asset_str = "、".join(volatile_assets[:2])
                            monitoring_points.append(
                                f"监控{asset_str}等高波动性资产的价格变化，设置波动率预警"
                            )
                        else:
                            monitoring_points.append(
                                "监控高波动性资产的价格变化，设置波动率预警"
                            )

                        monitoring_points.append(
                            "关注市场流动性变化，特别是在极端波动时期"
                        )
                    elif score > 40:
                        monitoring_points.append(
                            "定期关注市场波动指标和主要资产的波动率"
                        )
                        monitoring_points.append("监控投资组合的整体波动性变化")
                    else:
                        monitoring_points.append(
                            "定期检查市场波动性状况，确保风险在可控范围内"
                        )

                elif "趋势" in factor_name:
                    if score > 70:
                        point = (
                            "密切跟踪主要技术指标，如移动平均线和RSI，关注趋势反转信号"
                        )
                        monitoring_points.append(point)
                        priority_monitoring_points.append(
                            {
                                "point": point,
                                "priority": "高",
                                "frequency": "每日",
                                "threshold": "MA交叉或RSI超买/超卖",
                            }
                        )

                        monitoring_points.append(
                            "监控市场情绪指标，如交易量和持仓比例变化"
                        )
                        monitoring_points.append("关注宏观经济事件对市场趋势的影响")
                    elif score > 40:
                        monitoring_points.append("定期跟踪主要技术指标和市场趋势变化")
                        monitoring_points.append("关注重要支撑位和阻力位的突破情况")
                    else:
                        monitoring_points.append(
                            "定期检查市场趋势状况，关注潜在的趋势变化信号"
                        )

                elif "相关性" in factor_name:
                    if score > 70:
                        point = "密切关注投资组合的相关性矩阵变化，特别是在市场波动时期"
                        monitoring_points.append(point)
                        priority_monitoring_points.append(
                            {
                                "point": point,
                                "priority": "中",
                                "frequency": "每周",
                                "threshold": "相关系数变化>0.2",
                            }
                        )

                        # 提取高相关性对
                        high_corr_pairs = []
                        for dp in data_points:
                            if "asset_pair" in dp and "correlation" in dp:
                                if dp.get("correlation", 0) > 0.8:
                                    high_corr_pairs.append(dp.get("asset_pair", ""))

                        if high_corr_pairs:
                            pair_str = "、".join(high_corr_pairs[:2])
                            monitoring_points.append(
                                f"监控{pair_str}等高相关性资产对的价格变动，关注相关性突变"
                            )
                        else:
                            monitoring_points.append(
                                "监控高相关性资产对的价格变动，关注相关性突变"
                            )

                        monitoring_points.append("关注可能影响多个资产的系统性风险因素")
                    elif score > 40:
                        monitoring_points.append("定期评估投资组合的相关性矩阵")
                        monitoring_points.append("关注市场环境变化对资产相关性的影响")
                    else:
                        monitoring_points.append(
                            "定期检查资产相关性状况，确保维持良好的多元化效果"
                        )

            # 如果没有生成任何监控点，添加一般性监控点
            if not monitoring_points:
                monitoring_points = [
                    "定期检查市场整体状况和宏观经济指标",
                    "关注重要的市场事件和政策变化",
                    "定期评估投资组合的风险收益特征",
                ]

            # 确保监控点不重复
            monitoring_points = list(set(monitoring_points))

            return {
                "monitoring_points": monitoring_points,
                "priority_monitoring_points": priority_monitoring_points,
            }
        except Exception as e:
            self.logger.error(f"生成市场风险监控点时出错: {str(e)}")
            return {
                "monitoring_points": [
                    "定期检查市场整体状况和宏观经济指标",
                    "关注重要的市场事件和政策变化",
                    "定期评估投资组合的风险收益特征",
                ]
            }

    def analyze_generic(
        self, analysis_type: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        通用分析方法，用于处理未专门实现的分析类型

        Args:
            analysis_type: 分析类型
            data: 分析数据

        Returns:
            Dict: 分析结果
        """
        self.logger.info(f"使用通用分析方法处理分析类型: {analysis_type}")

        # 根据分析类型返回基本结果
        if "risk" in analysis_type.lower():
            return {
                "risk_score": 50,
                "description": f"使用通用分析方法处理{analysis_type}",
                "trend": "稳定",
                "data_points": [],
            }
        elif "recommendation" in analysis_type.lower():
            return {
                "recommendations": [
                    "定期检查市场状况，及时调整投资策略",
                    "关注宏观经济因素对加密货币市场的影响",
                    "建立系统性的风险管理策略，包括止损和止盈计划",
                ]
            }
        elif "monitoring" in analysis_type.lower():
            return {
                "monitoring_points": [
                    "定期检查市场整体状况和宏观经济指标",
                    "关注重要的市场事件和政策变化",
                    "定期评估投资组合的风险收益特征",
                ]
            }
        else:
            return {"message": f"未找到专门的分析方法处理{analysis_type}", "data": data}

    def analyze_assets_correlation(
        self, historical_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        分析资产相关性风险（基于历史数据）

        Args:
            historical_data: 包含资产历史数据的字典，格式为 {"BTC": DataFrame, "ETH": DataFrame, ...}

        Returns:
            Dict: 相关性风险分析结果
        """
        try:
            self.logger.info("开始分析资产历史数据相关性风险")

            # 提取资产列表
            assets = list(historical_data.keys())

            if not assets or len(assets) < 2:
                return {
                    "risk_score": 50,
                    "description": "无法分析资产相关性风险，资产数量不足",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 计算相关性矩阵
            correlation_matrix = {}
            high_correlation_pairs = []
            avg_correlation = 0
            correlation_count = 0

            # 生成相关性矩阵
            for i in range(len(assets)):
                asset1 = assets[i]
                correlation_matrix[asset1] = {}

                for j in range(i + 1, len(assets)):
                    asset2 = assets[j]

                    # 计算相关系数（基于历史价格数据）
                    correlation = 0

                    # 如果两个资产都有历史数据，计算实际相关性
                    df1 = historical_data[asset1]
                    df2 = historical_data[asset2]

                    if not df1.empty and not df2.empty:
                        # 确保两个数据集有相同的时间索引
                        if "timestamp" in df1.columns and "timestamp" in df2.columns:
                            # 合并数据集
                            merged = pd.merge(
                                df1[["timestamp", "price"]],
                                df2[["timestamp", "price"]],
                                on="timestamp",
                                how="inner",
                                suffixes=("_1", "_2"),
                            )

                            if len(merged) > 1:
                                # 计算相关系数
                                correlation = np.corrcoef(
                                    merged["price_1"].values, merged["price_2"].values
                                )[0, 1]

                    # 如果无法计算实际相关性，使用模拟值
                    if correlation == 0 or np.isnan(correlation):
                        correlation = 0.5 + np.random.random() * 0.4

                    # 存储相关系数
                    correlation_matrix[asset1][asset2] = correlation

                    # 累加相关系数
                    avg_correlation += correlation
                    correlation_count += 1

                    # 检查高相关性对
                    if correlation > 0.7:
                        high_correlation_pairs.append(
                            {
                                "asset1": asset1,
                                "asset2": asset2,
                                "correlation": correlation,
                            }
                        )

            # 计算平均相关系数
            if correlation_count > 0:
                avg_correlation = avg_correlation / correlation_count
            else:
                avg_correlation = 0

            # 计算风险评分
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

            return {
                "risk_score": correlation_score,
                "description": description,
                "trend": trend,
                "data_points": data_points,
                "correlation_matrix": correlation_matrix,
            }
        except Exception as e:
            self.logger.error(f"分析资产历史数据相关性风险时出错: {str(e)}")
            return {
                "risk_score": 50,
                "description": f"分析资产历史数据相关性风险时出错: {str(e)}",
                "trend": "稳定",
                "data_points": [],
            }

    def analyze_protocol_correlation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析协议相关性风险

        Args:
            data: 包含协议列表和权重的数据，格式为 {"protocols": ["Aave", "Uniswap", ...], "weights": {"Aave": 0.4, "Uniswap": 0.3, ...}}

        Returns:
            Dict: 协议相关性风险分析结果
        """
        try:
            self.logger.info("开始分析协议相关性风险")

            # 提取协议列表和权重
            protocols = data.get("protocols", [])
            weights = data.get("weights", {})

            if not protocols or len(protocols) < 2:
                return {
                    "risk_score": 50,
                    "description": "无法分析协议相关性风险，协议数量不足",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 计算赫芬达尔指数 (HHI)
            hhi = sum((weights.get(protocol, 0) ** 2) for protocol in protocols)

            # 根据HHI评估风险
            if hhi > 0.5:
                risk_score = 80  # 高风险
                description = "投资组合高度集中在少数几个协议，增加了相关性风险"
                trend = "上升"
            elif hhi > 0.3:
                risk_score = 60  # 中高风险
                description = "投资组合在协议分布上较为集中，存在一定相关性风险"
                trend = "稳定"
            elif hhi > 0.2:
                risk_score = 40  # 中等风险
                description = "投资组合在协议分布上相对分散，相关性风险适中"
                trend = "稳定"
            else:
                risk_score = 20  # 低风险
                description = "投资组合在协议分布上高度分散，相关性风险较低"
                trend = "下降"

            # 构建数据点
            data_points = [
                {
                    "name": "赫芬达尔指数(HHI)",
                    "value": hhi,
                    "description": "衡量协议集中度的指标，值越高表示集中度越高",
                },
            ]

            # 添加协议分布数据
            for protocol, weight in weights.items():
                data_points.append(
                    {
                        "name": "协议权重",
                        "protocol": protocol,
                        "value": weight,
                    }
                )

            return {
                "risk_score": risk_score,
                "description": description,
                "trend": trend,
                "data_points": data_points,
                "hhi": hhi,
            }
        except Exception as e:
            self.logger.error(f"分析协议相关性风险时出错: {str(e)}")
            return {
                "risk_score": 50,
                "description": f"分析协议相关性风险时出错: {str(e)}",
                "trend": "稳定",
                "data_points": [],
            }
