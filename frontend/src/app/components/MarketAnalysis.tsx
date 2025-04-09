"use client";

import React, { useState, useEffect } from "react";
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Loader2, TrendingUp, TrendingDown, AlertTriangle, Info, ArrowUpDown } from "lucide-react";
import type { MarketPrediction, Portfolio } from "../services/api";
import { apiService } from "../services/api";
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
  recommendations: string[];
  timestamp: string;
  confidence: number;
}

interface MarketAnalysisProps {
  portfolio: Portfolio | null;
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ portfolio }) => {
  const [timeFrame, setTimeFrame] = useState<"24h" | "7d" | "30d">("24h");
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");
  const [marketPredictions, setMarketPredictions] = useState<{ [key: string]: ExtendedMarketPrediction } | null>(null);
  const [loadingMarketData, setLoadingMarketData] = useState(false);

  const prediction = marketPredictions?.[selectedAsset];
  const isLoading = loadingMarketData || !prediction;

  // 获取市场分析数据
  const fetchMarketData = async (asset: string) => {
    try {
      setLoadingMarketData(true);

      // 判断是否是特定资产的测试数据

      // 调用市场预测API
      const prediction = await apiService.predictMarket(asset, "24h");

      // 扩展市场预测数据
      const extendedPrediction = {
        ...prediction,
        asset,
        time_frame: "24h",
        price_history: prediction.price_history || {
          timestamp: { "1": new Date().toISOString(), "2": new Date(Date.now() - 86400000).toISOString() },
          price: { "1": 1800, "2": 1750 }, // 示例数据，实际应从API获取
          volume: { "1": 3000000, "2": 2800000 },
          market_cap: { "1": 200000000, "2": 195000000 },
          source: { "1": "api", "2": "api" },
        },
        predictions: prediction.predictions || [
          {
            target: "price",
            timeframe: "24h",
            value: prediction.predicted_price_range["24h"][1],
            probability: 0.8,
            range: prediction.predicted_price_range["24h"],
          },
        ],
        insights: prediction.insights || prediction.recommendations || [],
        recommendations: prediction.recommendations || [],
        timestamp: prediction.timestamp || new Date().toISOString(),
        confidence: prediction.confidence || 0.75,
      };

      setMarketPredictions((prev) => ({
        ...prev,
        [asset]: extendedPrediction,
      }));
    } catch (error) {
      console.error("获取市场分析数据失败:", error);
    } finally {
      setLoadingMarketData(false);
    }
  };

  // 处理资产选择
  const handleAssetSelect = (asset: string) => {
    setSelectedAsset(asset);
    if (!marketPredictions?.[asset]) {
      fetchMarketData(asset);
    }
  };

  // 当portfolio变化时，自动选择第一个可用资产并获取数据
  useEffect(() => {
    if (portfolio && portfolio.positions && portfolio.positions.length > 0) {
      const uniqueAssets = [...new Set(portfolio.positions.map((position) => position.asset))];
      if (uniqueAssets.length > 0) {
        const newAsset = uniqueAssets[0];
        setSelectedAsset(newAsset);
        fetchMarketData(newAsset);
      }
    }
  }, [portfolio]);

  // 当选择的资产变化时，获取数据
  useEffect(() => {
    if (selectedAsset && !marketPredictions?.[selectedAsset]) {
      fetchMarketData(selectedAsset);
    }
  }, [selectedAsset]);

  // 获取可用资产列表
  const getAssetOptions = () => {
    if (portfolio && portfolio.positions && portfolio.positions.length > 0) {
      // 从portfolio中提取不重复的资产
      const uniqueAssets = [...new Set(portfolio.positions.map((position) => position.asset))];
      return uniqueAssets.map((asset) => (
        <option key={asset} value={asset}>
          {asset}
        </option>
      ));
    }
    // 默认选项，当portfolio不可用时
    return [
      <option key="ETH" value="ETH">
        ETH
      </option>,
      <option key="BTC" value="BTC">
        BTC
      </option>,
      <option key="USDC" value="USDC">
        USDC
      </option>,
    ];
  };

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

    // 根据选择的时间范围过滤数据
    let filteredData = timestamps.map((timestamp, index) => ({
      time: new Date(timestamp).toLocaleString(),
      price: prices[index],
      volume: volumes[index],
      rawTimestamp: new Date(timestamp).getTime(),
    }));

    // 根据timeFrame进行过滤
    if (timeFrame === "24h") {
      // 最近24小时的数据，取最后一天的数据
      const oneDayMs = 24 * 60 * 60 * 1000;
      const latestTime = Math.max(...filteredData.map((d) => d.rawTimestamp));
      filteredData = filteredData.filter((d) => d.rawTimestamp >= latestTime - oneDayMs);
    }
    // 7d 时显示所有数据

    return filteredData;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("zh-CN", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 5,
      maximumFractionDigits: 5,
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

    // 获取最新价格和前一天的价格用于计算24小时变化
    const currentPrice = prices[prices.length - 1];

    // 计算24小时前的价格
    let previousPriceIndex = prices.length - 1;
    if (timeFrame === "24h") {
      // 尝试找到接近24小时前的价格点
      const timestamps = Object.values(prediction.price_history.timestamp);
      const latestTime = new Date(timestamps[timestamps.length - 1]).getTime();
      const oneDayMs = 24 * 60 * 60 * 1000;
      const targetTime = latestTime - oneDayMs;

      // 寻找最接近目标时间的价格点
      let closestTimeDiff = Infinity;
      for (let i = 0; i < timestamps.length; i++) {
        const timeDiff = Math.abs(new Date(timestamps[i]).getTime() - targetTime);
        if (timeDiff < closestTimeDiff) {
          closestTimeDiff = timeDiff;
          previousPriceIndex = i;
        }
      }
    } else {
      // 7天模式，对比第一个和最后一个价格
      previousPriceIndex = 0;
    }

    const previousPrice = prices[previousPriceIndex];
    return ((currentPrice - previousPrice) / previousPrice) * 100;
  };

  const priceChange = calculatePriceChange();

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
                handleAssetSelect(e.target.value);
              }}
              className="px-3 py-1 text-sm border rounded-md border-input bg-background"
            >
              {getAssetOptions()}
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-10 h-10 mb-4 animate-spin text-primary" />
            <p className="text-muted-foreground">加载市场数据中...</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="p-4 border rounded-lg bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">价格趋势</div>
                <div className="flex items-center">
                  <Badge variant={priceChange > 0 ? "default" : priceChange < 0 ? "destructive" : "secondary"} className="flex items-center gap-1">
                    <span className="flex items-center gap-1">
                      {getTrendIcon(priceChange)}
                      {priceChange > 0 ? "看涨" : priceChange < 0 ? "看跌" : "中性"}
                    </span>
                  </Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">24h变化: {priceChange.toFixed(2)}%</div>
              </div>

              <div className="p-4 border rounded-lg bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">预测价格</div>
                <div className="flex items-center">
                  <Badge variant="default" className="flex items-center gap-1">
                    <span className="flex items-center gap-1">{formatCurrency(prediction?.predictions.find((p) => p.timeframe === timeFrame)?.value || prediction?.predictions[0]?.value || 0)}</span>
                  </Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  置信度: {(prediction?.confidence * 100).toFixed(1)}%{prediction?.predictions.find((p) => p.timeframe === timeFrame)?.probability && ` (概率: ${(prediction?.predictions.find((p) => p.timeframe === timeFrame)?.probability || 0) * 100}%)`}
                </div>
              </div>

              <div className="p-4 border rounded-lg bg-card/50">
                <div className="mb-1 text-sm text-muted-foreground">当前价格</div>
                <div className="text-sm font-medium">{formatCurrency(Object.values(prediction?.price_history.price || {}).pop() || 0)}</div>
                <div className="mt-2 text-xs text-muted-foreground">更新时间: {new Date(prediction?.timestamp || "").toLocaleString()}</div>
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
                  <Button variant={timeFrame === "30d" ? "default" : "outline"} size="sm" onClick={() => setTimeFrame("30d")}>
                    30天
                  </Button>
                </div>
              </div>

              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.1} />
                      </linearGradient>
                      <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--secondary))" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="hsl(var(--secondary))" stopOpacity={0.1} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                    <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
                    <YAxis yAxisId="left" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" domain={["auto", "auto"]} tickFormatter={(value) => `$${formatLargeNumber(value)}`} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" domain={["auto", "auto"]} tickFormatter={(value) => formatLargeNumber(value)} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--background))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
                        padding: "10px",
                      }}
                      labelStyle={{ color: "hsl(var(--foreground))", fontWeight: "bold", marginBottom: "8px" }}
                      formatter={(value, name) => {
                        if (name === "price") return [`$${Number(value).toFixed(2)}`, "价格"];
                        if (name === "volume") return [formatLargeNumber(Number(value)), "交易量"];
                        return [value, name];
                      }}
                    />
                    <Area yAxisId="left" type="monotone" dataKey="price" stroke="hsl(var(--primary))" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" activeDot={{ r: 6, strokeWidth: 2, stroke: "white" }} />
                    <Area yAxisId="right" type="monotone" dataKey="volume" stroke="hsl(var(--secondary))" strokeWidth={1.5} fillOpacity={1} fill="url(#colorVolume)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <h3 className="mb-4 text-lg font-medium">市场洞察</h3>
                <div className="p-4 border rounded-lg bg-card/50">
                  <div className="space-y-2">
                    {prediction?.insights && prediction.insights.length > 0 ? (
                      prediction.insights.map((insight, index) => (
                        <div key={index} className="flex items-start gap-2">
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
                <div className="p-4 border rounded-lg bg-card/50">
                  <div className="space-y-2">
                    {prediction?.recommendations && prediction.recommendations.length > 0 ? (
                      prediction.recommendations.map((recommendation, index) => (
                        <div key={index} className="flex items-start gap-2">
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
