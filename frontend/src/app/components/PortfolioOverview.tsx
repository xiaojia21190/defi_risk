"use client";

import React from "react";
import { Portfolio } from "../services/api";
import { TrendingUp, Wallet, BarChart3, Percent, ChartBar, Target, DollarSign, ArrowUpDown, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

// 使用简单的自定义饼图组件
const SimplePieChart: React.FC<{
  data: Array<{
    title: string;
    value: number;
    color: string;
  }>;
  total: number;
}> = ({ data, total }) => {
  const totalValue = total || data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="relative w-full h-full">
      <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
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

          return <path key={item.title} d={pathData} fill={item.color} stroke="white" strokeWidth="0.5" />;
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        {data.map((item) => {
          const percentage = (item.value / totalValue) * 100;
          if (percentage > 5) {
            return (
              <div key={item.title} className="text-xs font-medium text-white" style={{ textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}>
                {item.title}
                <br />
                {percentage.toFixed(1)}%
              </div>
            );
          }
          return null;
        })}
      </div>
    </div>
  );
};

interface PortfolioOverviewProps {
  portfolio: Portfolio | null;
  loading?: boolean;
  error?: string | null;
}

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ portfolio, loading, error }) => {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>投资组合概览</CardTitle>
          <CardDescription>加载中...</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>投资组合概览</CardTitle>
          <CardDescription className="text-destructive">{error}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!portfolio) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>投资组合概览</CardTitle>
          <CardDescription>暂无数据</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // 计算每个协议的总价值
  const protocolValues = portfolio.positions.reduce((acc, pos) => {
    // 获取资产符号，优先使用tokenList
    const assetSymbol = pos.tokenList && pos.tokenList.length > 0 ? pos.tokenList[0].tokenSymbol.split("/")[0] : pos.asset.split("/")[0];

    const marketAnalysis = portfolio.market_analysis[assetSymbol];

    // 获取资产价值，优先使用amount，如果没有则尝试从tokenList获取
    let value = 0;
    if (pos.amount !== undefined) {
      value = pos.amount * (marketAnalysis?.current_price || 0);
    } else if (pos.tokenList && pos.tokenList.length > 0) {
      // 使用currencyAmount作为美元价值
      value = parseFloat(pos.tokenList[0].currencyAmount || "0");
    }

    acc[pos.protocol] = (acc[pos.protocol] || 0) + value;
    return acc;
  }, {} as { [key: string]: number });

  // 生成饼图数据
  const pieData = Object.entries(protocolValues).map(([protocol, value], index) => ({
    title: protocol,
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

  // 计算总收益率
  const totalAPY = portfolio.positions.reduce((sum, pos) => sum + (pos.apy || 0), 0) / portfolio.positions.length;

  // 计算资产类型分布
  const assetTypeDistribution = portfolio.positions.reduce((acc, pos) => {
    // 获取资产符号，优先使用tokenList
    const assetSymbol = pos.tokenList && pos.tokenList.length > 0 ? pos.tokenList[0].tokenSymbol.split("/")[0] : pos.asset.split("/")[0];

    const marketAnalysis = portfolio.market_analysis[assetSymbol];

    // 获取资产价值，优先使用amount，如果没有则尝试从tokenList获取
    let value = 0;
    if (pos.amount !== undefined) {
      value = pos.amount * (marketAnalysis?.current_price || 0);
    } else if (pos.tokenList && pos.tokenList.length > 0) {
      // 使用currencyAmount作为美元价值
      value = parseFloat(pos.tokenList[0].currencyAmount || "0");
    }

    // 根据invest_type分类资产类型
    let type = "其他";
    if (pos.invest_type === 1) {
      type = "存币";
    } else if (pos.invest_type === 2) {
      type = "流动性池";
    } else if (pos.invest_type === 3) {
      type = "挖矿";
    } else if (pos.invest_type === 4) {
      type = "机枪池";
    } else if (pos.invest_type === 5) {
      type = "质押";
    } else if (pos.invest_type === 6) {
      type = "借贷";
    } else {
      // 如果没有invest_type，使用旧的分类逻辑
      if (assetSymbol === "ETH" || assetSymbol === "WETH" || assetSymbol === "BTC") {
        type = "主流币";
      } else if (assetSymbol === "USDC" || assetSymbol === "USDT" || assetSymbol === "DAI") {
        type = "稳定币";
      } else if (assetSymbol.includes("LP") || assetSymbol.includes("Pool")) {
        type = "流动性代币";
      }
    }

    acc[type] = (acc[type] || 0) + value;
    return acc;
  }, {} as { [key: string]: number });

  // 计算APY趋势
  const calculateAPYTrend = () => {
    const apys = portfolio.positions.map((pos) => pos.apy || 0);
    const avgAPY = apys.reduce((sum, apy) => sum + apy, 0) / apys.length;

    if (avgAPY > 15) return "高";
    if (avgAPY > 5) return "中";
    return "低";
  };

  // 计算杠杆使用情况
  const calculateLeverageUsage = () => {
    const leveragedPositions = portfolio.positions.filter((pos) => pos.leverage && pos.leverage > 1);
    const avgLeverage = leveragedPositions.length > 0 ? leveragedPositions.reduce((sum, pos) => sum + (pos.leverage || 1), 0) / leveragedPositions.length : 1;

    if (avgLeverage > 2) return "高";
    if (avgLeverage > 1.5) return "中";
    return "低";
  };

  // 计算多样性得分
  const calculateDiversityScore = () => {
    const protocols = new Set(portfolio.positions.map((pos) => pos.protocol)).size;
    const assets = new Set(portfolio.positions.map((pos) => pos.asset)).size;

    const protocolScore = Math.min(protocols / 3, 1); // 最多3个协议为满分
    const assetScore = Math.min(assets / 5, 1); // 最多5个资产为满分

    const score = ((protocolScore + assetScore) / 2) * 100;

    if (score > 70) return "高";
    if (score > 40) return "中";
    return "低";
  };

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

  const apyTrend = calculateAPYTrend();
  const leverageUsage = calculateLeverageUsage();
  const diversityScore = calculateDiversityScore();

  return (
    <Card>
      <CardHeader>
        <CardTitle>投资组合概览</CardTitle>
        <CardDescription>总资产价值: {formatCurrency(portfolio?.total_value || 0)}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <h3 className="mb-4 text-lg font-medium">资产分布</h3>
            <div className="w-full aspect-square max-w-[300px] mx-auto relative bg-slate-900 rounded-full">
              {pieData.length > 0 ? (
                <SimplePieChart data={pieData} total={portfolio?.total_value || 0} />
              ) : (
                <div className="flex items-center justify-center h-full rounded-full bg-muted/20">
                  <p className="text-muted-foreground">暂无数据</p>
                </div>
              )}
            </div>
          </div>
          <div>
            <h3 className="mb-4 text-lg font-medium">投资组合指标</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="p-2 mr-2 rounded-full bg-primary/20">
                    <Percent className="w-5 h-5 text-primary" />
                  </div>
                  <span className="text-sm font-medium">平均收益率</span>
                </div>
                <div className="flex items-center">
                  <span className="mr-2 text-sm">{formatPercentage(totalAPY)}</span>
                  <Badge variant={apyTrend === "高" ? "destructive" : apyTrend === "中" ? "secondary" : "outline"}>{apyTrend}</Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="p-2 mr-2 rounded-full bg-secondary/20">
                    <Target className="w-5 h-5 text-secondary" />
                  </div>
                  <span className="text-sm font-medium">杠杆使用</span>
                </div>
                <div className="flex items-center">
                  <Badge variant={leverageUsage === "高" ? "destructive" : leverageUsage === "中" ? "secondary" : "outline"}>{leverageUsage}</Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="p-2 mr-2 rounded-full bg-primary/20">
                    <BarChart3 className="w-5 h-5 text-primary" />
                  </div>
                  <span className="text-sm font-medium">多样性得分</span>
                </div>
                <div className="flex items-center">
                  <Badge variant={diversityScore === "高" ? "destructive" : diversityScore === "中" ? "secondary" : "outline"}>{diversityScore}</Badge>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="mb-4 text-lg font-medium">资产列表</h3>
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>资产</TableHead>
                  <TableHead>协议</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead className="text-right">数量</TableHead>
                  <TableHead className="text-right">价值</TableHead>
                  <TableHead className="text-right">收益率</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {portfolio.positions.map((position, index) => {
                  // 获取资产符号，优先使用tokenList
                  const assetSymbol = position.tokenList && position.tokenList.length > 0 ? position.tokenList[0].tokenSymbol.split("/")[0] : position.asset.split("/")[0];

                  const marketAnalysis = portfolio.market_analysis[assetSymbol];

                  // 获取资产价值，优先使用amount，如果没有则尝试从tokenList获取
                  let value = 0;
                  let displayAmount = "0";

                  if (position.amount !== undefined) {
                    value = position.amount * (marketAnalysis?.current_price || 0);
                    displayAmount = position.amount.toFixed(4);
                  } else if (position.tokenList && position.tokenList.length > 0) {
                    // 使用currencyAmount作为美元价值
                    value = parseFloat(position.tokenList[0].currencyAmount || "0");
                    displayAmount = position.tokenList[0].coinAmount || "0";
                  }

                  // 获取投资类型
                  let investType = "未知";
                  if (position.invest_type === 1) investType = "存币";
                  else if (position.invest_type === 2) investType = "流动性池";
                  else if (position.invest_type === 3) investType = "挖矿";
                  else if (position.invest_type === 4) investType = "机枪池";
                  else if (position.invest_type === 5) investType = "质押";
                  else if (position.invest_type === 6) investType = "借贷";

                  // 获取显示的资产名称
                  const displayAsset = position.tokenList && position.tokenList.length > 0 ? position.tokenList[0].tokenSymbol : position.asset;

                  return (
                    <TableRow key={index}>
                      <TableCell>{displayAsset}</TableCell>
                      <TableCell>{position.protocol}</TableCell>
                      <TableCell>{investType}</TableCell>
                      <TableCell className="text-right">{displayAmount}</TableCell>
                      <TableCell className="text-right">{formatCurrency(value)}</TableCell>
                      <TableCell className="text-right">{position.apy ? <span className={cn(position.apy > 0 ? "text-green-500" : "text-red-500")}>{formatPercentage(position.apy)}</span> : <span className="text-muted-foreground">-</span>}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default PortfolioOverview;
