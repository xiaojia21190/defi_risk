from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.core.init_app import get_blockchain_service, get_ai_service
import logging


router = APIRouter()
logger = logging.getLogger("defi_risk.api.protocol")


@router.get("/list")
async def get_supported_protocols(
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取支持的协议列表
    """
    try:
        logger.info("收到支持协议列表请求")

        # 这里应该从区块链服务获取支持的协议列表
        # 简化处理，使用模拟数据
        protocols = [
            {"name": "Aave", "chain": "Ethereum", "tvl": 5000000000},
            {"name": "Compound", "chain": "Ethereum", "tvl": 3000000000},
            {"name": "Uniswap", "chain": "Ethereum", "tvl": 8000000000},
            {"name": "Curve", "chain": "Ethereum", "tvl": 4000000000},
            {"name": "MakerDAO", "chain": "Ethereum", "tvl": 7000000000},
            {"name": "SushiSwap", "chain": "Ethereum", "tvl": 2000000000},
            {"name": "Balancer", "chain": "Ethereum", "tvl": 1500000000},
            {"name": "Yearn", "chain": "Ethereum", "tvl": 1000000000},
            {"name": "PancakeSwap", "chain": "BSC", "tvl": 6000000000},
            {"name": "dYdX", "chain": "Ethereum", "tvl": 900000000},
        ]

        return {
            "protocols": protocols,
            "count": len(protocols),
        }
    except Exception as e:
        logger.error(f"获取支持协议列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取支持协议列表失败: {str(e)}")


@router.get("/{protocol_name}")
async def get_protocol_info(
    protocol_name: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取协议信息

    - **protocol_name**: 协议名称
    """
    try:
        logger.info(f"收到协议信息请求: {protocol_name}")

        # 获取协议TVL
        tvl = await blockchain_service.get_protocol_tvl(protocol_name)

        # 获取协议审计状态
        audit_status = await blockchain_service.get_protocol_audit_status(protocol_name)

        return {
            "name": protocol_name,
            "tvl": tvl,
            "audit_status": audit_status,
        }
    except Exception as e:
        logger.error(f"获取协议信息时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取协议信息失败: {str(e)}")


@router.get("/risk/{protocol_name}")
async def analyze_protocol_risk(
    protocol_name: str,
    ai_service: AiService = Depends(get_ai_service),
):
    """
    分析协议风险

    - **protocol_name**: 协议名称
    """
    try:
        logger.info(f"收到协议风险分析请求: {protocol_name}")

        # 构建AI分析上下文
        context = {
            "protocol": protocol_name,
        }

        # 调用AI服务进行分析
        analysis = await ai_service.analyze("protocol_risk", context)

        return {
            "protocol": protocol_name,
            "risk_score": analysis.supporting_data.get("protocol_risk_score", 50),
            "risk_level": (
                "HIGH"
                if analysis.supporting_data.get("protocol_risk_score", 50) > 70
                else (
                    "MEDIUM"
                    if analysis.supporting_data.get("protocol_risk_score", 50) > 40
                    else "LOW"
                )
            ),
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
            "confidence": analysis.confidence,
        }
    except Exception as e:
        logger.error(f"分析协议风险时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析协议风险失败: {str(e)}")


@router.get("/positions/{wallet_address}/{protocol_name}")
async def get_protocol_positions(
    wallet_address: str,
    protocol_name: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取钱包在特定协议中的头寸

    - **wallet_address**: 钱包地址
    - **protocol_name**: 协议名称
    """
    try:
        logger.info(f"收到协议头寸请求: {wallet_address}, 协议: {protocol_name}")

        # 获取协议头寸
        positions = await blockchain_service.get_protocol_positions(
            wallet_address, protocol_name
        )

        return {
            "wallet_address": wallet_address,
            "protocol": protocol_name,
            "positions": positions,
        }
    except Exception as e:
        logger.error(f"获取协议头寸时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取协议头寸失败: {str(e)}")
