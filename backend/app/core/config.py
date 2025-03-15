import os
from typing import Dict, Any, Optional
from pydantic import Field


class Settings:
    """应用配置设置"""

    # 应用设置
    APP_NAME: str = "DeFi风险分析API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG")

    # API设置
    API_PREFIX: str = "/api/v1"

    # 区块链设置
    WEB3_PROVIDER_URL: str = os.getenv("WEB3_PROVIDER_URL")

    # AI设置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_API_URL: str = os.getenv("OPENAI_API_URL")

    AI_MODEL: str = Field(default="gpt-4", env="AI_MODEL")

    # 代理设置
    PROXY_URL: Optional[str] = Field(default="http://127.0.0.1:7890", env="PROXY_URL")

    # 风险权重配置
    RISK_WEIGHTS: Dict[str, float] = {
        "MARKET": 0.3,
        "SMART_CONTRACT": 0.2,
        "LIQUIDITY": 0.2,
        "PROTOCOL": 0.15,
        "CORRELATION": 0.1,
        "REGULATORY": 0.05,
    }

    # 缓存设置
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")  # 默认5分钟

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局设置实例
settings = Settings()


def get_settings() -> Settings:
    """获取应用设置"""
    return settings
