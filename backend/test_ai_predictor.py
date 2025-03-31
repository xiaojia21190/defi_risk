"""
测试 AiPredictor 类
"""

import asyncio
import logging
import json
from app.services.ai_predictor import AiPredictor

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_ai_predictor")


async def test_analyze_correlation_risk():
    try:
        logger.info("开始测试 analyze_correlation_risk 方法")

        # 初始化 AiPredictor
        ai = AiPredictor()
        logger.info("成功初始化 AiPredictor")

        # 准备测试数据
        test_data = {
            "correlation_type": "asset_correlation",
            "assets": ["BTC", "ETH", "USDT", "SOL"],
        }

        # 调用方法
        logger.info("开始调用 analyze_correlation_risk 方法")
        result = await ai.analyze_correlation_risk(test_data)

        # 输出结果
        logger.info("相关性风险分析结果:")
        logger.info(f"风险分数: {result.get('score', 'N/A')}")
        logger.info(f"描述: {result.get('description', 'N/A')}")
        logger.info(f"趋势: {result.get('trend', 'N/A')}")

        # 输出建议和监控点
        recommendations = result.get("recommendations", [])
        logger.info(f"建议数量: {len(recommendations)}")
        if recommendations:
            logger.info("建议:")
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"  {i}. {rec}")

        monitoring_points = result.get("monitoring_points", [])
        logger.info(f"监控点数量: {len(monitoring_points)}")
        if monitoring_points:
            logger.info("监控点:")
            for i, point in enumerate(monitoring_points, 1):
                logger.info(f"  {i}. {point}")

        logger.info("测试成功完成")
        return result
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}", exc_info=True)
        return {"error": str(e)}


if __name__ == "__main__":
    result = asyncio.run(test_analyze_correlation_risk())
    print("\n完整结果:")
    try:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except:
        print(str(result))
