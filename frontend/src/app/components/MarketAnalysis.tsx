"use client";

import React, { useState, useEffect, memo } from "react";
import { XAxis, YAxis, CartesianGrid, ResponsiveContainer, AreaChart, Area, Tooltip as RechartsTooltip } from "recharts";
import { motion } from "framer-motion";
import { Loader2, TrendingUp, TrendingDown, ArrowUpDown, RefreshCw } from "lucide-react";
import type { MarketPrediction, Portfolio } from "../services/api";
import { apiService } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// 创建自定义Skeleton组件
const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => {
  return <div className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />;
};

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

// 价格卡片组件
interface PriceCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  animate?: boolean;
  delay?: number;
  className?: string;
}

const PriceCard = memo(({ title, value, subtitle, icon, trend, animate = true, delay = 0, className }: PriceCardProps) => {
  const getTrendColor = () => {
    if (trend === "up") return "bg-green-500/10 text-green-600 dark:text-green-400";
    if (trend === "down") return "bg-red-500/10 text-red-600 dark:text-red-400";
    return "bg-blue-500/10 text-blue-600 dark:text-blue-400";
  };

  const getTrendIcon = () => {
    if (trend === "up") return <TrendingUp className="w-4 h-4" />;
    if (trend === "down") return <TrendingDown className="w-4 h-4" />;
    return icon || <ArrowUpDown className="w-4 h-4" />;
  };

  return (
    <motion.div
      initial={animate ? { opacity: 0, y: 20 } : false}
      animate={animate ? { opacity: 1, y: 0 } : false}
      transition={{ duration: 0.4, delay: delay }}
      className={cn("relative p-4 overflow-hidden border rounded-lg transition-all duration-300", "bg-gradient-to-b from-card/50 to-card", "hover:shadow-md group backdrop-blur-sm", className)}
    >
      <div className="absolute top-0 right-0 w-24 h-24 -mt-8 -mr-8 transition-opacity duration-500 rounded-full opacity-5 bg-gradient-to-br from-blue-300 to-purple-600 blur-2xl group-hover:opacity-10"></div>

      <div className="mb-1 text-sm text-muted-foreground">{title}</div>
      <div className="flex items-center space-x-2">
        <div className={cn("text-base font-semibold", typeof value === "string" ? "font-mono" : "")}>{value}</div>
        {trend && (
          <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 200, delay: delay + 0.1 }}>
            <Badge variant="outline" className={cn("flex items-center gap-1 px-1.5 py-0", getTrendColor())}>
              {getTrendIcon()}
            </Badge>
          </motion.div>
        )}
      </div>
      <div className="mt-1 text-xs text-muted-foreground">{subtitle}</div>
    </motion.div>
  );
});
PriceCard.displayName = "PriceCard";

// 见解卡片组件
interface InsightCardProps {
  title: string;
  items: string[];
  delay?: number;
  className?: string;
  emptyMessage?: string;
}

const InsightCard = memo(({ title, items, delay = 0, className, emptyMessage = "暂无数据" }: InsightCardProps) => {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay }} className="space-y-2">
      <h3 className="mb-2 text-lg font-medium">{title}</h3>
      <div className={cn("p-4 border rounded-lg bg-gradient-to-b from-card/50 to-card backdrop-blur-sm", "transition-all duration-300 hover:shadow-md", className)}>
        <div className="space-y-2">
          {items && items.length > 0 ? (
            items.map((item, index) => (
              <motion.div key={index} className="flex items-start gap-2" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3, delay: delay + index * 0.05 }}>
                <motion.div className="min-w-4 mt-0.5" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300, delay: delay + index * 0.05 + 0.1 }}>
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                </motion.div>
                <span className="text-sm">{item}</span>
              </motion.div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">{emptyMessage}</p>
          )}
        </div>
      </div>
    </motion.div>
  );
});
InsightCard.displayName = "InsightCard";

// 图表骨架加载状态
const ChartSkeleton = () => (
  <div className="space-y-2 animate-pulse">
    <div className="flex items-center justify-between mb-4">
      <div className="w-24 h-6 rounded-md bg-muted"></div>
      <div className="flex gap-2">
        <div className="w-20 h-8 rounded-md bg-muted"></div>
        <div className="w-20 h-8 rounded-md bg-muted"></div>
        <div className="w-20 h-8 rounded-md bg-muted"></div>
      </div>
    </div>
    <div className="h-[300px] w-full bg-muted/50 rounded-lg border border-muted"></div>
  </div>
);

interface MarketAnalysisProps {
  portfolio: Portfolio | null;
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ portfolio }) => {
  const [timeFrame, setTimeFrame] = useState<"24h" | "7d" | "30d">("24h");
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");
  const [marketPredictions, setMarketPredictions] = useState<{ [key: string]: ExtendedMarketPrediction } | null>(null);
  const [loadingMarketData, setLoadingMarketData] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const prediction = marketPredictions?.[selectedAsset];
  const isLoading = loadingMarketData || !prediction;

  // 获取市场分析数据
  const fetchMarketData = async (asset: string) => {
    try {
      setLoadingMarketData(true);

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

  // 刷新市场数据
  const refreshMarketData = async () => {
    if (refreshing) return;

    setRefreshing(true);
    await fetchMarketData(selectedAsset);
    setRefreshing(false);
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
      return uniqueAssets;
    }
    // 默认选项，当portfolio不可用时
    return ["ETH", "BTC", "USDC"];
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

  // 计算历史价格变化
  const calculatePriceChange = () => {
    // 检查必要的数据是否存在
    if (!prediction?.price_history.price || !prediction?.price_history.timestamp) return 0;

    const prices = Object.values(prediction.price_history.price);
    const timestamps = Object.values(prediction.price_history.timestamp);

    // 确保有足够的数据点进行比较
    if (prices.length < 2 || timestamps.length < 2) return 0;

    // 将价格和时间戳配对并按时间排序（从旧到新）
    const priceTimestampPairs = timestamps
      .map((timestamp, index) => ({
        price: prices[index],
        time: new Date(timestamp).getTime(),
      }))
      .sort((a, b) => a.time - b.time);

    // 获取最新价格（排序后数组的最后一个元素）
    const currentPrice = priceTimestampPairs[priceTimestampPairs.length - 1].price;

    let previousPrice;

    if (timeFrame === "24h") {
      // 对于24小时时间段，查找最接近24小时前的价格点
      const latestTime = priceTimestampPairs[priceTimestampPairs.length - 1].time;
      const oneDayMs = 24 * 60 * 60 * 1000;
      const targetTime = latestTime - oneDayMs;

      // 寻找最接近目标时间的价格点
      let closestPair = priceTimestampPairs[0];
      let closestTimeDiff = Math.abs(closestPair.time - targetTime);

      for (let i = 1; i < priceTimestampPairs.length - 1; i++) {
        const timeDiff = Math.abs(priceTimestampPairs[i].time - targetTime);
        if (timeDiff < closestTimeDiff) {
          closestTimeDiff = timeDiff;
          closestPair = priceTimestampPairs[i];
        }
      }

      previousPrice = closestPair.price;
    } else {
      // 7天或30天模式，使用最早的价格点作为对比基准
      previousPrice = priceTimestampPairs[0].price;
    }

    // 计算百分比变化
    return ((currentPrice - previousPrice) / previousPrice) * 100;
  };

  // 根据预测价格与当前价格比较计算趋势
  const calculatePredictionTrend = (): "up" | "down" | "neutral" => {
    // 检查必要的数据是否存在
    if (!prediction?.predictions || !prediction?.price_history?.price) return "neutral";

    // 获取当前价格
    const currentPrice = Object.values(prediction.price_history.price).pop() || 0;

    // 获取当前选择的timeFrame对应的预测价格
    const predictedPrice = prediction.predictions.find((p) => p.timeframe === timeFrame)?.value || prediction.predictions[0]?.value || 0;

    // 忽略极小的差异 (小于0.1%)
    const diffPercentage = ((predictedPrice - currentPrice) / currentPrice) * 100;
    if (Math.abs(diffPercentage) < 0.1) return "neutral";

    // 返回趋势方向
    return predictedPrice > currentPrice ? "up" : "down";
  };

  const priceChange = calculatePriceChange();
  const priceChangeFormatted = priceChange.toFixed(2);
  const priceChangeTrend = priceChange > 0 ? "up" : priceChange < 0 ? "down" : "neutral";

  // 基于预测的趋势
  const predictionTrend = calculatePredictionTrend();

  // 计算预测与当前价格的差异百分比
  const getPredictionDiffPercentage = () => {
    if (!prediction?.predictions || !prediction?.price_history?.price) return 0;

    const currentPrice = Object.values(prediction.price_history.price).pop() || 0;
    const predictedPrice = prediction.predictions.find((p) => p.timeframe === timeFrame)?.value || prediction.predictions[0]?.value || 0;

    return ((predictedPrice - currentPrice) / currentPrice) * 100;
  };

  const predictionDiffPercentage = getPredictionDiffPercentage().toFixed(2);

  // 获取更友好的趋势文本
  const getTrendText = (trend: "up" | "down" | "neutral") => {
    switch (trend) {
      case "up":
        return "看涨";
      case "down":
        return "看跌";
      default:
        return "中性";
    }
  };

  // 渲染加载状态
  const renderLoading = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="w-full h-24" />
        ))}
      </div>
      <ChartSkeleton />
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="space-y-2">
          <Skeleton className="w-40 h-8 mb-4" />
          <Skeleton className="w-full h-40" />
        </div>
        <div className="space-y-2">
          <Skeleton className="w-40 h-8 mb-4" />
          <Skeleton className="w-full h-40" />
        </div>
      </div>
    </div>
  );

  return (
    <Card className="relative w-full overflow-hidden border">
      <div className="absolute inset-0 opacity-50 bg-gradient-to-br from-blue-50/40 via-transparent to-purple-50/40 dark:from-blue-950/20 dark:to-purple-950/20"></div>

      <CardHeader className="relative">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              市场分析
              <Button variant="ghost" size="icon" onClick={refreshMarketData} disabled={refreshing || isLoading} className="w-6 h-6 rounded-full">
                <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
              </Button>
            </CardTitle>
            <CardDescription>{selectedAsset} 市场趋势和预测</CardDescription>
          </div>
          <div className="flex gap-2">
            <select value={selectedAsset} onChange={(e) => handleAssetSelect(e.target.value)} className="px-3 py-1 text-sm transition-colors border rounded-md shadow-sm border-input bg-background/80 backdrop-blur-sm hover:bg-background/90">
              {getAssetOptions().map((asset) => (
                <option key={asset} value={asset}>
                  {asset}
                </option>
              ))}
            </select>
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative">
        {isLoading ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="py-2">
            {renderLoading()}
          </motion.div>
        ) : (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <PriceCard title="预测趋势" value={getTrendText(predictionTrend)} subtitle={`${timeFrame}预测差异: ${predictionDiffPercentage}%`} trend={predictionTrend} delay={0.1} />

              <PriceCard title="预测价格" value={formatCurrency(prediction?.predictions.find((p) => p.timeframe === timeFrame)?.value || prediction?.predictions[0]?.value || 0)} subtitle={`置信度: ${(prediction?.confidence * 100).toFixed(1)}%`} trend={predictionTrend} delay={0.2} />

              <PriceCard title="当前价格" value={formatCurrency(Object.values(prediction?.price_history.price || {}).pop() || 0)} subtitle={`历史变化: ${priceChangeFormatted}%`} trend={priceChangeTrend} delay={0.3} />
            </div>

            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium">价格走势</h3>
                <div className="flex gap-2">
                  <Button variant={timeFrame === "24h" ? "default" : "outline"} size="sm" onClick={() => setTimeFrame("24h")} className="shadow-sm">
                    24小时
                  </Button>
                  <Button variant={timeFrame === "7d" ? "default" : "outline"} size="sm" onClick={() => setTimeFrame("7d")} className="shadow-sm">
                    7天
                  </Button>
                  <Button variant={timeFrame === "30d" ? "default" : "outline"} size="sm" onClick={() => setTimeFrame("30d")} className="shadow-sm">
                    30天
                  </Button>
                </div>
              </div>

              <motion.div className="h-[300px] w-full rounded-lg border backdrop-blur-sm bg-card/30 overflow-hidden" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 }}>
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
                    <RechartsTooltip
                      cursor={{ stroke: "hsl(var(--muted))", strokeWidth: 1 }}
                      content={({ active, payload, label }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="p-2 border rounded-md shadow-md bg-background">
                              <p className="text-xs font-medium">{label}</p>
                              <p className="text-xs text-primary">价格: ${Number(payload[0].value).toFixed(5)}</p>
                              {payload[1] && <p className="text-xs text-secondary">交易量: {formatLargeNumber(Number(payload[1].value))}</p>}
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Area yAxisId="left" type="monotone" dataKey="price" stroke="hsl(var(--primary))" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" activeDot={{ r: 6, strokeWidth: 2, stroke: "white" }} />
                    <Area yAxisId="right" type="monotone" dataKey="volume" stroke="hsl(var(--secondary))" strokeWidth={1.5} fillOpacity={1} fill="url(#colorVolume)" />
                  </AreaChart>
                </ResponsiveContainer>
              </motion.div>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <InsightCard title="市场洞察" items={prediction?.insights || []} delay={0.4} emptyMessage="暂无市场洞察" />

              <InsightCard title="投资建议" items={prediction?.recommendations || []} delay={0.5} emptyMessage="暂无投资建议" />
            </div>
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
};

export default MarketAnalysis;
