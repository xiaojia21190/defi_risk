"use client";

import React, { useState } from "react";
import { MarketPrediction } from "../services/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Loader2, TrendingUp, TrendingDown, AlertTriangle, Info } from "lucide-react";

interface MarketAnalysisProps {
  asset: string;
  prediction?: MarketPrediction;
  marketAnalysis?: {
    current_price: number;
    volume_24h: number;
    market_cap: number;
    price_change_24h: number;
    volatility_30d: number;
  };
  aiPrediction?: {
    trend: string;
    trend_strength: string;
    risk_level: string;
    predicted_price_range: {
      "24h": [number, number];
      "7d": [number, number];
    };
    technical_analysis: {
      ma_trend: string;
      macd_signal: string;
      bollinger_signal: string;
      volume_analysis: string;
    };
    recommendations: string[];
    trading_signals: string[];
    key_levels?: {
      support: number[];
      resistance: number[];
      stop_loss?: number;
      take_profit?: number[];
    };
  };
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ asset, prediction, marketAnalysis, aiPrediction }) => {
  const [timeFrame, setTimeFrame] = useState<"24h" | "7d">("24h");

  if (!marketAnalysis || !aiPrediction) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 rounded-full bg-muted mx-auto mb-4 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
        <h3 className="text-lg font-medium mb-2">加载市场数据</h3>
        <p className="text-muted">正在获取 {asset} 的市场分析数据</p>
      </div>
    );
  }

  const getTrendColor = (trend: string) => {
    switch (trend.toLowerCase()) {
      case "bullish":
      case "看涨":
        return "text-success";
      case "bearish":
      case "看跌":
        return "text-destructive";
      case "neutral":
      case "中性":
        return "text-amber-500";
      default:
        return "text-muted";
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend.toLowerCase()) {
      case "bullish":
      case "看涨":
        return <TrendingUp className="h-4 w-4 text-success" />;
      case "bearish":
      case "看跌":
        return <TrendingDown className="h-4 w-4 text-destructive" />;
      default:
        return <Info className="h-4 w-4 text-amber-500" />;
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case "low":
      case "低":
        return "bg-success/10 text-success";
      case "medium":
      case "中":
        return "bg-amber-500/10 text-amber-500";
      case "high":
      case "高":
        return "bg-destructive/10 text-destructive";
      default:
        return "bg-muted text-muted-foreground";
    }
  };

  // 生成模拟价格图表数据
  const generateChartData = () => {
    const currentPrice = marketAnalysis.current_price;
    const predictedRange = aiPrediction.predicted_price_range[timeFrame];
    const midPoint = (predictedRange[0] + predictedRange[1]) / 2;

    // 生成7天或24小时的数据点
    const points = timeFrame === "7d" ? 7 : 24;
    const data = [];

    // 添加历史数据点
    for (let i = 0; i < points; i++) {
      const factor = Math.sin(i / (points / Math.PI)) * (marketAnalysis.volatility_30d / 100);
      const historicalPrice = currentPrice * (1 - factor * Math.random());
      data.push({
        time: timeFrame === "7d" ? `Day ${i + 1}` : `Hour ${i + 1}`,
        price: historicalPrice,
        type: "历史",
      });
    }

    // 添加预测数据点
    for (let i = 0; i < Math.floor(points / 3); i++) {
      const factor = (i / (points / 3)) * ((midPoint - currentPrice) / currentPrice);
      const predictedPrice = currentPrice * (1 + factor);
      data.push({
        time: timeFrame === "7d" ? `Day ${points + i + 1}` : `Hour ${points + i + 1}`,
        price: predictedPrice,
        type: "预测",
      });
    }

    return data;
  };

  const chartData = generateChartData();

  return (
    <div className="space-y-8">
      {/* 基本市场数据 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
          <h4 className="text-sm font-medium text-muted mb-2">当前价格</h4>
          <p className="text-2xl font-semibold">${marketAnalysis.current_price.toLocaleString()}</p>
          <span className={`text-sm ${marketAnalysis.price_change_24h > 0 ? "text-success" : "text-destructive"} flex items-center gap-1`}>
            {marketAnalysis.price_change_24h > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {marketAnalysis.price_change_24h > 0 ? "+" : ""}
            {marketAnalysis.price_change_24h.toFixed(2)}%
          </span>
        </div>
        <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
          <h4 className="text-sm font-medium text-muted mb-2">24h成交量</h4>
          <p className="text-2xl font-semibold">${(marketAnalysis.volume_24h / 1000000).toFixed(2)}M</p>
        </div>
        <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
          <h4 className="text-sm font-medium text-muted mb-2">市值</h4>
          <p className="text-2xl font-semibold">${(marketAnalysis.market_cap / 1000000000).toFixed(2)}B</p>
        </div>
        <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
          <h4 className="text-sm font-medium text-muted mb-2">30天波动率</h4>
          <p className="text-2xl font-semibold">{marketAnalysis.volatility_30d.toFixed(2)}%</p>
          <span className={`text-xs px-2 py-0.5 rounded-full ${getRiskColor(aiPrediction.risk_level)}`}>{aiPrediction.risk_level}风险</span>
        </div>
      </div>

      {/* 价格图表 */}
      <div className="p-6 rounded-lg bg-card border border-border hover:shadow-md transition-all">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">{asset} 价格走势</h3>
          <div className="flex gap-2">
            <button onClick={() => setTimeFrame("24h")} className={`px-3 py-1 text-sm rounded-lg transition-colors ${timeFrame === "24h" ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}>
              24小时
            </button>
            <button onClick={() => setTimeFrame("7d")} className={`px-3 py-1 text-sm rounded-lg transition-colors ${timeFrame === "7d" ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}>
              7天
            </button>
          </div>
        </div>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" opacity={0.1} />
              <XAxis dataKey="time" />
              <YAxis domain={["auto", "auto"]} />
              <Tooltip contentStyle={{ backgroundColor: "rgba(0, 0, 0, 0.8)", border: "none", borderRadius: "8px" }} itemStyle={{ color: "#fff" }} formatter={(value: number) => [`$${value.toFixed(2)}`, "价格"]} labelFormatter={(label) => `${label}`} />
              <Area type="monotone" dataKey="price" stroke="#8884d8" fillOpacity={1} fill="url(#colorPrice)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        {aiPrediction.key_levels && (
          <div className="mt-4 flex flex-wrap gap-3">
            {aiPrediction.key_levels.support.length > 0 && (
              <div className="text-sm">
                <span className="text-muted mr-2">支撑位:</span>
                {aiPrediction.key_levels.support.map((level, i) => (
                  <span key={i} className="px-2 py-1 bg-success/10 text-success rounded-lg mr-2">
                    ${level.toFixed(2)}
                  </span>
                ))}
              </div>
            )}
            {aiPrediction.key_levels.resistance.length > 0 && (
              <div className="text-sm">
                <span className="text-muted mr-2">阻力位:</span>
                {aiPrediction.key_levels.resistance.map((level, i) => (
                  <span key={i} className="px-2 py-1 bg-destructive/10 text-destructive rounded-lg mr-2">
                    ${level.toFixed(2)}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* AI预测分析 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-4">AI市场预测</h3>
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="font-medium">市场趋势</h4>
                  <span className={`px-2 py-1 text-sm rounded-full flex items-center gap-1 ${getTrendColor(aiPrediction.trend)} bg-card`}>
                    {getTrendIcon(aiPrediction.trend)}
                    {aiPrediction.trend_strength} {aiPrediction.trend}
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted">24h预测区间</span>
                    <span>
                      ${aiPrediction.predicted_price_range["24h"][0].toFixed(2)} - ${aiPrediction.predicted_price_range["24h"][1].toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted">7d预测区间</span>
                    <span>
                      ${aiPrediction.predicted_price_range["7d"][0].toFixed(2)} - ${aiPrediction.predicted_price_range["7d"][1].toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
                <h4 className="font-medium mb-3">技术指标</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">MA趋势</span>
                    <span className={getTrendColor(aiPrediction.technical_analysis.ma_trend)}>{aiPrediction.technical_analysis.ma_trend}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">MACD信号</span>
                    <span className={getTrendColor(aiPrediction.technical_analysis.macd_signal)}>{aiPrediction.technical_analysis.macd_signal}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">布林带位置</span>
                    <span>{aiPrediction.technical_analysis.bollinger_signal}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">成交量分析</span>
                    <span>{aiPrediction.technical_analysis.volume_analysis}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-medium mb-3">交易信号</h4>
            <div className="space-y-2">
              {aiPrediction.trading_signals.map((signal, index) => (
                <div key={index} className="p-3 rounded-lg bg-muted text-sm flex items-start gap-2">
                  <div className="mt-0.5">
                    {signal.toLowerCase().includes("买入") || signal.toLowerCase().includes("buy") ? (
                      <TrendingUp className="h-4 w-4 text-success" />
                    ) : signal.toLowerCase().includes("卖出") || signal.toLowerCase().includes("sell") ? (
                      <TrendingDown className="h-4 w-4 text-destructive" />
                    ) : (
                      <Info className="h-4 w-4 text-amber-500" />
                    )}
                  </div>
                  <span>{signal}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold mb-4">投资建议</h3>
          <div className="space-y-4">
            {aiPrediction.recommendations.map((recommendation, index) => (
              <div key={index} className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">{index + 1}</div>
                <p className="text-sm">{recommendation}</p>
              </div>
            ))}
          </div>

          {prediction && prediction.alerts && prediction.alerts.length > 0 && (
            <div className="mt-6">
              <h4 className="font-medium mb-3">市场警报</h4>
              <div className="space-y-3">
                {prediction.alerts.map((alert, index) => (
                  <div key={index} className="p-3 rounded-lg bg-destructive/10 text-sm flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
                    <span>{alert.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MarketAnalysis;
