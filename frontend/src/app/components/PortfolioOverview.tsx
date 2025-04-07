"use client";

import React, { useState, useEffect } from "react";
import { BarChart3, Percent, DollarSign, Loader2, Network, Coins, Info, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { apiService } from "../services/api";

// 增强SimplePieChart组件，添加悬停效果
const SimplePieChart: React.FC<{
  data: Array<{
    title: string;
    value: number;
    color: string;
  }>;
  formatValue?: (value: number) => string;
}> = ({ data, formatValue }) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const totalValue = data.reduce((sum, item) => sum + item.value, 0);
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipContent, setTooltipContent] = useState({ title: "", value: 0, x: 0, y: 0 });

  // 如果没有提供 formatValue 函数，使用默认格式化
  const formatTooltipValue = (value: number) => {
    if (formatValue) return formatValue(value);
    return value.toFixed(2);
  };

  return (
    <div className="relative w-full h-full group">
      <div className="absolute inset-0 transition-opacity rounded-full opacity-50 bg-slate-900/50 blur-xl group-hover:opacity-70"></div>
      <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90 drop-shadow-lg">
        {data.map((item, index) => {
          const previousItems = data.slice(0, index);
          const startAngle = (previousItems.reduce((sum, prev) => sum + prev.value, 0) / totalValue) * 360;
          const angle = (item.value / totalValue) * 360;

          const x1 = 50 + 40 * Math.cos((startAngle * Math.PI) / 180);
          const y1 = 50 + 40 * Math.sin((startAngle * Math.PI) / 180);
          const x2 = 50 + 40 * Math.cos(((startAngle + angle) * Math.PI) / 180);
          const y2 = 50 + 40 * Math.sin(((startAngle + angle) * Math.PI) / 180);

          const largeArcFlag = angle > 180 ? 1 : 0;

          const pathData = [`M 50 50`, `L ${x1} ${y1}`, `A 40 40 0 ${largeArcFlag} 1 ${x2} ${y2}`, `L 50 50`].join(" ");

          const midAngle = startAngle + angle / 2;
          const labelRadius = 40 * 0.6;
          const x = 50 + labelRadius * Math.cos((midAngle * Math.PI) / 180);
          const y = 50 + labelRadius * Math.sin((midAngle * Math.PI) / 180);
          const percentage = (item.value / totalValue) * 100;

          // Calculate rotation angle for the label
          let rotation = 90;

          // Calculate tooltip position
          const tooltipX = 50 + 45 * Math.cos((midAngle * Math.PI) / 180);
          const tooltipY = 50 + 45 * Math.sin((midAngle * Math.PI) / 180);

          return (
            <React.Fragment key={item.title}>
              <path
                d={pathData}
                fill={item.color}
                stroke="white"
                strokeWidth="0.5"
                className="transition-all duration-300 cursor-pointer hover:brightness-110"
                style={{
                  transform: activeIndex === index ? "scale(1.05) translate(1px, 1px)" : "none",
                  filter: activeIndex === index ? "drop-shadow(0 0 8px rgba(0,0,0,0.5))" : "none",
                  opacity: activeIndex !== null && activeIndex !== index ? 0.7 : 1,
                }}
                onMouseEnter={() => {
                  setActiveIndex(index);
                  setTooltipContent({
                    title: item.title,
                    value: item.value,
                    x: tooltipX,
                    y: tooltipY,
                  });
                  setShowTooltip(true);
                }}
                onMouseLeave={() => {
                  setActiveIndex(null);
                  setShowTooltip(false);
                }}
              />
              {percentage > 5 && (
                <text
                  x={x}
                  y={y}
                  fill="white"
                  fontSize="3.8"
                  fontWeight="bold"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  pointerEvents="none"
                  style={{
                    textShadow: "0 1px 2px rgba(0,0,0,0.8)",
                    opacity: activeIndex === index ? 1 : 0.9,
                  }}
                  key={item.title + "-label"}
                  transform={`rotate(${rotation} ${x} ${y})`}
                >
                  <tspan x={x} dy="-0.3em">
                    {item.title}
                  </tspan>
                  <tspan x={x} dy="1.2em" fontWeight="normal" fontSize="3.5">
                    {percentage.toFixed(1)}%
                  </tspan>
                </text>
              )}
            </React.Fragment>
          );
        })}

        {showTooltip && (
          <g className="pointer-events-none">
            <rect x={tooltipContent.x - 15} y={tooltipContent.y - 12} width="30" height="24" rx="4" fill="rgba(0,0,0,0.8)" className="animate-fadeIn" />
            <text x={tooltipContent.x} y={tooltipContent.y} fontSize="4" fontWeight="bold" fill="white" textAnchor="middle" dominantBaseline="middle">
              {formatTooltipValue(tooltipContent.value)}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
};

interface PortfolioOverviewProps {
  portfolio: {
    wallet_address: string;
    total_value: number;
    total_value_usd: number;
    position_count: number;
    protocol_count: number;
    positions: Array<{
      protocol: string;
      total_assets: number;
      total_debts: number;
      leverage: number;
      positions: Array<{
        protocol: string;
        asset: string;
        amount: number;
        invest_type: number;
        apy: number | null;
        tokenList: Array<{
          tokenSymbol: string;
          tokenLogo: string;
          tokenType?: string;
          coinAmount: string;
          currencyAmount: string;
          tokenPrecision: number;
          tokenAddress: string;
          network: string;
        }>;
      }>;
    }>;
    protocols: Array<{
      name: string;
      chain: string;
      tvl: number;
      supported_assets: string[];
      features: string[];
      description: string;
    }>;
    timestamp: string;
    is_demo_data: boolean;
  } | null;
  loading?: boolean;
  error?: string | null;
}

interface ProtocolRiskAnalysis {
  protocol: string;
  risk_score: number;
  risk_level: string;
  risk_factors: Array<{
    factor: string;
    score: number;
    description: string;
  }>;
  recommendations: string[];
}

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ portfolio, loading, error }) => {
  const [selectedProtocol, setSelectedProtocol] = useState<{
    name: string;
    chain: string;
    tvl: number;
    supported_assets: string[];
    features: string[];
    description: string;
  } | null>(null);
  const [protocolRisk, setProtocolRisk] = useState<ProtocolRiskAnalysis | null>(null);
  const [loadingRisk, setLoadingRisk] = useState(false);
  const [activeTab, setActiveTab] = useState<"info" | "risk">("info");
  const [mounted, setMounted] = useState(false);

  // 添加入场动画效果
  useEffect(() => {
    setMounted(true);

    // 添加CSS动画
    const style = document.createElement("style");
    style.innerHTML = `
      @keyframes fadeInUp {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }

      .animate-fadeIn {
        animation: fadeIn 0.5s ease-out forwards;
      }
    `;
    document.head.appendChild(style);

    // 清理函数
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  // 计算平均APY
  const calculateAverageApy = (portfolio: any) => {
    if (!portfolio || !portfolio.positions) return 0;

    let totalApy = 0;
    let validPositionsCount = 0;

    portfolio.positions.forEach((protocolPos: any) => {
      protocolPos.positions.forEach((position: any) => {
        if (position.apy && !isNaN(position.apy)) {
          totalApy += position.apy;
          validPositionsCount++;
        }
      });
    });

    return validPositionsCount > 0 ? (totalApy / validPositionsCount).toFixed(2) : 0;
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl animate-fadeIn">
        <Card className="border shadow-lg bg-gradient-to-br from-slate-900/30 to-slate-800/30 border-slate-700/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <BarChart3 className="w-5 h-5 text-primary animate-pulse" />
              投资组合概览
            </CardTitle>
            <CardDescription className="text-base">正在获取数据...</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center py-20">
            <div className="relative w-20 h-20">
              <div className="absolute inset-0 border-4 rounded-full border-slate-700/30"></div>
              <div className="absolute inset-0 border-4 rounded-full border-t-primary border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
            </div>
            <Loader2 className="absolute w-10 h-10 animate-spin text-primary/70" />
            <p className="mt-6 text-slate-400">加载投资组合数据中，请稍候...</p>
            <div className="grid grid-cols-3 gap-4 mt-8">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-24 rounded-lg bg-slate-800/40 animate-pulse"></div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl animate-fadeIn">
        <Card className="border shadow-lg bg-gradient-to-br from-red-900/20 to-red-950/30 border-red-800/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl text-red-400">
              <AlertTriangle className="w-5 h-5" />
              获取投资组合数据失败
            </CardTitle>
            <CardDescription className="text-base text-red-300/70">{error}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center py-10">
            <div className="p-6 text-red-400 rounded-full bg-red-500/10">
              <AlertTriangle className="w-16 h-16" />
            </div>
            <p className="max-w-lg mt-6 text-center text-slate-300">很抱歉，在获取您的投资组合数据时遇到了问题。这可能是由于网络连接问题或服务暂时不可用。</p>
            <Button size="lg" className="gap-2 mt-8 text-white bg-red-500 hover:bg-red-600" onClick={() => window.location.reload()}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-spin">
                <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
                <path d="M3 3v5h5"></path>
                <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
                <path d="M16 21h5v-5"></path>
              </svg>
              重新加载
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="mx-auto max-w-7xl animate-fadeIn">
        <Card className="border shadow-lg bg-gradient-to-br from-amber-900/20 to-amber-950/30 border-amber-800/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl text-amber-400">
              <Info className="w-5 h-5" />
              暂无数据
            </CardTitle>
            <CardDescription className="text-base text-amber-300/70">没有找到投资组合数据</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center py-10">
            <div className="p-6 rounded-full bg-amber-500/10 text-amber-400">
              <Coins className="w-16 h-16" />
            </div>
            <p className="max-w-lg mt-6 text-center text-slate-300">您当前没有任何投资组合数据。请连接钱包或选择一个演示账户来查看投资组合信息。</p>
            <div className="flex flex-wrap justify-center gap-4 mt-8">
              <Button className="gap-2 bg-primary hover:bg-primary/90">
                <Network className="w-4 h-4" />
                连接钱包
              </Button>
              <Button variant="outline" className="gap-2">
                <Coins className="w-4 h-4" />
                查看演示账户
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // 生成协议分布饼图数据
  const protocolData = portfolio.positions.map((protocolPos, index) => ({
    title: protocolPos.protocol,
    value: protocolPos.total_assets,
    color: [
      "#2563eb", // blue-600
      "#16a34a", // green-600
      "#dc2626", // red-600
      "#9333ea", // purple-600
      "#ea580c", // orange-600
      "#0891b2", // cyan-600
      "#4f46e5", // indigo-600
      "#db2777", // pink-600
    ][index % 8],
  }));

  const getInvestTypeName = (type: number) => {
    switch (type) {
      case 1:
        return "存币";
      case 2:
        return "流动性池";
      case 3:
        return "挖矿";
      case 4:
        return "机枪池";
      case 5:
        return "质押";
      case 6:
        return "借贷";
      default:
        return "其他";
    }
  };

  // 生成资产类型分布数据
  const assetTypeData = portfolio.positions.reduce((acc, protocolPos) => {
    protocolPos.positions.forEach((position) => {
      const type = getInvestTypeName(position.invest_type);
      acc[type] = (acc[type] || 0) + position.amount;
    });
    return acc;
  }, {} as { [key: string]: number });

  const assetTypeChartData = Object.entries(assetTypeData).map(([type, value], index) => ({
    title: type,
    value,
    color: [
      "#2563eb", // blue-600
      "#16a34a", // green-600
      "#dc2626", // red-600
      "#9333ea", // purple-600
      "#ea580c", // orange-600
      "#0891b2", // cyan-600
      "#4f46e5", // indigo-600
      "#db2777", // pink-600
    ][index % 8],
  }));

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("zh-CN", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  // 获取协议风险分析
  const fetchProtocolRisk = async (protocolName: string) => {
    try {
      setLoadingRisk(true);
      const riskData = await apiService.analyzeProtocolRisk(protocolName);
      setProtocolRisk(riskData);
    } catch (error) {
      console.error(`获取协议 ${protocolName} 风险分析失败:`, error);
      setProtocolRisk(null);
    } finally {
      setLoadingRisk(false);
    }
  };

  // 打开协议详情
  const openProtocolDetails = (protocol: any) => {
    setSelectedProtocol(protocol);
    setActiveTab("info");
    // 获取风险分析
    fetchProtocolRisk(protocol.name);
  };

  // 关闭协议详情
  const closeProtocolDetails = () => {
    setSelectedProtocol(null);
    setProtocolRisk(null);
  };

  // 渲染风险等级标签
  const renderRiskLevel = (level: string) => {
    let variant: "default" | "secondary" | "destructive" | "outline" = "default";
    if (level === "高") variant = "destructive";
    else if (level === "中等") variant = "secondary";

    return <Badge variant={variant}>{level}</Badge>;
  };

  return (
    <div className={`max-w-7xl mx-auto space-y-8 transition-opacity duration-500 ${mounted ? "opacity-100" : "opacity-0"}`}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="transition-all border shadow-md bg-gradient-to-br from-primary/20 to-primary/5 border-primary/10 hover:shadow-lg">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">总资产价值</p>
                <h3 className="mt-1.5 text-2xl font-bold tracking-tight">{formatCurrency(portfolio.total_value_usd)}</h3>
              </div>
              <div className="p-3 rounded-full bg-primary/20 text-primary ring-2 ring-primary/20">
                <DollarSign className="w-5 h-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="transition-all border shadow-md bg-gradient-to-br from-blue-500/20 to-blue-500/5 border-blue-500/10 hover:shadow-lg">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">协议数量</p>
                <h3 className="mt-1.5 text-2xl font-bold tracking-tight">{portfolio.protocol_count}</h3>
              </div>
              <div className="p-3 text-blue-500 rounded-full bg-blue-500/20 ring-2 ring-blue-500/20">
                <Network className="w-5 h-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="transition-all border shadow-md bg-gradient-to-br from-amber-500/20 to-amber-500/5 border-amber-500/10 hover:shadow-lg">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">头寸数量</p>
                <h3 className="mt-1.5 text-2xl font-bold tracking-tight">{portfolio.position_count}</h3>
              </div>
              <div className="p-3 rounded-full bg-amber-500/20 text-amber-500 ring-2 ring-amber-500/20">
                <Coins className="w-5 h-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="transition-all border shadow-md bg-gradient-to-br from-green-500/20 to-green-500/5 border-green-500/10 hover:shadow-lg">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">平均APY</p>
                <h3 className="mt-1.5 text-2xl font-bold tracking-tight">{calculateAverageApy(portfolio)}%</h3>
              </div>
              <div className="p-3 text-green-500 rounded-full bg-green-500/20 ring-2 ring-green-500/20">
                <Percent className="w-5 h-5" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-3 md:gap-6">
        <Card className="border shadow-lg bg-gradient-to-br from-slate-900/50 to-slate-800/50 border-slate-700/50 md:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <BarChart3 className="w-5 h-5 text-primary" />
              投资组合概览
            </CardTitle>
            <CardDescription className="text-base">
              总资产价值: <span className="font-medium text-primary">{formatCurrency(portfolio.total_value_usd)}</span>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
              <div className="p-5 rounded-lg shadow-inner bg-gradient-to-br from-slate-800 to-slate-900">
                <h3 className="flex items-center gap-2 mb-4 text-lg font-medium">
                  <Network className="w-4 h-4 text-primary" />
                  协议分布
                </h3>
                <div className="w-full aspect-square max-w-[300px] mx-auto relative">
                  <SimplePieChart data={protocolData} formatValue={formatCurrency} />
                </div>
              </div>
              <div className="p-5 rounded-lg shadow-inner bg-gradient-to-br from-slate-800 to-slate-900">
                <h3 className="flex items-center gap-2 mb-4 text-lg font-medium">
                  <Coins className="w-4 h-4 text-primary" />
                  资产类型分布
                </h3>
                <div className="w-full aspect-square max-w-[300px] mx-auto relative">
                  <SimplePieChart data={assetTypeChartData} formatValue={formatCurrency} />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-xl bg-gradient-to-br from-slate-900/30 to-black/30 border-slate-700/50 md:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Coins className="w-5 h-5 text-primary" />
              持仓详情
            </CardTitle>
            <CardDescription className="text-base">
              共 <span className="font-medium text-primary">{portfolio.position_count}</span> 个持仓，
              <span className="font-medium text-primary">{portfolio.protocol_count}</span> 个协议
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-10">
              {portfolio.positions.map((protocolPos) => (
                <div key={protocolPos.protocol} className="pb-6 space-y-4 border-b border-slate-700/30">
                  <div className="p-4 rounded-lg shadow-md bg-gradient-to-r from-slate-800/50 to-slate-900/50">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex-shrink-0 p-2 rounded-full bg-primary/20">
                          <Network className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <h4 className="text-lg font-medium text-primary">{protocolPos.protocol}</h4>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Badge variant="outline" className="shadow-sm">
                              杠杆率: {protocolPos.leverage}x
                            </Badge>
                            <span>•</span>
                            <span>总资产: {formatCurrency(protocolPos.total_assets)}</span>
                          </div>
                        </div>
                      </div>
                      <Button variant="outline" size="sm" className="gap-1 mt-2 text-xs transition-colors bg-slate-800/50 hover:bg-slate-700/50 sm:mt-0">
                        <Info className="w-3.5 h-3.5" />
                        查看分析
                      </Button>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <Table className="overflow-hidden border rounded-lg border-slate-700/20">
                      <TableHeader className="bg-slate-800/50">
                        <TableRow className="border-b-0 hover:bg-slate-700/30">
                          <TableHead className="font-medium">资产</TableHead>
                          <TableHead className="font-medium">数量</TableHead>
                          <TableHead className="font-medium">价值</TableHead>
                          <TableHead className="font-medium">类型</TableHead>
                          <TableHead className="font-medium">APY</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {protocolPos.positions.map((position, index) => {
                          const assetTokens = position.tokenList || [];
                          const mainToken = assetTokens.find((t) => !t.tokenType || t.tokenType !== "reward") || assetTokens[0];

                          return (
                            <TableRow key={`${position.protocol}-${position.asset}`} className={`hover:bg-slate-700/20 transition-colors ${index % 2 === 0 ? "bg-slate-800/10" : ""}`}>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  {mainToken && mainToken.tokenLogo ? (
                                    <div className="w-8 h-8 rounded-full bg-slate-700/50 p-0.5 shadow-md flex items-center justify-center">
                                      <img
                                        src={mainToken.tokenLogo}
                                        alt={`${position.asset} logo`}
                                        className="w-full h-full rounded-full"
                                        onError={(e) => {
                                          // 如果图片加载失败，隐藏图片元素
                                          (e.target as HTMLImageElement).style.display = "none";
                                        }}
                                      />
                                    </div>
                                  ) : (
                                    <div className="flex items-center justify-center w-8 h-8 text-sm font-bold rounded-full shadow-md bg-gradient-to-br from-slate-600 to-slate-800">{position.asset.charAt(0)}</div>
                                  )}
                                  <div>
                                    <div className="flex items-center gap-1">
                                      <span className="text-sm font-medium text-slate-100">{position.asset}</span>
                                    </div>
                                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                      <span>{getInvestTypeName(position.invest_type)}</span>
                                      <span>•</span>
                                      <span>{formatCurrency(position.amount)}</span>
                                    </div>
                                  </div>
                                </div>
                              </TableCell>
                              <TableCell className="text-slate-300">{parseFloat(position.tokenList[0]?.coinAmount || "0").toFixed(4)}</TableCell>
                              <TableCell className="font-medium text-slate-200">{formatCurrency(parseFloat(position.tokenList[0]?.currencyAmount || "0"))}</TableCell>
                              <TableCell>
                                <Badge variant="secondary" className="shadow-sm">
                                  {getInvestTypeName(position.invest_type)}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                {position.apy ? (
                                  <Badge variant="default" className={`shadow-sm ${position.apy > 5 ? "bg-green-500/90" : position.apy > 2 ? "bg-blue-500/90" : ""}`}>
                                    {formatPercentage(position.apy)}
                                  </Badge>
                                ) : (
                                  <span className="text-muted-foreground">-</span>
                                )}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-xl bg-gradient-to-br from-slate-900/40 to-black/40 border-slate-700/50 md:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Network className="w-5 h-5 text-primary" />
              协议信息
            </CardTitle>
            <CardDescription className="text-base">支持的DeFi协议和功能</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2 lg:grid-cols-3">
              {portfolio.protocols.map((protocol, index) => (
                <div
                  key={protocol.name}
                  className="relative p-5 transition-all duration-300 border rounded-lg shadow-md cursor-pointer group bg-gradient-to-br from-slate-800/70 to-slate-900/90 hover:from-slate-700/70 hover:to-slate-800/90 border-slate-700/40 hover:border-primary/40 hover:shadow-xl hover:-translate-y-1"
                  onClick={() => openProtocolDetails(protocol)}
                  style={{
                    animationDelay: `${index * 50}ms`,
                    animation: "fadeInUp 0.5s ease-out forwards",
                    opacity: 0,
                    transform: "translateY(10px)",
                  }}
                >
                  <div className="absolute top-0 left-0 w-full h-full transition-opacity rounded-lg opacity-0 bg-primary/5 group-hover:opacity-100"></div>

                  <div className="relative z-10 flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary/10 text-primary">
                        {protocol.name.toLowerCase().includes("lend") || protocol.features.some((f) => f.includes("借贷")) ? (
                          <Coins className="w-5 h-5" />
                        ) : protocol.name.toLowerCase().includes("swap") || protocol.features.some((f) => f.includes("交易")) ? (
                          <BarChart3 className="w-5 h-5" />
                        ) : (
                          <Network className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <h4 className="font-medium text-slate-100">{protocol.name}</h4>
                        <div className="flex items-center gap-1.5">
                          <Badge variant="outline" className="text-xs px-1.5 py-0 h-5">
                            {"Ethereum"}
                          </Badge>
                          <span className="text-xs text-muted-foreground">TVL: {formatCurrency(protocol.tvl)}</span>
                        </div>
                      </div>
                    </div>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="w-8 h-8 rounded-full opacity-70 hover:opacity-100 hover:bg-slate-700/50 hover:text-primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        openProtocolDetails(protocol);
                      }}
                    >
                      <Info className="w-4 h-4" />
                    </Button>
                  </div>

                  <p className="relative z-10 mb-4 text-sm text-slate-300 line-clamp-2">{protocol.description || "无描述信息"}</p>

                  {protocol.supported_assets && protocol.supported_assets.length > 0 && (
                    <div className="relative z-10 flex items-center gap-2 mb-3 text-sm text-slate-400">
                      <Coins className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate">
                        支持资产: {protocol.supported_assets.slice(0, 3).join(", ")}
                        {protocol.supported_assets.length > 3 ? "..." : ""}
                      </span>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-1.5 mt-3 relative z-10">
                    {protocol.features.slice(0, 3).map((feature) => (
                      <Badge key={feature} variant="secondary" className="text-xs bg-slate-700/50 hover:bg-slate-600/50">
                        {feature}
                      </Badge>
                    ))}
                    {protocol.features.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{protocol.features.length - 3}
                      </Badge>
                    )}
                  </div>

                  <div className="absolute z-10 transition-opacity opacity-0 bottom-4 right-4 group-hover:opacity-100">
                    <Badge variant="default" className="bg-primary/90 hover:bg-primary">
                      查看详情
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 协议详情弹窗 */}
      <Dialog open={selectedProtocol !== null} onOpenChange={(open: boolean) => !open && closeProtocolDetails()}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-700/50 shadow-2xl">
          {selectedProtocol && (
            <>
              <DialogHeader className="space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-3 shadow-md rounded-xl bg-primary/10 text-primary">
                      {selectedProtocol?.name.toLowerCase().includes("lend") || (selectedProtocol?.features && selectedProtocol.features.some((f) => f.includes("借贷"))) ? (
                        <Coins className="w-6 h-6" />
                      ) : selectedProtocol?.name.toLowerCase().includes("swap") || (selectedProtocol?.features && selectedProtocol.features.some((f) => f.includes("交易"))) ? (
                        <BarChart3 className="w-6 h-6" />
                      ) : (
                        <Network className="w-6 h-6" />
                      )}
                    </div>
                    <div>
                      <DialogTitle className="text-2xl font-bold tracking-tight">
                        <span>{selectedProtocol?.name}</span>
                      </DialogTitle>
                      <div className="flex items-center gap-2 mt-1">
                        {selectedProtocol?.chain && (
                          <Badge variant="outline" className="bg-slate-800/50">
                            {selectedProtocol?.chain}
                          </Badge>
                        )}
                        <Badge variant="default" className="bg-primary/80">
                          TVL: {formatCurrency(selectedProtocol?.tvl)}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
                <DialogDescription className="text-base leading-relaxed text-slate-300">{selectedProtocol.description || "暂无描述"}</DialogDescription>
              </DialogHeader>

              <Tabs defaultValue={activeTab} onValueChange={(value: string) => setActiveTab(value as "info" | "risk")} className="mt-6">
                <TabsList className="grid grid-cols-2 p-1 mb-6 bg-slate-800/50">
                  <TabsTrigger value="info" className="data-[state=active]:bg-primary data-[state=active]:text-white">
                    <Info className="w-4 h-4 mr-2" />
                    协议信息
                  </TabsTrigger>
                  <TabsTrigger value="risk" className="data-[state=active]:bg-primary data-[state=active]:text-white">
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    风险分析
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="info" className="space-y-6 animate-fadeIn">
                  {/* 协议基本信息 */}
                  <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                    {selectedProtocol?.tvl !== undefined && (
                      <div className="p-5 border rounded-lg shadow-md bg-slate-800/30 border-slate-700/30">
                        <h4 className="mb-2 text-sm font-medium text-slate-400">总锁仓价值</h4>
                        <div className="flex items-center gap-2">
                          <BarChart3 className="w-5 h-5 text-primary" />
                          <p className="text-2xl font-bold">{formatCurrency(selectedProtocol?.tvl)}</p>
                        </div>
                      </div>
                    )}

                    <div className="p-5 border rounded-lg shadow-md bg-slate-800/30 border-slate-700/30">
                      <h4 className="mb-2 text-sm font-medium text-slate-400">主要功能</h4>
                      <div className="flex items-center gap-2">
                        <Network className="w-5 h-5 text-primary" />
                        <p className="text-xl font-medium">{selectedProtocol?.features && selectedProtocol?.features.length > 0 ? selectedProtocol?.features[0] : "未知"}</p>
                      </div>
                    </div>
                  </div>

                  {/* 支持的资产 */}
                  {selectedProtocol?.supported_assets && selectedProtocol?.supported_assets.length > 0 && (
                    <div className="p-5 mt-4 border rounded-lg bg-slate-800/20 border-slate-700/20">
                      <h4 className="flex items-center gap-2 mb-3 text-base font-medium">
                        <Coins className="w-4 h-4 text-primary" />
                        支持的资产
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedProtocol?.supported_assets.map((asset) => (
                          <Badge key={asset} variant="secondary" className="px-3 py-1 shadow-sm">
                            {asset}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 功能特性 */}
                  {selectedProtocol?.features && selectedProtocol?.features.length > 0 && (
                    <div className="p-5 mt-4 border rounded-lg bg-slate-800/20 border-slate-700/20">
                      <h4 className="flex items-center gap-2 mb-3 text-base font-medium">
                        <Network className="w-4 h-4 text-primary" />
                        功能特性
                      </h4>
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        {selectedProtocol?.features.map((feature, index) => (
                          <div key={index} className="flex items-start gap-2 p-2 rounded-md bg-slate-800/30">
                            <span className="mt-0.5 text-primary">•</span>
                            <span className="text-sm">{feature}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="risk" className="space-y-6 animate-fadeIn">
                  {loadingRisk ? (
                    <div className="flex flex-col items-center justify-center py-16 border rounded-lg bg-slate-800/10 border-slate-700/20">
                      <Loader2 className="w-10 h-10 mb-4 animate-spin text-primary" />
                      <p className="text-slate-400">获取风险分析数据中...</p>
                    </div>
                  ) : !protocolRisk ? (
                    <div className="py-16 text-center border rounded-lg bg-slate-800/10 border-slate-700/20">
                      <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-amber-500" />
                      <p className="mb-2 text-lg font-medium">无法获取风险分析数据</p>
                      <p className="mb-6 text-muted-foreground">可能是网络问题或该协议暂无风险评估</p>
                      <Button className="bg-primary hover:bg-primary/90" onClick={() => fetchProtocolRisk(selectedProtocol.name)}>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        重试
                      </Button>
                    </div>
                  ) : (
                    <>
                      {/* 风险评分 */}
                      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div className="relative p-5 overflow-hidden border rounded-lg shadow-md bg-slate-800/30 border-slate-700/30">
                          <div className="absolute bottom-0 left-0 h-1.5 bg-gradient-to-r from-green-500 via-yellow-500 to-red-500" style={{ width: "100%" }}></div>
                          <div className="absolute bottom-0 left-0 h-1.5 bg-black/30" style={{ width: `${100 - protocolRisk?.risk_score}%` }}></div>

                          <h4 className="mb-2 text-sm font-medium text-slate-400">风险评分</h4>
                          <div className="flex items-end justify-between">
                            <div className="flex items-baseline gap-2">
                              <p className="text-3xl font-bold">{protocolRisk?.risk_score}</p>
                              <span className="text-sm text-muted-foreground">/100</span>
                            </div>
                            <div>{renderRiskLevel(protocolRisk?.risk_level || "")}</div>
                          </div>
                        </div>

                        <div className="p-5 border rounded-lg shadow-md bg-slate-800/30 border-slate-700/30">
                          <h4 className="mb-2 text-sm font-medium text-slate-400">总体评估</h4>
                          <p className="text-base">
                            {protocolRisk?.risk_level === "高" ? (
                              <span className="text-red-400">该协议存在较高风险，请谨慎使用</span>
                            ) : protocolRisk?.risk_level === "中等" ? (
                              <span className="text-yellow-400">该协议存在一定风险，建议了解更多后使用</span>
                            ) : (
                              <span className="text-green-400">该协议风险较低，但仍需注意DeFi固有风险</span>
                            )}
                          </p>
                        </div>
                      </div>

                      {/* 风险因素 */}
                      {protocolRisk?.risk_factors && protocolRisk.risk_factors.length > 0 && (
                        <div className="mt-6">
                          <h4 className="flex items-center gap-2 mb-4 text-lg font-medium">
                            <AlertTriangle className="w-4 h-4 text-primary" />
                            风险因素
                          </h4>
                          <div className="space-y-4">
                            {protocolRisk.risk_factors.map((factor, index) => (
                              <div key={index} className="p-4 transition-all border rounded-md shadow-sm bg-slate-800/40 border-slate-700/30 hover:shadow-md hover:bg-slate-800/60">
                                <div className="flex items-center justify-between mb-2">
                                  <h5 className="font-medium text-slate-200">{factor.factor}</h5>
                                  <Badge variant={factor.score > 80 ? "default" : factor.score > 60 ? "secondary" : "destructive"} className="shadow-sm">
                                    {factor.score}/100
                                  </Badge>
                                </div>
                                <p className="text-sm text-slate-300">{factor.description}</p>
                                <div className="w-full h-1 mt-2 overflow-hidden rounded-full bg-slate-700">
                                  <div className={`h-full rounded-full ${factor.score > 80 ? "bg-green-500" : factor.score > 60 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${factor.score}%` }}></div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* AI建议 */}
                      {protocolRisk?.recommendations && protocolRisk.recommendations.length > 0 && (
                        <div className="p-5 mt-6 border rounded-lg bg-primary/10 border-primary/20">
                          <h4 className="mb-3 text-lg font-medium">
                            <span className="bg-primary text-white px-2 py-0.5 rounded mr-2 text-sm">AI</span>
                            投资建议
                          </h4>
                          <ul className="space-y-2 text-sm">
                            {protocolRisk.recommendations.map((rec, index) => (
                              <li key={index} className="flex items-start gap-2 p-3 rounded-md bg-slate-800/30">
                                <span className="mt-0.5 text-primary">•</span>
                                <span>{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  )}
                </TabsContent>
              </Tabs>

              <DialogFooter className="flex items-center justify-between pt-4 mt-8 border-t border-slate-700/30">
                <Button variant="outline" className="gap-2" onClick={() => selectedProtocol?.name && window.open(`https://etherscan.io/address/${selectedProtocol.name}`, "_blank")}>
                  <Network className="w-4 h-4" />
                  查看合约
                </Button>
                <Button className="gap-2 bg-primary hover:bg-primary/90" onClick={closeProtocolDetails}>
                  关闭
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PortfolioOverview;
