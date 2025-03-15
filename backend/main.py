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

from risk_calculator import RiskCalculator, Position
from blockchain_service import BlockchainService
from ai_predictor import AiPredictor
from dataclasses import dataclass


# 定义新的数据结构
@dataclass
class PlatformAsset:
    protocol: str
    asset: str
    amount: float
    apy: Optional[float] = None
    invest_type: int = 0


@dataclass
class ProtocolPosition:
    total_assets: float
    total_debts: float
    leverage: float
    positions: List[PlatformAsset]


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
    return {"message": "DeFi存款分析API"}


@app.post("/analyze", response_model=PortfolioAnalysis)
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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/market-alerts")
async def get_market_alerts(request: PortfolioRequest):
    """获取市场警报"""
    return await blockchain_service.get_market_alerts(request.wallet_address)


@app.post("/predict/market")
async def predict_market(request: MarketPredictionRequest):
    """获取市场预测"""
    try:
        # 跳过 USDT 资产的风险警报
        if request.asset == "USDT":
            raise HTTPException(status_code=400, detail="USDT 资产不支持市场预测")

        # 获取历史数据
        historical_data = await blockchain_service.get_asset_historical_data(
            request.asset
        )
        if historical_data.empty:
            raise HTTPException(
                status_code=404, detail=f"未找到 {request.asset} 的市场数据"
            )

        # 获取AI预测
        prediction = ai_predictor.analyze_market_trend(historical_data, request.asset)

        # # 获取市场警报
        # alerts = await blockchain_service.get_market_alerts(
        #     "0x655b35f11006617696a4b31978ba4c078b6b7145"
        # )  # 使用演示地址获取警报
        # relevant_alerts = [alert for alert in alerts if alert["asset"] == request.asset]

        return {
            "asset": request.asset,
            "current_price": prediction["current_price"],
            "predicted_price": (
                prediction["predicted_price_range"]["24h"][0]
                + prediction["predicted_price_range"]["24h"][1]
            )
            / 2,
            "trend": prediction["trend"],
            "risk_level": prediction["risk_level"],
            "volatility": prediction["volatility"],
            "recommendations": prediction["recommendations"],
            "signals": prediction["trading_signals"],
            "key_price_levels": {
                "support": (
                    prediction["key_levels"]["support"]
                    if "key_levels" in prediction
                    else prediction.get("support_levels", [])
                ),
                "resistance": (
                    prediction["key_levels"]["resistance"]
                    if "key_levels" in prediction
                    else prediction.get("resistance_levels", [])
                ),
            },
        }

    except Exception as e:
        logger.error(f"获取市场预测时出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predict/protocol/{protocol_name}")
async def predict_protocol_risk(protocol_name: str):
    """分析DeFi协议风险"""
    try:
        risk_analysis = ai_predictor.analyze_defi_protocol_risk(protocol_name)
        return risk_analysis
    except Exception as e:
        logger.error(f"分析协议风险时出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/protocols")
async def get_supported_protocols():
    """获取支持的DeFi协议列表"""
    return {
        "protocols": [
            {
                "name": "Aave-V3",
                "description": "去中心化借贷协议",
                "supported_assets": ["ETH", "USDC", "DAI", "BTC"],
                "features": ["存款", "借贷", "抵押"],
            },
            {
                "name": "Compound-V3",
                "description": "去中心化借贷协议",
                "supported_assets": ["ETH", "USDC", "DAI"],
                "features": ["存款", "借贷"],
            },
            {
                "name": "Curve Finance",
                "description": "稳定币交易协议",
                "supported_assets": ["USDC", "DAI", "USDT"],
                "features": ["流动性挖矿", "稳定币交换"],
            },
            {
                "name": "Uniswap-V3",
                "description": "去中心化交易所",
                "supported_assets": ["ETH", "USDC", "BTC", "DAI"],
                "features": ["流动性提供", "交易"],
            },
            {
                "name": "MakerDAO",
                "description": "去中心化稳定币协议",
                "supported_assets": ["ETH", "BTC"],
                "features": ["抵押", "稳定币铸造"],
            },
            {
                "name": "Balancer",
                "description": "多资产流动性池",
                "supported_assets": ["ETH", "USDC", "DAI", "BTC"],
                "features": ["流动性挖矿", "交易"],
            },
            {
                "name": "Yearn-Finance",
                "description": "收益聚合器",
                "supported_assets": ["ETH", "USDC", "DAI", "BTC"],
                "features": ["收益优化", "自动复投"],
            },
            {
                "name": "dYdX",
                "description": "去中心化衍生品交易所",
                "supported_assets": ["ETH", "USDC"],
                "features": ["杠杆交易", "永续合约"],
            },
            {
                "name": "Synthetix",
                "description": "合成资产协议",
                "supported_assets": ["ETH", "SNX"],
                "features": ["合成资产", "抵押"],
            },
        ]
    }


@app.get("/market-data/{asset}")
async def get_market_data(asset: str) -> MarketData:
    """获取资产的市场数据"""
    try:
        # 跳过 USDT 资产的市场数据
        if asset == "USDT":
            raise HTTPException(status_code=400, detail="USDT 资产不支持市场数据")

        # 获取历史数据
        historical_data = await blockchain_service.get_asset_historical_data(asset)
        if historical_data.empty:
            raise HTTPException(status_code=404, detail=f"未找到 {asset} 的市场数据")

        # 获取最新数据
        latest_data = historical_data.iloc[-1]

        return MarketData(
            asset=asset,
            price=latest_data["price"],
            volume_24h=latest_data["volume"],
            price_change_24h=(
                latest_data["price"] / historical_data.iloc[-2]["price"] - 1
            )
            * 100,
            market_cap=latest_data["market_cap"],
        )
    except Exception as e:
        logger.error(f"获取市场数据时出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gas-price")
async def get_gas_price() -> float:
    """获取当前gas价格"""
    try:
        return await blockchain_service.get_gas_price()
    except Exception as e:
        logger.error(f"获取gas价格时出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_market_analysis(positions: List[PlatformAsset]) -> Dict[str, Any]:
    """获取市场分析数据"""
    try:
        analysis = {}
        for pos in positions:
            # 获取资产的历史数据
            asset = pos.asset.split("/")[0]
            if asset == "USDT":
                continue
            historical_data = await blockchain_service.get_asset_historical_data(asset)
            if not historical_data.empty:
                latest_data = historical_data.iloc[-1]
                analysis[pos.asset] = {
                    "current_price": latest_data["price"],
                    "volume_24h": latest_data["volume"],
                    "market_cap": latest_data["market_cap"],
                    "price_change_24h": (
                        latest_data["price"] / historical_data.iloc[-2]["price"] - 1
                    )
                    * 100,
                    "volatility_30d": historical_data["price"].std()
                    / historical_data["price"].mean()
                    * 100,
                }
        return analysis
    except Exception as e:
        logger.error(f"获取市场分析数据时出错: {e}")
        return {}


def monitor_liquidity_pool_example(pool_data):
    """
    流动性池风险监测示例函数

    Args:
        pool_data: 流动性池数据

    Returns:
        Dict: 风险分析结果
    """
    # 初始化风险计算器
    risk_calculator = RiskCalculator()

    # 调用流动性池风险监测方法
    risk_analysis = risk_calculator.monitor_liquidity_pool_risk(pool_data)

    # 打印风险分析结果
    print(f"流动性池: {risk_analysis['pool_name']}")
    print(f"风险评分: {risk_analysis['risk_score']}")
    print(f"风险等级: {risk_analysis['risk_level']}")

    print("\n风险因素:")
    for factor in risk_analysis["risk_factors"]:
        print(f"- {factor}")

    print("\n建议:")
    for recommendation in risk_analysis["recommendations"]:
        print(f"- {recommendation}")

    print("\n监控点:")
    for point in risk_analysis["monitoring_points"]:
        print(f"- {point}")

    # 返回详细风险分析结果
    return risk_analysis


def monitor_mining_example(mining_data):
    """
    挖矿风险监测示例函数

    Args:
        mining_data: 挖矿数据

    Returns:
        Dict: 风险分析结果
    """
    # 初始化风险计算器
    risk_calculator = RiskCalculator()

    # 调用挖矿风险监测方法
    risk_analysis = risk_calculator.monitor_mining_risk(mining_data)

    # 打印风险分析结果
    print(f"挖矿项目: {risk_analysis['pool_name']}")
    print(f"风险评分: {risk_analysis['risk_score']}")
    print(f"风险等级: {risk_analysis['risk_level']}")

    print("\n风险因素:")
    for factor in risk_analysis["risk_factors"]:
        print(f"- {factor}")

    print("\n建议:")
    for recommendation in risk_analysis["recommendations"]:
        print(f"- {recommendation}")

    print("\n监控点:")
    for point in risk_analysis["monitoring_points"]:
        print(f"- {point}")

    # 返回详细风险分析结果
    return risk_analysis


def monitor_staking_example(staking_data):
    """
    质押风险监测示例函数

    Args:
        staking_data: 质押数据

    Returns:
        Dict: 风险分析结果
    """
    # 初始化风险计算器
    risk_calculator = RiskCalculator()

    # 调用质押风险监测方法
    risk_analysis = risk_calculator.monitor_staking_risk(staking_data)

    # 打印风险分析结果
    print(f"质押项目: {risk_analysis['pool_name']}")
    print(f"风险评分: {risk_analysis['risk_score']}")
    print(f"风险等级: {risk_analysis['risk_level']}")

    print("\n风险因素:")
    for factor in risk_analysis["risk_factors"]:
        print(f"- {factor}")

    print("\n建议:")
    for recommendation in risk_analysis["recommendations"]:
        print(f"- {recommendation}")

    print("\n监控点:")
    for point in risk_analysis["monitoring_points"]:
        print(f"- {point}")

    # 返回详细风险分析结果
    return risk_analysis


def monitor_save_example(save_data):
    """
    存币风险监测示例函数

    Args:
        save_data: 存币数据

    Returns:
        Dict: 风险分析结果
    """
    # 初始化风险计算器
    risk_calculator = RiskCalculator()

    # 调用存币风险监测方法
    risk_analysis = risk_calculator.monitor_save_risk(save_data)

    # 打印风险分析结果
    print(f"存币项目: {risk_analysis['pool_name']}")
    print(f"风险评分: {risk_analysis['risk_score']}")
    print(f"风险等级: {risk_analysis['risk_level']}")

    print("\n风险因素:")
    for factor in risk_analysis["risk_factors"]:
        print(f"- {factor}")

    print("\n建议:")
    for recommendation in risk_analysis["recommendations"]:
        print(f"- {recommendation}")

    print("\n监控点:")
    for point in risk_analysis["monitoring_points"]:
        print(f"- {point}")

    # 返回详细风险分析结果
    return risk_analysis


if __name__ == "__main__":
    import uvicorn
    import asyncio
    from dotenv import load_dotenv

    # 加载环境变量
    load_dotenv()

    # 测试数据
    DEMO_ADDRESS = "0x655b35f11006617696a4b31978ba4c078b6b7145"
    TEST_ASSETS = ["ETH", "USDC", "USDT", "BTC"]
    TEST_PROTOCOLS = ["Aave-V3", "Compound-V3", "Curve Finance", "Uniswap-V3"]

    async def test_api_endpoints():
        """测试主要API端点"""
        try:
            print("\n=== 测试API端点 ===\n")

            # for asset in TEST_ASSETS:
            #     _get_24h_data = await blockchain_service._get_24h_data(asset)
            #     print(f"24h data for {asset}: {_get_24h_data}")
            #     price = await blockchain_service.get_asset_price(asset)
            #     print(f"Price for {asset}: {price}")

            # 1. 测试分析DeFi存款
            print("1. 测试分析DeFi存款")
            portfolio_request = PortfolioRequest(wallet_address=DEMO_ADDRESS)
            portfolio_analysis = await analyze_defi_deposits(portfolio_request)
            print("portfolio_analysis", portfolio_analysis)
            print(f"总存款价值: ${portfolio_analysis.total_value:,.2f}")
            print(f"风险等级: {portfolio_analysis.risk_level}")
            print("-" * 50)

            # # 2. 测试市场预测
            # print("\n2. 测试市场预测")
            # for asset in TEST_ASSETS[:2]:  # 只测试前两个资产
            #     prediction_request = MarketPredictionRequest(asset=asset)
            #     prediction = await predict_market(prediction_request)
            #     print(f"\n{asset} 市场预测:")
            #     print(f"当前价格: ${prediction['current_price']:,.2f}")
            #     print(f"趋势: {prediction['trend']}")
            #     print(f"风险等级: {prediction['risk_level']}")
            # print("-" * 50)

            # # 3. 测试协议风险分析
            # print("\n3. 测试协议风险分析")
            # for protocol in TEST_PROTOCOLS[:2]:  # 只测试前两个协议
            #     risk_analysis = await predict_protocol_risk(protocol)
            #     print(f"\n{protocol} 风险分析:")
            #     print(
            #         "risk_analysis.ai_risk_analysis",
            #         risk_analysis["ai_risk_analysis"]["risk_score"],
            #     )
            # print("-" * 50)

            # # 4. 测试市场数据
            # print("\n4. 测试市场数据")
            # for asset in TEST_ASSETS[:2]:  # 只测试前两个资产
            #     market_data = await get_market_data(asset)
            #     print(f"\n{asset} 市场数据:")
            #     print(f"价格: ${market_data.price:,.2f}")
            #     print(f"24h成交量: ${market_data.volume_24h:,.2f}")
            #     print(f"24h价格变化: {market_data.price_change_24h:.2f}%")
            # print("-" * 50)

            print("\n所有测试完成!")

        except Exception as e:
            print(f"测试过程中出错: {e}")

    # 运行测试
    asyncio.run(test_api_endpoints())

    # 示例调用流动性池风险监测
    usdc_usdt_pool_data = {
        "investmentName": "USDC-USDT",
        "investmentKey": "1-0xc36442b4a4522e871399cd717abdd847ab11fe88-0x3416cf6c708da44db2624d63ea0aaef7113527c6",
        "feeRate": "0.00010",
        "investType": 2,
        "investName": "Pool",
        "positionList": [
            {
                "rangeInfo": {
                    "lowerPrice": "0.994813755230067338",
                    "upperPrice": "1.004911778445206683",
                    "token0Symbol": "USDC",
                    "token1Symbol": "USDT",
                },
                "tokenId": "541977",
                "positionName": "USDC-USDT",
                "positionStatus": "ACTIVE",
                "assetsTokenList": [
                    {
                        "tokenSymbol": "USDC",
                        "tokenLogo": "https://static.coinall.ltd/cdn/wallet/logo/USDC.png",
                        "coinAmount": "0.978179",
                        "currencyAmount": "0.9780811821",
                        "tokenPrecision": 6,
                        "tokenAddress": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                        "network": "ETH",
                    },
                    {
                        "tokenSymbol": "USDT",
                        "tokenLogo": "https://static.coinall.ltd/cdn/wallet/logo/USDT-991ffed9-e495-4d1b-80c2-a4c5f96ce22d.png",
                        "coinAmount": "1.003816",
                        "currencyAmount": "1.00365538944",
                        "tokenPrecision": 6,
                        "tokenAddress": "0xdac17f958d2ee523a2206206994597c13d831ec7",
                        "network": "ETH",
                    },
                ],
                "unclaimFeesDefiTokenInfo": [
                    {
                        "baseDefiTokenInfos": [
                            {
                                "tokenSymbol": "USDC",
                                "tokenLogo": "https://static.coinall.ltd/cdn/wallet/logo/USDC.png",
                                "coinAmount": "0.080475",
                                "currencyAmount": "0.0804669525",
                                "tokenPrecision": 6,
                                "tokenAddress": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                                "network": "ETH",
                            },
                            {
                                "tokenSymbol": "USDT",
                                "tokenLogo": "https://static.coinall.ltd/cdn/wallet/logo/USDT-991ffed9-e495-4d1b-80c2-a4c5f96ce22d.png",
                                "coinAmount": "0.080623",
                                "currencyAmount": "0.08061010032",
                                "tokenPrecision": 6,
                                "tokenAddress": "0xdac17f958d2ee523a2206206994597c13d831ec7",
                                "network": "ETH",
                            },
                        ],
                        "currencyAmount": "0.16107705282",
                    },
                ],
                "totalValue": "2.14281362436",
            },
        ],
    }

    # 调用风险监测函数
    risk_result = monitor_liquidity_pool_example(usdc_usdt_pool_data)

    # 可以进一步处理风险结果
    # 例如，如果风险等级为HIGH，可以发送警报
    if risk_result["risk_level"] == "HIGH":
        print("\n⚠️ 高风险警报! 建议立即检查您的流动性池投资")

    # 示例调用挖矿风险监测
    ibeur_ageur_mining_data = {
        "investmentName": "LP ibEUR-agEUR",
        "investmentKey": "1-0x38039dd47636154273b287f74c432cac83da97e2-0xb37d6c07482bc11cd28a1f11f1a6ad7b66dec933",
        "investType": 3,
        "investName": "Farm",
        "assetsTokenList": [
            {
                "tokenSymbol": "ibEUR",
                "tokenLogo": "https://static.coinall.ltd/cdn/wallet/logo/ibeur-19cca0a3beaf4e83b4b52725e48a8e61-20220721.png",
                "coinAmount": "34.578266602423679254",
                "currencyAmount": "26.0954567003005293403445947583767916",
                "tokenPrecision": 18,
                "tokenAddress": "0x96e61422b6a9ba0e068b6c5add4ffabc6a4aae27",
                "network": "ETH",
            },
            {
                "tokenSymbol": "EURA",
                "tokenLogo": "https://static.coinall.ltd/cdn/invest/coin/logo/ETH/AGEUR-0x1a7e4e63778b4f12a199c062f3efdd288afcbce8.png",
                "coinAmount": "1.298239373044056277",
                "currencyAmount": "1.4116594094769705924895889040857011",
                "tokenPrecision": 18,
                "tokenAddress": "0x1a7e4e63778b4f12a199c062f3efdd288afcbce8",
                "network": "ETH",
            },
        ],
        "rewardDefiTokenInfo": [
            {
                "baseDefiTokenInfos": [
                    {
                        "tokenSymbol": "ANGLE",
                        "tokenLogo": "https://static.coinall.ltd/cdn/wallet/logo/ANGLE-0x31429d1856ad1377a8a0079410b297e1a9e214c2.png",
                        "coinAmount": "0",
                        "currencyAmount": "0",
                        "tokenPrecision": 18,
                        "tokenAddress": "0x31429d1856ad1377a8a0079410b297e1a9e214c2",
                        "network": "ETH",
                    },
                    {
                        "tokenSymbol": "rKP3R",
                        "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/default-logo/token_custom_logo_default_r.png/type=default_350_0",
                        "coinAmount": "0",
                        "currencyAmount": "0",
                        "tokenPrecision": 18,
                        "tokenAddress": "0xedb67ee1b171c4ec66e6c10ec43edbba20fae8e9",
                        "network": "ETH",
                    },
                ],
                "rewardType": 1,
            },
            {
                "baseDefiTokenInfos": [
                    {
                        "tokenSymbol": "CRV",
                        "tokenLogo": "https://static.coinall.ltd/cdn/invest/coin/CRV.png",
                        "coinAmount": "0.005633827373819009",
                        "currencyAmount": "0.0022601550144048042276916685339936",
                        "tokenPrecision": 18,
                        "tokenAddress": "0xd533a949740bb3306d119cc777fa900ba034cd52",
                        "network": "ETH",
                    },
                ],
                "rewardType": 1,
            },
        ],
        "totalValue": "27.5093762647919047370618753309964863",
    }

    # 调用挖矿风险监测函数
    mining_risk_result = monitor_mining_example(ibeur_ageur_mining_data)

    # 可以进一步处理风险结果
    # 例如，如果风险等级为HIGH，可以发送警报
    if mining_risk_result["risk_level"] == "HIGH":
        print("\n⚠️ 高风险警报! 建议立即检查您的挖矿投资")

    # 示例调用质押风险监测
    ath_staking_data = {
        "investmentName": "ATH",
        "investmentKey": "1-0x6f5c81fe067ae25afd52218f140a73d51f0c6b31-0",
        "investType": 5,
        "investName": "Stake",
        "assetsTokenList": [
            {
                "tokenSymbol": "ATH",
                "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/1-0xbe0ed4138121ecfc5c0e56b40517da27e6c5226b-97.png/type=default_350_0",
                "coinAmount": "700",
                "currencyAmount": "25.527897036276257",
                "tokenPrecision": 18,
                "tokenAddress": "0xbe0ed4138121ecfc5c0e56b40517da27e6c5226b",
                "network": "ETH",
            }
        ],
        "rewardDefiTokenInfo": [
            {
                "baseDefiTokenInfos": [
                    {
                        "tokenSymbol": "ATH",
                        "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/1-0xbe0ed4138121ecfc5c0e56b40517da27e6c5226b-97.png/type=default_350_0",
                        "coinAmount": "141.566873923846617599",
                        "currencyAmount": "5.16272083039351228430531090228863849",
                        "tokenPrecision": 18,
                        "tokenAddress": "0xbe0ed4138121ecfc5c0e56b40517da27e6c5226b",
                        "network": "ETH",
                    },
                    {
                        "tokenSymbol": "$MICRO",
                        "tokenLogo": "https://static.coinall.ltd/cdn/web3/currency/token/1-0x8cedb0680531d26e62abdbd0f4c5428b7fdc26d5-97.png/type=default_350_0?v=1737438768635",
                        "coinAmount": "0",
                        "currencyAmount": "0",
                        "tokenPrecision": 18,
                        "tokenAddress": "0x8cedb0680531d26e62abdbd0f4c5428b7fdc26d5",
                        "network": "ETH",
                    },
                ],
                "rewardType": 1,
            }
        ],
        "totalValue": "30.69061786666976928430531090228863849",
    }

    # 调用质押风险监测函数
    staking_risk_result = monitor_staking_example(ath_staking_data)

    # 可以进一步处理风险结果
    # 例如，如果风险等级为HIGH，可以发送警报
    if staking_risk_result["risk_level"] == "HIGH":
        print("\n⚠️ 高风险警报! 建议立即检查您的质押投资")

    # 示例调用存币风险监测
    usdt_save_data = {
        "investmentName": "USDT",
        "investmentKey": "1-0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9-0x3ed3b47dd13ec9a98b44e6204a523e766b225811",
        "investType": 1,
        "investName": "Save",
        "assetsTokenList": [
            {
                "tokenSymbol": "USDT",
                "tokenLogo": "https://static.coinall.ltd/cdn/wallet/logo/USDT-991ffed9-e495-4d1b-80c2-a4c5f96ce22d.png",
                "coinAmount": "1.541928",
                "currencyAmount": "1.54152709872",
                "tokenPrecision": 6,
                "tokenAddress": "0xdac17f958d2ee523a2206206994597c13d831ec7",
                "network": "ETH",
            }
        ],
        "rewardDefiTokenInfo": [],
        "totalValue": "1.54152709872",
    }

    # 调用存币风险监测函数
    save_risk_result = monitor_save_example(usdt_save_data)

    # 可以进一步处理风险结果
    # 例如，如果风险等级为HIGH，可以发送警报
    if save_risk_result["risk_level"] == "HIGH":
        print("\n⚠️ 高风险警报! 建议立即检查您的存币投资")

    # 启动FastAPI服务器
    # print("\n启动FastAPI服务器...")
    # uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
