"""
测试协议分析功能的脚本
"""

from app.services.ai_predictor import AiPredictor
from app.services.ai_service import AiService
import asyncio


async def test_protocol_analysis():
    print("开始测试协议分析功能...")

    # 测试直接调用AiPredictor方法
    ai = AiPredictor()
    print("成功创建AiPredictor实例")

    # 测试复杂性分析
    complexity_result = ai._analyze_protocol_complexity(
        protocol_name="Test Protocol",
        protocol_metadata={
            "category": "Lending",
            "openSource": True,
            "github": ["repo1", "repo2"],
        },
        chain_distribution={"Ethereum": 1000000, "BSC": 500000},
        risk_score=50,
        risk_metrics={},
        risk_level="中",
    )
    print(
        f"复杂性分析结果: 类型={complexity_result.get('analysis_type')}, 风险评分={complexity_result.get('risk_score')}"
    )

    # 测试通过analyze_defi_protocol_risk调用复杂性分析
    protocol_data = {
        "protocol_name": "Test Protocol",
        "analysis_focus": "complexity",
        "protocol_metadata": {
            "category": "Lending",
            "openSource": True,
            "github": ["repo1", "repo2"],
        },
        "chain_distribution": {"Ethereum": 1000000, "BSC": 500000},
    }
    full_result = ai.analyze_defi_protocol_risk(protocol_data)
    print(
        f"通过主方法调用复杂性分析结果: 类型={full_result.get('analysis_type')}, 风险评分={full_result.get('risk_score')}"
    )

    # 测试AiService的analyze_with_predictor方法
    service = AiService()
    print("成功创建AiService实例")

    service_result = await service.analyze_with_predictor(
        analysis_type="protocol_complexity",
        data=protocol_data,
    )
    print(
        f"通过AiService分析结果: 类型={service_result.get('analysis_type')}, 风险评分={service_result.get('risk_score')}"
    )

    print("协议分析功能测试完成")


if __name__ == "__main__":
    asyncio.run(test_protocol_analysis())
