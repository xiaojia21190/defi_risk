from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.services.blockchain import BlockchainService
from app.services.ai_service import AiService
from app.core.init_app import get_blockchain_service, get_ai_service, get_risk_engine
import logging

from app.services.risk_engine import RiskEngine


router = APIRouter()
logger = logging.getLogger("defi_risk.api.wallet")


@router.get("/{wallet_address}/balance")
async def get_wallet_balance(
    wallet_address: str,
    token_address: Optional[str] = None,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取钱包余额

    - **wallet_address**: 钱包地址
    - **token_address**: 代币合约地址（可选，如果不提供则返回ETH余额）
    """
    try:
        logger.info(
            f"收到钱包余额请求: {wallet_address}, 代币: {token_address or 'ETH'}"
        )

        # 获取代币余额
        balance = await blockchain_service.get_token_balance(
            wallet_address, token_address
        )

        # 如果提供了代币地址，获取代币价格
        token_price = None
        if token_address:
            token_price = await blockchain_service.get_token_price(token_address)
        else:
            # 获取ETH价格
            token_price = await blockchain_service.get_token_price("ETH")

        # 计算美元价值
        usd_value = balance * token_price if token_price else None

        return {
            "wallet_address": wallet_address,
            "token": token_address or "ETH",
            "balance": balance,
            "token_price_usd": token_price,
            "usd_value": usd_value,
        }
    except Exception as e:
        logger.error(f"获取钱包余额时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取钱包余额失败: {str(e)}")


@router.get("/{wallet_address}/positions")
async def get_wallet_positions(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取钱包在所有协议中的头寸

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包头寸请求: {wallet_address}")

        # 获取所有协议头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        # 计算总价值
        total_value = sum(position.get("usd_value", 0) for position in positions)

        return {
            "wallet_address": wallet_address,
            "positions": positions,
            "total_value_usd": total_value,
            "position_count": len(positions),
        }
    except Exception as e:
        logger.error(f"获取钱包头寸时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取钱包头寸失败: {str(e)}")


@router.get("/{wallet_address}/risk")
async def analyze_wallet_risk(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    risk_engine: RiskEngine = Depends(get_risk_engine),
):
    """
    分析钱包风险

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包风险分析请求: {wallet_address}")

        # 获取钱包头寸
        positions = await blockchain_service.get_all_positions(wallet_address)

        # 构建AI分析上下文
        context = {
            "wallet_address": wallet_address,
            "positions": positions,
        }

        # 调用AI服务进行分析
        analysis = await risk_engine.analyze_wallet_risk(context)

        # 计算总风险分数（简化处理）
        risk_scores = {
            "market_risk": analysis.supporting_data.get("market_risk_score", 50),
            "protocol_risk": analysis.supporting_data.get("protocol_risk_score", 50),
            "liquidity_risk": analysis.supporting_data.get("liquidity_risk_score", 50),
            "smart_contract_risk": analysis.supporting_data.get(
                "smart_contract_risk_score", 50
            ),
            "correlation_risk": analysis.supporting_data.get(
                "correlation_risk_score", 50
            ),
        }

        # 计算总风险分数（简单平均）
        total_risk_score = sum(risk_scores.values()) / len(risk_scores)

        # 确定风险等级
        risk_level = (
            "HIGH"
            if total_risk_score > 70
            else "MEDIUM" if total_risk_score > 40 else "LOW"
        )

        return {
            "wallet_address": wallet_address,
            "total_risk_score": total_risk_score,
            "risk_level": risk_level,
            "risk_breakdown": risk_scores,
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
            "confidence": analysis.confidence,
        }
    except Exception as e:
        logger.error(f"分析钱包风险时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析钱包风险失败: {str(e)}")


@router.get("/{wallet_address}/alerts")
async def get_wallet_alerts(
    wallet_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
):
    """
    获取钱包相关的市场警报

    - **wallet_address**: 钱包地址
    """
    try:
        logger.info(f"收到钱包警报请求: {wallet_address}")

        # 获取市场警报
        alerts = await blockchain_service.get_market_alerts(wallet_address)

        return {
            "wallet_address": wallet_address,
            "alerts": alerts,
            "alert_count": len(alerts),
        }
    except Exception as e:
        logger.error(f"获取钱包警报时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取钱包警报失败: {str(e)}")
