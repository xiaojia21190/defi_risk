"use client";

import React from "react";
import { MarketPrediction } from "../services/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

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
  };
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ asset, prediction, marketAnalysis, aiPrediction }) => {
  if (!marketAnalysis || !aiPrediction) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 rounded-full bg-muted mx-auto mb-4 flex items-center justify-center">
          <span className="text-2xl">📊</span>
        </div>
        <h3 className="text-lg font-medium mb-2">暂无市场数据</h3>
        <p className="text-muted">无法获取 {asset} 的市场分析数据</p>
      </div>
    );
  }

  const getTrendColor = (trend: string) => {
    switch (trend.toLowerCase()) {
      case "bullish":
        return "text-success";
      case "bearish":
        return "text-destructive";
      default:
        return "text-muted";
    }
  };

  return (
    <div className="space-y-8">
      {/* 基本市场数据 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-card border border-border">
          <h4 className="text-sm font-medium text-muted mb-2">当前价格</h4>
          <p className="text-2xl font-semibold">${marketAnalysis.current_price.toLocaleString()}</p>
          <span className={`text-sm ${marketAnalysis.price_change_24h > 0 ? "text-success" : "text-destructive"}`}>
            {marketAnalysis.price_change_24h > 0 ? "+" : ""}
            {marketAnalysis.price_change_24h.toFixed(2)}%
          </span>
        </div>
        <div className="p-4 rounded-lg bg-card border border-border">
          <h4 className="text-sm font-medium text-muted mb-2">24h成交量</h4>
          <p className="text-2xl font-semibold">${(marketAnalysis.volume_24h / 1000000).toFixed(2)}M</p>
        </div>
        <div className="p-4 rounded-lg bg-card border border-border">
          <h4 className="text-sm font-medium text-muted mb-2">市值</h4>
          <p className="text-2xl font-semibold">${(marketAnalysis.market_cap / 1000000000).toFixed(2)}B</p>
        </div>
        <div className="p-4 rounded-lg bg-card border border-border">
          <h4 className="text-sm font-medium text-muted mb-2">30天波动率</h4>
          <p className="text-2xl font-semibold">{marketAnalysis.volatility_30d.toFixed(2)}%</p>
        </div>
      </div>

      {/* AI预测分析 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-4">AI市场预测</h3>
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-card border border-border">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="font-medium">市场趋势</h4>
                  <span className={`px-2 py-1 text-sm rounded-full ${getTrendColor(aiPrediction.trend)} bg-card`}>
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

              <div className="p-4 rounded-lg bg-card border border-border">
                <h4 className="font-medium mb-3">技术指标</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">MA趋势</span>
                    <span>{aiPrediction.technical_analysis.ma_trend}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">MACD信号</span>
                    <span>{aiPrediction.technical_analysis.macd_signal}</span>
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
                <div key={index} className="p-2 rounded bg-muted text-sm">
                  {signal}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold mb-4">投资建议</h3>
          <div className="space-y-4">
            {aiPrediction.recommendations.map((recommendation, index) => (
              <div key={index} className="p-4 rounded-lg bg-card border border-border flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">{index + 1}</div>
                <p className="text-sm">{recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketAnalysis;
