from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid


@dataclass
class AiPrediction:
    """AI预测结果"""

    target: str  # 预测目标
    timeframe: str  # 时间范围
    value: float  # 预测值
    probability: float  # 概率
    range: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))  # 预测范围


@dataclass
class AiInsight:
    """AI洞察"""

    content: str  # 洞察内容
    confidence: float  # 置信度
    category: str  # 类别
    tags: List[str] = field(default_factory=list)  # 标签


@dataclass
class AiRecommendation:
    """AI建议"""

    content: str  # 建议内容
    priority: int  # 优先级
    confidence: float  # 置信度
    impact: str  # 影响
    tags: List[str] = field(default_factory=list)  # 标签


@dataclass
class AiAnalysis:
    """AI分析结果"""

    analysis_type: str  # 分析类型
    confidence: float  # 总体置信度
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    predictions: List[AiPrediction] = field(default_factory=list)  # 预测列表
    insights: List[str] = field(default_factory=list)  # 洞察列表
    recommendations: List[str] = field(default_factory=list)  # 建议列表
    monitoring_points: List[str] = field(default_factory=list)  # 监控点列表
    supporting_data: Dict[str, Any] = field(default_factory=dict)  # 支持数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class AiRequest:
    """AI分析请求"""

    analysis_type: str  # 分析类型
    context: Dict[str, Any]  # 上下文数据
    parameters: Dict[str, Any] = field(default_factory=dict)  # 参数
