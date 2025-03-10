from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import logging

from risk_calculator import RiskCalculator, Position
from blockchain_service import BlockchainService
from ai_predictor import AiPredictor

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
risk_calculator = RiskCalculator()
ai_predictor = AiPredictor()


class PortfolioRequest(BaseModel):
    wallet_address: str


class DefiPosition(BaseModel):
    protocol: str
    asset: str
    amount: float
    apy: float
    leverage: Optional[float] = None


class PortfolioAnalysis(BaseModel):
    total_value: float
    positions: List[DefiPosition]
    risk_level: str
    recommendations: List[str]
    market_analysis: Dict[str, Any]
    ai_predictions: Dict[str, Any]


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
        positions = await blockchain_service.get_all_positions(request.wallet_address)

        if not positions:
            raise HTTPException(status_code=404, detail="未找到DeFi存款")

        # 计算风险评估
        risk_assessment = risk_calculator.assess_portfolio_risk(positions)

        # 计算总存款价值
        total_value = 0
        for position in positions:
            asset_type = position.asset.split("/")[0]  # 处理LP token的情况
            asset_price = await blockchain_service.get_asset_price(asset_type)
            position_value = position.amount * asset_price
            total_value += position_value

        # 获取市场分析数据
        market_analysis = await get_market_analysis(positions)

        # 获取AI预测数据
        ai_predictions = {}
        for pos in positions:
            asset = pos.asset.split("/")[0]  # 处理LP token的情况
            if asset == "USDT":
                continue
            historical_data = await blockchain_service.get_asset_historical_data(asset)
            if not historical_data.empty:
                prediction = ai_predictor.analyze_market_trend(historical_data, asset)
                # 确保预测数据包含前端需要的字段
                if (
                    "predicted_price_range" in prediction
                    and "24h" in prediction["predicted_price_range"]
                ):
                    prediction["predicted_price"] = (
                        prediction["predicted_price_range"]["24h"][0]
                        + prediction["predicted_price_range"]["24h"][1]
                    ) / 2

                # 确保key_price_levels结构正确
                if "key_levels" in prediction and "key_price_levels" not in prediction:
                    prediction["key_price_levels"] = {
                        "support": prediction["key_levels"]["support"],
                        "resistance": prediction["key_levels"]["resistance"],
                    }

                # 确保signals字段存在
                if "trading_signals" in prediction and "signals" not in prediction:
                    prediction["signals"] = prediction["trading_signals"]

                ai_predictions[asset] = prediction

        # 转换为响应格式
        defi_positions = [
            DefiPosition(
                protocol=pos.protocol,
                asset=pos.asset,
                amount=pos.amount,
                apy=pos.apy or 0.0,
                leverage=pos.leverage,
            )
            for pos in positions
        ]

        # 构建并返回响应
        return PortfolioAnalysis(
            total_value=total_value,
            positions=defi_positions,
            risk_level=risk_assessment["risk_level"],
            recommendations=risk_assessment["recommendations"],
            market_analysis=market_analysis,
            ai_predictions=ai_predictions,
        )

    except Exception as e:
        logger.error(f"分析DeFi存款时出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 增加获取市场警报
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
        #     "0xAbCdEf123456789AbCdEf123456789AbCdEf1234"
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


# @app.get("/predict/protocol/{protocol_name}")
# async def predict_protocol_risk(protocol_name: str):
#     """分析DeFi协议风险"""
#     try:
#         protocol_data = {"name": protocol_name}
#         risk_analysis = ai_predictor.analyze_defi_protocol_risk(protocol_name)
#         return risk_analysis
#     except Exception as e:
#         logger.error(f"分析协议风险时出错: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


@app.get("/protocols")
async def get_supported_protocols():
    """获取支持的DeFi协议列表"""
    return {
        "protocols": [
            {
                "name": "Aave V3",
                "description": "去中心化借贷协议",
                "supported_assets": ["ETH", "USDC", "DAI", "BTC"],
                "features": ["存款", "借贷", "抵押"],
            },
            {
                "name": "Compound V3",
                "description": "去中心化借贷协议",
                "supported_assets": ["ETH", "USDC", "DAI"],
                "features": ["存款", "借贷"],
            },
            {
                "name": "Curve",
                "description": "稳定币交易协议",
                "supported_assets": ["USDC", "DAI", "USDT"],
                "features": ["流动性挖矿", "稳定币交换"],
            },
            {
                "name": "Uniswap V3",
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
                "name": "Yearn Finance",
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


async def get_market_analysis(positions: List[Position]) -> Dict[str, Any]:
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


if __name__ == "__main__":
    import uvicorn
    import asyncio
    from dotenv import load_dotenv

    # 加载环境变量
    load_dotenv()

    # 测试数据
    DEMO_ADDRESS = "0xAbCdEf123456789AbCdEf123456789AbCdEf1234"
    TEST_ASSETS = ["ETH", "USDC", "USDT", "BTC"]
    TEST_PROTOCOLS = ["Aave V3", "Compound V3", "Curve", "Uniswap V2"]

    async def test_api_endpoints():
        """测试主要API端点"""
        try:
            print("\n=== 测试API端点 ===\n")

            for asset in TEST_ASSETS:
                _get_24h_data = await blockchain_service._get_24h_data(asset)
                print(f"24h data for {asset}: {_get_24h_data}")
                price = await blockchain_service.get_asset_price(asset)
                print(f"Price for {asset}: {price}")

            # # 1. 测试分析DeFi存款
            # print("1. 测试分析DeFi存款")
            # portfolio_request = PortfolioRequest(wallet_address=DEMO_ADDRESS)
            # portfolio_analysis = await analyze_defi_deposits(portfolio_request)
            # print(f"总存款价值: ${portfolio_analysis.total_value:,.2f}")
            # print(f"风险等级: {portfolio_analysis.risk_level}")
            # print("-" * 50)

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
            #     print(f"风险评分: {risk_analysis['risk_score']}")
            #     print(f"风险等级: {risk_analysis['risk_level']}")
            #     print(f"安全评分: {risk_analysis['security_score']}")
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

    # 启动FastAPI服务器
    # print("\n启动FastAPI服务器...")
    # uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
