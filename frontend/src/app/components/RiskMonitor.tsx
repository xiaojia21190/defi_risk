"use client";

import React from "react";

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

interface RiskMonitorProps {
  portfolio: Portfolio | null;
}

const RiskMonitor: React.FC<RiskMonitorProps> = ({ portfolio }) => {
  if (!portfolio) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">风险监控</h2>
        <p className="text-gray-600">加载中...</p>
      </div>
    );
  }

  const getRiskLevel = (score: number) => {
    if (score < 0.3) return { level: "低风险", color: "text-green-600" };
    if (score < 0.7) return { level: "中等风险", color: "text-yellow-600" };
    return { level: "高风险", color: "text-red-600" };
  };

  const { level, color } = getRiskLevel(portfolio.riskScore);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">风险监控</h2>

      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-600">总体风险等级:</span>
          <span className={`font-bold ${color}`}>{level}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-gray-600">投资组合总值:</span>
          <span className="font-bold">${portfolio.totalValue.toLocaleString()}</span>
        </div>

        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">头寸风险分析</h3>
          <div className="space-y-3">
            {portfolio.positions.map((position, index) => (
              <div key={index} className="bg-gray-50 p-3 rounded">
                <div className="flex justify-between mb-1">
                  <span className="font-medium">
                    {position.protocol} - {position.asset}
                  </span>
                  <span>${position.amount.toLocaleString()}</span>
                </div>
                {position.leverage && <div className="text-sm text-gray-600">杠杆率: {position.leverage}x</div>}
                {position.apy && <div className="text-sm text-gray-600">APY: {(position.apy * 100).toFixed(2)}%</div>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskMonitor;
