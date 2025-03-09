"use client";

import React from "react";
import { Portfolio } from "../services/api";

interface Position {
  protocol: string;
  asset: string;
  amount: number;
  leverage?: number;
  apy?: number;
}

interface RiskMonitorProps {
  portfolio: Portfolio | null;
}

const RiskMonitor: React.FC<RiskMonitorProps> = ({ portfolio }) => {
  if (!portfolio) {
    return (
      <div>
        <h2 className="text-xl font-bold mb-6">风险监控</h2>
        <div className="flex justify-center items-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-t-primary border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
        </div>
      </div>
    );
  }

  const getRiskScore = (risk_level: string): number => {
    switch (risk_level.toUpperCase()) {
      case "HIGH":
        return 0.8;
      case "MEDIUM":
        return 0.5;
      case "LOW":
        return 0.2;
      default:
        return 0.5;
    }
  };

  const riskScore = getRiskScore(portfolio.risk_level);

  const getRiskLevel = (score: number) => {
    if (score < 0.3)
      return {
        level: "低风险",
        color: "text-success",
        bg: "bg-success/10",
        border: "border-success/20",
        percent: Math.round(score * 100),
      };
    if (score < 0.7)
      return {
        level: "中等风险",
        color: "text-warning",
        bg: "bg-warning/10",
        border: "border-warning/20",
        percent: Math.round(score * 100),
      };
    return {
      level: "高风险",
      color: "text-error",
      bg: "bg-error/10",
      border: "border-error/20",
      percent: Math.round(score * 100),
    };
  };

  const { level, color, bg, border, percent } = getRiskLevel(riskScore);

  // 计算每个资产的风险评分
  const assetRiskScores = portfolio.positions
    .map((position) => {
      const asset = position.asset.split("/")[0];
      const marketData = portfolio.market_analysis[asset];
      const aiPrediction = portfolio.ai_predictions[asset];

      // 基于市场数据和AI预测计算风险分数
      let riskScore = 0.5; // 默认中等风险

      if (marketData) {
        // 波动性风险
        if (marketData.volatility_30d > 20) {
          riskScore += 0.2;
        } else if (marketData.volatility_30d < 5) {
          riskScore -= 0.1;
        }

        // 价格变化风险
        if (Math.abs(marketData.price_change_24h) > 10) {
          riskScore += 0.1;
        }
      }

      if (aiPrediction) {
        // AI预测风险
        if (aiPrediction.risk_level.toUpperCase() === "HIGH") {
          riskScore += 0.2;
        } else if (aiPrediction.risk_level.toUpperCase() === "LOW") {
          riskScore -= 0.1;
        }
      }

      // 杠杆风险
      if (position.leverage && position.leverage > 1.5) {
        riskScore += 0.2 * position.leverage;
      }

      // 确保风险分数在0-1之间
      riskScore = Math.max(0, Math.min(1, riskScore));

      return {
        position,
        riskScore,
        riskLevel: getRiskLevel(riskScore),
      };
    })
    .sort((a, b) => b.riskScore - a.riskScore); // 按风险从高到低排序

  return (
    <div>
      <h2 className="text-xl font-bold mb-6">风险监控</h2>

      <div className="space-y-6">
        <div className="flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <span className="text-muted">总体风险等级</span>
            <span className={`font-medium ${color}`}>{level}</span>
          </div>

          <div className="w-full h-3 bg-background rounded-full overflow-hidden">
            <div className={`h-full ${bg}`} style={{ width: `${percent}%` }}></div>
          </div>

          <div className="flex justify-between text-xs text-muted">
            <span>低</span>
            <span>中</span>
            <span>高</span>
          </div>
        </div>

        <div className={`p-4 rounded-xl ${bg} ${border} border`}>
          <div className="flex justify-between items-center">
            <div>
              <span className="text-sm text-muted">投资组合总值</span>
              <div className="text-xl font-bold">${portfolio.total_value.toLocaleString()}</div>
            </div>
            <div className={`w-12 h-12 rounded-full ${bg} ${color} flex items-center justify-center`}>
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            </div>
          </div>
        </div>

        {/* 风险建议 */}
        {portfolio.recommendations && portfolio.recommendations.length > 0 && (
          <div className="p-4 rounded-xl bg-muted/20 border border-muted">
            <h3 className="font-medium mb-2">风险建议</h3>
            <ul className="space-y-1 text-sm">
              {portfolio.recommendations.map((rec, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-primary mt-0.5">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-medium">头寸风险分析</h3>
            <span className="text-xs px-2 py-1 rounded-md bg-background text-muted">{portfolio.positions.length} 个头寸</span>
          </div>

          <div className="space-y-3">
            {assetRiskScores.map(({ position, riskScore, riskLevel }, index) => (
              <div key={index} className={`p-3 rounded-xl border ${riskLevel.border} ${riskLevel.bg} transition-colors`}>
                <div className="flex justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-medium">{position.asset.substring(0, 2)}</div>
                    <span className="font-medium">
                      {position.protocol} - {position.asset}
                    </span>
                  </div>
                  <span className={`font-medium ${riskLevel.color}`}>{riskLevel.level}</span>
                </div>

                <div className="w-full h-2 bg-background rounded-full overflow-hidden mb-2">
                  <div className={`h-full ${riskLevel.bg}`} style={{ width: `${riskLevel.percent}%` }}></div>
                </div>

                <div className="flex flex-wrap gap-2 mt-2">
                  {position.leverage && (
                    <span className="px-2 py-1 text-xs rounded-md bg-background text-muted">
                      杠杆率: <span className={position.leverage > 1.5 ? "font-medium text-warning" : "font-medium"}>{position.leverage}x</span>
                    </span>
                  )}
                  {position.apy && (
                    <span className="px-2 py-1 text-xs rounded-md bg-background text-muted">
                      APY: <span className="font-medium">{(position.apy * 100).toFixed(2)}%</span>
                    </span>
                  )}
                  {portfolio.market_analysis[position.asset.split("/")[0]] && (
                    <span className="px-2 py-1 text-xs rounded-md bg-background text-muted">
                      波动率: <span className="font-medium">{portfolio.market_analysis[position.asset.split("/")[0]].volatility_30d.toFixed(2)}%</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskMonitor;
