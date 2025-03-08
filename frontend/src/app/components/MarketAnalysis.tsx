"use client";

import React, { useState, useEffect } from "react";
import { apiService } from "../services/api";

interface MarketAnalysisProps {
  asset: string;
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ asset }) => {
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiService.getMarketAnalysis(asset);
        setAnalysis(data);
      } catch (err) {
        setError("获取市场分析数据失败");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    if (asset) {
      fetchAnalysis();
    }
  }, [asset]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">市场分析</h2>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">市场分析</h2>
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!analysis) {
    return null;
  }

  const getTrendColor = (trend: string) => {
    switch (trend.toLowerCase()) {
      case "bullish":
        return "text-green-600";
      case "bearish":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case "high":
        return "text-red-600";
      case "medium":
        return "text-yellow-600";
      case "low":
        return "text-green-600";
      default:
        return "text-gray-600";
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">市场分析 - {asset}</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold mb-2">价格信息</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">当前价格:</span>
                <span className="font-bold">${analysis.current_price.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">预测价格:</span>
                <span className="font-bold">${analysis.predicted_price.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">预期变化:</span>
                <span className={analysis.price_change_prediction >= 0 ? "text-green-600" : "text-red-600"}>{analysis.price_change_prediction.toFixed(2)}%</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-2">技术指标</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">波动率:</span>
                <span className="font-bold">{(analysis.volatility * 100).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">RSI:</span>
                <span className="font-bold">{analysis.rsi.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">趋势:</span>
                <span className={`font-bold ${getTrendColor(analysis.trend)}`}>{analysis.trend}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold mb-2">风险评估</h3>
            <div className="p-4 rounded-lg bg-gray-50">
              <div className="flex justify-between items-center mb-4">
                <span className="text-gray-600">风险等级:</span>
                <span className={`font-bold ${getRiskColor(analysis.risk_level)}`}>{analysis.risk_level}</span>
              </div>
              <div className="space-y-2">
                {analysis.signals.map((signal: string, index: number) => (
                  <div key={index} className="text-sm text-gray-600">
                    • {signal}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketAnalysis;
