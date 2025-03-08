from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime

from risk_calculator import RiskCalculator, Position
from blockchain_service import BlockchainService
from ai_predictor import AiPredictor

app = FastAPI(title="DeFi Risk Monitor API")

# 配置 CORS
app.CORSMiddleware = CORSMiddleware
app.add_middleware(
    allow_origins=[
        "http://localhost:3000",  # 开发环境
        "http://127.0.0.1:3000",
        "https://your-production-domain.com",  # 生产环境
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
web3_provider = os.getenv(
    "WEB3_PROVIDER_URL", "https://eth-sepolia.g.alchemy.com/v2/8GHYFBqZcX9OEuKkgB1N3u1RDPBYy9Mm"
)
blockchain_service = BlockchainService(web3_provider)
risk_calculator = RiskCalculator()
ai_predictor = AiPredictor()


# 数据模型
class PortfolioRequest(BaseModel):
    wallet_address: str


class Alert(BaseModel):
    id: str
    type: str  # liquidation, impermanentLoss, marketVolatility
    severity: str  # high, medium, low
    message: str
    timestamp: str
    protocol: str
    asset: str


class RiskAssessmentResponse(BaseModel):
    risk_level: str
    liquidation_risk: float
    impermanent_loss_risk: float
    market_volatility_risk: float
    recommendations: List[str]
    timestamp: str


class MarketAnalysis(BaseModel):
    asset: str
    current_price: float
    predicted_price: float
    price_change_prediction: float
    volatility: float
    rsi: float
    trend: str
    risk_level: str
    signals: List[str]


@app.get("/")
async def root():
    return {"message": "DeFi Risk Monitor API"}


@app.post("/portfolio/analyze", response_model=RiskAssessmentResponse)
async def analyze_portfolio(request: PortfolioRequest):
    try:
        # 获取用户在各协议中的头寸
        positions = await blockchain_service.get_all_positions(request.wallet_address)

        if not positions:
            raise HTTPException(status_code=404, detail="No positions found")

        # 计算投资组合风险
        portfolio_risk = risk_calculator.assess_portfolio_risk(positions)

        return RiskAssessmentResponse(
            risk_level=portfolio_risk["risk_level"],
            liquidation_risk=portfolio_risk["liquidation_risk"],
            impermanent_loss_risk=portfolio_risk["impermanent_loss_risk"],
            market_volatility_risk=portfolio_risk["market_volatility_risk"],
            recommendations=portfolio_risk["recommendations"],
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/{address}", response_model=List[Alert])
async def get_user_alerts(address: str):
    try:
        # 获取链上警报
        chain_alerts = await blockchain_service.get_chain_alerts(address)

        # 获取风险计算器的警报
        risk_alerts = risk_calculator.get_active_alerts(address)

        # 获取 AI 预测的警报
        market_alerts = ai_predictor.get_market_alerts(address)

        # 合并所有警报
        all_alerts = []

        # 处理链上警报
        for alert in chain_alerts:
            all_alerts.append(
                Alert(
                    id=f"chain_{alert['timestamp']}",
                    type="liquidation",
                    severity="high" if float(alert["risk_level"]) > 0.7 else "medium",
                    message=f"清算风险警报: 风险等级 {float(alert['risk_level']):.2f}",
                    timestamp=datetime.fromtimestamp(
                        int(alert["timestamp"])
                    ).isoformat(),
                    protocol=alert["protocol"],
                    asset=alert["asset"],
                )
            )

        # 处理风险计算器警报
        for alert in risk_alerts:
            all_alerts.append(
                Alert(
                    id=f"risk_{alert['timestamp']}",
                    type=alert["type"],
                    severity=alert["severity"],
                    message=alert["message"],
                    timestamp=alert["timestamp"],
                    protocol=alert["protocol"],
                    asset=alert["asset"],
                )
            )

        # 处理市场预测警报
        for alert in market_alerts:
            all_alerts.append(
                Alert(
                    id=f"market_{alert['timestamp']}",
                    type="marketVolatility",
                    severity=alert["severity"],
                    message=alert["message"],
                    timestamp=alert["timestamp"],
                    protocol=alert["protocol"],
                    asset=alert["asset"],
                )
            )

        # 按时间戳排序，最新的在前
        all_alerts.sort(key=lambda x: x.timestamp, reverse=True)

        return all_alerts

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/market/analysis/{asset}", response_model=MarketAnalysis)
async def get_market_analysis(asset: str):
    try:
        # 获取历史数据
        historical_data = await blockchain_service.get_asset_historical_data(asset)

        if not historical_data.empty:
            # 进行市场分析
            analysis = ai_predictor.analyze_market_trend(historical_data, asset)
            signals = ai_predictor.generate_trading_signals(analysis, position_size=1.0)

            return MarketAnalysis(
                asset=analysis["asset"],
                current_price=analysis["current_price"],
                predicted_price=analysis["predicted_price"],
                price_change_prediction=analysis["price_change_prediction"],
                volatility=analysis["volatility"],
                rsi=analysis["rsi"],
                trend=analysis["trend"],
                risk_level=analysis["risk_level"],
                signals=signals,
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"No historical data found for {asset}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/protocols")
async def get_supported_protocols():
    return {
        "protocols": [
            {
                "name": "Aave",
                "version": "V2",
                "supported_assets": ["ETH", "USDC", "DAI", "WBTC"],
                "features": ["lending", "borrowing"],
            },
            {
                "name": "Uniswap",
                "version": "V2",
                "supported_assets": ["ETH", "USDC", "DAI", "WBTC"],
                "features": ["liquidity", "swapping"],
            },
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
