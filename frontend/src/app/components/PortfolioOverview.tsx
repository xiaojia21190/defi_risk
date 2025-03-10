"use client";

import React from "react";
import { Portfolio } from "../services/api";
import { PieChart } from "react-minimal-pie-chart";
import { TrendingUp, Wallet, BarChart3, Percent, ChartBar, Target, DollarSign, ArrowUpDown } from "lucide-react";

interface PortfolioOverviewProps {
  portfolio: Portfolio;
}

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ portfolio }) => {
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
    } else if (pos.asset.includes("/")) {
      type = "LP代币";
    }

    acc[type] = (acc[type] || 0) + value;
    return acc;
  }, {} as { [key: string]: number });

  // 计算总收益率趋势
  const calculateAPYTrend = () => {
    const apyValues = portfolio.positions.map(pos => pos.apy || 0);
    const avgAPY = apyValues.reduce((sum, apy) => sum + apy, 0) / apyValues.length;
    const maxAPY = Math.max(...apyValues);
    const minAPY = Math.min(...apyValues);

    return {
      average: avgAPY,
      max: maxAPY,
      min: minAPY,
      trend: avgAPY > 0.1 ? "上升" : avgAPY < 0.05 ? "下降" : "稳定"
    };
  };

  const apyTrend = calculateAPYTrend();

  // 计算投资组合多样性得分
  const calculateDiversityScore = () => {
    const protocolCount = Object.keys(protocolValues).length;
    const assetTypeCount = Object.keys(assetTypeDistribution).length;
    const maxProtocolShare = Math.max(...Object.values(protocolValues)) / portfolio.total_value;

    // 多样性得分计算 (0-100)
    const protocolScore = Math.min(protocolCount * 20, 100);
    const assetTypeScore = Math.min(assetTypeCount * 25, 100);
    const concentrationScore = Math.max(0, 100 - maxProtocolShare * 100);

    return Math.round((protocolScore + assetTypeScore + concentrationScore) / 3);
  };

  const diversityScore = calculateDiversityScore();

  return (
    <div>
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
        <Wallet className="h-5 w-5 text-primary" />
        投资组合概览
      </h2>

      {/* 总览卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
          <div className="flex items-center gap-2 text-muted mb-2">
            <DollarSign className="h-4 w-4" />
            <span className="text-sm">总资产价值</span>
          </div>
          <p className="text-2xl font-bold">${portfolio.total_value.toLocaleString()}</p>
        </div>

        <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
          <div className="flex items-center gap-2 text-muted mb-2">
            <Percent className="h-4 w-4" />
            <span className="text-sm">平均APY</span>
          </div>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold text-success">{(apyTrend.average * 100).toFixed(2)}%</p>
            <span className={`text-xs px-2 py-0.5 rounded-full ${apyTrend.trend === "上升" ? "bg-success/10 text-success" : apyTrend.trend === "下降" ? "bg-destructive/10 text-destructive" : "bg-amber-500/10 text-amber-500"}`}>
              {apyTrend.trend}
            </span>
          </div>
          <div className="mt-1 text-xs text-muted">
            范围: {(apyTrend.min * 100).toFixed(1)}% - {(apyTrend.max * 100).toFixed(1)}%
          </div>
        </div>

        <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
          <div className="flex items-center gap-2 text-muted mb-2">
            <Target className="h-4 w-4" />
            <span className="text-sm">多样性得分</span>
          </div>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold">{diversityScore}</p>
            <span className={`text-xs px-2 py-0.5 rounded-full ${diversityScore >= 80 ? "bg-success/10 text-success" : diversityScore >= 60 ? "bg-amber-500/10 text-amber-500" : "bg-destructive/10 text-destructive"}`}>
              {diversityScore >= 80 ? "优秀" : diversityScore >= 60 ? "良好" : "需优化"}
            </span>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
          <div className="flex items-center gap-2 text-muted mb-2">
            <BarChart3 className="h-4 w-4" />
            <span className="text-sm">资产数量</span>
          </div>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold">{portfolio.positions.length}</p>
            <span className="text-xs px-2 py-0.5 rounded-full bg-muted">
              {Object.keys(protocolValues).length} 个协议
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
              <ChartBar className="h-4 w-4 text-primary" />
              协议分布
            </h3>
            <div className="space-y-4">
              {Object.entries(protocolValues).map(([protocol, value], index) => (
                <div key={protocol} className="flex items-center gap-3 group">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: pieData[index].color }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-baseline">
                      <span className="font-medium group-hover:text-primary transition-colors">{protocol}</span>
                      <div className="text-right">
                        <span className="text-sm">${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        <span className="text-xs text-muted ml-2">({((value / portfolio.total_value) * 100).toFixed(1)}%)</span>
                      </div>
                    </div>
                    <div className="w-full bg-muted/30 rounded-full h-1.5 mt-1.5 overflow-hidden">
                      <div
                        className="h-1.5 rounded-full transition-all duration-500 ease-out group-hover:opacity-90"
                        style={{
                          width: `${(value / portfolio.total_value) * 100}%`,
                          backgroundColor: pieData[index].color,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
              <ArrowUpDown className="h-4 w-4 text-primary" />
              资产类型分布
            </h3>
            <div className="space-y-4">
              {Object.entries(assetTypeDistribution).map(([type, value], index) => (
                <div key={type} className="flex items-center gap-3 group">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{
                      backgroundColor: [
                        "#2563eb", // 主流币 - 蓝色
                        "#16a34a", // 稳定币 - 绿色
                        "#9333ea", // LP代币 - 紫色
                        "#ea580c", // 其他 - 橙色
                      ][index % 4],
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-baseline">
                      <span className="font-medium group-hover:text-primary transition-colors">{type}</span>
                      <div className="text-right">
                        <span className="text-sm">${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        <span className="text-xs text-muted ml-2">({((value / portfolio.total_value) * 100).toFixed(1)}%)</span>
                      </div>
                    </div>
                    <div className="w-full bg-muted/30 rounded-full h-1.5 mt-1.5 overflow-hidden">
                      <div
                        className="h-1.5 rounded-full transition-all duration-500 ease-out group-hover:opacity-90"
                        style={{
                          width: `${(value / portfolio.total_value) * 100}%`,
                          backgroundColor: [
                            "#2563eb", // 主流币 - 蓝色
                            "#16a34a", // 稳定币 - 绿色
                            "#9333ea", // LP代币 - 紫色
                            "#ea580c", // 其他 - 橙色
                          ][index % 4],
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Percent className="h-4 w-4 text-primary" />
            资产占比
          </h3>
          <div className="relative aspect-square">
            <PieChart
              data={pieData}
              lineWidth={20}
              paddingAngle={2}
              rounded
              animate
              animationDuration={500}
              label={({ dataEntry }) => `${((dataEntry.value / portfolio.total_value) * 100).toFixed(1)}%`}
              labelStyle={{
                fontSize: "6px",
                fill: "#fff",
                fontWeight: "bold",
              }}
              labelPosition={75}
              className="hover:drop-shadow-xl transition-all"
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <p className="text-xs text-muted">总资产</p>
                <p className="text-lg font-bold">${portfolio.total_value.toLocaleString()}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          最大头寸
        </h3>
        <div className="space-y-3">
          {[...portfolio.positions]
            .sort((a, b) => {
              const aValue = a.amount * (portfolio.market_analysis[a.asset.split("/")[0]]?.current_price || 0);
              const bValue = b.amount * (portfolio.market_analysis[b.asset.split("/")[0]]?.current_price || 0);
              return bValue - aValue;
            })
            .slice(0, 3)
            .map((position, index) => {
              const asset = position.asset.split("/")[0];
              const marketAnalysis = portfolio.market_analysis[asset];
              const value = position.amount * (marketAnalysis?.current_price || 0);
              const percentOfTotal = (value / portfolio.total_value) * 100;
              const priceChange = marketAnalysis?.price_change_24h || 0;

              return (
                <div key={index} className="p-4 rounded-lg border border-border bg-card/50 hover:bg-card hover:shadow-md transition-all">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium"
                        style={{
                          background: `linear-gradient(135deg, ${pieData[index % pieData.length].color}33, ${pieData[index % pieData.length].color}66)`,
                          color: pieData[index % pieData.length].color,
                        }}
                      >
                        {position.asset.substring(0, 2)}
                      </div>
                      <div>
                        <h4 className="font-medium">{position.protocol}</h4>
                        <p className="text-sm text-muted">{position.asset}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                      <div className="flex items-center justify-end gap-2 mt-1">
                        {position.apy && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-success/10 text-success">
                            APY: {(position.apy * 100).toFixed(2)}%
                          </span>
                        )}
                        <span className={`text-xs px-2 py-0.5 rounded-full ${priceChange >= 0 ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}`}>
                          {priceChange >= 0 ? "+" : ""}
                          {priceChange.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 w-full bg-muted/30 rounded-full h-1 overflow-hidden">
                    <div
                      className="h-1 rounded-full"
                      style={{
                        width: `${percentOfTotal}%`,
                        backgroundColor: pieData[index % pieData.length].color,
                      }}
                    />
                  </div>
                  <div className="mt-1 text-xs text-muted text-right">占总资产 {percentOfTotal.toFixed(2)}%</div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
};

export default PortfolioOverview;
