"use client";

import React from "react";
import { Portfolio } from "../services/api";
import { PieChart } from "react-minimal-pie-chart";
import { TrendingUp, Wallet, BarChart3, Percent, ChartBar, Target, DollarSign, ArrowUpDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";

interface PortfolioOverviewProps {
  portfolio: Portfolio | null;
}

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ portfolio }) => {
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
    const assetSymbol = pos.tokenList && pos.tokenList.length > 0
      ? pos.tokenList[0].tokenSymbol.split("/")[0]
      : pos.asset.split("/")[0];

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
    const assetSymbol = pos.tokenList && pos.tokenList.length > 0
      ? pos.tokenList[0].tokenSymbol.split("/")[0]
      : pos.asset.split("/")[0];

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
    const apys = portfolio.positions.map(pos => pos.apy || 0);
    const avgAPY = apys.reduce((sum, apy) => sum + apy, 0) / apys.length;

    if (avgAPY > 15) return "高";
    if (avgAPY > 5) return "中";
    return "低";
  };

  // 计算杠杆使用情况
  const calculateLeverageUsage = () => {
    const leveragedPositions = portfolio.positions.filter(pos => pos.leverage && pos.leverage > 1);
    const avgLeverage = leveragedPositions.length > 0
      ? leveragedPositions.reduce((sum, pos) => sum + (pos.leverage || 1), 0) / leveragedPositions.length
      : 1;

    if (avgLeverage > 2) return "高";
    if (avgLeverage > 1.5) return "中";
    return "低";
  };

  // 计算多样性得分
  const calculateDiversityScore = () => {
    const protocols = new Set(portfolio.positions.map(pos => pos.protocol)).size;
    const assets = new Set(portfolio.positions.map(pos => pos.asset)).size;

    const protocolScore = Math.min(protocols / 3, 1); // 最多3个协议为满分
    const assetScore = Math.min(assets / 5, 1); // 最多5个资产为满分

    const score = (protocolScore + assetScore) / 2 * 100;

    if (score > 70) return "高";
    if (score > 40) return "中";
    return "低";
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
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
        <CardDescription>
          总资产价值: {formatCurrency(portfolio.total_value)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-medium mb-4">资产分布</h3>
            <div className="w-full aspect-square max-w-[250px] mx-auto">
              {pieData.length > 0 ? (
                <PieChart
                  data={pieData}
                  lineWidth={40}
                  paddingAngle={2}
                  rounded
                  label={({ dataEntry }) =>
                    dataEntry.value > portfolio.total_value * 0.05 ? dataEntry.title : ''
                  }
                  labelStyle={{
                    fontSize: '5px',
                    fontWeight: 'bold',
                    fill: '#fff',
                  }}
                  labelPosition={70}
                />
              ) : (
                <div className="flex items-center justify-center h-full bg-muted/20 rounded-full">
                  <p className="text-muted-foreground">暂无数据</p>
                </div>
              )}
            </div>
          </div>
          <div>
            <h3 className="text-lg font-medium mb-4">投资组合指标</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="mr-2 p-2 bg-primary/10 rounded-full">
                    <Percent className="h-5 w-5 text-primary" />
                  </div>
                  <span>平均收益率</span>
                </div>
                <div className="flex items-center">
                  <span className="mr-2">{formatPercentage(totalAPY)}</span>
                  <Badge variant={apyTrend === "高" ? "success" : apyTrend === "中" ? "warning" : "outline"}>
                    {apyTrend}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="mr-2 p-2 bg-secondary/10 rounded-full">
                    <Target className="h-5 w-5 text-secondary" />
                  </div>
                  <span>多样性</span>
                </div>
                <div className="flex items-center">
                  <Badge variant={diversityScore === "高" ? "success" : diversityScore === "中" ? "warning" : "destructive"}>
                    {diversityScore}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="mr-2 p-2 bg-accent/10 rounded-full">
                    <ArrowUpDown className="h-5 w-5 text-accent" />
                  </div>
                  <span>杠杆使用</span>
                </div>
                <div className="flex items-center">
                  <Badge variant={leverageUsage === "低" ? "success" : leverageUsage === "中" ? "warning" : "destructive"}>
                    {leverageUsage}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="text-lg font-medium mb-4">资产列表</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 font-medium">资产</th>
                  <th className="text-left py-2 font-medium">协议</th>
                  <th className="text-left py-2 font-medium">类型</th>
                  <th className="text-right py-2 font-medium">数量</th>
                  <th className="text-right py-2 font-medium">价值</th>
                  <th className="text-right py-2 font-medium">收益率</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((position, index) => {
                  // 获取资产符号，优先使用tokenList
                  const assetSymbol = position.tokenList && position.tokenList.length > 0
                    ? position.tokenList[0].tokenSymbol.split("/")[0]
                    : position.asset.split("/")[0];

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
                  const displayAsset = position.tokenList && position.tokenList.length > 0
                    ? position.tokenList[0].tokenSymbol
                    : position.asset;

                  return (
                    <tr key={index} className="border-b hover:bg-muted/20">
                      <td className="py-2">{displayAsset}</td>
                      <td className="py-2">{position.protocol}</td>
                      <td className="py-2">{investType}</td>
                      <td className="py-2 text-right">{displayAmount}</td>
                      <td className="py-2 text-right">{formatCurrency(value)}</td>
                      <td className="py-2 text-right">
                        {position.apy ? (
                          <span className={position.apy > 0 ? "text-success" : "text-destructive"}>
                            {formatPercentage(position.apy)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default PortfolioOverview;
