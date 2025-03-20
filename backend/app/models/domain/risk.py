from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid
from pydantic import BaseModel, Field


class RiskLevel(Enum):
    """风险等级枚举"""

    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    EXTREME = "极高风险"


class RiskType(Enum):
    """风险类型枚举"""

    MARKET = "市场风险"
    SMART_CONTRACT = "智能合约风险"
    LIQUIDITY = "流动性风险"
    PROTOCOL = "协议风险"
    CORRELATION = "相关性风险"
    REGULATORY = "监管风险"


@dataclass
class RiskFactor:
    """风险因子"""

    id: str  # 风险因子ID，格式为"风险类型.因子名称"
    name: str  # 风险因子名称
    score: float  # 风险评分(0-100)
    weight: float  # 权重
    description: str  # 描述
    trend: str  # 趋势："上升", "下降", "稳定"
    data_points: List[Dict[str, Any]] = field(
        default_factory=list
    )  # 支持该评分的数据点
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class RiskAssessment:
    """风险评估结果"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_score: float = 0.0  # 总体风险评分(0-100)
    risk_level: RiskLevel = RiskLevel.LOW
    risk_factors: Dict[str, RiskFactor] = field(default_factory=dict)  # 风险因子字典
    warnings: List[str] = field(default_factory=list)  # 警告列表
    recommendations: List[str] = field(default_factory=list)  # 建议列表
    mitigation_strategies: List[str] = field(default_factory=list)  # 风险缓解策略
    monitoring_points: List[str] = field(default_factory=list)  # 需要监控的关键指标
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)  # 详细分析
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class Position:
    """投资头寸"""

    protocol: str  # 协议名称
    asset: str  # 资产名称
    amount: float  # 金额
    apy: Optional[float] = None  # 年化收益率
    invest_type: Optional[int] = None  # 投资类型ID
    invest_type_name: Optional[str] = None  # 投资类型名称


@dataclass
class Portfolio:
    """投资组合"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    wallet_address: Optional[str] = None  # 钱包地址
    positions: List[Position] = field(default_factory=list)  # 头寸列表
    total_value: float = 0.0  # 总价值
    timestamp: datetime = field(default_factory=datetime.utcnow)  # 时间戳
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


class RiskMetrics(BaseModel):
    """风险指标数据模型"""

    price_volatility: float = Field(default=0.0, description="价格波动率(%)")
    market_cap: float = Field(default=0.0, description="市值(USD)")
    market_cap_rank: int = Field(default=0, description="市值排名")
    volume_to_mcap_ratio: float = Field(default=0.0, description="交易量/市值比率")
    tvl_stability: Optional[float] = Field(default=None, description="TVL稳定性(%)")
    audit_score: Optional[int] = Field(default=None, description="审计评分")


class RiskAnalysis(BaseModel):
    """风险分析结果详情"""

    market_cap_analysis: Optional[str] = None
    liquidity_analysis: Optional[str] = None
    volatility_analysis: Optional[str] = None
    trend_analysis: Optional[str] = None
    tvl_factor: Optional[str] = None
    stability_factor: Optional[str] = None
    audit_factor: Optional[str] = None
    chain_factor: Optional[str] = None


class RiskAnalysisResult(BaseModel):
    """统一的风险分析结果模型"""

    asset_id: str = Field(..., description="资产或协议标识符")
    risk_score: float = Field(..., description="风险评分(0-100)")
    risk_level: str = Field(..., description="风险等级(极低/低/中/高/极高)")
    metrics: RiskMetrics = Field(..., description="风险指标数据")
    analysis: RiskAnalysis = Field(..., description="风险分析详情")
    recommendations: List[str] = Field(default_factory=list, description="风险建议")
    confidence: Optional[float] = Field(default=None, description="AI分析可信度")
    timestamp: datetime = Field(default_factory=datetime.now, description="分析时间戳")
    raw_data: Optional[Dict] = Field(default=None, description="原始数据")
    error: Optional[str] = Field(default=None, description="错误信息")
