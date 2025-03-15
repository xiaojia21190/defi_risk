from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import logging
import asyncio
import json
from datetime import datetime

import pandas as pd
import uvicorn
from dotenv import load_dotenv

from risk_calculator import RiskCalculator, Position
from blockchain_service import BlockchainService, PlatformAsset, ProtocolPosition
from ai_predictor import AiPredictor
from dataclasses import dataclass

# 加载环境变量
load_dotenv()

# 设置日志记录
logger = logging.getLogger("defi_risk")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="DeFi风险分析API")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
web3_provider = os.getenv(
    "WEB3_PROVIDER_URL",
    "https://eth-sepolia.g.alchemy.com/v2/8GHYFBqZcX9OEuKkgB1N3u1RDPBYy9Mm",
)
blockchain_service = BlockchainService(web3_provider)
risk_calculator = RiskCalculator(blockchain_service)
ai_predictor = AiPredictor()


class PortfolioRequest(BaseModel):
    wallet_address: str


class DefiPosition(BaseModel):
    protocol: str
    asset: str
    amount: float
    apy: float
    leverage: Optional[float] = None
    invest_type: Optional[int] = None
    invest_type_name: Optional[str] = None


class InvestmentTypeDistribution(BaseModel):
    type_id: int
    type_name: str
    amount: float
    percentage: float
    risk_score: float
    risk_level: str


class PortfolioAnalysis(BaseModel):
    total_value: float
    positions: List[DefiPosition]
    risk_level: str
    risk_score: int
    risk_factors: Dict[str, Any]
    recommendations: List[str]
    risk_mitigation_strategies: List[str]
    monitoring_points: List[str]
    market_analysis: Dict[str, Any]
    investment_type_distribution: Optional[List[InvestmentTypeDistribution]] = None
    investment_type_recommendations: Optional[List[str]] = None
    investment_type_risk_mitigations: Optional[List[str]] = None
    investment_type_warnings: Optional[List[str]] = None


class InvestmentTypeAnalysis(BaseModel):
    total_value: float
    distribution: List[InvestmentTypeDistribution]
    risk_score: int
    risk_level: str
    recommendations: List[str]
    risk_mitigation_strategies: List[str]
    warnings: List[str]


class MarketData(BaseModel):
    asset: str
    price: float
    volume_24h: float
    price_change_24h: float
    market_cap: float


class TokenPrice(BaseModel):
    token_address: str


class MarketPredictionRequest(BaseModel):
    asset: str
    time_frame: Optional[str] = "24h"  # 24h, 7d, 30d


@app.get("/")
async def root():
    return {"message": "DeFi风险分析API"}


@app.post("/api/v1/portfolio/analyze", response_model=PortfolioAnalysis)
async def analyze_defi_deposits(request: PortfolioRequest):
    """分析用户的DeFi存款情况"""
    try:
        logger.info(f"分析钱包地址: {request.wallet_address} 的DeFi存款")

        # 获取用户在各协议中的存款头寸
        protocol_positions = await blockchain_service.get_all_positions(
            request.wallet_address
        )

        if not protocol_positions:
            raise HTTPException(status_code=404, detail="未找到DeFi存款")

        # 合并所有协议的头寸
        all_positions = []
        total_assets = 0
        total_debts = 0
        weighted_leverage = 0
        total_weight = 0

        for protocol_pos in protocol_positions:
            all_positions.extend(protocol_pos.positions)
            total_assets += protocol_pos.total_assets
            total_debts += protocol_pos.total_debts
            # 计算加权杠杆率
            weighted_leverage += protocol_pos.leverage * protocol_pos.total_assets
            total_weight += protocol_pos.total_assets

        if not all_positions:
            raise HTTPException(status_code=404, detail="未找到有效的DeFi存款")

        # 计算整体杠杆率
        overall_leverage = weighted_leverage / total_weight if total_weight > 0 else 0

        # 计算风险评估
        risk_assessment = risk_calculator.assess_portfolio_risk(all_positions)

        # 获取市场分析数据
        market_analysis = await get_market_analysis(all_positions)

        # 获取投资类型名称
        invest_type_map = (
            risk_calculator.investment_type_risk_analyzer.invest_type_map
            if risk_calculator.investment_type_risk_analyzer
            else {}
        )

        # 获取投资类型分布数据
        investment_type_distribution = risk_assessment.detailed_analysis.get(
            "investment_type_distribution", {}
        )
        distribution_data = investment_type_distribution.get("distribution", {})
        percentage_data = investment_type_distribution.get("percentage", {})
        names_data = investment_type_distribution.get("names", {})

        # 获取投资类型风险详情
        investment_type_risk_details = risk_assessment.detailed_analysis.get(
            "investment_type_risk_details", {}
        )

        # 构建投资类型分布列表
        investment_type_distribution_list = []

        for invest_type_id, amount in distribution_data.items():
            invest_type_id = (
                int(invest_type_id)
                if isinstance(invest_type_id, str)
                else invest_type_id
            )
            percentage = percentage_data.get(str(invest_type_id), 0)
            type_name = names_data.get(str(invest_type_id), "未知类型")

            # 获取风险评分
            risk_score = 0.3  # 默认中等风险
            risk_level = "中等风险"

            if (
                str(invest_type_id) in investment_type_risk_details
                or invest_type_id in investment_type_risk_details
            ):
                risk_details = investment_type_risk_details.get(
                    str(invest_type_id),
                    investment_type_risk_details.get(invest_type_id, {}),
                )
                risk_score = risk_details.get("risk_score", 0.3)

                # 设置风险等级
                if risk_score >= 0.7:
                    risk_level = "高风险"
                elif risk_score <= 0.3:
                    risk_level = "低风险"
                else:
                    risk_level = "中等风险"

            investment_type_distribution_list.append(
                InvestmentTypeDistribution(
                    type_id=invest_type_id,
                    type_name=type_name,
                    amount=amount,
                    percentage=percentage,
                    risk_score=risk_score * 100,  # 转换为0-100范围
                    risk_level=risk_level,
                )
            )

        # 按金额降序排序
        investment_type_distribution_list.sort(key=lambda x: x.amount, reverse=True)

        # 提取投资类型相关的建议和风险缓解策略
        investment_type_recommendations = []
        investment_type_risk_mitigations = []
        investment_type_warnings = []

        for rec in risk_assessment.recommendations:
            if any(
                keyword in rec.lower()
                for keyword in [
                    "投资类型",
                    "存币",
                    "流动性池",
                    "挖矿",
                    "机枪池",
                    "质押",
                    "借贷",
                ]
            ):
                investment_type_recommendations.append(rec)

        for strategy in risk_assessment.risk_mitigation_strategies:
            if any(
                keyword in strategy.lower()
                for keyword in [
                    "投资类型",
                    "存币",
                    "流动性池",
                    "挖矿",
                    "机枪池",
                    "质押",
                    "借贷",
                ]
            ):
                investment_type_risk_mitigations.append(strategy)

        for warning in risk_assessment.warnings:
            if any(
                keyword in warning.lower()
                for keyword in [
                    "投资类型",
                    "存币",
                    "流动性池",
                    "挖矿",
                    "机枪池",
                    "质押",
                    "借贷",
                ]
            ):
                investment_type_warnings.append(warning)

        # 转换为响应格式
        defi_positions = [
            DefiPosition(
                protocol=pos.protocol,
                asset=pos.asset,
                amount=pos.amount,
                apy=pos.apy or 0.0,
                leverage=overall_leverage,
                invest_type=pos.invest_type,
                invest_type_name=(
                    invest_type_map.get(pos.invest_type, "未知类型")
                    if pos.invest_type
                    else "未知类型"
                ),
            )
            for pos in all_positions
        ]

        # 构建并返回响应
        return PortfolioAnalysis(
            total_value=total_assets,
            positions=defi_positions,
            risk_level=risk_assessment.risk_level.value,
            risk_score=risk_assessment.risk_score,
            risk_factors=risk_assessment.risk_factors,
            recommendations=risk_assessment.recommendations,
            risk_mitigation_strategies=risk_assessment.risk_mitigation_strategies,
            monitoring_points=risk_assessment.monitoring_points,
            market_analysis=market_analysis,
            investment_type_distribution=investment_type_distribution_list,
            investment_type_recommendations=investment_type_recommendations,
            investment_type_risk_mitigations=investment_type_risk_mitigations,
            investment_type_warnings=investment_type_warnings,
        )
    except Exception as e:
        logger.error(f"分析DeFi存款时出错: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.get("/api/v1/market/data/{asset}", response_model=MarketData)
async def get_market_data(asset: str) -> MarketData:
    """获取资产的市场数据"""
    try:
        logger.info(f"获取资产 {asset} 的市场数据")

        # 获取资产价格
        price = await blockchain_service.get_asset_price(asset)

        # 获取24小时数据
        data_24h = await blockchain_service._get_24h_data(asset)

        if not data_24h:
            raise HTTPException(
                status_code=404, detail=f"未找到资产 {asset} 的市场数据"
            )

        return MarketData(
            asset=asset,
            price=price,
            volume_24h=data_24h.get("volume", 0),
            price_change_24h=data_24h.get("price_change_percentage", 0),
            market_cap=data_24h.get("market_cap", 0),
        )
    except Exception as e:
        logger.error(f"获取市场数据时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取市场数据失败: {str(e)}")


@app.get("/api/v1/market/gas")
async def get_gas_price() -> Dict[str, float]:
    """获取当前gas价格"""
    try:
        gas_price = await blockchain_service.get_gas_price()
        return {"gas_price": gas_price}
    except Exception as e:
        logger.error(f"获取gas价格时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取gas价格失败: {str(e)}")


@app.post("/api/v1/market/predict/{asset}")
async def predict_market(asset: str, request: MarketPredictionRequest):
    """预测资产市场趋势"""
    try:
        logger.info(f"预测资产 {asset} 的市场趋势")

        # 获取历史数据
        historical_data = await blockchain_service.get_asset_historical_data(asset)

        if historical_data.empty:
            raise HTTPException(
                status_code=404, detail=f"未找到资产 {asset} 的历史数据"
            )

        # 使用AI预测器分析市场趋势
        market_trend = ai_predictor.analyze_market_trend(historical_data, asset)

        return {
            "asset": asset,
            "time_frame": request.time_frame,
            "prediction": market_trend,
        }
    except Exception as e:
        logger.error(f"预测市场趋势时出错: {e}")
        raise HTTPException(status_code=500, detail=f"预测市场趋势失败: {str(e)}")


@app.get("/api/v1/protocol/list")
async def get_supported_protocols():
    """获取支持的协议列表"""
    try:
        # 这里可以从配置或数据库中获取支持的协议列表
        # 暂时返回一个固定的列表
        protocols = [
            {
                "name": "Aave",
                "description": "去中心化借贷协议",
                "category": "借贷",
                "chain": "Ethereum",
                "url": "https://aave.com",
            },
            {
                "name": "Uniswap",
                "description": "去中心化交易所",
                "category": "DEX",
                "chain": "Ethereum",
                "url": "https://uniswap.org",
            },
            {
                "name": "Curve",
                "description": "稳定币交易协议",
                "category": "DEX",
                "chain": "Ethereum",
                "url": "https://curve.fi",
            },
            {
                "name": "Compound",
                "description": "去中心化借贷协议",
                "category": "借贷",
                "chain": "Ethereum",
                "url": "https://compound.finance",
            },
            {
                "name": "MakerDAO",
                "description": "去中心化稳定币协议",
                "category": "稳定币",
                "chain": "Ethereum",
                "url": "https://makerdao.com",
            },
        ]

        return {"protocols": protocols}
    except Exception as e:
        logger.error(f"获取协议列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取协议列表失败: {str(e)}")


@app.get("/api/v1/protocol/{protocol_name}")
async def get_protocol_info(protocol_name: str):
    """获取协议信息"""
    try:
        logger.info(f"获取协议 {protocol_name} 的信息")

        # 获取协议信息
        protocol_info = await blockchain_service.get_protocol_info(protocol_name)

        if not protocol_info:
            raise HTTPException(
                status_code=404, detail=f"未找到协议 {protocol_name} 的信息"
            )

        return protocol_info
    except Exception as e:
        logger.error(f"获取协议信息时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取协议信息失败: {str(e)}")


@app.get("/api/v1/protocol/risk/{protocol_name}")
async def analyze_protocol_risk(protocol_name: str):
    """分析协议风险"""
    try:
        logger.info(f"分析协议 {protocol_name} 的风险")

        # 分析协议风险
        risk_analysis = await blockchain_service.analyze_protocol_risk(protocol_name)

        if not risk_analysis:
            raise HTTPException(
                status_code=404, detail=f"未能分析协议 {protocol_name} 的风险"
            )

        return risk_analysis
    except Exception as e:
        logger.error(f"分析协议风险时出错: {e}")
        raise HTTPException(status_code=500, detail=f"分析协议风险失败: {str(e)}")


@app.get("/api/v1/wallet/{wallet_address}/balance")
async def get_wallet_balance(wallet_address: str):
    """获取钱包余额"""
    try:
        logger.info(f"获取钱包 {wallet_address} 的余额")

        # 获取用户在各协议中的存款头寸
        protocol_positions = await blockchain_service.get_all_positions(wallet_address)

        if not protocol_positions:
            raise HTTPException(status_code=404, detail="未找到DeFi存款")

        # 计算总资产和总负债
        total_assets = sum(pos.total_assets for pos in protocol_positions)
        total_debts = sum(pos.total_debts for pos in protocol_positions)

        # 构建资产列表
        assets = []
        for protocol_pos in protocol_positions:
            for pos in protocol_pos.positions:
                assets.append(
                    {
                        "protocol": pos.protocol,
                        "asset": pos.asset,
                        "amount": pos.amount,
                        "value_usd": pos.amount,  # 这里应该是美元价值，暂时使用数量代替
                    }
                )

        return {
            "wallet_address": wallet_address,
            "total_assets": total_assets,
            "total_debts": total_debts,
            "net_worth": total_assets - total_debts,
            "assets": assets,
        }
    except Exception as e:
        logger.error(f"获取钱包余额时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取钱包余额失败: {str(e)}")


@app.get("/api/v1/wallet/{wallet_address}/positions")
async def get_wallet_positions(wallet_address: str):
    """获取钱包在所有协议中的头寸"""
    try:
        logger.info(f"获取钱包 {wallet_address} 的头寸")

        # 获取用户在各协议中的存款头寸
        protocol_positions = await blockchain_service.get_all_positions(wallet_address)

        if not protocol_positions:
            raise HTTPException(status_code=404, detail="未找到DeFi存款")

        # 构建头寸列表
        positions = []
        for protocol_pos in protocol_positions:
            protocol_name = (
                protocol_pos.positions[0].protocol
                if protocol_pos.positions
                else "未知协议"
            )

            positions.append(
                {
                    "protocol": protocol_name,
                    "total_assets": protocol_pos.total_assets,
                    "total_debts": protocol_pos.total_debts,
                    "leverage": protocol_pos.leverage,
                    "positions": [
                        {
                            "asset": pos.asset,
                            "amount": pos.amount,
                            "apy": pos.apy or 0.0,
                            "invest_type": pos.invest_type,
                        }
                        for pos in protocol_pos.positions
                    ],
                }
            )

        return {
            "wallet_address": wallet_address,
            "positions": positions,
        }
    except Exception as e:
        logger.error(f"获取钱包头寸时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取钱包头寸失败: {str(e)}")


@app.get("/api/v1/wallet/{wallet_address}/risk")
async def analyze_wallet_risk(wallet_address: str):
    """分析钱包风险"""
    try:
        logger.info(f"分析钱包 {wallet_address} 的风险")

        # 获取用户在各协议中的存款头寸
        protocol_positions = await blockchain_service.get_all_positions(wallet_address)

        if not protocol_positions:
            raise HTTPException(status_code=404, detail="未找到DeFi存款")

        # 合并所有协议的头寸
        all_positions = []
        for protocol_pos in protocol_positions:
            all_positions.extend(protocol_pos.positions)

        # 计算风险评估
        risk_assessment = risk_calculator.assess_portfolio_risk(all_positions)

        return {
            "wallet_address": wallet_address,
            "risk_level": risk_assessment.risk_level.value,
            "risk_score": risk_assessment.risk_score,
            "risk_factors": risk_assessment.risk_factors,
            "recommendations": risk_assessment.recommendations,
            "risk_mitigation_strategies": risk_assessment.risk_mitigation_strategies,
            "monitoring_points": risk_assessment.monitoring_points,
        }
    except Exception as e:
        logger.error(f"分析钱包风险时出错: {e}")
        raise HTTPException(status_code=500, detail=f"分析钱包风险失败: {str(e)}")


@app.get("/api/v1/wallet/{wallet_address}/alerts")
async def get_wallet_alerts(wallet_address: str):
    """获取钱包相关的市场警报"""
    try:
        logger.info(f"获取钱包 {wallet_address} 的市场警报")

        # 获取市场警报
        alerts = await blockchain_service.get_market_alerts(wallet_address)

        return {
            "wallet_address": wallet_address,
            "alerts": alerts,
        }
    except Exception as e:
        logger.error(f"获取钱包警报时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取钱包警报失败: {str(e)}")


async def get_market_analysis(positions: List[PlatformAsset]) -> Dict[str, Any]:
    """获取市场分析数据"""
    try:
        # 提取资产列表
        assets = list(set(pos.asset.split("/")[0] for pos in positions))

        # 获取资产价格和趋势
        market_data = {}
        for asset in assets:
            try:
                # 获取资产历史数据
                historical_data = await blockchain_service.get_asset_historical_data(
                    asset
                )

                if not historical_data.empty:
                    # 分析市场趋势
                    market_trend = ai_predictor.analyze_market_trend(
                        historical_data, asset
                    )
                    market_data[asset] = market_trend
            except Exception as e:
                logger.warning(f"获取资产 {asset} 的市场数据时出错: {e}")

        return {
            "assets": market_data,
            "market_sentiment": "中性",  # 可以根据市场数据计算整体情绪
            "key_indicators": {
                "btc_dominance": 45.5,  # 示例数据
                "market_cap": 1.2e12,  # 示例数据
                "fear_greed_index": 55,  # 示例数据
            },
        }
    except Exception as e:
        logger.error(f"获取市场分析数据时出错: {e}")
        return {
            "assets": {},
            "market_sentiment": "未知",
            "key_indicators": {},
            "error": str(e),
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
