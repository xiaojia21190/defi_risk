"use client";

import React, { useState } from "react";
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Loader2, TrendingUp, TrendingDown, AlertTriangle, Info, ArrowUpDown } from "lucide-react";
import type { MarketPrediction, Portfolio } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface MarketAnalysisProps {
  portfolio: Portfolio | null;
  marketPredictions: { [key: string]: MarketPrediction };
  loading: boolean;
  onAssetSelect: (asset: string) => void;
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ portfolio, marketPredictions, loading, onAssetSelect }) => {
  const [timeFrame, setTimeFrame] = useState<"24h" | "7d">("24h");
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");

  const prediction = marketPredictions[selectedAsset];
  const isLoading = loading || !prediction;

  const getTrendIcon = (trend: string) => {
    switch (trend?.toLowerCase()) {
      case "bullish":
      case "看涨":
        return <TrendingUp className="w-4 h-4" />;
      case "bearish":
      case "看跌":
        return <TrendingDown className="w-4 h-4" />;
      case "neutral":
      case "中性":
        return <ArrowUpDown className="w-4 h-4" />;
      default:
        return <Info className="w-4 h-4" />;
    }
  };

  const generateChartData = () => {
    if (!prediction) return [];

    const data = [];
    const points = timeFrame === "24h" ? 24 : 7;
    const priceRange = prediction.predicted_price_range?.[timeFrame] || [1000, 1100];
    const currentPrice = priceRange[0];
    const volatility = 0.02; // 使用固定的波动率
    const trend = prediction.trend?.toLowerCase() === "看涨" ? 1 : prediction.trend?.toLowerCase() === "看跌" ? -1 : 0;

    let lastPrice = currentPrice;
    const targetPrice = trend === 1 ? priceRange[1] : trend === -1 ? priceRange[0] : currentPrice;

    for (let i = 0; i < points; i++) {
      const progress = i / (points - 1);
      const trendComponent = (targetPrice - currentPrice) * progress;
      const randomComponent = (Math.random() - 0.5) * volatility * currentPrice;
      lastPrice = Math.max(currentPrice + trendComponent + randomComponent, 0);

      data.push({
        time: timeFrame === "24h" ? `${i}:00` : `Day ${i + 1}`,
        price: parseFloat(lastPrice.toFixed(2)),
      });
    }

    return data;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("zh-CN", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
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
    <Card className="relative w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>市场分析</CardTitle>
            <CardDescription>{selectedAsset} 市场趋势和预测</CardDescription>
          </div>
          <div className="flex gap-2">
            <select
              value={selectedAsset}
              onChange={(e) => {
                setSelectedAsset(e.target.value);
                onAssetSelect(e.target.value);
              }}
              className="px-3 py-1 text-sm border rounded-md border-input bg-background"
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
            <Loader2 className="w-10 h-10 mb-4 text-primary animate-spin" />
            <p className="text-muted-foreground">加载市场数据中...</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="p-4 border rounded-lg bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">预测趋势</div>
                <div className="flex items-center">
                  <Badge variant={prediction.trend?.toLowerCase() === "bullish" || prediction.trend?.toLowerCase() === "看涨" ? "default" : prediction.trend?.toLowerCase() === "bearish" || prediction.trend?.toLowerCase() === "看跌" ? "destructive" : "secondary"} className="flex items-center gap-1">
                    <span className="flex items-center gap-1">
                      {getTrendIcon(prediction.trend)}
                      {prediction.trend}
                    </span>
                  </Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">趋势强度: {prediction.trend_strength}</div>
              </div>

              <div className="p-4 border rounded-lg bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">风险等级</div>
                <div className="flex items-center">
                  <Badge variant={prediction.risk_level?.toLowerCase() === "high" || prediction.risk_level?.toLowerCase() === "高" ? "destructive" : prediction.risk_level?.toLowerCase() === "medium" || prediction.risk_level?.toLowerCase() === "中" ? "secondary" : "default"}>
                    {prediction.risk_level}
                  </Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">技术分析: {prediction.technical_analysis?.ma_trend || "未知"}</div>
              </div>

              <div className="p-4 border rounded-lg bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">预测价格区间</div>
                <div className="text-sm font-medium">
                  {formatCurrency(priceRange.min)} - {formatCurrency(priceRange.max)}
                </div>
                <div className="mt-2 text-xs text-muted-foreground">时间范围: {timeFrame === "24h" ? "24小时" : "7天"}</div>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium">价格走势</h3>
                <div className="flex gap-2">
                  <Button variant={timeFrame === "24h" ? "default" : "outline"} size="sm" onClick={() => setTimeFrame("24h")}>
                    24小时
                  </Button>
                  <Button variant={timeFrame === "7d" ? "default" : "outline"} size="sm" onClick={() => setTimeFrame("7d")}>
                    7天
                  </Button>
                </div>
              </div>

              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                    <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" domain={["auto", "auto"]} tickFormatter={(value) => `$${formatLargeNumber(value)}`} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--background))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "6px",
                      }}
                      labelStyle={{ color: "hsl(var(--foreground))" }}
                    />
                    <Area type="monotone" dataKey="price" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorPrice)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <h3 className="mb-4 text-lg font-medium">技术分析</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">MA趋势</span>
                    <span className="font-medium">{prediction.technical_analysis?.ma_trend || "未知"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">MACD信号</span>
                    <span className="font-medium">{prediction.technical_analysis?.macd_signal || "未知"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">布林带信号</span>
                    <span className="font-medium">{prediction.technical_analysis?.bollinger_signal || "未知"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">成交量分析</span>
                    <span className="font-medium">{prediction.technical_analysis?.volume_analysis || "未知"}</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="mb-4 text-lg font-medium">交易信号</h3>
                <div className="p-4 border rounded-lg bg-card/50">
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
                  <div className="p-4 mt-4 border rounded-lg bg-card/50">
                    <h4 className="mb-2 text-sm font-medium">关键价格水平</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">支撑位: </span>
                        {prediction.key_levels.support.map((level, i) => (
                          <span key={i} className="font-medium">
                            ${level.toFixed(2)}
                            {i < prediction.key_levels!.support.length - 1 ? ", " : ""}
                          </span>
                        ))}
                      </div>
                      <div>
                        <span className="text-muted-foreground">阻力位: </span>
                        {prediction.key_levels.resistance.map((level, i) => (
                          <span key={i} className="font-medium">
                            ${level.toFixed(2)}
                            {i < prediction.key_levels!.resistance.length - 1 ? ", " : ""}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {prediction.recommendations && prediction.recommendations.length > 0 && (
              <div>
                <h3 className="mb-4 text-lg font-medium">建议</h3>
                <div className="p-4 border rounded-lg bg-card/50">
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
