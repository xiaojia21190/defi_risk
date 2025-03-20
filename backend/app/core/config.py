import os
from typing import Dict, Any, Optional, List
from pydantic import Field


class Settings:
    """应用配置设置"""

    # 应用设置
    APP_NAME: str = "DeFi风险分析API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # 演示模式设置
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "True").lower() == "true"
    DEMO_ACCOUNTS: List[Dict[str, str]] = [
        {
            "address": "0xdemo1234567890abcdef1234567890abcdef123456",
            "name": "演示账户1",
            "type": "demo",
            "description": "包含多种DeFi头寸的演示账户",
            "risk_level": "medium",
        },
        {
            "address": "0xdemo2234567890abcdef1234567890abcdef123456",
            "name": "演示账户2",
            "type": "demo",
            "description": "高风险DeFi投资组合演示账户",
            "risk_level": "high",
        },
        {
            "address": "0xdemo3234567890abcdef1234567890abcdef123456",
            "name": "低风险投资账户",
            "type": "demo",
            "description": "主要持有稳定币和蓝筹资产的保守型账户",
            "risk_level": "low",
        },
        {
            "address": "0xdemo5234567890abcdef1234567890abcdef123456",
            "name": "LP流动性提供者",
            "type": "demo",
            "description": "专注于Uniswap和Curve上提供流动性的账户",
            "risk_level": "medium",
        },
    ]

    # API设置
    API_PREFIX: str = "/api/v1"

    # 区块链设置
    WEB3_PROVIDER_URL: str = os.getenv("WEB3_PROVIDER_URL")

    # AI设置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_API_URL: str = os.getenv("OPENAI_API_URL")

    AI_MODEL: str = os.getenv("OPENAI_API_MODEL")

    # 代理设置
    PROXY_URL = "http://127.0.0.1:7890"

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
