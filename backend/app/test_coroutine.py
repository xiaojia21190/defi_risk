import inspect
import sys
import os

# 添加父级目录到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_predictor import AiPredictor


def check_coroutine():
    print("检查AiPredictor方法是否是协程函数:")

    # 获取AiPredictor中的所有方法
    methods = [
        "analyze_correlation_risk",
        "analyze_defi_protocol_risk",
        "analyze_market_trend",
        "analyze_concentration_risk",
        "analyze_generic",
    ]

    for method_name in methods:
        if hasattr(AiPredictor, method_name):
            method = getattr(AiPredictor, method_name)
            is_coroutine = inspect.iscoroutinefunction(method)
            print(f"- {method_name}: {'是' if is_coroutine else '否'}")
        else:
            print(f"- {method_name}: 方法不存在")


if __name__ == "__main__":
    check_coroutine()
