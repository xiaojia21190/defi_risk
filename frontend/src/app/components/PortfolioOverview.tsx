"use client";

import React from "react";
import { PieChart } from "react-minimal-pie-chart";

interface Position {
  protocol: string;
  asset: string;
  amount: number;
  leverage?: number;
  apy?: number;
}

interface Portfolio {
  positions: Position[];
  totalValue: number;
  riskScore: number;
}

interface PortfolioOverviewProps {
  portfolio: Portfolio | null;
}

interface DataEntry {
  title: string;
  value: number;
  color: string;
  percentage?: number;
}

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ portfolio }) => {
  if (!portfolio) {
    return (
      <div className="p-6 bg-white rounded-lg shadow">
        <h2 className="mb-4 text-xl font-bold">投资组合概览</h2>
        <p className="text-gray-600">加载中...</p>
      </div>
    );
  }

  // 按协议分组
  const protocolData = portfolio.positions.reduce((acc: { [key: string]: number }, position) => {
    acc[position.protocol] = (acc[position.protocol] || 0) + position.amount;
    return acc;
  }, {});

  // 生成饼图数据
  const pieData: DataEntry[] = Object.entries(protocolData).map(([protocol, amount], index) => ({
    title: protocol,
    value: amount,
    color: ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF"][index % 5],
  }));

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="mb-4 text-xl font-bold">投资组合概览</h2>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <h3 className="mb-3 text-lg font-semibold">资产分布</h3>
          <div className="w-full h-64">
            <PieChart
              data={pieData}
              label={({ dataEntry }: { dataEntry: DataEntry }) => `${dataEntry.title} (${Math.round(dataEntry.percentage || 0)}%)`}
              labelStyle={{
                fontSize: "5px",
                fontFamily: "sans-serif",
              }}
              labelPosition={60}
              animate
            />
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-lg font-semibold">主要指标</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">总资产价值:</span>
              <span className="font-bold">${portfolio.totalValue.toLocaleString()}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">协议数量:</span>
              <span className="font-bold">{Object.keys(protocolData).length}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">头寸数量:</span>
              <span className="font-bold">{portfolio.positions.length}</span>
            </div>
          </div>

          <div className="mt-6">
            <h3 className="mb-3 text-lg font-semibold">最大头寸</h3>
            {[...portfolio.positions]
              .sort((a, b) => b.amount - a.amount)
              .slice(0, 3)
              .map((position, index) => (
                <div key={index} className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">
                    {position.protocol} - {position.asset}
                  </span>
                  <span className="font-bold">${position.amount.toLocaleString()}</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PortfolioOverview;
