"""
情绪数据模型 - 定义与市场情绪分析相关的数据结构
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid


class SentimentSource(Enum):
    """情绪数据来源"""

    TWITTER = "twitter"
    NEWS = "news"
    GOOGLE_TRENDS = "google_trends"
    COMBINED = "combined"  # 组合数据源


class SentimentType(Enum):
    """情绪类型"""

    POSITIVE = "正面"
    NEGATIVE = "负面"
    NEUTRAL = "中性"
    MIXED = "混合"


@dataclass
class RawSentimentItem:
    """原始情绪数据项"""

    source: str  # 数据来源
    asset: str  # 资产符号
    content: str  # 原始内容
    timestamp: datetime  # 内容发布时间
    author: Optional[str] = None  # 作者
    url: Optional[str] = None  # 链接
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    engagement: Dict[str, Any] = field(default_factory=dict)  # 互动指标
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class SentimentAnalysisResult:
    """情绪分析结果"""

    raw_item_id: str  # 原始数据项ID
    asset: str  # 资产符号
    source: str  # 数据来源
    timestamp: datetime  # 分析时间
    sentiment_type: SentimentType  # 情绪类型
    sentiment_score: float  # 情绪评分 (-1.0 极负面到 1.0 极正面)
    confidence: float  # 置信度 (0.0 - 1.0)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topics: List[str] = field(default_factory=list)  # 识别的主题
    keywords: List[str] = field(default_factory=list)  # 关键词
    entities: List[Dict[str, Any]] = field(default_factory=list)  # 实体 (人物、组织等)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class SentimentTimeSeriesPoint:
    """情绪时间序列数据点"""

    timestamp: datetime  # 时间戳
    sentiment_score: float  # 情绪评分
    volume: int  # 数据量
    source: str  # 数据来源
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class SentimentTimeSeries:
    """情绪时间序列"""

    asset: str  # 资产符号
    source: str  # 数据来源
    resolution: str  # 时间分辨率 ("1h", "1d" 等)
    data: List[SentimentTimeSeriesPoint] = field(default_factory=list)  # 时间序列数据点
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class SentimentRiskMetrics:
    """情绪风险指标"""

    average_sentiment: float  # 平均情绪评分
    sentiment_volatility: float  # 情绪波动性
    sentiment_momentum: float  # 情绪动量 (短期趋势)
    sentiment_trend: float  # 情绪趋势 (中长期)
    divergence: float  # 观点分歧度 (意见不一致程度)
    source_diversity: float  # 来源多样性
    topic_concentration: float  # 话题集中度
    abnormal_activity: float  # 异常活跃度
    regulatory_focus: float  # 监管关注度
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class SentimentRiskFactor:
    """情绪风险因子"""

    name: str  # 风险因子名称
    description: str  # 风险描述
    asset: str  # 资产符号
    score: float  # 风险评分 (0-100, 越高风险越大)
    weight: float  # 权重
    trend: str  # 趋势 ("上升", "下降", "稳定")
    metrics: SentimentRiskMetrics  # 情绪风险指标
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    time_series: List[SentimentTimeSeriesPoint] = field(
        default_factory=list
    )  # 简化的时间序列
    topics: List[Dict[str, float]] = field(default_factory=list)  # 主要话题及其情绪影响
    data_points: List[Dict[str, Any]] = field(
        default_factory=list
    )  # 支持风险评分的数据点
    recommendations: List[str] = field(default_factory=list)  # 风险缓解建议
    monitoring_points: List[str] = field(default_factory=list)  # 监控点
    timestamp: datetime = field(default_factory=datetime.utcnow)  # 分析时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class AssetSentimentSummary:
    """资产情绪摘要"""

    asset: str  # 资产符号
    overall_sentiment: float  # 整体情绪得分 (-1.0 到 1.0)
    sentiment_change_24h: float  # 24小时情绪变化
    sentiment_change_7d: float  # 7天情绪变化
    social_sentiment: float  # 社交媒体情绪
    news_sentiment: float  # 新闻情绪
    risk_factors: List[SentimentRiskFactor] = field(
        default_factory=list
    )  # 情绪风险因子
    timestamp: datetime = field(default_factory=datetime.utcnow)  # 分析时间
    total_mentions: int = 0  # 总提及量
    bullish_percentage: float = 0.0  # 看涨观点百分比
    bearish_percentage: float = 0.0  # 看跌观点百分比
    neutral_percentage: float = 0.0  # 中性观点百分比
    top_topics: List[Dict[str, Any]] = field(default_factory=list)  # 热门话题
    key_influencers: List[Dict[str, Any]] = field(default_factory=list)  # 关键影响者
    price_correlation: float = 0.0  # 与价格的相关性
    time_series: Dict[str, SentimentTimeSeries] = field(
        default_factory=dict
    )  # 按来源分组的时间序列
    recommendations: List[str] = field(default_factory=list)  # 建议
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
