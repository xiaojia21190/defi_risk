"""
通用工具函数模块 - 提供各种通用功能函数
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


def create_standard_response(
    data: Dict[str, Any], wallet_address: Optional[str] = None, is_demo: bool = False
) -> Dict[str, Any]:
    """
    创建标准的API响应格式

    Args:
        data: 响应数据
        wallet_address: 可选的钱包地址
        is_demo: 是否为演示数据

    Returns:
        包含标准字段的响应字典
    """
    # 复制原始数据，避免修改原始对象
    response = data.copy()

    # 添加钱包地址（如果提供）
    if wallet_address and "wallet_address" not in response:
        response["wallet_address"] = wallet_address

    # 添加时间戳
    if "timestamp" not in response:
        response["timestamp"] = datetime.now().isoformat()

    # 添加演示数据标记
    if "is_demo_data" not in response:
        response["is_demo_data"] = is_demo

    return response


def safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """
    安全获取对象属性或字典值

    Args:
        obj: 目标对象或字典
        attr: 属性名或键名
        default: 如果属性/键不存在时返回的默认值

    Returns:
        属性/键值或默认值
    """
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(attr, default)

    return getattr(obj, attr, default)


def ensure_list(value: Any) -> List:
    """
    确保返回列表类型

    Args:
        value: 输入值，可以是任何类型

    Returns:
        列表形式的值:
        - 如果输入是None，返回空列表
        - 如果输入是列表，原样返回
        - 如果输入是其他类型，将其包装在列表中
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
