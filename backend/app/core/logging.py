import logging
import sys
from typing import List
import json
from datetime import datetime

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "extra"):
            log_record.update(record.extra)

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # 设置ensure_ascii=False，确保中文不被转义为Unicode序列
        return json.dumps(log_record, ensure_ascii=False)


def setup_logging():
    """设置日志记录"""
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)

    # 设置格式化器
    if settings.DEBUG:
        # 开发环境使用可读格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        # 生产环境使用JSON格式
        formatter = JsonFormatter()

    console_handler.setFormatter(formatter)

    # 添加处理器到根日志记录器
    root_logger.addHandler(console_handler)

    # 设置特定模块的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # 设置应用日志记录器
    app_logger = logging.getLogger("defi_risk")
    app_logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)

    return root_logger
