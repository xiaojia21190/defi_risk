"""
情绪分析服务 - 负责处理和分析加密货币相关的市场情绪数据
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.domain.sentiment import (
    SentimentType,
    RawSentimentItem,
    SentimentAnalysisResult,
    SentimentTimeSeriesPoint,
    SentimentTimeSeries,
    SentimentRiskMetrics,
    SentimentRiskFactor,
    AssetSentimentSummary,
)
from dataclasses import asdict
import json
from cachetools import TTLCache
import statistics
from textblob import TextBlob
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk
from scipy import stats
from collections import Counter


# 确保必要的NLTK资源已下载
try:
    nltk.data.find("tokenizers/punkt")
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("punkt")
    nltk.download("stopwords")


logger = logging.getLogger("defi_risk.sentiment_analysis_service")


class SentimentAnalysisService:
    """情绪分析服务"""

    def __init__(self, ai_service=None, data_service=None):
        """
        初始化情绪分析服务

        Args:
            ai_service: 可选的AI服务实例，用于高级情绪分析
            data_service: 可选的数据服务实例，用于获取原始情绪数据
        """
        self.logger = logger
        self.ai_service = ai_service
        self.data_service = data_service
        self.cache = TTLCache(maxsize=1000, ttl=3600 * 6)  # 6小时缓存

        # 停用词
        self.stop_words = set(stopwords.words("english"))
        self.crypto_stop_words = {
            "crypto",
            "cryptocurrency",
            "token",
            "blockchain",
            "defi",
            "bitcoin",
            "ethereum",
            "coin",
            "trading",
            "market",
            "price",
        }
        self.stop_words.update(self.crypto_stop_words)

        # 加密货币情绪词典
        self.sentiment_lexicon = self._load_sentiment_lexicon()

        # 情绪分析配置
        self.config = {
            "default_window": "7d",  # 默认情绪分析窗口
            "min_data_points": 10,  # 有效分析的最小数据点数量
            "time_decay_factor": 0.9,  # 时间衰减因子
            "social_weight": 0.6,  # 社交媒体权重
            "news_weight": 0.4,  # 新闻权重
            "sentiment_thresholds": {
                "very_negative": -0.6,
                "negative": -0.2,
                "neutral_low": -0.1,
                "neutral_high": 0.1,
                "positive": 0.2,
                "very_positive": 0.6,
            },
            # 不同来源的权重配置
            "source_weights": {
                "twitter": 0.6,  # 社交媒体
                "reddit": 0.6,  # 社交媒体
                "crypto_news": 0.4,  # 新闻
                "blog": 0.4,  # 博客
                "default": 0.5,  # 默认权重
            },
        }

        self.logger.info("情绪分析服务初始化完成")

    def _load_sentiment_lexicon(self) -> Dict[str, float]:
        """
        加载加密货币特定的情绪词典

        Returns:
            情绪词典，单词到情绪分数的映射
        """
        # 这里可以从文件加载自定义的加密货币情绪词典
        # 简化起见，这里仅提供一个小型示例词典
        lexicon = {
            # 正面词汇
            "bullish": 0.8,
            "moon": 0.7,
            "rally": 0.6,
            "surge": 0.7,
            "adoption": 0.5,
            "breakthrough": 0.6,
            "partnership": 0.5,
            "soar": 0.7,
            "gain": 0.4,
            "upgrade": 0.5,
            # 负面词汇
            "bearish": -0.8,
            "crash": -0.9,
            "dump": -0.7,
            "scam": -0.9,
            "hack": -0.8,
            "ban": -0.7,
            "regulation": -0.4,
            "sell": -0.3,
            "fud": -0.6,
            "bubble": -0.5,
            # 中性但在加密上下文中有倾向的词
            "dip": -0.2,  # 轻微负面
            "hodl": 0.3,  # 轻微正面
            "whale": 0.0,  # 中性，取决于上下文
            "altcoin": 0.0,
            "mining": 0.0,
            "stake": 0.2,  # 轻微正面
            "yield": 0.2,  # 轻微正面
        }
        return lexicon

    def _get_bucket_start_time(
        self, timestamp: datetime, interval: timedelta
    ) -> datetime:
        """计算给定时间戳和间隔的标准化时间桶开始时间"""
        if interval == timedelta(hours=1):
            # 每小时桶：将分钟、秒、微秒归零
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif interval == timedelta(hours=6):
            # 每6小时桶：将小时向下取整到0, 6, 12, 18，并归零分钟、秒、微秒
            hour_bucket = (timestamp.hour // 6) * 6
            return timestamp.replace(
                hour=hour_bucket, minute=0, second=0, microsecond=0
            )
        elif interval == timedelta(days=1):
            # 每日桶：将时间归零到午夜
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # 对于不支持的间隔，可以返回原始时间戳或抛出错误
            # 这里选择返回按小时归零的时间作为备用逻辑
            self.logger.warning(
                f"Unsupported interval {interval} for bucketing, falling back to hourly."
            )
            return timestamp.replace(minute=0, second=0, microsecond=0)

    async def analyze_raw_sentiment_data(
        self, raw_data: List[RawSentimentItem]
    ) -> List[SentimentAnalysisResult]:
        """
        分析原始情绪数据

        Args:
            raw_data: 原始情绪数据列表

        Returns:
            情绪分析结果列表
        """
        if not raw_data:
            return []

        results = []

        # 尝试使用AI服务进行高级分析
        if self.ai_service and settings.ENABLE_AI_SENTIMENT_ANALYSIS:
            try:
                ai_results = await self._analyze_with_ai(raw_data)
                if ai_results:
                    self.logger.info(f"使用AI服务成功分析了{len(ai_results)}条情绪数据")
                    results.extend(ai_results)
                    return results
            except Exception as e:
                self.logger.error(f"使用AI服务分析情绪数据失败: {str(e)}")
                # 继续使用传统方法

        # 使用传统的NLP方法分析
        for item in raw_data:
            try:
                # 简单的文本预处理
                text = self._preprocess_text(item.content)

                # 使用TextBlob进行情感分析
                blob = TextBlob(text)
                sentiment_score = blob.sentiment.polarity

                # 应用加密货币特定词典调整
                adjusted_score = self._adjust_sentiment_with_lexicon(
                    text, sentiment_score
                )

                # 确定情绪类型
                sentiment_type = self._determine_sentiment_type(adjusted_score)

                # 提取关键词和主题
                keywords = self._extract_keywords(text)
                topics = self._extract_topics(text, keywords)

                # 创建分析结果
                result = SentimentAnalysisResult(
                    raw_item_id=item.id,
                    asset=item.asset,
                    source=item.source,
                    timestamp=datetime.utcnow(),
                    sentiment_type=sentiment_type,
                    sentiment_score=adjusted_score,
                    confidence=0.7,  # 传统方法的置信度相对较低
                    topics=topics,
                    keywords=keywords,
                    entities=[],  # 简单实现不提取实体
                    metadata={
                        "original_score": sentiment_score,
                        "engagement": item.engagement,
                    },
                )
                results.append(result)
            except Exception as e:
                self.logger.error(f"分析情绪数据项失败: {str(e)}, 项目ID: {item.id}")

        self.logger.info(f"成功分析了{len(results)}/{len(raw_data)}条情绪数据")
        return results

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        if not text:
            return ""

        # 转换为小写
        text = text.lower()

        # 移除URL
        text = re.sub(r"http\S+", "", text)

        # 移除HTML标签
        text = re.sub(r"<.*?>", "", text)

        # 移除特殊字符，但保留基本标点
        text = re.sub(r"[^\w\s\.\,\!\?\-\:]", "", text)

        # 移除多余的空白
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _adjust_sentiment_with_lexicon(self, text: str, base_score: float) -> float:
        """使用加密货币词典调整情感分数"""
        if not text:
            return base_score

        words = word_tokenize(text.lower())
        lexicon_scores = []

        for word in words:
            if word in self.sentiment_lexicon:
                lexicon_scores.append(self.sentiment_lexicon[word])

        if not lexicon_scores:
            return base_score

        # 将基础分数与词典分数结合
        lexicon_avg = sum(lexicon_scores) / len(lexicon_scores)
        adjusted_score = 0.7 * base_score + 0.3 * lexicon_avg

        # 确保在[-1, 1]范围内
        return max(-1.0, min(1.0, adjusted_score))

    def _determine_sentiment_type(self, score: float) -> SentimentType:
        """根据情感分数确定情绪类型"""
        thresholds = self.config["sentiment_thresholds"]

        if score <= thresholds["very_negative"]:
            return SentimentType.NEGATIVE
        elif score <= thresholds["negative"]:
            return SentimentType.NEGATIVE
        elif score >= thresholds["very_positive"]:
            return SentimentType.POSITIVE
        elif score >= thresholds["positive"]:
            return SentimentType.POSITIVE
        else:
            return SentimentType.NEUTRAL

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        从文本中提取关键词

        Args:
            text: 文本内容
            max_keywords: 最大关键词数量

        Returns:
            关键词列表
        """
        if not text:
            return []

        # 分词
        words = word_tokenize(text.lower())

        # 过滤停用词
        filtered_words = [w for w in words if w not in self.stop_words and len(w) > 2]

        # 统计词频
        word_freq = Counter(filtered_words)

        # 返回频率最高的关键词
        return [word for word, _ in word_freq.most_common(max_keywords)]

    def _extract_topics(self, text: str, keywords: List[str] = None) -> List[str]:
        """
        从文本中提取主题
        简化实现：使用特定领域的主题列表进行匹配

        Args:
            text: 文本内容
            keywords: 已提取的关键词

        Returns:
            主题列表
        """
        # 简化实现：预定义的加密货币主题列表
        crypto_topics = {
            "price": ["price", "value", "worth", "cost", "expensive", "cheap"],
            "trading": ["trade", "buy", "sell", "exchange", "order", "position"],
            "technology": [
                "tech",
                "blockchain",
                "protocol",
                "network",
                "node",
                "smart contract",
            ],
            "regulation": ["regulation", "law", "legal", "government", "ban", "policy"],
            "adoption": [
                "adoption",
                "use",
                "mainstream",
                "institutional",
                "company",
                "corporate",
            ],
            "security": ["security", "hack", "vulnerability", "attack", "safe", "risk"],
            "defi": ["defi", "yield", "farm", "stake", "liquidity", "pool"],
            "nft": ["nft", "collectible", "art", "unique", "token"],
        }

        matched_topics = []

        # 检查每个主题的关键词是否出现在文本中
        text_lower = text.lower()
        for topic, topic_keywords in crypto_topics.items():
            for keyword in topic_keywords:
                if keyword in text_lower:
                    matched_topics.append(topic)
                    break

        # 如果找不到主题但有关键词，使用第一个关键词作为主题
        if not matched_topics and keywords:
            matched_topics.append(keywords[0])

        return matched_topics[:3]  # 最多返回3个主题

    async def _analyze_with_ai(
        self, raw_data: List[RawSentimentItem]
    ) -> List[SentimentAnalysisResult]:
        """
        使用AI服务分析情绪数据

        Args:
            raw_data: 原始情绪数据列表

        Returns:
            AI分析的情绪结果列表
        """
        if not self.ai_service or not raw_data:
            return []

        try:
            # 准备AI分析的数据
            analysis_data = []
            for item in raw_data:
                analysis_data.append(
                    {
                        "id": item.id,
                        "content": item.content,
                        "source": item.source,
                        "asset": item.asset,
                        "timestamp": item.timestamp.isoformat(),
                        "engagement": item.engagement,
                    }
                )

            # 调用AI服务进行批量分析
            ai_context = {
                "task": "sentiment_analysis",
                "data": analysis_data,
                "asset_context": raw_data[0].asset if raw_data else "",
            }

            ai_analysis = await self.ai_service.analyze(
                analysis_type="crypto_sentiment", context=ai_context
            )

            # 处理AI分析结果
            results = []

            if (
                hasattr(ai_analysis, "supporting_data")
                and "sentiment_results" in ai_analysis.supporting_data
            ):
                sentiment_results = ai_analysis.supporting_data["sentiment_results"]

                for result_data in sentiment_results:
                    try:
                        # 查找对应的原始数据项
                        raw_item = next(
                            (
                                item
                                for item in raw_data
                                if item.id == result_data.get("id")
                            ),
                            None,
                        )
                        if not raw_item:
                            continue

                        # 创建分析结果
                        result = SentimentAnalysisResult(
                            raw_item_id=raw_item.id,
                            asset=raw_item.asset,
                            source=raw_item.source,
                            timestamp=datetime.utcnow(),
                            sentiment_type=self._map_ai_sentiment_type(
                                result_data.get("sentiment_type", "neutral")
                            ),
                            sentiment_score=result_data.get("sentiment_score", 0.0),
                            confidence=result_data.get("confidence", 0.8),
                            topics=result_data.get("topics", []),
                            keywords=result_data.get("keywords", []),
                            entities=result_data.get("entities", []),
                            metadata={
                                "ai_analysis": True,
                                "engagement": raw_item.engagement,
                                "ai_insights": result_data.get("insights", []),
                            },
                        )
                        results.append(result)
                    except Exception as e:
                        self.logger.error(f"处理AI情绪分析结果失败: {str(e)}")

            return results
        except Exception as e:
            self.logger.error(f"使用AI分析情绪数据失败: {str(e)}")
            return []

    def _map_ai_sentiment_type(self, ai_sentiment: str) -> SentimentType:
        """映射AI返回的情绪类型到标准类型"""
        sentiment_map = {
            "positive": SentimentType.POSITIVE,
            "negative": SentimentType.NEGATIVE,
            "neutral": SentimentType.NEUTRAL,
            "mixed": SentimentType.MIXED,
        }
        return sentiment_map.get(ai_sentiment.lower(), SentimentType.NEUTRAL)

    async def create_sentiment_time_series(
        self,
        analysis_results: List[SentimentAnalysisResult],
        asset: str,
        resolution: str = "1d",
    ) -> SentimentTimeSeries:
        """
        创建情绪时间序列

        Args:
            analysis_results: 情绪分析结果列表
            asset: 资产符号
            resolution: 时间分辨率 ("1h", "6h", "1d" 等)

        Returns:
            情绪时间序列
        """
        try:
            if not analysis_results:
                self.logger.warning(
                    f"无情绪分析结果用于创建{asset}的时间序列，返回空序列"
                )
                return SentimentTimeSeries(
                    asset=asset, source="combined", resolution=resolution, data=[]
                )

            self.logger.info(
                f"开始为{asset}创建情绪时间序列，分辨率为{resolution}，共{len(analysis_results)}条分析结果"
            )

            # 按来源分组
            results_by_source = {}
            for result in analysis_results:
                if result.source not in results_by_source:
                    results_by_source[result.source] = []
                results_by_source[result.source].append(result)

            self.logger.debug(f"按来源分组完成，共有{len(results_by_source)}个不同来源")

            # 设置时间间隔
            if resolution == "1h":
                interval = timedelta(hours=1)
            elif resolution == "6h":
                interval = timedelta(hours=6)
            elif resolution == "1d":
                interval = timedelta(days=1)
            else:
                # 默认为1天
                self.logger.warning(f"不支持的分辨率'{resolution}'，默认使用'1d'。")
                interval = timedelta(days=1)
                resolution = "1d"  # 确保resolution与interval匹配

            # 为每个来源创建时间序列
            source_series = {}

            for source, results in results_by_source.items():
                try:
                    self.logger.debug(f"处理来源'{source}'的{len(results)}条结果")
                    series_data = []

                    # 动态创建时间桶
                    time_buckets = {}  # 初始化空字典

                    # 将结果放入对应的时间桶
                    for result in results:
                        try:
                            # 计算标准化的桶开始时间
                            bucket_start_time = self._get_bucket_start_time(
                                result.timestamp, interval
                            )
                            # 使用标准化的开始时间生成唯一的键 (ISO格式推荐)
                            bucket_key = bucket_start_time.isoformat()

                            # 如果桶不存在，则创建
                            if bucket_key not in time_buckets:
                                time_buckets[bucket_key] = {
                                    "timestamp": bucket_start_time,  # 存储标准化的时间戳
                                    "scores": [],
                                    "volume": 0,
                                }

                            # 添加数据到桶
                            time_buckets[bucket_key]["scores"].append(
                                result.sentiment_score
                            )
                            time_buckets[bucket_key]["volume"] += 1
                        except Exception as e:
                            self.logger.error(f"处理单个结果时出错: {str(e)}")
                            continue

                    # 创建时间序列数据点 (使用 time_buckets.values())
                    for bucket_data in time_buckets.values():
                        if bucket_data["volume"] > 0:
                            try:
                                avg_score = sum(bucket_data["scores"]) / len(
                                    bucket_data["scores"]
                                )
                                series_data.append(
                                    SentimentTimeSeriesPoint(
                                        timestamp=bucket_data[
                                            "timestamp"
                                        ],  # 使用桶的标准时间戳
                                        sentiment_score=avg_score,
                                        volume=bucket_data["volume"],
                                        source=source,
                                    )
                                )
                            except Exception as e:
                                self.logger.error(f"创建时间序列点时出错: {str(e)}")
                                continue

                    # 按时间排序
                    series_data.sort(key=lambda x: x.timestamp)

                    # 保存该来源的时间序列
                    source_series[source] = SentimentTimeSeries(
                        asset=asset,
                        source=source,
                        resolution=resolution,
                        data=series_data,
                    )
                except Exception as e:
                    self.logger.error(f"处理来源'{source}'时出错: {str(e)}")
                    continue

            self.logger.info(f"已为{len(source_series)}个来源创建时间序列，开始合并")

            # 检查是否有可用的来源序列
            if not source_series:
                self.logger.warning(f"没有可用的来源序列用于合并，返回空的组合序列")
                return SentimentTimeSeries(
                    asset=asset, source="combined", resolution=resolution, data=[]
                )

            # 创建合并的时间序列
            try:
                # 查找所有唯一的时间戳
                all_timestamps = set()
                for source, series in source_series.items():
                    for point in series.data:
                        all_timestamps.add(point.timestamp)

                # 按时间排序
                sorted_timestamps = sorted(all_timestamps)
                self.logger.debug(
                    f"合并时间序列：共有{len(sorted_timestamps)}个唯一时间戳"
                )

                # 使用辅助方法合并时间序列数据点
                combined_data = self._merge_time_series_points(
                    source_series, sorted_timestamps
                )

                self.logger.info(f"合并时间序列完成，共有{len(combined_data)}个数据点")

                # 创建合并的时间序列
                combined_series = SentimentTimeSeries(
                    asset=asset,
                    source="combined",
                    resolution=resolution,
                    data=combined_data,
                )

                return combined_series
            except Exception as e:
                self.logger.error(f"合并时间序列时出错: {str(e)}")
                # 失败时，返回一个空的合并序列
                return SentimentTimeSeries(
                    asset=asset, source="combined", resolution=resolution, data=[]
                )

        except Exception as e:
            self.logger.error(f"创建时间序列过程中发生未处理的异常: {str(e)}")
            # 发生异常时返回空序列
            return SentimentTimeSeries(
                asset=asset, source="combined", resolution=resolution, data=[]
            )

    def calculate_sentiment_risk_metrics(
        self,
        time_series: SentimentTimeSeries,
        analysis_results: List[SentimentAnalysisResult] = None,
    ) -> SentimentRiskMetrics:
        """
        计算情绪风险指标

        Args:
            time_series: 情绪时间序列
            analysis_results: 情绪分析结果列表 (可选)

        Returns:
            情绪风险指标
        """
        # 默认值
        metrics = SentimentRiskMetrics(
            average_sentiment=0.0,
            sentiment_volatility=0.0,
            sentiment_momentum=0.0,
            sentiment_trend=0.0,
            divergence=0.0,
            source_diversity=0.0,
            topic_concentration=0.0,
            abnormal_activity=0.0,
            regulatory_focus=0.0,
        )

        # 检查是否有足够的数据
        if not time_series.data or len(time_series.data) < 3:
            return metrics

        # 提取情绪分数和时间戳
        scores = [point.sentiment_score for point in time_series.data]
        timestamps = [point.timestamp for point in time_series.data]
        volumes = [point.volume for point in time_series.data]

        # 1. 计算平均情绪
        metrics.average_sentiment = sum(scores) / len(scores)

        # 2. 计算情绪波动性 (标准差)
        if len(scores) >= 2:
            metrics.sentiment_volatility = statistics.stdev(scores)

        # 3. 计算情绪动量 (短期趋势)
        if len(scores) >= 5:
            recent_scores = scores[-5:]
            oldest_scores = scores[-10:-5] if len(scores) >= 10 else scores[:5]

            recent_avg = sum(recent_scores) / len(recent_scores)
            oldest_avg = sum(oldest_scores) / len(oldest_scores)

            metrics.sentiment_momentum = recent_avg - oldest_avg

        # 4. 计算长期情绪趋势 (使用简单线性回归)
        if len(scores) >= 7:
            # 将时间戳转换为数值 (距离第一个点的天数)
            first_ts = timestamps[0]
            days = [(ts - first_ts).total_seconds() / 86400 for ts in timestamps]

            # 计算趋势
            slope, _, _, _, _ = stats.linregress(days, scores)
            metrics.sentiment_trend = slope * 7  # 缩放为每周变化率

        # 5. 计算观点分歧度 (基于分数分布)
        if len(scores) >= 5:
            positive_count = sum(1 for s in scores if s > 0.2)
            negative_count = sum(1 for s in scores if s < -0.2)
            neutral_count = len(scores) - positive_count - negative_count

            # 计算分布熵
            total = len(scores)
            pos_ratio = positive_count / total if total > 0 else 0
            neg_ratio = negative_count / total if total > 0 else 0
            neu_ratio = neutral_count / total if total > 0 else 0

            # 使用熵作为分歧度指标，均匀分布的熵最高，表示分歧最大
            entropy = 0
            for ratio in [pos_ratio, neg_ratio, neu_ratio]:
                if ratio > 0:
                    entropy -= ratio * np.log2(ratio)

            # 归一化到0-1范围
            metrics.divergence = entropy / np.log2(3)

        # 6. 分析来源多样性
        if analysis_results:
            sources = [result.source for result in analysis_results]
            unique_sources = set(sources)

            # 使用相对熵作为多样性指标
            if sources:
                source_counts = Counter(sources)
                source_ratios = [
                    count / len(sources) for count in source_counts.values()
                ]

                source_entropy = 0
                for ratio in source_ratios:
                    source_entropy -= ratio * np.log2(ratio)

                # 归一化到0-1范围
                max_entropy = (
                    np.log2(len(unique_sources)) if len(unique_sources) > 0 else 1
                )
                metrics.source_diversity = (
                    source_entropy / max_entropy if max_entropy > 0 else 0
                )

        # 7. 话题集中度
        if analysis_results:
            all_topics = []
            for result in analysis_results:
                all_topics.extend(result.topics)

            if all_topics:
                topic_counts = Counter(all_topics)
                most_common_count = (
                    topic_counts.most_common(1)[0][1] if topic_counts else 0
                )

                # 集中度 = 最常见话题的比例
                metrics.topic_concentration = (
                    most_common_count / len(all_topics) if len(all_topics) > 0 else 0
                )

        # 8. 异常活跃度 (基于体量变化)
        if len(volumes) >= 5:
            avg_volume = sum(volumes) / len(volumes)
            recent_volume = sum(volumes[-3:]) / 3  # 最近3个时间点的平均体量

            # 计算Z分数作为异常程度
            if avg_volume > 0 and recent_volume > 0:
                metrics.abnormal_activity = (recent_volume - avg_volume) / avg_volume

        # 9. 监管关注度
        if analysis_results:
            regulatory_keywords = [
                "regulation",
                "regulatory",
                "sec",
                "cftc",
                "law",
                "legal",
                "compliance",
                "ban",
                "restrict",
                "government",
                "policy",
                "central bank",
                "监管",
            ]

            reg_mentions = 0
            for result in analysis_results:
                content = result.metadata.get("original_content", "").lower()
                if any(keyword in content for keyword in regulatory_keywords):
                    reg_mentions += 1

            metrics.regulatory_focus = (
                reg_mentions / len(analysis_results) if analysis_results else 0
            )

        return metrics

    async def calculate_asset_correlation(
        self, asset1: str, asset2: str, days: int = 30
    ) -> float:
        """
        计算两个资产情绪之间的相关性

        Args:
            asset1: 第一个资产
            asset2: 第二个资产
            days: 数据天数

        Returns:
            相关系数 (-1.0 到 1.0)
        """
        # 实现资产情绪相关性分析
        # 为简化，这里仅返回一个示例值
        return 0.5

    async def get_asset_sentiment_summary(
        self, asset: str, days: int = 7
    ) -> Optional[AssetSentimentSummary]:
        """
        获取资产的情绪分析摘要

        Args:
            asset: 资产符号 (例如 "BTC", "ETH")
            days: 分析的天数，默认7天

        Returns:
            资产情绪摘要，如果无法获取数据则返回None
        """
        self.logger.info(f"获取{asset}的情绪分析摘要，时间范围: {days}天")

        # 检查缓存
        cache_key = f"summary_{asset}_{days}"
        if cache_key in self.cache:
            self.logger.info(f"使用缓存的情绪摘要: {cache_key}")
            return self.cache[cache_key]

        try:
            # 确保数据服务可用
            if not hasattr(self, "data_service") or not self.data_service:
                self.logger.error("情绪数据服务不可用")
                return None

            # 获取原始情绪数据
            raw_sentiment_data = await self.data_service.get_asset_sentiment_data(
                asset=asset, days=days
            )

            if not raw_sentiment_data:
                self.logger.warning(f"未找到{asset}的情绪数据")
                return None

            # 将RawSentimentData转换为RawSentimentItem
            raw_items = []
            for source, items in raw_sentiment_data.items():
                for i, item in enumerate(items):
                    raw_items.append(
                        RawSentimentItem(
                            id=f"{source}_{i}_{item.timestamp.isoformat()}",
                            asset=asset,
                            source=source,
                            timestamp=item.timestamp,
                            content=item.content,
                            author=item.author,
                            url=item.url,
                            engagement=item.engagement,
                            metadata=item.metadata,
                        )
                    )

            # 如果没有足够的数据点
            if len(raw_items) < self.config["min_data_points"]:
                self.logger.warning(
                    f"{asset}的情绪数据点数量不足: {len(raw_items)} < {self.config['min_data_points']}"
                )
                # 仍然继续处理，但在日志中警告

            # 分析情绪数据
            analysis_results = await self.analyze_raw_sentiment_data(raw_items)

            if not analysis_results:
                self.logger.warning(f"未能分析{asset}的情绪数据")
                return None

            # 生成情绪摘要
            summary = await self.generate_asset_sentiment_summary(
                asset=asset, analysis_results=analysis_results
            )

            # 缓存结果
            self.cache[cache_key] = summary

            return summary

        except Exception as e:
            self.logger.error(f"获取{asset}的情绪分析摘要时出错: {str(e)}")
            return None

    async def generate_asset_sentiment_summary(
        self,
        asset: str,
        analysis_results: List[SentimentAnalysisResult],
        time_series: SentimentTimeSeries = None,
        risk_metrics: SentimentRiskMetrics = None,
    ) -> AssetSentimentSummary:
        """
        生成资产情绪摘要

        Args:
            asset: 资产符号
            analysis_results: 情绪分析结果列表
            time_series: 情绪时间序列 (可选)
            risk_metrics: 情绪风险指标 (可选)

        Returns:
            资产情绪摘要
        """
        if not analysis_results:
            self.logger.warning(
                f"generate_asset_sentiment_summary: No analysis results provided for asset {asset}. Returning default summary."
            )
            return AssetSentimentSummary(
                asset=asset,
                overall_sentiment=0.0,
                sentiment_change_24h=0.0,
                sentiment_change_7d=0.0,
                social_sentiment=0.0,
                news_sentiment=0.0,
            )

        self.logger.info(
            f"generate_asset_sentiment_summary: Received {len(analysis_results)} analysis results for asset {asset}."
        )

        # 创建时间序列，如果未提供
        if not time_series:
            time_series = await self.create_sentiment_time_series(
                analysis_results=analysis_results, asset=asset, resolution="1d"
            )
        if time_series and time_series.data:
            self.logger.info(
                f"generate_asset_sentiment_summary: Generated time series with {len(time_series.data)} data points for asset {asset}."
            )
        else:
            self.logger.warning(
                f"generate_asset_sentiment_summary: Generated time series is empty or has no data for asset {asset}."
            )

        # 计算风险指标，如果未提供
        if not risk_metrics:
            risk_metrics = self.calculate_sentiment_risk_metrics(
                time_series=time_series, analysis_results=analysis_results
            )
        if risk_metrics:
            self.logger.info(
                f"generate_asset_sentiment_summary: Calculated risk_metrics.average_sentiment: {risk_metrics.average_sentiment} for asset {asset}."
            )
        else:
            self.logger.warning(
                f"generate_asset_sentiment_summary: Failed to calculate risk metrics for asset {asset}."
            )

        # 初始化风险因子列表
        risk_factors = []

        # 1. 情绪波动风险因子
        if risk_metrics.sentiment_volatility > 0:
            volatility_risk_score = min(100, risk_metrics.sentiment_volatility * 100)
            volatility_trend = (
                "上升"
                if risk_metrics.sentiment_momentum > 0.1
                else "下降" if risk_metrics.sentiment_momentum < -0.1 else "稳定"
            )

            volatility_factor = SentimentRiskFactor(
                name="情绪波动风险",
                description=f"{asset}的市场情绪波动性{volatility_trend}，表明市场观点不稳定",
                asset=asset,
                score=volatility_risk_score,
                weight=0.3,
                trend=volatility_trend,
                metrics=risk_metrics,
                data_points=[
                    {"name": "情绪波动性", "value": risk_metrics.sentiment_volatility}
                ],
            )
            risk_factors.append(volatility_factor)

        # 2. 情绪分歧风险因子
        if risk_metrics.divergence > 0:
            divergence_risk_score = min(100, risk_metrics.divergence * 100)
            divergence_trend = (
                "上升"
                if risk_metrics.divergence > 0.7
                else "下降" if risk_metrics.divergence < 0.3 else "稳定"
            )

            divergence_factor = SentimentRiskFactor(
                name="观点分歧风险",
                description=f"{asset}的市场观点分歧程度{divergence_trend}，表明市场存在不确定性",
                asset=asset,
                score=divergence_risk_score,
                weight=0.25,
                trend=divergence_trend,
                metrics=risk_metrics,
                data_points=[{"name": "观点分歧度", "value": risk_metrics.divergence}],
            )
            risk_factors.append(divergence_factor)

        # 3. 监管关注风险因子
        if risk_metrics.regulatory_focus > 0:
            reg_risk_score = min(
                100, risk_metrics.regulatory_focus * 150
            )  # 放大监管风险影响
            reg_trend = "上升" if reg_risk_score > 50 else "稳定"

            reg_factor = SentimentRiskFactor(
                name="监管关注风险",
                description=f"{asset}的监管讨论占比较高，可能面临监管变化",
                asset=asset,
                score=reg_risk_score,
                weight=0.3,
                trend=reg_trend,
                metrics=risk_metrics,
                data_points=[
                    {"name": "监管讨论比例", "value": risk_metrics.regulatory_focus}
                ],
            )
            risk_factors.append(reg_factor)

        # 计算社交媒体和新闻的情绪
        social_scores = []
        news_scores = []

        for result in analysis_results:
            if result.source in ["twitter"]:
                social_scores.append(result.sentiment_score)
            elif result.source in ["crypto_news"]:
                news_scores.append(result.sentiment_score)

        social_sentiment = (
            sum(social_scores) / len(social_scores) if social_scores else 0
        )
        news_sentiment = sum(news_scores) / len(news_scores) if news_scores else 0

        # 计算24小时和7天的情绪变化
        sentiment_change_24h = 0.0
        sentiment_change_7d = 0.0

        if time_series and time_series.data:
            series_data = time_series.data
            # 计算24小时变化
            if len(series_data) >= 2:
                now_sentiment = series_data[-1].sentiment_score
                day_ago_sentiment = series_data[-2].sentiment_score
                sentiment_change_24h = now_sentiment - day_ago_sentiment
            else:
                self.logger.info(
                    f"generate_asset_sentiment_summary: Insufficient data for 24h change ({len(series_data)} points) for asset {asset}."
                )

            # 计算7天变化
            if len(series_data) >= 7:
                now_sentiment = series_data[-1].sentiment_score
                week_ago_idx = max(0, len(series_data) - 7)
                week_ago_sentiment = series_data[week_ago_idx].sentiment_score
                sentiment_change_7d = now_sentiment - week_ago_sentiment
            else:
                self.logger.info(
                    f"generate_asset_sentiment_summary: Insufficient data for 7d change ({len(series_data)} points) for asset {asset}."
                )

        # Log final calculated change values before creating summary object
        self.logger.info(
            f"generate_asset_sentiment_summary: Final calculated sentiment_change_24h: {sentiment_change_24h} for asset {asset}."
        )
        self.logger.info(
            f"generate_asset_sentiment_summary: Final calculated sentiment_change_7d: {sentiment_change_7d} for asset {asset}."
        )

        # 计算情绪类型比例
        total_count = len(analysis_results)
        bullish_count = sum(
            1 for r in analysis_results if r.sentiment_type == SentimentType.POSITIVE
        )
        bearish_count = sum(
            1 for r in analysis_results if r.sentiment_type == SentimentType.NEGATIVE
        )
        neutral_count = total_count - bullish_count - bearish_count

        bullish_percentage = (
            (bullish_count / total_count) * 100 if total_count > 0 else 0
        )
        bearish_percentage = (
            (bearish_count / total_count) * 100 if total_count > 0 else 0
        )
        neutral_percentage = (
            (neutral_count / total_count) * 100 if total_count > 0 else 0
        )

        # 提取热门话题
        all_topics = []
        for result in analysis_results:
            all_topics.extend(result.topics)

        top_topics = []
        if all_topics:
            topic_counts = Counter(all_topics)
            for topic, count in topic_counts.most_common(5):
                top_topics.append(
                    {
                        "topic": topic,
                        "count": count,
                        "percentage": (count / len(all_topics)) * 100,
                    }
                )

        # 创建时间序列字典
        time_series_dict = {}
        if time_series:
            time_series_dict["combined"] = time_series

        # 创建资产情绪摘要
        summary = AssetSentimentSummary(
            asset=asset,
            overall_sentiment=risk_metrics.average_sentiment if risk_metrics else 0.0,
            sentiment_change_24h=sentiment_change_24h,
            sentiment_change_7d=sentiment_change_7d,
            social_sentiment=social_sentiment,
            news_sentiment=news_sentiment,
            risk_factors=risk_factors,
            total_mentions=total_count,
            bullish_percentage=bullish_percentage,
            bearish_percentage=bearish_percentage,
            neutral_percentage=neutral_percentage,
            top_topics=top_topics,
            time_series=time_series_dict,
        )

        # 生成建议
        summary.recommendations = self._generate_sentiment_recommendations(summary)

        return summary

    def _generate_sentiment_recommendations(
        self, summary: AssetSentimentSummary
    ) -> List[str]:
        """生成基于情绪分析的建议"""
        recommendations = []

        # 基于整体情绪的建议
        if summary.overall_sentiment < -0.5:
            recommendations.append(
                f"{summary.asset}的市场情绪极度负面，建议谨慎操作，观察情绪反转信号"
            )
        elif summary.overall_sentiment < -0.2:
            recommendations.append(f"{summary.asset}的市场情绪偏负面，可能存在下行压力")
        elif summary.overall_sentiment > 0.5:
            recommendations.append(
                f"{summary.asset}的市场情绪极度正面，需警惕可能的过度乐观"
            )
        elif summary.overall_sentiment > 0.2:
            recommendations.append(f"{summary.asset}的市场情绪偏正面，但仍需关注基本面")

        # 基于情绪变化的建议
        if summary.sentiment_change_24h > 0.3:
            recommendations.append(
                f"{summary.asset}的24小时情绪显著上升，可能表明短期看涨动能"
            )
        elif summary.sentiment_change_24h < -0.3:
            recommendations.append(
                f"{summary.asset}的24小时情绪显著下降，可能存在短期风险"
            )

        if summary.sentiment_change_7d > 0.5:
            recommendations.append(
                f"{summary.asset}的周度情绪趋势明显上升，可能正处于情绪修复阶段"
            )
        elif summary.sentiment_change_7d < -0.5:
            recommendations.append(
                f"{summary.asset}的周度情绪趋势明显下降，建议关注底部信号"
            )

        # 基于社交媒体与新闻情绪差异的建议
        sentiment_gap = summary.social_sentiment - summary.news_sentiment
        if abs(sentiment_gap) > 0.4:
            if sentiment_gap > 0:
                recommendations.append(
                    f"{summary.asset}的社交媒体情绪明显高于新闻情绪，可能存在过度炒作风险"
                )
            else:
                recommendations.append(
                    f"{summary.asset}的新闻情绪明显高于社交媒体情绪，关注社交情绪是否将跟随改善"
                )

        # 基于风险因子的建议
        for factor in summary.risk_factors:
            if factor.score > 70:
                if "波动" in factor.name:
                    recommendations.append(
                        f"情绪波动风险高，建议使用分散投资或对冲策略降低风险"
                    )
                elif "分歧" in factor.name:
                    recommendations.append(
                        f"市场观点存在较大分歧，建议深入研究基本面再做决策"
                    )
                elif "监管" in factor.name:
                    recommendations.append(
                        f"监管关注度较高，建议密切追踪相关监管新闻和政策变化"
                    )

        # 确保至少有一条建议
        if not recommendations:
            recommendations.append(
                f"{summary.asset}的市场情绪中性，建议结合技术分析和基本面做出决策"
            )

        return recommendations

    async def generate_portfolio_recommendations(
        self,
        asset_sentiments: Dict[str, Any],
        weighted_sentiment: float,
        weighted_change: float,
        source: str = "portfolio",
    ) -> List[str]:
        """
        生成投资组合级别的情绪分析建议

        Args:
            asset_sentiments: 各资产的情绪数据
            weighted_sentiment: 加权平均情绪分数
            weighted_change: 加权平均情绪变化
            source: 数据来源，默认为'portfolio'

        Returns:
            投资组合建议列表
        """
        self.logger.info("生成投资组合情绪分析建议")

        recommendations = []

        # 基于整体情绪分数生成建议
        if weighted_sentiment < -0.5:
            recommendations.append(
                "投资组合整体情绪极度负面，建议减少风险敞口并关注市场变化"
            )
            recommendations.append("考虑将部分资产转移到稳定币或低波动性资产中")
        elif weighted_sentiment < -0.2:
            recommendations.append(
                "投资组合整体情绪负面，建议保持谨慎并密切监控市场动向"
            )
            recommendations.append("可考虑降低高波动性资产的敞口")
        elif weighted_sentiment > 0.5:
            recommendations.append("投资组合整体情绪极度乐观，注意市场可能存在过热现象")
            recommendations.append("警惕短期内可能的调整，考虑适度获利了结")
        elif weighted_sentiment > 0.2:
            recommendations.append("投资组合整体情绪乐观，可适度增加配置但保持风险意识")
        else:
            recommendations.append(
                "投资组合整体情绪中性，维持当前配置并持续观察市场变化"
            )

        # 基于情绪变化生成建议
        if abs(weighted_change) > 0.3:
            if weighted_change > 0:
                recommendations.append("市场情绪快速转向积极，但仍需关注变化持续性")
            else:
                recommendations.append("市场情绪快速恶化，建议增加防御性配置")

        # 针对特定资产的建议
        negative_assets = []
        positive_assets = []

        for asset, data in asset_sentiments.items():
            sentiment = data.get("overall_sentiment", 0)
            if sentiment < -0.3 and data.get("weight", 0) > 0.1:
                negative_assets.append(asset)
            elif sentiment > 0.3 and data.get("weight", 0) > 0.1:
                positive_assets.append(asset)

        if negative_assets:
            assets_str = "、".join(negative_assets[:3])
            if len(negative_assets) > 3:
                assets_str += "等"
            recommendations.append(f"重点关注{assets_str}的负面情绪变化")

        if positive_assets:
            assets_str = "、".join(positive_assets[:3])
            if len(positive_assets) > 3:
                assets_str += "等"
            recommendations.append(f"{assets_str}的市场情绪较为积极")

        # 确保至少有一条建议
        if not recommendations:
            recommendations.append(
                "基于当前情绪数据无法提供明确建议，请结合其他风险指标综合评估"
            )

        return recommendations

    async def close(self):
        """关闭服务并释放资源"""
        self.logger.info("关闭情绪分析服务")

        # 释放情绪数据服务资源
        if (
            hasattr(self, "data_service")
            and self.data_service
            and hasattr(self.data_service, "close")
        ):
            await self.data_service.close()

        # 清空缓存
        if hasattr(self, "cache"):
            self.cache.clear()

        self.logger.info("情绪分析服务已关闭")

    def _merge_time_series_points(
        self, source_series: Dict[str, SentimentTimeSeries], timestamps: List[datetime]
    ) -> List[SentimentTimeSeriesPoint]:
        """
        合并多个来源的时间序列数据点

        Args:
            source_series: 按来源分组的时间序列字典
            timestamps: 排序后的唯一时间戳列表

        Returns:
            合并后的时间序列数据点列表
        """
        combined_data = []

        # 为每个时间戳计算合并的情绪分数
        for ts in timestamps:
            points_at_ts = []

            # 收集该时间戳的所有数据点
            for source, series in source_series.items():
                for point in series.data:
                    if point.timestamp == ts:
                        points_at_ts.append(point)

            if points_at_ts:
                # 计算加权平均分数
                total_weighted_score = 0
                total_volume = 0

                for point in points_at_ts:
                    # 获取来源权重
                    weight = self.config["source_weights"].get(
                        point.source, self.config["source_weights"]["default"]
                    )

                    total_weighted_score += (
                        point.sentiment_score * point.volume * weight
                    )
                    total_volume += point.volume * weight

                avg_score = (
                    total_weighted_score / total_volume if total_volume > 0 else 0
                )
                total_vol = sum(p.volume for p in points_at_ts)

                combined_data.append(
                    SentimentTimeSeriesPoint(
                        timestamp=ts,
                        sentiment_score=avg_score,
                        volume=total_vol,
                        source="combined",
                        metadata={
                            "source_breakdown": {
                                p.source: p.volume for p in points_at_ts
                            }
                        },
                    )
                )

        return combined_data
