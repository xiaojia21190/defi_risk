"use client";

import React, { useState } from "react";
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Loader2, TrendingUp, TrendingDown, AlertTriangle, Info, ArrowUpDown } from "lucide-react";
import type { MarketPrediction, Portfolio } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// 扩展的市场预测数据接口，包含价格历史等前端展示所需的数据
interface ExtendedMarketPrediction extends MarketPrediction {
  asset: string;
  time_frame: string;
  price_history: {
    timestamp: { [key: string]: string };
    price: { [key: string]: number };
    volume: { [key: string]: number };
    market_cap: { [key: string]: number };
    source: { [key: string]: string };
  };
  predictions: Array<{
    target: string;
    timeframe: string;
    value: number;
    probability: number;
    range: [number, number];
  }>;
  insights: string[];
  timestamp: string;
  confidence: number;
}

interface MarketAnalysisProps {
  marketPredictions: { [key: string]: ExtendedMarketPrediction } | null;
  loading: boolean;
  onAssetSelect: (asset: string) => void;
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ marketPredictions, loading, onAssetSelect }) => {
  const [timeFrame, setTimeFrame] = useState<"24h" | "7d">("24h");
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");

  const prediction = marketPredictions?.[selectedAsset];
  const isLoading = loading || !prediction;

  const getTrendIcon = (priceChange: number) => {
    if (priceChange > 0) {
      return <TrendingUp className="w-4 h-4" />;
    } else if (priceChange < 0) {
      return <TrendingDown className="w-4 h-4" />;
    }
    return <ArrowUpDown className="w-4 h-4" />;
  };

  const generateChartData = () => {
    if (!prediction?.price_history) return [];

    const timestamps = Object.values(prediction.price_history.timestamp);
    const prices = Object.values(prediction.price_history.price);
    const volumes = Object.values(prediction.price_history.volume);

    return timestamps.map((timestamp, index) => ({
      time: new Date(timestamp).toLocaleString(),
      price: prices[index],
      volume: volumes[index],
    }));
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

  // 计算价格变化
  const calculatePriceChange = () => {
    if (!prediction?.price_history.price) return 0;
    const prices = Object.values(prediction.price_history.price);
    if (prices.length < 2) return 0;
    const currentPrice = prices[prices.length - 1];
    const previousPrice = prices[prices.length - 2];
    return ((currentPrice - previousPrice) / previousPrice) * 100;
  };

  const priceChange = calculatePriceChange();

  return (
    <Card className="relative w-full">
      <CardHeader>
        <div className="flex justify-between items-center">
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
              className="px-3 py-1 text-sm rounded-md border border-input bg-background"
            >
              <option value="ETH">ETH</option>
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col justify-center items-center py-12">
            <Loader2 className="mb-4 w-10 h-10 animate-spin text-primary" />
            <p className="text-muted-foreground">加载市场数据中...</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="p-4 rounded-lg border bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">价格趋势</div>
                <div className="flex items-center">
                  <Badge variant={priceChange > 0 ? "default" : priceChange < 0 ? "destructive" : "secondary"} className="flex gap-1 items-center">
                    <span className="flex gap-1 items-center">
                      {getTrendIcon(priceChange)}
                      {priceChange > 0 ? "看涨" : priceChange < 0 ? "看跌" : "中性"}
                    </span>
                  </Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">24h变化: {priceChange.toFixed(2)}%</div>
              </div>

              <div className="p-4 rounded-lg border bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">预测价格</div>
                <div className="flex items-center">
                  <Badge variant="default" className="flex gap-1 items-center">
                    <span className="flex gap-1 items-center">{formatCurrency(prediction?.predictions[0]?.value || 0)}</span>
                  </Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">置信度: {(prediction?.confidence * 100).toFixed(1)}%</div>
              </div>

              <div className="p-4 rounded-lg border bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">当前价格</div>
                <div className="text-sm font-medium">{formatCurrency(Object.values(prediction?.price_history.price || {}).pop() || 0)}</div>
                <div className="mt-2 text-xs text-muted-foreground">更新时间: {new Date(prediction?.timestamp || "").toLocaleString()}</div>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-4">
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
                      <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--secondary))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--secondary))" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                    <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
                    <YAxis yAxisId="left" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" domain={["auto", "auto"]} tickFormatter={(value) => `$${formatLargeNumber(value)}`} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" domain={["auto", "auto"]} tickFormatter={(value) => formatLargeNumber(value)} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--background))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "6px",
                      }}
                      labelStyle={{ color: "hsl(var(--foreground))" }}
                    />
                    <Area yAxisId="left" type="monotone" dataKey="price" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorPrice)" strokeWidth={2} />
                    <Area yAxisId="right" type="monotone" dataKey="volume" stroke="hsl(var(--secondary))" fillOpacity={1} fill="url(#colorVolume)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <h3 className="mb-4 text-lg font-medium">市场洞察</h3>
                <div className="p-4 rounded-lg border bg-card/50">
                  <div className="space-y-2">
                    {prediction?.insights && prediction.insights.length > 0 ? (
                      prediction.insights.map((insight, index) => (
                        <div key={index} className="flex gap-2 items-start">
                          <div className="min-w-4 mt-0.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                          </div>
                          <span className="text-sm">{insight}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无市场洞察</p>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <h3 className="mb-4 text-lg font-medium">投资建议</h3>
                <div className="p-4 rounded-lg border bg-card/50">
                  <div className="space-y-2">
                    {prediction?.recommendations && prediction.recommendations.length > 0 ? (
                      prediction.recommendations.map((recommendation, index) => (
                        <div key={index} className="flex gap-2 items-start">
                          <div className="min-w-4 mt-0.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                          </div>
                          <span className="text-sm">{recommendation}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无投资建议</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default MarketAnalysis;
