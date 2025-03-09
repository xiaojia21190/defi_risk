"use client";

import React from "react";
import { Portfolio } from "../services/api";
import { PieChart } from "react-minimal-pie-chart";

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
    ][index % 5],
  }));

  // 计算总收益率
  const totalAPY = portfolio.positions.reduce((sum, pos) => sum + (pos.apy || 0), 0) / portfolio.positions.length;

  return (
    <div>
      <h2 className="text-xl font-semibold mb-6">投资组合概览</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <div className="mb-6">
            <div className="flex justify-between items-baseline mb-2">
              <h3 className="font-medium">总资产价值</h3>
              <span className="text-2xl font-bold">${portfolio.total_value.toLocaleString()}</span>
            </div>
            <div className="flex justify-between items-center text-sm text-muted">
              <span>平均APY</span>
              <span className="text-success">{(totalAPY * 100).toFixed(2)}%</span>
            </div>
          </div>

          <div className="space-y-4">
            {Object.entries(protocolValues).map(([protocol, value], index) => (
              <div key={protocol} className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: pieData[index].color }} />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline">
                    <span className="font-medium">{protocol}</span>
                    <span className="text-sm text-muted">${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                  </div>
                  <div className="w-full bg-muted/30 rounded-full h-1 mt-1">
                    <div
                      className="h-1 rounded-full"
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
          <div className="relative aspect-square">
            <PieChart
              data={pieData}
              lineWidth={20}
              paddingAngle={2}
              rounded
              label={({ dataEntry }) => `${((dataEntry.value / portfolio.total_value) * 100).toFixed(1)}%`}
              labelStyle={{
                fontSize: "6px",
                fill: "#fff",
                fontWeight: "bold",
              }}
              labelPosition={75}
            />
          </div>
        </div>
      </div>

      <div className="mt-8">
        <h3 className="font-medium mb-4">最大头寸</h3>
        <div className="space-y-3">
          {[...portfolio.positions]
            .sort((a, b) => {
              const aValue = a.amount * (portfolio.market_analysis[a.asset.split("/")[0]]?.current_price || 0);
              const bValue = b.amount * (portfolio.market_analysis[b.asset.split("/")[0]]?.current_price || 0);
              return bValue - aValue;
            })
            .slice(0, 3)
            .map((position, index) => {
              const marketAnalysis = portfolio.market_analysis[position.asset.split("/")[0]];
              const value = position.amount * (marketAnalysis?.current_price || 0);
              return (
                <div key={index} className="p-4 rounded-lg border border-border bg-card/50 hover:bg-card transition-colors">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-medium">{position.asset.substring(0, 2)}</div>
                      <div>
                        <h4 className="font-medium">{position.protocol}</h4>
                        <p className="text-sm text-muted">{position.asset}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                      {position.apy && <p className="text-sm text-success">APY: {(position.apy * 100).toFixed(2)}%</p>}
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
};

export default PortfolioOverview;
