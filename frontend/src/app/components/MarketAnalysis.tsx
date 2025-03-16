"use client";

import React, { useState } from "react";
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Loader2, TrendingUp, TrendingDown, AlertTriangle, Info, ArrowUpDown } from "lucide-react";
import type { MarketPrediction } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

interface MarketAnalysisProps {
  marketPredictions: { [key: string]: MarketPrediction };
  selectedAsset: string;
  onAssetChange: (asset: string) => void;
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({
  marketPredictions,
  selectedAsset,
  onAssetChange
}) => {
  const [timeFrame, setTimeFrame] = useState<"24h" | "7d">("24h");

  const prediction = marketPredictions[selectedAsset];
  const isLoading = !prediction;

  const getTrendColor = (trend: string) => {
    switch (trend?.toLowerCase()) {
      case "bullish":
      case "看涨":
        return "success";
      case "bearish":
      case "看跌":
        return "destructive";
      case "neutral":
      case "中性":
        return "warning";
      default:
        return "default";
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend?.toLowerCase()) {
      case "bullish":
      case "看涨":
        return <TrendingUp className="h-4 w-4" />;
      case "bearish":
      case "看跌":
        return <TrendingDown className="h-4 w-4" />;
      case "neutral":
      case "中性":
        return <ArrowUpDown className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk?.toLowerCase()) {
      case "high":
      case "高":
        return "destructive";
      case "medium":
      case "中":
        return "warning";
      case "low":
      case "低":
        return "success";
      default:
        return "default";
    }
  };

  const generateChartData = () => {
    if (!prediction) return [];

    // 生成模拟数据
    const data = [];
    const points = timeFrame === "24h" ? 24 : 7;
    const basePrice = 1000; // 默认基础价格
    const volatility = 0.05; // 默认波动率

    let lastPrice = basePrice;

    for (let i = 0; i < points; i++) {
      const change = (Math.random() - 0.5) * volatility * basePrice;
      lastPrice = Math.max(lastPrice + change, 0);

      data.push({
        time: timeFrame === "24h" ? `${i}:00` : `Day ${i+1}`,
        price: lastPrice,
      });
    }

    return data;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatLargeNumber = (value: number) => {
    if (value >= 1000000000) {
      return `${(value / 1000000000).toFixed(2)}B`;
    }
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(2)}M`;
    }
    if (value >= 1000) {
      return `${(value / 1000).toFixed(2)}K`;
    }
    return value.toString();
  };

  const chartData = generateChartData();

  // 获取预测价格范围
  const getPredictedPriceRange = () => {
    if (!prediction || !prediction.predicted_price_range) {
      return { min: 0, max: 0 };
    }

    const range = prediction.predicted_price_range[timeFrame as "24h" | "7d"];
    return { min: range[0], max: range[1] };
  };

  const priceRange = getPredictedPriceRange();

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>市场分析</CardTitle>
            <CardDescription>
              {selectedAsset} 市场趋势和预测
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <select
              value={selectedAsset}
              onChange={(e) => onAssetChange(e.target.value)}
              className="px-3 py-1 rounded-md border border-input bg-background text-sm"
            >
              {Object.keys(marketPredictions).map((asset) => (
                <option key={asset} value={asset}>
                  {asset}
                </option>
              ))}
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-10 w-10 text-primary animate-spin mb-4" />
            <p className="text-muted-foreground">加载市场数据中...</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg border bg-card/50">
                <div className="text-sm text-muted-foreground mb-1">预测趋势</div>
                <div className="flex items-center">
                  <Badge variant={getTrendColor(prediction.trend)}>
                    <span className="flex items-center gap-1">
                      {getTrendIcon(prediction.trend)}
                      {prediction.trend}
                    </span>
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground mt-2">
                  趋势强度: {prediction.trend_strength}
                </div>
              </div>

              <div className="p-4 rounded-lg border bg-card/50">
                <div className="text-sm text-muted-foreground mb-1">风险等级</div>
                <div className="flex items-center">
                  <Badge variant={getRiskColor(prediction.risk_level)}>
                    {prediction.risk_level}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground mt-2">
                  技术分析: {prediction.technical_analysis?.ma_trend || "未知"}
                </div>
              </div>

              <div className="p-4 rounded-lg border bg-card/50">
                <div className="text-sm text-muted-foreground mb-1">预测价格区间</div>
                <div className="text-sm font-medium">
                  {formatCurrency(priceRange.min)} - {formatCurrency(priceRange.max)}
                </div>
                <div className="text-xs text-muted-foreground mt-2">
                  时间范围: {timeFrame === "24h" ? "24小时" : "7天"}
                </div>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium">价格走势</h3>
                <div className="flex gap-2">
                  <Button
                    variant={timeFrame === "24h" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTimeFrame("24h")}
                  >
                    24小时
                  </Button>
                  <Button
                    variant={timeFrame === "7d" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTimeFrame("7d")}
                  >
                    7天
                  </Button>
                </div>
              </div>

              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={chartData}
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 12 }}
                      stroke="hsl(var(--muted-foreground))"
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      stroke="hsl(var(--muted-foreground))"
                      domain={['auto', 'auto']}
                      tickFormatter={(value) => `$${value.toFixed(0)}`}
                    />
                    <Tooltip
                      formatter={(value: number) => [`$${value.toFixed(2)}`, '价格']}
                      labelFormatter={(label) => `时间: ${label}`}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        borderColor: 'hsl(var(--border))',
                        borderRadius: 'var(--radius)',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="price"
                      stroke="hsl(var(--primary))"
                      fillOpacity={1}
                      fill="url(#colorPrice)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-medium mb-4">技术分析</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">MA趋势</span>
                    <span className="font-medium">{prediction.technical_analysis?.ma_trend || "未知"}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">MACD信号</span>
                    <span className="font-medium">{prediction.technical_analysis?.macd_signal || "未知"}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">布林带信号</span>
                    <span className="font-medium">{prediction.technical_analysis?.bollinger_signal || "未知"}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">成交量分析</span>
                    <span className="font-medium">{prediction.technical_analysis?.volume_analysis || "未知"}</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-4">交易信号</h3>
                <div className="p-4 rounded-lg border bg-card/50">
                  <div className="space-y-2">
                    {prediction.trading_signals && prediction.trading_signals.length > 0 ? (
                      prediction.trading_signals.map((signal, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <div className="min-w-4 mt-0.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                          </div>
                          <span className="text-sm">{signal}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无交易信号</p>
                    )}
                  </div>
                </div>

                {prediction.key_levels && (
                  <div className="mt-4 p-4 rounded-lg border bg-card/50">
                    <h4 className="text-sm font-medium mb-2">关键价格水平</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">支撑位: </span>
                        {prediction.key_levels.support.map((level, i) => (
                          <span key={i} className="font-medium">${level.toFixed(2)}{i < prediction.key_levels!.support.length - 1 ? ', ' : ''}</span>
                        ))}
                      </div>
                      <div>
                        <span className="text-muted-foreground">阻力位: </span>
                        {prediction.key_levels.resistance.map((level, i) => (
                          <span key={i} className="font-medium">${level.toFixed(2)}{i < prediction.key_levels!.resistance.length - 1 ? ', ' : ''}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {prediction.recommendations && prediction.recommendations.length > 0 && (
              <div>
                <h3 className="text-lg font-medium mb-4">建议</h3>
                <div className="p-4 rounded-lg border bg-card/50">
                  <ul className="space-y-2">
                    {prediction.recommendations.map((recommendation, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <div className="min-w-4 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        </div>
                        <span className="text-sm">{recommendation}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default MarketAnalysis;
