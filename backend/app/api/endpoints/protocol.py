from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.services.demo_data import DemoDataService, get_demo_data_service
from app.core.init_app import get_blockchain_service, get_ai_service
from app.core.config import settings
import logging


router = APIRouter()
logger = logging.getLogger("defi_risk.api.protocol")


@router.get("/{protocol_name}")
async def get_protocol_info(
    protocol_name: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    获取协议信息

    - **protocol_name**: 协议名称
    """
    try:
        logger.info(f"收到协议信息请求: {protocol_name}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 协议信息 {protocol_name}")
            return demo_service.get_protocol_info(protocol_name)

        # 获取协议信息
        protocol_info = await blockchain_service.get_protocol_info(protocol_name)
        return protocol_info
    except Exception as e:
        logger.error(f"获取协议信息时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: 协议信息 {protocol_name}")
            return demo_service.get_protocol_info(protocol_name)
        raise HTTPException(status_code=500, detail=f"获取协议信息失败: {str(e)}")


@router.get("/risk/{protocol_name}")
async def analyze_protocol_risk(
    protocol_name: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    ai_service: AiService = Depends(get_ai_service),
    demo_service: DemoDataService = Depends(get_demo_data_service),
):
    """
    分析协议风险

    - **protocol_name**: 协议名称
    """
    try:
        logger.info(f"收到协议风险分析请求: {protocol_name}")

        # 如果是演示模式，使用演示数据
        if settings.DEMO_MODE:
            logger.info(f"使用演示数据: 协议风险 {protocol_name}")
            protocol_info = demo_service.get_protocol_info(protocol_name)
            risk_score = protocol_info.get("risk_score", 80)

            # 根据风险分数生成风险评估
            risk_level = "低"
            if risk_score < 75:
                risk_level = "高"
            elif risk_score < 85:
                risk_level = "中等"

            return {
                "protocol": protocol_name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": [
                    {
                        "factor": "智能合约风险",
                        "score": risk_score + 5 if risk_score + 5 <= 100 else 100,
                        "description": "协议经过多次审计，但仍存在潜在漏洞风险。",
                    },
                    {
                        "factor": "经济模型风险",
                        "score": risk_score - 5 if risk_score - 5 >= 0 else 0,
                        "description": "协议经济模型相对稳定，但在极端市场条件下可能面临挑战。",
                    },
                    {
                        "factor": "治理风险",
                        "score": risk_score,
                        "description": "协议治理机制较为完善，但决策过程可能存在中心化风险。",
                    },
                ],
                "recommendations": [
                    "关注协议安全更新和审计报告",
                    "分散投资，避免将大量资金集中在单一协议",
                    "了解协议治理机制和决策流程",
                ],
                "is_demo_data": True,
            }

        # 获取协议信息
        protocol_info = await blockchain_service.get_protocol_info(protocol_name)

        # 分析协议风险
        risk_analysis = await ai_service.analyze_protocol_risk(
            protocol_name, protocol_info
        )
        return risk_analysis
    except Exception as e:
        logger.error(f"分析协议风险时出错: {str(e)}")
        # 如果出错且是演示模式，返回演示数据
        if settings.DEMO_MODE:
            logger.info(f"出错时使用演示数据: 协议风险 {protocol_name}")
            protocol_info = demo_service.get_protocol_info(protocol_name)
            risk_score = protocol_info.get("risk_score", 80)

            # 根据风险分数生成风险评估
            risk_level = "低"
            if risk_score < 75:
                risk_level = "高"
            elif risk_score < 85:
                risk_level = "中等"

            return {
                "protocol": protocol_name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": [
                    {
                        "factor": "智能合约风险",
                        "score": risk_score + 5 if risk_score + 5 <= 100 else 100,
                        "description": "协议经过多次审计，但仍存在潜在漏洞风险。",
                    },
                    {
                        "factor": "经济模型风险",
                        "score": risk_score - 5 if risk_score - 5 >= 0 else 0,
                        "description": "协议经济模型相对稳定，但在极端市场条件下可能面临挑战。",
                    },
                    {
                        "factor": "治理风险",
                        "score": risk_score,
                        "description": "协议治理机制较为完善，但决策过程可能存在中心化风险。",
                    },
                ],
                "recommendations": [
                    "关注协议安全更新和审计报告",
                    "分散投资，避免将大量资金集中在单一协议",
                    "了解协议治理机制和决策流程",
                ],
                "is_demo_data": True,
            }
        raise HTTPException(status_code=500, detail=f"分析协议风险失败: {str(e)}")
