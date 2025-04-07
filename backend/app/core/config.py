import os
import yaml
from typing import Dict, Any, Optional, List
from pydantic import Field, BaseSettings


# 加载外部配置文件
def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """从YAML文件加载配置"""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        return {}
    except Exception as e:
        print(f"加载配置文件 {file_path} 时出错: {str(e)}")
        return {}


# 获取配置文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RISK_WEIGHTS_FILE = os.path.join(BASE_DIR, "config", "risk_weights.yaml")
DEMO_ACCOUNTS_FILE = os.path.join(BASE_DIR, "config", "demo_accounts.yaml")

# 加载配置
risk_weights_config = load_yaml_config(RISK_WEIGHTS_FILE)
demo_accounts_config = load_yaml_config(DEMO_ACCOUNTS_FILE)


class Settings(BaseSettings):
    """应用配置设置"""

    # 应用设置
    APP_NAME: str = "DeFi风险分析API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")

    # 演示模式设置 - 从环境变量读取，不再硬编码
    DEMO_MODE: bool = Field(default=False, env="DEMO_MODE")

    # 从外部配置文件加载演示账户
    DEMO_ACCOUNTS: List[Dict[str, str]] = Field(
        default_factory=lambda: demo_accounts_config.get("DEMO_ACCOUNTS", [])
    )

    # API设置
    API_PREFIX: str = "/api/v1"

    # 区块链设置
    WEB3_PROVIDER_URL: str = Field(..., env="WEB3_PROVIDER_URL")

    # AI设置
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_API_URL: str = Field(..., env="OPENAI_API_URL")

    AI_MODEL: str = Field(default="gpt-3.5-turbo", env="OPENAI_API_MODEL")

    # 代理设置
    PROXY_URL: str = Field(default="http://127.0.0.1:7890", env="PROXY_URL")

    # 从外部配置文件加载风险权重
    RISK_WEIGHTS: Dict[str, float] = Field(
        default_factory=lambda: risk_weights_config.get(
            "RISK_WEIGHTS",
            {
                "MARKET": 0.3,
                "SMART_CONTRACT": 0.2,
                "LIQUIDITY": 0.2,
                "PROTOCOL": 0.15,
                "CORRELATION": 0.1,
                "REGULATORY": 0.05,
            },
        )
    )

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
