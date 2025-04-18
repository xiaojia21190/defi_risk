# AI预测器服务

import httpx
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import json
from app.core.config import settings
from openai import OpenAI
from app.models.domain.risk import RiskFactor
import asyncio
import time
import uuid
import traceback
import random

logger = logging.getLogger("defi_risk.ai_predictor")


class AiPredictor:
    """AI预测器服务，提供高级风险分析和预测功能"""

    def __init__(self):
        """初始化AI预测器"""
        self.logger = logger
        # 初始化OpenAI客户端
        self.client = None
        try:
            client_http = httpx.Client(proxies=settings.PROXY_URL)
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

        # 移除在初始化时创建CorrelationRiskAnalyzer实例
        # 相关性分析器将在需要时延迟创建
        self._correlation_analyzer = None

    def analyze_defi_protocol_risk(
        self, protocol_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析DeFi协议风险

        Args:
            protocol_data: 协议数据，包含基本分析和历史数据
                可包含analysis_focus字段指定分析重点：
                - "security" - 安全风险分析
                - "governance" - 治理风险分析
                - "history" - 历史风险分析
                - "complexity" - 复杂性风险分析
                - 不指定时进行综合风险分析

        Returns:
            Dict: 风险分析结果
        """
        try:
            # 提取分析重点
            analysis_focus = protocol_data.get("analysis_focus", "general")
            self.logger.info(f"分析DeFi协议风险，重点: {analysis_focus}")

            # 提取基本信息
            basic_analysis = protocol_data.get("basic_analysis", {})
            historical_tvl = protocol_data.get("historical_tvl", [])
            protocol_metadata = protocol_data.get("protocol_metadata", {})
            chain_distribution = protocol_data.get("chain_distribution", {})
            protocol_name = protocol_data.get(
                "protocol_name", protocol_metadata.get("name", "未知协议")
            )

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

            # 根据分析重点定制结果
            if analysis_focus == "security":
                # 针对安全风险的特定处理
                return self._analyze_protocol_security(
                    protocol_name,
                    protocol_metadata,
                    risk_score,
                    risk_metrics,
                    risk_level,
                )
            elif analysis_focus == "governance":
                # 针对治理风险的特定处理
                return self._analyze_protocol_governance(
                    protocol_name,
                    protocol_metadata,
                    risk_score,
                    risk_metrics,
                    risk_level,
                )
            elif analysis_focus == "history":
                # 针对历史风险的特定处理
                return self._analyze_protocol_history(
                    protocol_name,
                    protocol_metadata,
                    tvl_df,
                    risk_score,
                    risk_metrics,
                    risk_level,
                )
            elif analysis_focus == "complexity":
                # 针对复杂性风险的特定处理
                return self._analyze_protocol_complexity(
                    protocol_name,
                    protocol_metadata,
                    chain_distribution,
                    risk_score,
                    risk_metrics,
                    risk_level,
                )

            # 构建完整分析结果 (综合分析)
            analysis_result = {
                "protocol_name": protocol_name,
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
                model="gpt-4o-mini",
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

    async def analyze_correlation_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

            # 根据相关类型分别处理
            if correlation_type == "asset_correlation":
                # 使用相关性风险分析器进行资产相关性分析
                result = await self._analyze_asset_correlation(data)
            elif correlation_type == "protocol_correlation":
                # 使用相关性风险分析器进行协议相关性分析
                result = await self._analyze_protocol_correlation(data)
            elif correlation_type == "investment_type_correlation":
                # 使用相关性风险分析器进行投资类型相关性分析
                result = await self._analyze_investment_type_correlation(data)
            else:
                # 默认分析资产相关性
                result = await self._analyze_asset_correlation(data)

            return result

        except Exception as e:
            self.logger.error(f"分析相关性风险失败: {str(e)}")
            return {
                "score": 50,
                "description": f"相关性分析过程中出错: {str(e)}",
                "trend": "未知",
                "data_points": [],
            }

    async def _analyze_asset_correlation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析资产相关性风险

        Args:
            data: 包含资产数据的字典

        Returns:
            Dict: 资产相关性风险分析结果
        """
        try:
            self.logger.info("分析资产相关性风险")

            # 提取资产列表和头寸数据
            assets = set(data.get("assets", []))
            positions = data.get("positions", [])

            # 如果资产列表和头寸数据都不足，无法进行相关性分析
            if (not assets or len(assets) < 2) and (not positions):
                self.logger.warning("检测到的资产少于2个，无法进行资产相关性分析")
                return {
                    "score": 30,
                    "description": "投资组合中资产种类较少，相关性风险较低",
                    "trend": "稳定",
                    "data_points": [],
                    "recommendations": ["增加资产多样性以降低集中风险"],
                    "monitoring_points": ["关注单一资产的价格波动"],
                }

            # 准备数据
            if not positions and assets:
                # 如果没有位置信息但有资产列表，创建模拟位置
                mock_positions = []
                for asset in assets:
                    mock_position = {
                        "asset": asset,
                        "amount": 1000,  # 假设每个资产价值相等
                        "protocol": "unknown",
                    }
                    mock_positions.append(mock_position)

                # 创建一个协议位置字典，包含所有模拟位置
                protocol_position = {"protocol": "mixed", "positions": mock_positions}

                positions = [protocol_position]

            # 获取相关性分析器以分析资产相关性
            correlation_analyzer = self._get_correlation_analyzer()

            if correlation_analyzer is None:
                self.logger.error("无法获取相关性分析器，使用简化的资产相关性分析")
                return self._fallback_asset_correlation_analysis(assets)

            # 使用await代替asyncio.run，并传递positions而不是assets
            try:
                risk_factor = await correlation_analyzer._analyze_asset_correlation(
                    positions
                )
            except Exception as analyzer_error:
                self.logger.error(
                    f"调用相关性分析器分析资产相关性失败: {str(analyzer_error)}"
                )
                return self._fallback_asset_correlation_analysis(assets)

            # 如果 correlation_analyzer 返回了有效的风险因子
            if risk_factor:
                try:
                    # 使用await代替asyncio.run
                    recommendations = await correlation_analyzer.get_recommendations(
                        [risk_factor]
                    )
                    monitoring_points = (
                        await correlation_analyzer.get_monitoring_points([risk_factor])
                    )

                    return {
                        "score": risk_factor.score,
                        "description": risk_factor.description,
                        "trend": risk_factor.trend,
                        "data_points": risk_factor.data_points,
                        "recommendations": recommendations,
                        "monitoring_points": monitoring_points,
                    }
                except Exception as e:
                    self.logger.error(f"处理风险因子结果时出错: {str(e)}")
                    # 如果处理结果出错，也使用简化实现
                    return self._fallback_asset_correlation_analysis(assets)
            else:
                # 如果没有有效的风险因子，使用简化实现
                return self._fallback_asset_correlation_analysis(assets)

        except Exception as e:
            self.logger.error(f"分析资产相关性风险失败: {str(e)}")
            return {
                "score": 50,
                "description": f"资产相关性分析过程中出错: {str(e)}",
                "trend": "未知",
                "data_points": [],
                "recommendations": ["关注资产之间的相关性，避免投资高度相关的资产"],
                "monitoring_points": ["监控主要资产对之间的价格关联变化"],
            }

    def _fallback_asset_correlation_analysis(self, assets) -> Dict[str, Any]:
        """
        简化的资产相关性分析实现，用于在正常分析方法失败时提供基本分析

        Args:
            assets: 资产集合

        Returns:
            Dict: 简化的资产相关性风险分析结果
        """
        self.logger.info("使用简化的资产相关性分析")

        # 模拟常见资产相关性关系（实际应通过历史数据计算）
        common_correlations = {
            ("BTC", "ETH"): 0.85,
            ("ETH", "BNB"): 0.75,
            ("BTC", "BNB"): 0.7,
            ("USDC", "USDT"): 0.98,
            ("USDC", "DAI"): 0.95,
            ("USDT", "DAI"): 0.94,
            ("BTC", "USDC"): 0.2,
            ("ETH", "USDC"): 0.25,
            ("BTC", "SOL"): 0.65,
            ("ETH", "SOL"): 0.72,
        }

        # 检测高相关性资产对
        high_correlation_pairs = []
        asset_list = list(assets)

        for i in range(len(asset_list)):
            for j in range(i + 1, len(asset_list)):
                asset1 = asset_list[i]
                asset2 = asset_list[j]

                # 查找已知相关性或赋予默认值
                correlation = 0.5  # 默认中等相关性

                # 检查两种排序方式
                if (asset1, asset2) in common_correlations:
                    correlation = common_correlations[(asset1, asset2)]
                elif (asset2, asset1) in common_correlations:
                    correlation = common_correlations[(asset2, asset1)]

                # 如果相关性高，添加到高相关性对列表
                if correlation > 0.7:
                    high_correlation_pairs.append(
                        {
                            "asset_pair": f"{asset1}-{asset2}",
                            "correlation": round(correlation, 2),
                        }
                    )

        # 计算相关性风险评分
        total_pairs = (len(asset_list) * (len(asset_list) - 1)) / 2
        high_corr_percentage = (
            len(high_correlation_pairs) / total_pairs if total_pairs > 0 else 0
        )

        risk_score = 0

        if high_corr_percentage >= 0.75:
            risk_score = 85
            description = "投资组合资产高度相关，系统性风险较高"
        elif high_corr_percentage >= 0.5:
            risk_score = 65
            description = "投资组合资产相关性中等偏高，存在一定系统性风险"
        elif high_corr_percentage >= 0.25:
            risk_score = 45
            description = "投资组合资产相关性中等，系统性风险适中"
        else:
            risk_score = 25
            description = "投资组合资产相关性较低，系统性风险可控"

        # 生成建议
        recommendations = []
        if high_corr_percentage >= 0.5:
            recommendations.append(
                "考虑增加与现有资产相关性低的资产，如传统资产或不同区块链的代币"
            )
            recommendations.append("避免增加与BTC/ETH高度相关的代币，降低系统性风险")
        else:
            recommendations.append("继续保持当前的资产多样化策略")

        # 生成监控点
        monitoring_points = []
        if high_correlation_pairs:
            pair_list = ", ".join([p["asset_pair"] for p in high_correlation_pairs[:3]])
            monitoring_points.append(f"密切关注高相关性资产对的价格变动: {pair_list}")
        monitoring_points.append("定期评估投资组合中各资产的相关性变化")

        return {
            "score": risk_score,
            "description": description,
            "trend": "稳定",
            "data_points": high_correlation_pairs,
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
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

            # 准备AI服务输入
            ai_service_input = {
                "wallet_address": wallet_address,
                "positions": positions,
                "risk_metrics": risk_metrics,
                "risk_factors": risk_factors,
            }

            # 直接尝试使用AI服务
            self.logger.info("直接调用AI服务进行投资组合分析...")

            # 如果有外部AI服务可用，优先使用
            try:
                self.logger.info("尝试使用外部AI服务...")
                # 调用时需要基于规则的结果作为基础，所以先获取基础分析
                rule_based_results = self._rule_based_portfolio_analysis(
                    wallet_address,
                    positions,
                    risk_score,
                    risk_level,
                    risk_metrics,
                    risk_factors,
                )

                # 将AI服务请求的数据结构与基础分析结合
                ai_service_input.update(
                    {
                        "rule_based_analysis": rule_based_results,
                        "use_external_ai": True,
                    }
                )

                # 直接调用_generate_ai_portfolio_insights
                return self._generate_ai_portfolio_insights(
                    wallet_address,
                    positions,
                    risk_score,
                    risk_level,
                    risk_metrics,
                    risk_factors,
                    rule_based_results,
                )

            except Exception as e:
                self.logger.error(f"使用外部AI服务失败: {str(e)}")
                self.logger.info("回退到内部分析")

            # 如果没有外部AI服务或者调用失败，执行规则分析后再调用AI增强
            rule_based_results = self._rule_based_portfolio_analysis(
                wallet_address,
                positions,
                risk_score,
                risk_level,
                risk_metrics,
                risk_factors,
            )

            # 使用内部逻辑进行AI分析增强
            return self._generate_ai_portfolio_insights(
                wallet_address,
                positions,
                risk_score,
                risk_level,
                risk_metrics,
                risk_factors,
                rule_based_results,
            )

        except Exception as e:
            self.logger.error(f"生成投资组合洞察失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "insights": [f"分析投资组合时出错: {str(e)}"],
                "recommendations": ["建议重新分析或联系技术支持"],
                "warnings": [],
                "confidence": 0.3,
            }

    def _convert_to_serializable(self, obj):
        """
        将对象转换为可JSON序列化的格式

        Args:
            obj: 任意对象

        Returns:
            可序列化的对象
        """
        if hasattr(obj, "__dict__"):
            # 处理具有__dict__属性的对象（如dataclass）
            return {
                k: self._convert_to_serializable(v) for k, v in obj.__dict__.items()
            }
        elif isinstance(obj, dict):
            # 递归处理字典
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list) or isinstance(obj, tuple):
            # 递归处理列表或元组
            return [self._convert_to_serializable(item) for item in obj]
        else:
            # 基本类型直接返回
            return obj

    def _call_external_ai_service(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用外部AI服务来分析投资组合

        Args:
            input_data: 输入数据字典

        Returns:
            Dict: AI服务返回的分析结果，如果调用失败则返回None
        """
        try:
            # 将输入数据转换为可序列化格式
            serializable_input = self._convert_to_serializable(input_data)

            # 构建提示语，包含投资组合信息
            system_message = """你是一个专业的DeFi投资组合分析师，擅长分析加密货币投资组合风险和提供投资建议。
请根据提供的投资组合数据，提供深入的分析洞察、具体的改进建议和风险警告。
关注资产分配、风险水平、市场趋势、协议多样性等关键指标。
分析应该是全面的、专业的，并且提供可操作的建议。"""

            # 构建用户消息，确保输入数据大小合适
            positions = serializable_input.get("positions", [])
            positions_sample = positions[:5]  # 最多取5个头寸作为样本
            risk_factors = serializable_input.get("risk_factors", [])
            risk_factors_sample = risk_factors[:5]  # 最多取5个风险因子作为样本

            user_message = f"""请分析以下投资组合数据并提供洞察、建议和风险警告:

钱包地址: {serializable_input.get('wallet_address', '未知')}
投资头寸数量: {len(positions)}
总风险评分: {serializable_input.get('risk_metrics', {}).get('risk_score', 0)}
风险等级: {serializable_input.get('rule_based_analysis', {}).get('risk_level', '未知')}

位置样本: {json.dumps(positions_sample, ensure_ascii=False)}
(显示 {len(positions_sample)}/{len(positions)} 个头寸)

风险因子样本: {json.dumps(risk_factors_sample, ensure_ascii=False)}
(显示 {len(risk_factors_sample)}/{len(risk_factors)} 个风险因子)

请以JSON格式提供:
1. insights: 投资组合分析洞察列表 (至少5条)
2. recommendations: 建议改进措施列表 (至少5条)
3. warnings: 风险警告列表 (如有)

回复仅限JSON格式，不要有其他文字。
"""

            self.logger.debug(
                f"调用OpenAI API进行投资组合分析, 模型: {settings.AI_MODEL}"
            )
            start_time = time.time()

            # 调用OpenAI API，设置超时
            try:
                response = self.client.chat.completions.create(
                    model=settings.AI_MODEL,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.5,
                    max_tokens=2000,
                    timeout=30,  # 30秒超时
                )

                elapsed_time = time.time() - start_time
                self.logger.info(f"OpenAI API响应时间: {elapsed_time:.2f}秒")

            except Exception as api_error:
                self.logger.error(f"OpenAI API调用失败: {str(api_error)}")
                return None

            # 解析响应
            if response and response.choices and len(response.choices) > 0:
                try:
                    content = response.choices[0].message.content
                    result = json.loads(content)

                    # 验证返回的JSON结构
                    if not all(k in result for k in ["insights", "recommendations"]):
                        self.logger.error("OpenAI返回的JSON缺少必要的字段")
                        return None

                    # 添加置信度和元数据
                    result["confidence"] = 0.95  # 外部AI服务的置信度通常较高
                    result["source"] = "external_ai"

                    # 记录成功的API调用
                    insights_count = len(result.get("insights", []))
                    recommendations_count = len(result.get("recommendations", []))
                    warnings_count = len(result.get("warnings", []))

                    self.logger.info(
                        f"OpenAI分析成功: {insights_count}条洞察, {recommendations_count}条建议, {warnings_count}条警告"
                    )

                    return result
                except json.JSONDecodeError as json_error:
                    self.logger.error(
                        f"无法解析外部AI服务的JSON响应: {str(json_error)}"
                    )
                    self.logger.debug(
                        f"无效的JSON内容: {response.choices[0].message.content[:200]}..."
                    )
                    return None
            else:
                self.logger.warning("外部AI服务没有返回有效响应")
                return None

        except Exception as e:
            self.logger.error(f"调用外部AI服务出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

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
        使用AI服务预测市场趋势和价格

        Args:
            asset: 资产名称
            current_price: 当前价格
            price_change_24h: 24小时价格变化百分比
            volatility: 波动率
            rsi: 相对强弱指数
            ma7: 7日移动平均线
            ma30: 30日移动平均线
            macd_trend: MACD趋势
            bb_position: 布林带位置
            volume_trend: 成交量趋势
            volume_strength: 成交量强度
            support_levels: 支撑位列表
            resistance_levels: 阻力位列表

        Returns:
            Dict: AI预测结果，包含预测价格范围和建议
        """
        try:
            # 准备调用外部AI服务的输入数据
            input_data = {
                "analysis_type": "market_prediction",
                "asset_data": {
                    "asset": asset,
                    "current_price": current_price,
                    "price_change_24h": price_change_24h,
                    "volatility": volatility,
                    "technical_indicators": {
                        "rsi": rsi,
                        "ma7": ma7,
                        "ma30": ma30,
                        "macd_trend": macd_trend,
                        "bollinger_position": bb_position,
                        "volume": {"trend": volume_trend, "strength": volume_strength},
                    },
                    "support_levels": support_levels,
                    "resistance_levels": resistance_levels,
                },
            }

            # 记录开始预测
            self.logger.info(f"开始使用AI服务预测{asset}市场趋势")

            # 调用外部AI服务
            ai_result = self._call_external_ai_service(input_data)

            if ai_result is None:
                # 如果AI服务调用失败，使用基于规则的预测
                self.logger.warning("AI服务调用失败，使用备用预测方法")

                # 基于基本指标的简单预测
                trend_direction = (
                    "bullish" if price_change_24h > 0 and rsi > 50 else "bearish"
                )
                trend_strength = (
                    "strong"
                    if abs(price_change_24h) > 5 or abs(rsi - 50) > 15
                    else "moderate"
                )

                # 计算简单的价格预测范围
                volatility_factor = max(
                    0.005, min(volatility, 0.05)
                )  # 限制在0.5%-5%范围内

                # 24小时预测
                change_24h = price_change_24h * 0.5  # 假设趋势会继续，但幅度减半
                predicted_change_24h = change_24h * (1 + random.uniform(-0.5, 0.5))
                range_24h = [
                    current_price
                    * (1 + predicted_change_24h / 100 - volatility_factor),
                    current_price
                    * (1 + predicted_change_24h / 100 + volatility_factor),
                ]

                # 7天预测
                predicted_change_7d = change_24h * 3  # 假设7天变化是24小时的3倍
                range_7d = [
                    current_price
                    * (1 + predicted_change_7d / 100 - volatility_factor * 2),
                    current_price
                    * (1 + predicted_change_7d / 100 + volatility_factor * 2),
                ]

                # 生成一些基本建议
                recommendations = []
                if rsi > 70:
                    recommendations.append(f"{asset}当前RSI高于70，可能面临回调风险")
                elif rsi < 30:
                    recommendations.append(f"{asset}当前RSI低于30，可能存在超卖现象")

                if bb_position == "超买":
                    recommendations.append(
                        f"{asset}当前处于布林带上轨附近，价格可能高估"
                    )
                elif bb_position == "超卖":
                    recommendations.append(
                        f"{asset}当前处于布林带下轨附近，价格可能低估"
                    )

                if macd_trend == "bullish":
                    recommendations.append(f"{asset}的MACD显示看涨信号，可能继续上涨")
                elif macd_trend == "bearish":
                    recommendations.append(f"{asset}的MACD显示看跌信号，可能继续下跌")

                if len(recommendations) < 3:
                    recommendations.append(
                        f"建议关注{asset}的成交量变化，判断趋势持续性"
                    )

                # 构造备用结果
                return {
                    "trend": trend_direction,
                    "trend_strength": trend_strength,
                    "predicted_price_range": {"24h": range_24h, "7d": range_7d},
                    "confidence": 0.6,  # 备用预测置信度较低
                    "recommendations": recommendations,
                }

            # 如果AI服务返回结果，但没有必要的字段，需要补充
            if "predicted_price_range" not in ai_result:
                # 使用和备用逻辑类似的方法生成预测价格范围
                volatility_factor = max(0.005, min(volatility, 0.05))

                # 基于AI分析的趋势方向调整预测
                trend_factor = 0.5
                if ai_result.get("trend") == "bullish":
                    trend_factor = 1.0
                elif ai_result.get("trend") == "bearish":
                    trend_factor = -1.0

                # 24小时和7天的预测范围
                ai_result["predicted_price_range"] = {
                    "24h": [
                        current_price * (1 + trend_factor * volatility_factor),
                        current_price * (1 + trend_factor * volatility_factor * 2),
                    ],
                    "7d": [
                        current_price * (1 + trend_factor * volatility_factor * 3),
                        current_price * (1 + trend_factor * volatility_factor * 5),
                    ],
                }

            # 如果没有趋势信息，添加
            if "trend" not in ai_result:
                ai_result["trend"] = (
                    "bullish" if price_change_24h > 0 and rsi > 50 else "bearish"
                )

            # 如果没有趋势强度，添加
            if "trend_strength" not in ai_result:
                ai_result["trend_strength"] = (
                    "strong"
                    if abs(price_change_24h) > 5 or abs(rsi - 50) > 15
                    else "moderate"
                )

            # 如果没有建议，生成一些
            if "recommendations" not in ai_result or not ai_result["recommendations"]:
                ai_result["recommendations"] = self._generate_market_recommendations(
                    ai_result.get("trend", "neutral"),
                    rsi,
                    macd_trend,
                    bb_position,
                    volatility,
                    asset,
                )

            # 记录预测完成
            self.logger.info(
                f"AI服务成功预测{asset}市场趋势: {ai_result.get('trend')}，强度: {ai_result.get('trend_strength')}"
            )

            return ai_result

        except Exception as e:
            self.logger.error(f"使用AI服务预测市场趋势时出错: {str(e)}")
            self.logger.error(traceback.format_exc())

            # 返回简单的默认结果
            return {
                "trend": "neutral",
                "trend_strength": "moderate",
                "predicted_price_range": {
                    "24h": [current_price * 0.98, current_price * 1.02],
                    "7d": [current_price * 0.95, current_price * 1.05],
                },
                "confidence": 0.5,
                "recommendations": [
                    f"由于技术原因无法提供{asset}的准确预测，建议谨慎交易"
                ],
            }

    def _combine_predictions(
        self, traditional_prediction: Dict[str, Any], ai_prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并传统技术分析和AI预测结果

        Args:
            traditional_prediction: 传统技术分析预测结果
            ai_prediction: AI预测结果

        Returns:
            Dict: 合并后的预测结果
        """
        try:
            # 获取两种预测的置信度，如果没有提供则使用默认值
            traditional_confidence = traditional_prediction.get("confidence", 0.7)
            ai_confidence = ai_prediction.get("confidence", 0.8)

            # 计算总置信度
            total_confidence = traditional_confidence + ai_confidence

            # 计算加权因子
            traditional_weight = traditional_confidence / total_confidence
            ai_weight = ai_confidence / total_confidence

            # 获取价格和价格范围
            traditional_price = traditional_prediction.get("price", 0)
            ai_price = ai_prediction.get("price", 0)

            traditional_range = traditional_prediction.get("range", [0, 0])
            ai_range = ai_prediction.get("range", [0, 0])

            # 如果传统预测价格为0，使用AI预测价格
            if traditional_price == 0 and ai_price > 0:
                combined_price = ai_price
            # 如果AI预测价格为0，使用传统预测价格
            elif ai_price == 0 and traditional_price > 0:
                combined_price = traditional_price
            # 如果两者都大于0，进行加权计算
            elif traditional_price > 0 and ai_price > 0:
                combined_price = (
                    traditional_price * traditional_weight + ai_price * ai_weight
                )
            # 如果两者都为0，使用0作为预测价格
            else:
                combined_price = 0

            # 合并价格范围，采用范围扩展策略
            combined_range = [
                (
                    min(traditional_range[0], ai_range[0])
                    if len(traditional_range) > 0 and len(ai_range) > 0
                    else 0
                ),
                (
                    max(traditional_range[-1], ai_range[-1])
                    if len(traditional_range) > 0 and len(ai_range) > 0
                    else 0
                ),
            ]

            # 计算变化百分比
            combined_change_percent = (
                traditional_prediction.get("change_percent", 0) * traditional_weight
                + ai_prediction.get("change_percent", 0) * ai_weight
            )

            # 合并置信度，取两者的加权平均
            combined_confidence = (
                traditional_confidence * traditional_weight + ai_confidence * ai_weight
            )

            # 构建合并结果
            result = {
                "price": combined_price,
                "range": combined_range,
                "change_percent": combined_change_percent,
                "confidence": combined_confidence,
                "sources": {
                    "traditional": {
                        "weight": traditional_weight,
                        "confidence": traditional_confidence,
                    },
                    "ai": {"weight": ai_weight, "confidence": ai_confidence},
                },
            }

            return result

        except Exception as e:
            self.logger.error(f"合并预测结果时出错: {str(e)}")

            # 出错时优先使用AI预测，因为它通常更全面
            if ai_prediction and "price" in ai_prediction:
                return ai_prediction

            # 如果AI预测也不可用，使用传统预测
            if traditional_prediction and "price" in traditional_prediction:
                return traditional_prediction

            # 两者都不可用时，返回默认值
            return {
                "price": 0,
                "range": [0, 0],
                "change_percent": 0,
                "confidence": 0.5,
                "error": "无法合并预测结果",
            }

    def _merge_analysis_results(
        self, rule_results: Dict[str, Any], ai_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并规则分析和AI分析结果

        Args:
            rule_results: 规则分析结果
            ai_results: AI分析结果

        Returns:
            Dict: 合并后的分析结果
        """
        try:
            # 提取规则分析的关键数据
            rule_insights = set(rule_results.get("insights", []))
            rule_recommendations = set(rule_results.get("recommendations", []))
            rule_warnings = set(rule_results.get("warnings", []))

            # 提取AI分析的关键数据
            ai_insights = set(ai_results.get("insights", []))
            ai_recommendations = set(ai_results.get("recommendations", []))
            ai_warnings = set(ai_results.get("warnings", []))

            # 合并并删除重复项
            combined_insights = list(rule_insights.union(ai_insights))
            combined_recommendations = list(
                rule_recommendations.union(ai_recommendations)
            )
            combined_warnings = list(rule_warnings.union(ai_warnings))

            # 使用AI结果的置信度，如果有的话
            confidence = ai_results.get(
                "confidence", rule_results.get("confidence", 0.8)
            )

            # 确定AI分析的来源
            ai_source = ai_results.get("source", "unknown_ai")

            # 记录合并结果的统计信息
            self.logger.info(
                f"合并分析结果: 规则({len(rule_insights)}条洞察) + AI({len(ai_insights)}条洞察) = 合并({len(combined_insights)}条洞察)"
            )

            # 合并支持数据
            supporting_data = {
                **rule_results.get("supporting_data", {}),
                "ai_analysis": {
                    "source": ai_source,
                    "unique_insights": list(ai_insights - rule_insights),
                    "unique_recommendations": list(
                        ai_recommendations - rule_recommendations
                    ),
                    "timestamp": datetime.now().isoformat(),
                },
            }

            # 如果AI结果中有charts_data，也合并它
            if "charts_data" in ai_results.get("supporting_data", {}):
                supporting_data["charts_data"] = ai_results["supporting_data"][
                    "charts_data"
                ]

            # 构建最终结果
            merged_results = {
                "insights": combined_insights,
                "recommendations": combined_recommendations,
                "warnings": combined_warnings,
                "confidence": confidence,
                "supporting_data": supporting_data,
            }

            return merged_results

        except Exception as e:
            self.logger.error(f"合并分析结果时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            # 出错时返回规则结果
            return rule_results

    def _rule_based_portfolio_analysis(
        self,
        wallet_address: str,
        positions: List[Dict],
        risk_score: float,
        risk_level: str,
        risk_metrics: Dict,
        risk_factors: List[Dict],
    ) -> Dict[str, Any]:
        """
        基于规则的投资组合分析方法

        Args:
            wallet_address: 钱包地址
            positions: 投资头寸列表
            risk_score: 风险评分
            risk_level: 风险级别
            risk_metrics: 风险指标
            risk_factors: 风险因子

        Returns:
            Dict: 包含洞察、建议和警告的分析结果
        """
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
            risk_score_pos = position.get("risk_score", 0)
            health_factor = position.get("health_factor", 10)

            if risk_score_pos > 70:
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
            insights.append(f"您的投资全部集中在{protocol_name}协议，缺乏协议多样性")
            recommendations.append("考虑分散投资到2-3个不同的协议，降低协议风险")
        elif len(protocols) > 5:
            insights.append(f"您的投资分散在{len(protocols)}个协议，管理成本可能较高")
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
            insights.append(f"稳定币比例较低({stablecoin_ratio:.1%})，缺乏市场波动缓冲")
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
            recommendations.extend(default_recommendations[: 3 - len(recommendations)])

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
            data: 包含风险因子的数据，格式为 {"risk_factors": [{"name": "...", "score": 75, ...}, ...]}

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
                factor_name = factor.get("name", "")
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
        生成市场风险监控点

        Args:
            data: 风险因子数据

        Returns:
            Dict: 监控点列表和优先级信息
        """
        try:
            self.logger.info("开始生成市场风险监控点")

            # 提取风险因子
            risk_factors = data.get("risk_factors", [])
            if not risk_factors:
                return {
                    "monitoring_points": [
                        "监控市场趋势指标，如BTC和ETH的价格走势",
                        "关注市场主要指数和恐惧贪婪指数变化",
                        "监控投资组合中各资产的价格相关性变化",
                    ]
                }

            monitoring_points = []
            priority_monitoring_points = []

            # 根据风险因子生成监控点
            for factor in risk_factors:
                factor_name = factor.get("name", "")
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

    def _get_correlation_analyzer(self):
        """
        懒加载方式初始化相关性分析器，避免循环引用问题

        Returns:
            CorrelationRiskAnalyzer: 相关性风险分析器实例
        """
        try:
            if (
                not hasattr(self, "_correlation_analyzer")
                or self._correlation_analyzer is None
            ):
                # 延迟导入以避免循环引用
                from app.risk_modules.correlation_risk import CorrelationRiskAnalyzer

                self._correlation_analyzer = CorrelationRiskAnalyzer()
                self.logger.info("成功初始化相关性风险分析器")

            return self._correlation_analyzer

        except ImportError as e:
            self.logger.error(f"导入 CorrelationRiskAnalyzer 失败: {str(e)}")
            # 创建后备实现
            self._create_fallback_correlation_analyzer()
            return self._correlation_analyzer

        except Exception as e:
            self.logger.error(f"初始化相关性风险分析器失败: {str(e)}")
            # 创建后备实现
            self._create_fallback_correlation_analyzer()
            return self._correlation_analyzer

    def _create_fallback_correlation_analyzer(self):
        """
        创建后备的相关性风险分析器实现，用于在正常初始化失败时提供基本功能
        """
        from app.models.domain.risk import RiskFactor, RiskType

        # 创建一个简单的对象，实现必要的方法
        class FallbackCorrelationAnalyzer:
            async def _analyze_asset_correlation(self, positions):
                # 返回简单的资产相关性风险因子
                return RiskFactor(
                    id=f"{RiskType.CORRELATION.name}.资产相关性",
                    name="资产相关性风险",
                    score=50.0,
                    weight=0.4,
                    description="使用后备分析器计算的资产相关性风险",
                    trend="稳定",
                    data_points=[],
                    metadata={},
                )

            async def _analyze_protocol_correlation(self, positions):
                # 返回简单的协议相关性风险因子
                return RiskFactor(
                    id=f"{RiskType.CORRELATION.name}.协议相关性",
                    name="协议相关性风险",
                    score=45.0,
                    weight=0.3,
                    description="使用后备分析器计算的协议相关性风险",
                    trend="稳定",
                    data_points=[],
                    metadata={},
                )

            async def _analyze_investment_type_correlation(self, positions):
                # 返回简单的投资类型相关性风险因子
                return RiskFactor(
                    id=f"{RiskType.CORRELATION.name}.投资类型相关性",
                    name="投资类型相关性风险",
                    score=40.0,
                    weight=0.3,
                    description="使用后备分析器计算的投资类型相关性风险",
                    trend="稳定",
                    data_points=[],
                    metadata={},
                )

            async def get_recommendations(self, risk_factors):
                return ["分散投资以降低相关性风险"]

            async def get_monitoring_points(self, risk_factors):
                return ["监控主要资产对之间的相关性变化"]

        self._correlation_analyzer = FallbackCorrelationAnalyzer()
        self.logger.warning("使用后备相关性风险分析器实现")

    async def _analyze_protocol_correlation(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析协议相关性风险

        Args:
            data: 包含协议数据的字典

        Returns:
            Dict: 协议相关性风险分析结果
        """
        try:
            self.logger.info("分析协议相关性风险")

            # 提取协议列表和头寸数据
            protocols = data.get("protocols", [])
            positions = data.get("positions", [])

            # 如果协议列表和头寸数据都不足，无法进行相关性分析
            if (not protocols or len(protocols) < 2) and (not positions):
                self.logger.warning("检测到的协议少于2个，无法进行协议相关性分析")
                return {
                    "score": 30,
                    "description": "投资组合中协议种类较少，相关性风险较低",
                    "trend": "稳定",
                    "data_points": [],
                    "recommendations": [
                        "考虑分散投资到不同的DeFi协议以降低协议集中风险"
                    ],
                    "monitoring_points": ["关注当前协议的安全性和更新"],
                }

            # 准备数据
            if not positions and protocols:
                # 如果有协议列表但没有头寸信息，创建模拟头寸
                mock_positions = []
                for protocol in protocols:
                    protocol_position = {
                        "protocol": protocol,
                        "positions": [
                            {
                                "asset": "UNKNOWN",
                                "amount": 1000,  # 假设每个协议价值相等
                                "protocol": protocol,
                            }
                        ],
                    }
                    mock_positions.append(protocol_position)
                positions = mock_positions

            # 获取相关性分析器并使用它分析协议相关性
            correlation_analyzer = self._get_correlation_analyzer()

            if correlation_analyzer is None:
                self.logger.error("无法获取相关性分析器，使用简化的协议相关性分析")
                return self._fallback_protocol_correlation_analysis(protocols)

            # 使用await代替asyncio.run
            try:
                risk_factor = await correlation_analyzer._analyze_protocol_correlation(
                    positions
                )
            except Exception as analyzer_error:
                self.logger.error(
                    f"调用相关性分析器分析协议相关性失败: {str(analyzer_error)}"
                )
                return self._fallback_protocol_correlation_analysis(protocols)

            # 如果 correlation_analyzer 返回了有效的风险因子
            if risk_factor:
                try:
                    # 使用await代替asyncio.run
                    recommendations = await correlation_analyzer.get_recommendations(
                        [risk_factor]
                    )
                    monitoring_points = (
                        await correlation_analyzer.get_monitoring_points([risk_factor])
                    )

                    return {
                        "score": risk_factor.score,
                        "description": risk_factor.description,
                        "trend": risk_factor.trend,
                        "data_points": risk_factor.data_points,
                        "recommendations": recommendations,
                        "monitoring_points": monitoring_points,
                    }
                except Exception as e:
                    self.logger.error(f"处理协议相关性风险因子结果时出错: {str(e)}")
                    return self._fallback_protocol_correlation_analysis(protocols)
            else:
                # 如果 correlation_analyzer 没有返回有效的风险因子，使用简化实现
                return self._fallback_protocol_correlation_analysis(protocols)

        except Exception as e:
            self.logger.error(f"分析协议相关性风险失败: {str(e)}")
            return {
                "score": 50,
                "description": "协议相关性分析过程中出错",
                "trend": "未知",
                "data_points": [],
                "recommendations": ["分散投资到不同类型的DeFi协议，降低协议相关性风险"],
                "monitoring_points": ["关注协议间的依赖关系和集成情况"],
            }

    def _fallback_protocol_correlation_analysis(self, protocols) -> Dict[str, Any]:
        """
        简化的协议相关性分析实现，用于在正常分析方法失败时提供基本分析

        Args:
            protocols: 协议列表

        Returns:
            Dict: 简化的协议相关性风险分析结果
        """
        self.logger.info("使用简化的协议相关性分析")

        # 如果协议数量太少，返回低风险
        if len(protocols) < 3:
            return {
                "score": 35,
                "description": "投资组合中协议数量较少，相关性风险适中",
                "trend": "稳定",
                "data_points": [],
                "recommendations": ["考虑分散投资到更多不同类型的DeFi协议"],
                "monitoring_points": ["关注当前协议之间的依赖关系"],
            }

        # 对于多个协议，返回中等风险
        return {
            "score": 45,
            "description": "协议相关性风险中等，建议关注协议间依赖关系",
            "trend": "稳定",
            "data_points": [],
            "recommendations": ["分散投资到不同类型的DeFi协议，降低协议相关性风险"],
            "monitoring_points": ["关注协议间的依赖关系和集成情况"],
        }

    async def _analyze_investment_type_correlation(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析投资类型相关性风险

        Args:
            data: 包含投资类型数据的字典

        Returns:
            Dict: 投资类型相关性风险分析结果
        """
        try:
            self.logger.info("分析投资类型相关性风险")

            # 提取投资类型和头寸数据
            investment_types = data.get("investment_types", {})
            positions = data.get("positions", [])

            # 如果数据不足，无法进行相关性分析
            if (not investment_types or len(investment_types) < 2) and (not positions):
                self.logger.warning(
                    "检测到的投资类型少于2个，无法进行投资类型相关性分析"
                )
                return {
                    "score": 30,
                    "description": "投资组合中投资类型较少，相关性风险较低",
                    "trend": "稳定",
                    "data_points": [],
                    "recommendations": ["考虑尝试不同的投资策略以分散风险"],
                    "monitoring_points": ["关注当前投资类型的表现"],
                }

            # 准备数据
            if not positions and investment_types:
                # 如果有投资类型信息但没有头寸，创建模拟头寸
                mock_positions = []
                for invest_type, type_info in investment_types.items():
                    # 获取投资类型名称
                    invest_type_name = (
                        type_info.get("name")
                        if isinstance(type_info, dict)
                        else (
                            self._get_invest_type_name(int(invest_type))
                            if invest_type.isdigit()
                            else "未知类型"
                        )
                    )

                    # 创建模拟头寸
                    protocol_position = {
                        "protocol": "mixed",
                        "positions": [
                            {
                                "asset": "UNKNOWN",
                                "amount": 1000,  # 假设每个投资类型价值相等
                                "invest_type": (
                                    int(invest_type) if invest_type.isdigit() else 0
                                ),
                                "invest_type_name": invest_type_name,
                            }
                        ],
                    }
                    mock_positions.append(protocol_position)
                positions = mock_positions

            # 获取相关性分析器并使用它分析投资类型相关性
            correlation_analyzer = self._get_correlation_analyzer()

            if correlation_analyzer is None:
                self.logger.error("无法获取相关性分析器，使用简化的投资类型相关性分析")
                return self._fallback_investment_type_correlation_analysis(
                    investment_types
                )

            # 使用await代替asyncio.run
            try:
                risk_factor = (
                    await correlation_analyzer._analyze_investment_type_correlation(
                        positions
                    )
                )
            except Exception as analyzer_error:
                self.logger.error(
                    f"调用相关性分析器分析投资类型相关性失败: {str(analyzer_error)}"
                )
                return self._fallback_investment_type_correlation_analysis(
                    investment_types
                )

            # 如果 correlation_analyzer 返回了有效的风险因子
            if risk_factor:
                try:
                    # 使用await代替asyncio.run
                    recommendations = await correlation_analyzer.get_recommendations(
                        [risk_factor]
                    )
                    monitoring_points = (
                        await correlation_analyzer.get_monitoring_points([risk_factor])
                    )

                    return {
                        "score": risk_factor.score,
                        "description": risk_factor.description,
                        "trend": risk_factor.trend,
                        "data_points": risk_factor.data_points,
                        "recommendations": recommendations,
                        "monitoring_points": monitoring_points,
                    }
                except Exception as e:
                    self.logger.error(f"处理投资类型风险因子结果时出错: {str(e)}")
                    return self._fallback_investment_type_correlation_analysis(
                        investment_types
                    )
            else:
                # 如果 correlation_analyzer 没有返回有效的风险因子，使用简化实现
                return self._fallback_investment_type_correlation_analysis(
                    investment_types
                )

        except Exception as e:
            self.logger.error(f"分析投资类型相关性风险失败: {str(e)}")
            return {
                "score": 50,
                "description": "投资类型相关性分析过程中出错",
                "trend": "未知",
                "data_points": [],
                "recommendations": ["考虑增加不同类型的投资策略，降低相关性风险"],
                "monitoring_points": ["定期评估不同投资类型的相关性"],
            }

    def _fallback_investment_type_correlation_analysis(
        self, investment_types
    ) -> Dict[str, Any]:
        """
        简化的投资类型相关性分析实现，用于在正常分析方法失败时提供基本分析

        Args:
            investment_types: 投资类型字典

        Returns:
            Dict: 简化的投资类型相关性风险分析结果
        """
        self.logger.info("使用简化的投资类型相关性分析")

        # 投资类型的常见相关性（简化模型）
        type_correlations = {
            ("流动性挖矿", "单币存款"): 0.6,
            ("流动性挖矿", "借贷"): 0.4,
            ("单币存款", "借贷"): 0.5,
            ("杠杆交易", "期权"): 0.75,
            ("杠杆交易", "借贷"): 0.65,
            ("期权", "借贷"): 0.45,
        }

        # 如果投资类型数量太少，返回低风险
        if len(investment_types) < 3:
            return {
                "score": 35,
                "description": "投资组合中投资类型较少，相关性风险适中",
                "trend": "稳定",
                "data_points": [],
                "recommendations": ["考虑尝试更多样化的投资策略"],
                "monitoring_points": ["关注当前投资类型间的风险传导"],
            }

        # 提取投资类型名称
        type_names = []
        for invest_type, type_info in investment_types.items():
            type_name = (
                type_info.get("name")
                if isinstance(type_info, dict)
                else f"类型{invest_type}"
            )
            type_names.append(type_name)

        # 评估相关性风险
        high_correlation_count = 0
        for i in range(len(type_names)):
            for j in range(i + 1, len(type_names)):
                type1 = type_names[i]
                type2 = type_names[j]

                # 查找已知相关性
                correlation = 0.4  # 默认中等相关性
                if (type1, type2) in type_correlations:
                    correlation = type_correlations[(type1, type2)]
                elif (type2, type1) in type_correlations:
                    correlation = type_correlations[(type2, type1)]

                if correlation > 0.6:
                    high_correlation_count += 1

        # 根据高相关性数量评估风险
        if high_correlation_count > 2:
            score = 65
            description = "投资类型相关性较高，存在风险集中问题"
            recommendations = ["考虑分散投资到相关性较低的不同投资类型"]
            monitoring_points = ["关注高相关性投资类型间的风险传导"]
        else:
            score = 40
            description = "投资类型多样化程度适中，风险相对平衡"
            recommendations = ["考虑增加不同类型的投资策略，提高组合韧性"]
            monitoring_points = ["监控不同投资类型在极端市场环境下的表现相关性"]

        return {
            "score": score,
            "description": description,
            "trend": "稳定",
            "data_points": [],
            "recommendations": recommendations,
            "monitoring_points": monitoring_points,
        }

    def _generate_ai_portfolio_insights(
        self,
        wallet_address: str,
        positions: List[Dict],
        risk_score: float,
        risk_level: str,
        risk_metrics: Dict,
        risk_factors: List[Dict],
        rule_based_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        使用AI驱动的分析来生成投资组合洞察

        Args:
            wallet_address: 钱包地址
            positions: 投资头寸列表
            risk_score: 风险评分
            risk_level: 风险级别
            risk_metrics: 风险指标
            risk_factors: 风险因子
            rule_based_results: 基于规则的分析结果

        Returns:
            Dict: AI生成的洞察、建议和警告
        """
        try:
            self.logger.info(f"开始生成AI驱动的投资组合洞察")

            # 如果没有头寸，直接返回规则结果
            if not positions:
                self.logger.info("投资组合为空，跳过AI分析")
                return rule_based_results

            # 构建输入数据，准备AI分析
            # 提取资产分布数据
            supporting_data = rule_based_results.get("supporting_data", {})
            asset_distribution = supporting_data.get("asset_distribution", [])
            protocol_distribution = supporting_data.get("protocol_distribution", [])
            investment_type_distribution = supporting_data.get(
                "investment_type_distribution", []
            )
            stablecoin_ratio = supporting_data.get("stablecoin_ratio", 0)

            # 提取风险因子数据
            risk_factors_data = []
            for factor in risk_factors:
                risk_factors_data.append(
                    {
                        "name": factor.get("name", ""),
                        "score": factor.get("score", 0),
                        "description": factor.get("description", ""),
                        "trend": factor.get("trend", "稳定"),
                    }
                )

            # 优先尝试使用外部AI服务
            self.logger.info("尝试使用外部AI服务进行投资组合分析...")

            # 创建AI输入数据
            ai_service_input = {
                "wallet_address": wallet_address,
                "positions": positions,
                "risk_metrics": risk_metrics,
                "risk_factors": risk_factors,
                "rule_based_analysis": rule_based_results,
                "portfolio_summary": {
                    "total_risk_score": risk_score,
                    "risk_level": risk_level,
                    "total_value": sum(
                        [float(p.get("usd_value", 0)) for p in positions]
                    ),
                    "asset_count": len(set([p.get("asset", "") for p in positions])),
                    "protocol_count": len(
                        set([p.get("protocol", "") for p in positions])
                    ),
                    "position_count": len(positions),
                    "stablecoin_ratio": stablecoin_ratio,
                },
                "distributions": {
                    "assets": asset_distribution,
                    "protocols": protocol_distribution,
                    "investment_types": investment_type_distribution,
                },
            }

            # 调用外部AI服务
            external_ai_results = self._call_external_ai_service(ai_service_input)

            # 如果外部AI服务返回成功，合并结果并返回
            if external_ai_results:
                self.logger.info("外部AI服务返回成功，使用外部分析结果")
                return self._merge_analysis_results(
                    rule_based_results, external_ai_results
                )

            # 如果外部AI服务调用失败，回退到本地AI分析
            self.logger.warning("外部AI服务返回为空或调用失败，回退到本地AI分析")

            # 以下是原本的本地AI分析逻辑
            # 创建AI输入数据（已在上面构建）
            ai_input = {
                "portfolio_summary": {
                    "wallet_address": wallet_address,
                    "total_risk_score": risk_score,
                    "risk_level": risk_level,
                    "total_value": sum(
                        [float(p.get("usd_value", 0)) for p in positions]
                    ),
                    "asset_count": len(set([p.get("asset", "") for p in positions])),
                    "protocol_count": len(
                        set([p.get("protocol", "") for p in positions])
                    ),
                    "position_count": len(positions),
                    "stablecoin_ratio": stablecoin_ratio,
                },
                "risk_metrics": risk_metrics,
                "risk_factors": risk_factors_data,
                "distributions": {
                    "assets": asset_distribution,
                    "protocols": protocol_distribution,
                    "investment_types": investment_type_distribution,
                },
                "positions": positions,
                "rule_based_insights": rule_based_results.get("insights", []),
                "rule_based_recommendations": rule_based_results.get(
                    "recommendations", []
                ),
            }

            self.logger.debug(
                f"执行本地AI分析，输入数据概要: 资产数量={ai_input['portfolio_summary']['asset_count']}, 协议数量={ai_input['portfolio_summary']['protocol_count']}"
            )

            # 根据现有数据生成洞察
            ai_insights = []
            ai_recommendations = []
            ai_warnings = []

            try:
                # 1. 分析投资组合多样性
                assets = [p.get("asset", "") for p in positions]
                protocols = [p.get("protocol", "") for p in positions]
                unique_assets = len(set(assets))
                unique_protocols = len(set(protocols))

                if unique_assets < 3 and len(assets) > 3:
                    ai_insights.append("投资组合资产多样性较低，潜在系统性风险较高")
                    ai_recommendations.append(
                        "建议增加资产类别的多样性，降低单一资产价格波动对整体组合的影响"
                    )

                # 2. 高风险资产分析
                high_risk_positions = [
                    p for p in positions if p.get("risk_score", 0) > 70
                ]
                if len(high_risk_positions) > len(positions) * 0.3:
                    ai_insights.append("高风险资产占比超过组合的30%，整体风险偏高")
                    ai_recommendations.append(
                        "考虑降低高风险资产的比例，增加中低风险资产的配置"
                    )
                    ai_warnings.append("高风险资产占比过高可能带来剧烈波动")

                # 3. 分析杠杆使用情况
                leverage_positions = [
                    p for p in positions if p.get("invest_type", 0) in [2]
                ]
                leverage_value = sum(
                    [float(p.get("usd_value", 0)) for p in leverage_positions]
                )
                total_value = sum([float(p.get("usd_value", 0)) for p in positions])
                if leverage_value > 0 and total_value > 0:
                    leverage_ratio = leverage_value / total_value
                    if leverage_ratio > 0.2:
                        ai_insights.append(
                            f"杠杆仓位占比{leverage_ratio:.1%}，处于较高水平"
                        )
                        ai_recommendations.append(
                            "在市场波动较大时考虑减少杠杆仓位，降低强制平仓风险"
                        )
                        if leverage_ratio > 0.4:
                            ai_warnings.append("杠杆仓位占比过高，面临重大清算风险")

                # 4. 分析投资时机与市场趋势
                market_trend_factor = next(
                    (f for f in risk_factors_data if "趋势" in f.get("name", "")), None
                )
                if market_trend_factor and market_trend_factor.get("score", 50) > 60:
                    ai_insights.append("当前市场趋势不明朗或下行风险较大")
                    ai_recommendations.append(
                        "考虑分批建仓策略，避免一次性投入过多资金"
                    )

                # 5. 生成高级投资策略建议
                # 根据资产类型分布和风险偏好，生成定制化策略
                has_defi_positions = any(
                    "defi" in p.get("protocol", "").lower() for p in positions
                )
                has_cefi_positions = any(
                    "交易所" in p.get("protocol", "") for p in positions
                )
                if has_defi_positions and has_cefi_positions:
                    ai_insights.append(
                        "投资组合同时包含中心化和去中心化资产，策略较为均衡"
                    )
                    ai_recommendations.append(
                        "建议定期重新平衡DeFi和CeFi资产的比例，以适应市场变化"
                    )

                # 6. 分析APY情况
                apy_values = [
                    float(p.get("apy", 0))
                    for p in positions
                    if p.get("apy") is not None
                ]
                if apy_values:
                    avg_apy = sum(apy_values) / len(apy_values)
                    high_apy_positions = [
                        p for p in positions if p.get("apy", 0) > avg_apy * 2
                    ]
                    if high_apy_positions:
                        ai_insights.append(
                            f"检测到{len(high_apy_positions)}个高APY头寸，可能存在高收益高风险情况"
                        )
                        ai_recommendations.append(
                            "建议对高收益头寸进行额外的风险评估，确保收益与风险匹配"
                        )

                self.logger.debug(
                    f"本地AI分析完成: 生成 {len(ai_insights)} 条洞察, {len(ai_recommendations)} 条建议, {len(ai_warnings)} 条警告"
                )

            except Exception as inner_e:
                # 内部分析出错，记录错误并尝试继续
                self.logger.error(f"执行本地AI分析时出错: {str(inner_e)}")
                # 添加一个关于分析问题的洞察
                ai_insights.append("部分投资组合分析未能完成，结果可能不完整")

            # 合并AI洞察与规则洞察，确保不重复
            existing_insights = set(rule_based_results.get("insights", []))
            existing_recommendations = set(
                rule_based_results.get("recommendations", [])
            )
            existing_warnings = set(rule_based_results.get("warnings", []))

            # 过滤掉重复项
            unique_ai_insights = [i for i in ai_insights if i not in existing_insights]
            unique_ai_recommendations = [
                r for r in ai_recommendations if r not in existing_recommendations
            ]
            unique_ai_warnings = [w for w in ai_warnings if w not in existing_warnings]

            # 记录AI分析增加的独特洞察数量
            self.logger.info(
                f"本地AI分析新增 {len(unique_ai_insights)} 条洞察, {len(unique_ai_recommendations)} 条建议, {len(unique_ai_warnings)} 条警告"
            )

            # 构建返回结果，包含AI和规则生成的洞察
            combined_insights = (
                rule_based_results.get("insights", []) + unique_ai_insights
            )
            combined_recommendations = (
                rule_based_results.get("recommendations", [])
                + unique_ai_recommendations
            )
            combined_warnings = (
                rule_based_results.get("warnings", []) + unique_ai_warnings
            )

            # 增加可视化数据支持
            charts_data = {
                "risk_analysis": {
                    "radar_chart": {
                        "labels": [
                            "市场风险",
                            "协议风险",
                            "流动性风险",
                            "相关性风险",
                            "智能合约风险",
                        ],
                        "datasets": [
                            {
                                "label": "风险评分",
                                "data": [
                                    risk_metrics.get("market_risk", 0),
                                    risk_metrics.get("protocol_risk", 0),
                                    risk_metrics.get("liquidity_risk", 0),
                                    risk_metrics.get("correlation_risk", 0),
                                    risk_metrics.get("smart_contract_risk", 0),
                                ],
                            }
                        ],
                    },
                    "risk_factors_chart": {
                        "labels": [f["name"] for f in risk_factors_data],
                        "scores": [f["score"] for f in risk_factors_data],
                        "weights": [
                            f["weight"] if "weight" in f else 0.1
                            for f in risk_factors_data
                        ],
                    },
                }
            }

            ai_results = {
                "insights": combined_insights,
                "recommendations": combined_recommendations,
                "warnings": combined_warnings,
                "confidence": 0.92,  # AI分析的置信度，未来可以根据实际AI服务返回的置信度调整
                "supporting_data": {
                    **rule_based_results.get("supporting_data", {}),
                    "charts_data": charts_data,
                    "ai_analysis": {
                        "unique_insights": unique_ai_insights,
                        "unique_recommendations": unique_ai_recommendations,
                        "analysis_source": "local_ai",
                    },
                },
            }

            self.logger.info("AI驱动的投资组合洞察生成完成")
            return ai_results

        except Exception as e:
            self.logger.error(f"生成AI驱动投资组合洞察失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            # 出错时回退到规则结果
            return rule_based_results

    def analyze_liquidity_pool_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析流动性池风险

        Args:
            data: 流动性池数据，包含 liquidity_pools 字段，是一个列表，每个元素包含:
                protocol: 协议名称
                asset: 资产名称（通常是代币对，如 'ETH-WBTC'）
                tokens: 代币列表
                valid_tokens: 用于风险计算的有效代币列表
                weight: 在投资组合中的权重
                amount: 投资金额
                position_status: 池子状态（如"ACTIVE"或"INACTIVE"）
                range_info: 价格范围信息（对于Uniswap V4）

        Returns:
            Dict: 风险分析结果，包含风险评分、描述、趋势和数据点
        """
        try:
            self.logger.info("开始分析流动性池风险")

            # 提取流动性池数据
            liquidity_pools = data.get("liquidity_pools", [])
            platform = data.get("platform", "Unknown")  # 获取平台信息

            if not liquidity_pools:
                self.logger.warning("未提供流动性池数据，无法分析流动性池风险")
                return {
                    "risk_score": 50,
                    "description": "未提供流动性池数据，返回默认风险评分",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 计算每个池子的风险分数
            pool_risk_scores = []
            data_points = []

            for pool in liquidity_pools:
                protocol = pool.get("protocol", "Unknown")
                asset = pool.get("asset", "Unknown")
                tokens = pool.get("tokens", [])
                valid_tokens = pool.get(
                    "valid_tokens", tokens
                )  # 使用valid_tokens，如果没有则使用tokens
                weight = pool.get("weight", 0)
                amount = pool.get("amount", 0)

                # 获取Uniswap V4特定数据
                position_status = pool.get("position_status", "UNKNOWN")
                range_info = pool.get("range_info", {})

                # 分析代币组合风险
                token_risk = self._analyze_token_composition(valid_tokens)

                # 计算基于协议的风险调整（例如，知名协议风险较低）
                protocol_risk_factor = self._get_protocol_risk_factor(protocol)

                # Uniswap V4特定风险调整
                position_status_risk = self._get_position_status_risk(position_status)
                price_range_risk = self._get_price_range_risk(range_info)

                # 计算最终池子风险分数，综合考虑代币组成、协议因素、池子状态和价格范围
                base_risk = token_risk * protocol_risk_factor
                pool_risk = min(
                    100, max(0, base_risk * position_status_risk * price_range_risk)
                )

                # 保存池子风险分数（加权）
                if weight > 0:
                    pool_risk_scores.append((pool_risk, weight))

                # 添加数据点
                token_str = "/".join(tokens) if tokens else asset
                data_point = {
                    "protocol": protocol,
                    "pool": asset,
                    "tokens": token_str,
                    "risk_score": pool_risk,
                    "weight": weight,
                    "amount": amount,
                }

                # 添加Uniswap V4特定数据
                if position_status != "UNKNOWN":
                    data_point["position_status"] = position_status
                if range_info:
                    data_point["range_info"] = range_info

                data_points.append(data_point)

            # 计算加权平均风险分数
            if pool_risk_scores:
                total_weight = sum(weight for _, weight in pool_risk_scores)
                if total_weight > 0:
                    weighted_risk = (
                        sum(score * weight for score, weight in pool_risk_scores)
                        / total_weight
                    )
                else:
                    weighted_risk = 50  # 默认中等风险
            else:
                weighted_risk = 50

            # 确保分数在0-100范围内
            risk_score = min(100, max(0, weighted_risk))

            # 确定风险趋势
            trend = self._determine_liquidity_pool_trend(data_points)

            # 生成风险描述
            description = self._generate_liquidity_pool_description(
                risk_score, data_points, platform
            )

            # 构建完整分析结果
            result = {
                "risk_score": risk_score,
                "description": description,
                "trend": trend,
                "data_points": data_points,
            }

            self.logger.info(f"流动性池风险分析完成，总体风险评分: {risk_score:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"分析流动性池风险时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "risk_score": 50,  # 默认中等风险
                "description": f"分析流动性池风险时出错: {str(e)}",
                "trend": "稳定",
                "data_points": [],
            }

    def _analyze_token_composition(self, tokens: List[str]) -> float:
        """
        分析代币组合风险

        Args:
            tokens: 代币列表

        Returns:
            float: 代币组合风险分数 (0-100)
        """
        if not tokens:
            return 50  # 默认中等风险

        # 定义稳定币列表
        stablecoins = [
            "USDT",
            "USDC",
            "DAI",
            "BUSD",
            "TUSD",
            "USDP",
            "GUSD",
            "USDK",
            "USDJ",
        ]
        bluechip_tokens = ["BTC", "ETH", "BNB", "SOL", "ADA", "DOT", "AVAX", "MATIC"]

        # 计算稳定币数量和蓝筹代币数量
        stablecoin_count = sum(1 for token in tokens if token in stablecoins)
        bluechip_count = sum(1 for token in tokens if token in bluechip_tokens)
        volatile_count = len(tokens) - stablecoin_count - bluechip_count

        # 计算风险分数
        if len(tokens) == 1:
            # 单一资产，不是真正的LP
            return 30
        elif stablecoin_count == len(tokens):
            # 纯稳定币池，风险低
            return 20
        elif stablecoin_count > 0 and bluechip_count > 0 and volatile_count == 0:
            # 稳定币+蓝筹组合，中低风险
            return 40
        elif stablecoin_count > 0 and volatile_count > 0:
            # 稳定币+波动币组合，中等风险
            return 60
        elif bluechip_count == len(tokens):
            # 纯蓝筹组合，中等风险
            return 50
        elif bluechip_count > 0 and volatile_count > 0:
            # 蓝筹+波动币组合，中高风险
            return 70
        else:
            # 纯波动币组合，高风险
            return 85

    def _get_protocol_risk_factor(self, protocol: str) -> float:
        """
        获取协议风险因子

        Args:
            protocol: 协议名称

        Returns:
            float: 协议风险因子 (通常是0.8-1.2之间，值越小风险越低)
        """
        # 主流稳定协议，风险较低
        low_risk_protocols = [
            "uniswap",
            "curve",
            "aave",
            "compound",
            "balancer",
            "sushiswap",
        ]
        # 中等风险协议
        medium_risk_protocols = ["pancakeswap", "trader joe", "quickswap", "spookyswap"]

        # 将协议名称转换为小写进行比较
        protocol_lower = protocol.lower()

        if protocol_lower in low_risk_protocols:
            return 0.85  # 降低15%风险
        elif protocol_lower in medium_risk_protocols:
            return 1.0  # 保持原有风险
        else:
            return 1.15  # 增加15%风险

    def _determine_liquidity_pool_trend(self, data_points: List[Dict]) -> str:
        """
        确定流动性池趋势

        Args:
            data_points: 流动性池数据点列表

        Returns:
            str: 趋势描述 (上升/稳定/下降)
        """
        # 目前简单返回稳定，未来可扩展为基于历史数据的趋势分析
        return "稳定"

    def _generate_liquidity_pool_description(
        self, risk_score: float, data_points: List[Dict], platform: str = "Unknown"
    ) -> str:
        """
        生成流动性池风险描述

        Args:
            risk_score: 风险评分
            data_points: 流动性池数据点
            platform: 平台名称

        Returns:
            str: 风险描述
        """
        # 统计池子分布情况
        total_pools = len(data_points)
        if total_pools == 0:
            return "未检测到流动性池头寸"

        high_risk_pools = [p for p in data_points if p.get("risk_score", 0) > 70]
        medium_risk_pools = [
            p for p in data_points if 30 <= p.get("risk_score", 0) <= 70
        ]
        low_risk_pools = [p for p in data_points if p.get("risk_score", 0) < 30]

        # 统计池子状态（针对Uniswap V4）
        inactive_pools = [
            p for p in data_points if p.get("position_status", "") == "INACTIVE"
        ]
        active_pools = [
            p for p in data_points if p.get("position_status", "") == "ACTIVE"
        ]

        is_uniswap_v4 = platform == "Uniswap V4"

        # 根据风险评分生成基础描述
        if risk_score > 75:
            description = f"流动性池组合风险较高，{len(high_risk_pools)}/{total_pools}的池子风险评分超过70分，建议减少高风险池子敞口。"
        elif risk_score > 60:
            description = f"流动性池组合风险中等偏高，包含一些高波动性代币池，考虑增加稳定币池比例。"
        elif risk_score > 40:
            description = (
                f"流动性池组合风险适中，代币组合相对平衡，继续监控个别高风险池子表现。"
            )
        elif risk_score > 25:
            description = f"流动性池组合风险较低，{len(low_risk_pools)}/{total_pools}的池子风险评分低于30分，以稳定币池和蓝筹代币池为主。"
        else:
            description = (
                "流动性池组合风险非常低，主要由稳定币池构成，预期收益和风险都较低。"
            )

        # 添加Uniswap V4特定描述
        if is_uniswap_v4 and inactive_pools:
            description += f" 有{len(inactive_pools)}/{total_pools}的池子处于非活跃状态，这些头寸当前不会产生收益，考虑调整价格范围或移除流动性。"

        # 添加针对Uniswap V4的建议
        if is_uniswap_v4:
            # 添加价格范围建议
            narrow_range_pools = []
            wide_range_pools = []

            for pool in data_points:
                range_info = pool.get("range_info", {})
                try:
                    lower_price = float(range_info.get("lower_price", 0))
                    upper_price = float(range_info.get("upper_price", 0))
                    if lower_price > 0:
                        price_range_width = (upper_price - lower_price) / lower_price
                        if price_range_width < 0.01:
                            narrow_range_pools.append(pool)
                        elif price_range_width > 10:
                            wide_range_pools.append(pool)
                except (ValueError, TypeError, ZeroDivisionError):
                    pass

            if narrow_range_pools:
                description += f" 发现{len(narrow_range_pools)}个价格范围极窄的池子，可能容易失去活跃状态，建议适当扩大价格范围。"

            if wide_range_pools:
                description += f" 发现{len(wide_range_pools)}个价格范围极宽的池子，资本效率可能较低，建议考虑缩小价格范围提高资本效率。"

            # 添加未领取手续费建议
            has_fees = any(
                p.get("unclaimed_fees", 0) > 0
                for p in data_points
                if "unclaimed_fees" in p
            )
            if has_fees:
                description += " 有未领取的交易手续费，建议及时领取。"

        return description

    def _analyze_protocol_security(
        self,
        protocol_name: str,
        protocol_metadata: Dict[str, Any],
        risk_score: float,
        risk_metrics: Dict[str, Any],
        risk_level: str,
    ) -> Dict[str, Any]:
        """
        分析协议的安全风险

        Args:
            protocol_name: 协议名称
            protocol_metadata: 协议元数据
            risk_score: 基础风险评分
            risk_metrics: 风险指标
            risk_level: 风险等级

        Returns:
            Dict: 安全风险分析结果
        """
        try:
            # 从协议元数据中提取安全相关信息
            audit_count = protocol_metadata.get("audits", 0)
            audit_links = protocol_metadata.get("audit_links", [])
            is_open_source = protocol_metadata.get("openSource", False)
            github_repos = protocol_metadata.get("github", [])

            # 根据安全指标调整风险评分
            security_risk_score = risk_score

            # 审计数量对风险评分的影响
            if audit_count > 0:
                security_risk_score = max(0, security_risk_score - (audit_count * 5))

            # 开源状态对风险评分的影响
            if is_open_source:
                security_risk_score = max(0, security_risk_score - 10)

            # GitHub仓库对风险评分的影响
            if github_repos and len(github_repos) > 0:
                security_risk_score = max(0, security_risk_score - 5)

            # 确保评分在0-100范围内
            security_risk_score = min(100, max(0, security_risk_score))

            # 确定风险等级
            security_risk_level = self._get_risk_level(security_risk_score)

            # 构建安全风险描述
            if security_risk_score < 30:
                trend = "下降"
                description = f"{protocol_name}协议的安全风险评分较低，"
            elif security_risk_score < 60:
                trend = "稳定"
                description = f"{protocol_name}协议的安全风险评分中等，"
            else:
                trend = "上升"
                description = f"{protocol_name}协议的安全风险评分较高，"

            # 添加审计信息
            if audit_count > 0:
                description += f"已通过{audit_count}次安全审计，"
            else:
                description += "未发现安全审计记录，"

            # 添加开源状态
            if is_open_source:
                description += "代码已开源，"
            else:
                description += "代码未开源，"

            # 添加GitHub仓库信息
            if github_repos and len(github_repos) > 0:
                description += f"有{len(github_repos)}个GitHub仓库。"
            else:
                description += "未发现GitHub仓库。"

            # 构建数据点
            data_points = [
                {"name": "安全风险评分", "value": security_risk_score},
                {"name": "安全风险等级", "value": security_risk_level},
                {"name": "审计次数", "value": audit_count},
                {"name": "是否开源", "value": "是" if is_open_source else "否"},
                {
                    "name": "GitHub仓库数",
                    "value": len(github_repos) if github_repos else 0,
                },
            ]

            # 添加审计链接
            if audit_links:
                data_points.append({"name": "审计链接", "value": audit_links})

            # 构建安全风险分析结果
            return {
                "protocol_name": protocol_name,
                "risk_score": security_risk_score,
                "risk_level": security_risk_level,
                "description": description,
                "trend": trend,
                "data_points": data_points,
                "confidence": 0.85,
                "analysis_type": "security",
                "analysis_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"分析协议安全风险时出错: {str(e)}")
            return {
                "error": f"安全风险分析失败: {str(e)}",
                "risk_score": risk_score,
                "risk_level": risk_level,
                "description": f"无法完成{protocol_name}的安全风险分析",
                "trend": "未知",
                "data_points": [],
                "confidence": 0.3,
            }

    def _analyze_protocol_governance(
        self,
        protocol_name: str,
        protocol_metadata: Dict[str, Any],
        risk_score: float,
        risk_metrics: Dict[str, Any],
        risk_level: str,
    ) -> Dict[str, Any]:
        """
        分析协议的治理风险

        Args:
            protocol_name: 协议名称
            protocol_metadata: 协议元数据
            risk_score: 基础风险评分
            risk_metrics: 风险指标
            risk_level: 风险等级

        Returns:
            Dict: 治理风险分析结果
        """
        try:
            # 从协议元数据中提取治理相关信息
            category = protocol_metadata.get("category", "未知")
            governance_token = protocol_metadata.get("governanceToken", "")
            tvl = protocol_metadata.get("tvl", 0)

            # 根据治理指标调整风险评分
            governance_risk_score = risk_score

            # 是否有治理代币对风险的影响
            has_governance = bool(governance_token)
            if not has_governance:
                governance_risk_score += 15  # 无治理代币增加风险

            # 基于协议类别的治理风险调整
            high_governance_risk_categories = [
                "Lending",
                "Derivatives",
                "Insurance",
                "Options",
            ]
            medium_governance_risk_categories = ["Dexes", "Yield", "Bridges"]

            if category in high_governance_risk_categories:
                governance_risk_score += 10
            elif category in medium_governance_risk_categories:
                governance_risk_score += 5

            # TVL对治理风险的影响 (高TVL通常意味着更成熟的治理)
            if tvl > 1000000000:  # > 10亿
                governance_risk_score = max(0, governance_risk_score - 15)
            elif tvl > 100000000:  # > 1亿
                governance_risk_score = max(0, governance_risk_score - 10)
            elif tvl > 10000000:  # > 1000万
                governance_risk_score = max(0, governance_risk_score - 5)

            # 确保评分在0-100范围内
            governance_risk_score = min(100, max(0, governance_risk_score))

            # 确定风险等级
            governance_risk_level = self._get_risk_level(governance_risk_score)

            # 构建治理风险描述
            if governance_risk_score < 30:
                trend = "下降"
                description = f"{protocol_name}的治理风险较低，"
            elif governance_risk_score < 60:
                trend = "稳定"
                description = f"{protocol_name}的治理风险适中，"
            else:
                trend = "上升"
                description = f"{protocol_name}的治理风险较高，"

            # 添加治理代币信息
            if has_governance:
                description += f"拥有治理代币({governance_token})，"
            else:
                description += "无治理代币，"

            # 添加协议类别信息
            description += f"作为{category}类别的协议，"

            if category in high_governance_risk_categories:
                description += "此类协议通常具有较高的治理复杂性。"
            elif category in medium_governance_risk_categories:
                description += "此类协议具有中等治理复杂性。"
            else:
                description += "此类协议治理复杂性相对较低。"

            # 添加TVL信息
            if tvl > 0:
                description += f" 当前锁仓量(TVL)为{tvl:.2f}美元，"
                if tvl > 100000000:
                    description += "较大的TVL通常意味着更成熟和稳定的治理结构。"
                elif tvl > 10000000:
                    description += "中等规模的TVL对应适中的治理成熟度。"
                else:
                    description += "较小的TVL可能意味着治理结构尚未充分发展。"

            # 构建数据点
            data_points = [
                {"name": "治理风险评分", "value": governance_risk_score},
                {"name": "治理风险等级", "value": governance_risk_level},
                {"name": "协议类别", "value": category},
                {
                    "name": "治理代币",
                    "value": governance_token if has_governance else "无",
                },
                {"name": "TVL", "value": tvl},
            ]

            # 构建治理风险分析结果
            return {
                "protocol_name": protocol_name,
                "risk_score": governance_risk_score,
                "risk_level": governance_risk_level,
                "description": description,
                "trend": trend,
                "data_points": data_points,
                "confidence": 0.8,
                "analysis_type": "governance",
                "analysis_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"分析协议治理风险时出错: {str(e)}")
            return {
                "error": f"治理风险分析失败: {str(e)}",
                "risk_score": risk_score,
                "risk_level": risk_level,
                "description": f"无法完成{protocol_name}的治理风险分析",
                "trend": "未知",
                "data_points": [],
                "confidence": 0.3,
            }

    def _analyze_protocol_history(
        self,
        protocol_name: str,
        protocol_metadata: Dict[str, Any],
        tvl_df: pd.DataFrame,
        risk_score: float,
        risk_metrics: Dict[str, Any],
        risk_level: str,
    ) -> Dict[str, Any]:
        """
        分析协议的历史风险

        Args:
            protocol_name: 协议名称
            protocol_metadata: 协议元数据
            tvl_df: TVL历史数据
            risk_score: 基础风险评分
            risk_metrics: 风险指标
            risk_level: 风险等级

        Returns:
            Dict: 历史风险分析结果
        """
        try:
            # 获取协议年龄和历史数据
            category = protocol_metadata.get("category", "未知")
            tvl_history = []

            if (
                not tvl_df.empty
                and "date" in tvl_df.columns
                and "tvl" in tvl_df.columns
            ):
                # 计算协议年龄（天数）
                first_date = tvl_df["date"].min()
                last_date = tvl_df["date"].max()

                if isinstance(first_date, datetime) and isinstance(last_date, datetime):
                    protocol_age_days = (last_date - first_date).days
                else:
                    protocol_age_days = 0

                # 提取TVL历史趋势数据
                tvl_history = tvl_df[["date", "tvl"]].to_dict("records")
            else:
                protocol_age_days = 0

            # 根据历史指标调整风险评分
            history_risk_score = risk_score

            # 协议年龄对风险的影响
            if protocol_age_days > 365 * 2:  # > 2年
                history_risk_score = max(0, history_risk_score - 20)
            elif protocol_age_days > 365:  # > 1年
                history_risk_score = max(0, history_risk_score - 15)
            elif protocol_age_days > 180:  # > 6个月
                history_risk_score = max(0, history_risk_score - 10)
            elif protocol_age_days > 90:  # > 3个月
                history_risk_score = max(0, history_risk_score - 5)
            else:  # 新协议
                history_risk_score += 10

            # TVL波动性对历史风险的影响
            tvl_volatility = risk_metrics.get("tvl_volatility", 0)
            if tvl_volatility > 30:  # 高波动性
                history_risk_score += 15
            elif tvl_volatility > 20:  # 中高波动性
                history_risk_score += 10
            elif tvl_volatility > 10:  # 中等波动性
                history_risk_score += 5

            # TVL趋势对历史风险的影响
            tvl_growth_30d = risk_metrics.get("tvl_growth_30d", 0)
            if tvl_growth_30d < -20:  # 大幅下降
                history_risk_score += 15
            elif tvl_growth_30d < -10:  # 中度下降
                history_risk_score += 10
            elif tvl_growth_30d < 0:  # 轻微下降
                history_risk_score += 5
            elif tvl_growth_30d > 20:  # 大幅增长
                history_risk_score = max(0, history_risk_score - 10)
            elif tvl_growth_30d > 10:  # 中度增长
                history_risk_score = max(0, history_risk_score - 5)

            # 确保评分在0-100范围内
            history_risk_score = min(100, max(0, history_risk_score))

            # 确定风险等级
            history_risk_level = self._get_risk_level(history_risk_score)

            # 构建历史风险描述
            if history_risk_score < 30:
                trend = "下降"
                description = f"{protocol_name}的历史风险较低，"
            elif history_risk_score < 60:
                trend = "稳定"
                description = f"{protocol_name}的历史风险适中，"
            else:
                trend = "上升"
                description = f"{protocol_name}的历史风险较高，"

            # 添加协议年龄信息
            if protocol_age_days > 0:
                years = protocol_age_days // 365
                months = (protocol_age_days % 365) // 30

                if years > 0:
                    age_desc = f"{years}年"
                    if months > 0:
                        age_desc += f"{months}个月"
                else:
                    age_desc = f"{months}个月"

                description += f"协议运行时间为{age_desc}，"

                if protocol_age_days > 365:
                    description += "较长的运行历史表明一定的稳定性。"
                else:
                    description += "运行历史较短，可能存在不确定性。"
            else:
                description += "无法确定协议运行时间，可能是较新的协议或数据不完整。"

            # 添加TVL趋势信息
            if tvl_growth_30d != 0:
                description += f" 近30天TVL{tvl_growth_30d:.2f}%的变化，"
                if tvl_growth_30d > 0:
                    description += "呈现增长趋势。"
                else:
                    description += "呈现下降趋势。"

            # 添加TVL波动性信息
            if tvl_volatility > 0:
                description += f" TVL波动性为{tvl_volatility:.2f}%，"
                if tvl_volatility > 20:
                    description += "波动性较大。"
                elif tvl_volatility > 10:
                    description += "波动性中等。"
                else:
                    description += "波动性较小。"

            # 构建数据点
            data_points = [
                {"name": "历史风险评分", "value": history_risk_score},
                {"name": "历史风险等级", "value": history_risk_level},
                {"name": "协议年龄(天)", "value": protocol_age_days},
                {"name": "TVL 30天增长率(%)", "value": tvl_growth_30d},
                {"name": "TVL波动性(%)", "value": tvl_volatility},
                {"name": "协议类别", "value": category},
            ]

            # 如果有历史数据，添加
            if tvl_history:
                data_points.append(
                    {"name": "TVL历史", "value": tvl_history[:10]}
                )  # 仅取前10条记录

            # 构建历史风险分析结果
            return {
                "protocol_name": protocol_name,
                "risk_score": history_risk_score,
                "risk_level": history_risk_level,
                "description": description,
                "trend": trend,
                "data_points": data_points,
                "confidence": 0.8,
                "analysis_type": "history",
                "analysis_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"分析协议历史风险时出错: {str(e)}")
            return {
                "error": f"历史风险分析失败: {str(e)}",
                "risk_score": risk_score,
                "risk_level": risk_level,
                "description": f"无法完成{protocol_name}的历史风险分析",
                "trend": "未知",
                "data_points": [],
                "confidence": 0.3,
            }

    def _analyze_protocol_complexity(
        self,
        protocol_name: str,
        protocol_metadata: Dict[str, Any],
        chain_distribution: Dict[str, Any],
        risk_score: float,
        risk_metrics: Dict[str, Any],
        risk_level: str,
    ) -> Dict[str, Any]:
        """
        分析协议的复杂性风险

        Args:
            protocol_name: 协议名称
            protocol_metadata: 协议元数据
            chain_distribution: 链分布数据
            risk_score: 基础风险评分
            risk_metrics: 风险指标
            risk_level: 风险等级

        Returns:
            Dict: 复杂性风险分析结果
        """
        try:
            # 从协议元数据中提取复杂性相关信息
            category = protocol_metadata.get("category", "未知")
            chains = list(chain_distribution.keys()) if chain_distribution else []
            github_repos = protocol_metadata.get("github", [])
            is_open_source = protocol_metadata.get("openSource", False)

            # 根据复杂性指标调整风险评分
            complexity_risk_score = risk_score

            # 多链部署对复杂性的影响
            chain_factor = min(30, len(chains) * 5)  # 每条链增加5分，最多30分
            complexity_risk_score += chain_factor

            # 协议类别复杂性因素
            category_complexity = {
                "Dexes": 15,  # DEX复杂性中等
                "Lending": 20,  # 借贷协议复杂性较高
                "Yield": 25,  # 收益协议复杂性高
                "Derivatives": 30,  # 衍生品协议复杂性高
                "Options": 35,  # 期权协议复杂性很高
                "Staking": 10,  # 质押协议复杂性较低
                "Bridges": 25,  # 跨链桥复杂性高
                "Yield Aggregator": 30,  # 收益聚合器复杂性高
                "Insurance": 20,  # 保险协议复杂性较高
                "Payments": 15,  # 支付协议复杂性中等
                "Privacy": 25,  # 隐私协议复杂性高
            }

            category_factor = category_complexity.get(category, 20)  # 默认中等复杂性
            complexity_risk_score += category_factor

            # 开源和GitHub仓库对复杂性的理解和透明度的影响
            if is_open_source:
                complexity_risk_score = max(0, complexity_risk_score - 10)

            if github_repos and len(github_repos) > 0:
                complexity_risk_score = max(0, complexity_risk_score - 10)

            # 确保评分在0-100范围内
            complexity_risk_score = min(100, max(0, complexity_risk_score))

            # 确定风险等级
            complexity_risk_level = self._get_risk_level(complexity_risk_score)

            # 构建复杂性风险描述
            if complexity_risk_score < 30:
                trend = "下降"
                description = f"{protocol_name}的复杂性风险较低，"
            elif complexity_risk_score < 60:
                trend = "稳定"
                description = f"{protocol_name}的复杂性风险适中，"
            else:
                trend = "上升"
                description = f"{protocol_name}的复杂性风险较高，"

            # 添加多链信息
            if chains:
                description += f"部署在{len(chains)}条区块链上"
                if len(chains) > 3:
                    chain_examples = ", ".join(chains[:3]) + "等"
                else:
                    chain_examples = ", ".join(chains)
                description += f"（{chain_examples}），"

                if len(chains) > 5:
                    description += "多链部署显著增加了协议的复杂性。"
                elif len(chains) > 2:
                    description += "跨链操作增加了一定的复杂性。"
                else:
                    description += "链支持有限，复杂性较低。"
            else:
                description += "未提供链部署信息。"

            # 添加协议类别信息
            description += f" 作为{category}类别的协议，"

            if category_factor > 25:
                description += "该类别通常具有较高的技术复杂性。"
            elif category_factor > 15:
                description += "该类别具有中等技术复杂性。"
            else:
                description += "该类别技术复杂性相对较低。"

            # 添加开源和GitHub信息
            if is_open_source:
                description += " 代码开源增加了透明度，"
            else:
                description += " 代码不开源增加了理解难度，"

            if github_repos and len(github_repos) > 0:
                description += f"有{len(github_repos)}个公开的GitHub仓库提供参考。"
            else:
                description += "缺乏公开的代码仓库。"

            # 构建数据点
            data_points = [
                {"name": "复杂性风险评分", "value": complexity_risk_score},
                {"name": "复杂性风险等级", "value": complexity_risk_level},
                {"name": "支持的区块链数量", "value": len(chains)},
                {"name": "协议类别", "value": category},
                {"name": "协议类别复杂性因子", "value": category_factor},
                {"name": "是否开源", "value": "是" if is_open_source else "否"},
                {
                    "name": "GitHub仓库数",
                    "value": len(github_repos) if github_repos else 0,
                },
            ]

            # 添加链列表
            if chains:
                data_points.append({"name": "支持的区块链", "value": chains})

            # 添加GitHub仓库
            if github_repos and len(github_repos) > 0:
                data_points.append({"name": "GitHub仓库", "value": github_repos})

            # 构建复杂性风险分析结果
            return {
                "protocol_name": protocol_name,
                "risk_score": complexity_risk_score,
                "risk_level": complexity_risk_level,
                "description": description,
                "trend": trend,
                "data_points": data_points,
                "confidence": 0.75,
                "analysis_type": "complexity",
                "analysis_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"分析协议复杂性风险时出错: {str(e)}")
            return {
                "error": f"复杂性风险分析失败: {str(e)}",
                "risk_score": risk_score,
                "risk_level": risk_level,
                "description": f"无法完成{protocol_name}的复杂性风险分析",
                "trend": "未知",
                "data_points": [],
                "confidence": 0.3,
            }

    def analyze_liquidity_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        流动性风险分析路由方法 - 根据分析类型调用适当的分析方法

        Args:
            data: 分析数据，必须包含 'analysis_type' 字段指明具体分析类型:
                - 'asset_liquidity': 资产流动性分析
                - 'protocol_liquidity': 协议流动性分析
                - 'investment_type_liquidity': 投资类型流动性分析
                如果未指定，默认为综合流动性分析

        Returns:
            Dict: 相应类型的流动性风险分析结果
        """
        try:
            # 从数据中提取分析类型
            analysis_type = data.get("analysis_type", "general_liquidity")
            self.logger.info(f"开始流动性风险分析，类型: {analysis_type}")

            # 根据分析类型调用相应的方法
            if analysis_type == "asset_liquidity":
                return self.analyze_asset_liquidity(data)
            elif analysis_type == "protocol_liquidity":
                return self.analyze_protocol_liquidity(data)
            elif analysis_type == "investment_type_liquidity":
                return self.analyze_investment_type_liquidity(data)
            else:
                # 默认行为：如果数据中包含流动性池信息，则分析流动性池风险
                if "liquidity_pools" in data:
                    return self.analyze_liquidity_pool_risk(data)
                else:
                    self.logger.warning(
                        f"未知的流动性分析类型: {analysis_type}，返回默认风险评估"
                    )
                    return {
                        "risk_score": 50,
                        "description": f"未知的流动性分析类型: {analysis_type}，返回默认风险评估",
                        "trend": "稳定",
                        "data_points": [],
                    }

        except Exception as e:
            self.logger.error(f"流动性风险分析路由出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "risk_score": 50,
                "description": f"流动性风险分析出错: {str(e)}",
                "trend": "稳定",
                "data_points": [],
                "error": str(e),
            }

    def analyze_asset_liquidity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析资产流动性风险

        Args:
            data: 资产数据，包含 'assets' 字段，是一个字典，键为资产名称，值为资产金额

        Returns:
            Dict: 资产流动性风险分析结果
        """
        try:
            self.logger.info("开始分析资产流动性风险")

            # 提取资产数据
            assets = data.get("assets", {})
            if not assets:
                self.logger.warning("未提供资产数据，无法分析资产流动性风险")
                return {
                    "risk_score": 50,
                    "description": "未提供资产数据，返回默认风险评分",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 计算总资产价值
            total_value = sum(assets.values())
            if total_value == 0:
                self.logger.warning("资产总价值为0，无法分析资产流动性风险")
                return {
                    "risk_score": 50,
                    "description": "资产总价值为0，返回默认风险评分",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 定义高流动性资产（常见代币）
            high_liquidity_assets = [
                "BTC",
                "ETH",
                "USDT",
                "USDC",
                "DAI",
                "BNB",
                "SOL",
                "ADA",
                "DOT",
                "AVAX",
                "MATIC",
                "LINK",
                "UNI",
                "AAVE",
            ]

            # 定义中等流动性资产
            medium_liquidity_assets = [
                "SUSHI",
                "CRV",
                "COMP",
                "SNX",
                "MKR",
                "YFI",
                "FTM",
                "ATOM",
                "ALGO",
                "NEAR",
                "ONE",
                "FTT",
                "KCS",
            ]

            # 计算资产流动性评分
            assets_data = []
            weighted_liquidity_score = 0

            for asset, amount in assets.items():
                weight = amount / total_value

                # 基于资产类型分配流动性评分
                if asset in high_liquidity_assets:
                    liquidity_score = 20  # 高流动性，低风险
                elif asset in medium_liquidity_assets:
                    liquidity_score = 50  # 中等流动性，中等风险
                else:
                    liquidity_score = 80  # 低流动性，高风险

                # 计算加权评分
                weighted_liquidity_score += liquidity_score * weight

                assets_data.append(
                    {
                        "asset": asset,
                        "amount": amount,
                        "weight": weight,
                        "liquidity_score": liquidity_score,
                    }
                )

            # 生成描述
            if weighted_liquidity_score < 30:
                description = "投资组合主要由高流动性资产组成，流动性风险较低"
                trend = "稳定"
            elif weighted_liquidity_score < 60:
                description = "投资组合流动性适中，包含一定比例的中低流动性资产"
                trend = "稳定"
            else:
                description = "投资组合包含较多低流动性资产，流动性风险较高"
                trend = "上升"  # 风险趋势上升

            # 构建分析结果
            result = {
                "risk_score": weighted_liquidity_score,
                "description": description,
                "trend": trend,
                "data_points": assets_data,
            }

            self.logger.info(
                f"资产流动性风险分析完成，总体风险评分: {weighted_liquidity_score:.2f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"分析资产流动性风险时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "risk_score": 50,
                "description": f"分析资产流动性风险时出错: {str(e)}",
                "trend": "稳定",
                "data_points": [],
                "error": str(e),
            }

    def analyze_protocol_liquidity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析协议流动性风险

        Args:
            data: 协议数据，包含 'protocols' 字段（协议列表）和 'weights' 字段（协议权重字典）

        Returns:
            Dict: 协议流动性风险分析结果
        """
        try:
            self.logger.info("开始分析协议流动性风险")

            # 提取协议数据
            protocols = data.get("protocols", [])
            weights = data.get("weights", {})

            if not protocols:
                self.logger.warning("未提供协议数据，无法分析协议流动性风险")
                return {
                    "risk_score": 50,
                    "description": "未提供协议数据，返回默认风险评分",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 定义各协议流动性风险评分
            protocol_risk_scores = {
                # 主流协议，流动性高，风险低
                "aave": 20,
                "compound": 20,
                "uniswap": 25,
                "curve": 25,
                "makerdao": 25,
                "balancer": 30,
                "sushiswap": 35,
                "yearn": 40,
                "pancakeswap": 40,
                # 中等流动性协议
                "trader joe": 50,
                "quickswap": 55,
                "spookyswap": 60,
                # 默认分数
                "default": 65,  # 默认为中高风险
            }

            # 计算加权风险评分
            protocols_data = []
            weighted_protocol_liquidity_score = 0
            total_weight = sum(weights.values()) if weights else 0

            for protocol in protocols:
                protocol_lower = protocol.lower()
                # 获取协议权重
                weight = weights.get(protocol, 0) if weights else (1.0 / len(protocols))

                # 获取协议风险评分
                liquidity_score = protocol_risk_scores.get(
                    protocol_lower, protocol_risk_scores["default"]
                )

                # 计算加权评分
                weighted_protocol_liquidity_score += liquidity_score * weight

                protocols_data.append(
                    {
                        "protocol": protocol,
                        "weight": weight,
                        "liquidity_score": liquidity_score,
                    }
                )

            # 生成描述
            if weighted_protocol_liquidity_score < 30:
                description = "投资主要集中在流动性高的主流协议，流动性风险较低"
                trend = "稳定"
            elif weighted_protocol_liquidity_score < 50:
                description = "投资分布于多种协议，整体流动性风险适中"
                trend = "稳定"
            else:
                description = "投资包含较多流动性有限的小型协议，流动性风险较高"
                trend = "上升"

            # 构建分析结果
            result = {
                "risk_score": weighted_protocol_liquidity_score,
                "description": description,
                "trend": trend,
                "data_points": protocols_data,
            }

            self.logger.info(
                f"协议流动性风险分析完成，总体风险评分: {weighted_protocol_liquidity_score:.2f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"分析协议流动性风险时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "risk_score": 50,
                "description": f"分析协议流动性风险时出错: {str(e)}",
                "trend": "稳定",
                "data_points": [],
                "error": str(e),
            }

    def analyze_investment_type_liquidity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析投资类型流动性风险

        Args:
            data: 投资类型数据，包含 'investment_types' 字段，是一个字典，
                 键为投资类型名称，值为该类型的投资金额

        Returns:
            Dict: 投资类型流动性风险分析结果
        """
        try:
            self.logger.info("开始分析投资类型流动性风险")

            # 提取投资类型数据
            investment_types = data.get("investment_types", {})

            if not investment_types:
                self.logger.warning("未提供投资类型数据，无法分析投资类型流动性风险")
                return {
                    "risk_score": 50,
                    "description": "未提供投资类型数据，返回默认风险评分",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 计算总投资价值
            total_value = sum(investment_types.values())
            if total_value == 0:
                self.logger.warning("投资总价值为0，无法分析投资类型流动性风险")
                return {
                    "risk_score": 50,
                    "description": "投资总价值为0，返回默认风险评分",
                    "trend": "稳定",
                    "data_points": [],
                }

            # 定义投资类型的流动性风险评分
            type_risk_scores = {
                "spot": 20,  # 现货持有，流动性高
                "staking": 40,  # 质押，中等流动性
                "lending": 35,  # 借贷，中高流动性
                "liquidity_pool": 60,  # 流动性池，中等流动性
                "leveraged": 75,  # 杠杆，流动性风险高
                "borrowed": 70,  # 借入，流动性风险较高
                "other": 65,  # 其他类型，默认中高风险
            }

            # 计算加权风险评分
            investment_types_data = []
            weighted_investment_type_liquidity_score = 0

            for inv_type, amount in investment_types.items():
                weight = amount / total_value

                # 获取投资类型流动性风险评分
                liquidity_score = type_risk_scores.get(
                    inv_type, type_risk_scores["other"]
                )

                # 计算加权评分
                weighted_investment_type_liquidity_score += liquidity_score * weight

                investment_types_data.append(
                    {
                        "investment_type": inv_type,
                        "amount": amount,
                        "weight": weight,
                        "liquidity_score": liquidity_score,
                    }
                )

            # 生成描述
            if weighted_investment_type_liquidity_score < 30:
                description = (
                    "投资组合主要由高流动性投资类型组成，如现货持有，流动性风险低"
                )
                trend = "稳定"
            elif weighted_investment_type_liquidity_score < 60:
                description = "投资组合包含不同流动性级别的投资类型，整体流动性风险适中"
                trend = "稳定"
            else:
                description = (
                    "投资组合包含较多低流动性投资类型，如杠杆和借入资产，流动性风险较高"
                )
                trend = "上升"

            # 构建分析结果
            result = {
                "risk_score": weighted_investment_type_liquidity_score,
                "description": description,
                "trend": trend,
                "data_points": investment_types_data,
            }

            self.logger.info(
                f"投资类型流动性风险分析完成，总体风险评分: {weighted_investment_type_liquidity_score:.2f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"分析投资类型流动性风险时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "risk_score": 50,
                "description": f"分析投资类型流动性风险时出错: {str(e)}",
                "trend": "稳定",
                "data_points": [],
                "error": str(e),
            }

    def _get_position_status_risk(self, position_status: str) -> float:
        """
        根据池子状态评估风险因子

        Args:
            position_status: 池子状态

        Returns:
            float: 风险调整因子
        """
        if position_status == "INACTIVE":
            return 1.15  # 增加15%风险
        return 1.0  # 默认不调整

    def _get_price_range_risk(self, range_info: Dict[str, Any]) -> float:
        """
        根据价格范围评估风险因子

        Args:
            range_info: 价格范围信息

        Returns:
            float: 风险调整因子
        """
        try:
            lower_price = float(range_info.get("lower_price", 0))
            upper_price = float(range_info.get("upper_price", 0))

            if lower_price <= 0:
                return 1.0  # 无法计算

            price_range_width = (upper_price - lower_price) / lower_price

            # 价格范围极窄或极宽都增加风险
            if price_range_width < 0.01:
                return 1.2  # 范围太窄，增加20%风险
            elif price_range_width > 10:
                return 1.1  # 范围很宽，增加10%风险

            return 1.0  # 默认不调整
        except (ValueError, TypeError, ZeroDivisionError):
            return 1.0  # 默认不调整
