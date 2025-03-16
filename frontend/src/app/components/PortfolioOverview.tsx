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
    const marketAnalysis = portfolio.market_analysis[pos.asset.split("/")[0]];
    const value = pos.amount * (marketAnalysis?.current_price || 0);
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
    const asset = pos.asset.split("/")[0];
    const marketAnalysis = portfolio.market_analysis[asset];
    const value = pos.amount * (marketAnalysis?.current_price || 0);

    // 简单分类资产类型
    let type = "其他";
    if (asset === "ETH" || asset === "WETH" || asset === "BTC") {
      type = "主流币";
    } else if (asset === "USDC" || asset === "USDT" || asset === "DAI") {
      type = "稳定币";
    } else if (asset.includes("LP") || asset.includes("Pool")) {
      type = "流动性代币";
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
                  <th className="text-right py-2 font-medium">数量</th>
                  <th className="text-right py-2 font-medium">价值</th>
                  <th className="text-right py-2 font-medium">收益率</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((position, index) => {
                  const asset = position.asset.split("/")[0];
                  const marketAnalysis = portfolio.market_analysis[asset];
                  const value = position.amount * (marketAnalysis?.current_price || 0);

                  return (
                    <tr key={index} className="border-b hover:bg-muted/20">
                      <td className="py-2">{position.asset}</td>
                      <td className="py-2">{position.protocol}</td>
                      <td className="py-2 text-right">{position.amount.toFixed(4)}</td>
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
