#!/usr/bin/env python
"""
DeFi风险分析API启动脚本
"""
import os
import sys
import argparse
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="DeFi风险分析API服务")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务端口")
    parser.add_argument("--reload", action="store_true", help="启用热重载（开发模式）")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 设置环境变量
    if args.debug:
        os.environ["DEBUG"] = "True"

    # 打印启动信息
    print(f"启动 DeFi风险分析API")
    print(f"API文档: http://{args.host}:{args.port}/docs")
    print(f"调试模式: {'启用' if args.debug else '禁用'}")

    # 启动服务
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
