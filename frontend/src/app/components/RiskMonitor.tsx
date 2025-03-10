"use client";

import React from "react";
import { Portfolio } from "../services/api";
import { AlertTriangle, Shield, TrendingDown, Zap, BarChart3, DollarSign, Percent, ChartBar, Target, Wallet } from "lucide-react";

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
        <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          风险监控
        </h2>
        <div className="flex justify-center items-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-t-primary border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
        </div>
      </div>
    );
  }

  const getRiskScore = (risk_level: string): number => {
    switch (risk_level.toUpperCase()) {
      case "HIGH":
      case "高":
        return 0.8;
      case "MEDIUM":
      case "中":
        return 0.5;
      case "LOW":
      case "低":
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
        icon: <Shield className="h-4 w-4" />,
      };
    if (score < 0.7)
      return {
        level: "中等风险",
        color: "text-amber-500",
        bg: "bg-amber-500/10",
        border: "border-amber-500/20",
        percent: Math.round(score * 100),
        icon: <AlertTriangle className="h-4 w-4" />,
      };
    return {
      level: "高风险",
      color: "text-destructive",
      bg: "bg-destructive/10",
      border: "border-destructive/20",
      percent: Math.round(score * 100),
      icon: <Zap className="h-4 w-4" />,
    };
  };

  const { level, color, bg, border, percent, icon } = getRiskLevel(riskScore);

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

  // 计算风险分布
  const riskDistribution = {
    high: assetRiskScores.filter((item) => item.riskScore >= 0.7).length,
    medium: assetRiskScores.filter((item) => item.riskScore >= 0.3 && item.riskScore < 0.7).length,
    low: assetRiskScores.filter((item) => item.riskScore < 0.3).length,
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
        <Shield className="h-5 w-5 text-primary" />
        风险监控
      </h2>

      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
            <div className="flex items-center gap-2 text-muted mb-2">
              <Shield className="h-4 w-4" />
              <span className="text-sm">风险等级</span>
            </div>
            <div className="flex items-center gap-2">
              <p className={`text-xl font-bold ${color}`}>{level}</p>
              <span className={`text-xs px-2 py-0.5 rounded-full ${bg} ${color}`}>{percent}%</span>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
            <div className="flex items-center gap-2 text-muted mb-2">
              <Target className="h-4 w-4" />
              <span className="text-sm">风险分布</span>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-success"></span>
                <span className="text-xs text-muted">低({riskDistribution.low})</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                <span className="text-xs text-muted">中({riskDistribution.medium})</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-destructive"></span>
                <span className="text-xs text-muted">高({riskDistribution.high})</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
            <div className="flex items-center gap-2 text-muted mb-2">
              <Wallet className="h-4 w-4" />
              <span className="text-sm">投资组合总值</span>
            </div>
            <p className="text-xl font-bold">${portfolio.total_value.toLocaleString()}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
            <h3 className="font-medium mb-4 flex items-center gap-2">
              <ChartBar className="h-4 w-4 text-primary" />
              风险评分分布
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted">总体风险</span>
                <span className={`text-sm font-medium ${color}`}>{percent}%</span>
              </div>
              <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                <div className={`h-full ${bg} transition-all duration-1000 ease-out`} style={{ width: `${percent}%` }}></div>
              </div>
              <div className="grid grid-cols-3 text-xs text-muted">
                <div className="flex items-center gap-1">
                  <Shield className="h-3 w-3 text-success" />
                  <span>低风险</span>
                </div>
                <div className="flex items-center gap-1 justify-center">
                  <AlertTriangle className="h-3 w-3 text-amber-500" />
                  <span>中等风险</span>
                </div>
                <div className="flex items-center gap-1 justify-end">
                  <Zap className="h-3 w-3 text-destructive" />
                  <span>高风险</span>
                </div>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-all">
            <h3 className="font-medium mb-4 flex items-center gap-2">
              <Target className="h-4 w-4 text-primary" />
              风险类型分布
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted">市场波动风险</span>
                <span className="text-sm font-medium">{Math.round(riskScore * 100)}%</span>
              </div>
              <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                <div className="h-full bg-amber-500/50" style={{ width: `${Math.round(riskScore * 100)}%` }}></div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted">清算风险</span>
                <span className="text-sm font-medium">{Math.round(riskScore * 80)}%</span>
              </div>
              <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                <div className="h-full bg-destructive/50" style={{ width: `${Math.round(riskScore * 80)}%` }}></div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted">无常损失风险</span>
                <span className="text-sm font-medium">{Math.round(riskScore * 60)}%</span>
              </div>
              <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                <div className="h-full bg-primary/50" style={{ width: `${Math.round(riskScore * 60)}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* 风险建议 */}
        {portfolio.recommendations && portfolio.recommendations.length > 0 && (
          <div className="p-4 rounded-xl bg-muted/20 border border-muted hover:shadow-md transition-all">
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              风险建议
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {portfolio.recommendations.map((rec, index) => (
                <div key={index} className="p-3 rounded-lg bg-background/50 hover:bg-background transition-colors flex items-start gap-2">
                  <div className={`mt-0.5 w-5 h-5 rounded-full ${bg} ${color} flex items-center justify-center flex-shrink-0 text-xs`}>
                    {index + 1}
                  </div>
                  <p className="text-sm">{rec}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 头寸风险分析 */}
        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-medium flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary" />
              头寸风险分析
            </h3>
            <span className="text-xs px-2 py-1 rounded-md bg-background text-muted">
              {portfolio.positions.length} 个头寸
            </span>
          </div>

          <div className="space-y-3">
            {assetRiskScores.map(({ position, riskScore, riskLevel }, index) => {
              const asset = position.asset.split("/")[0];
              const marketData = portfolio.market_analysis[asset];
              const value = position.amount * (marketData?.current_price || 0);
              const percentOfTotal = (value / portfolio.total_value) * 100;

              return (
                <div key={index} className={`p-4 rounded-xl border ${riskLevel.border} ${riskLevel.bg} hover:shadow-md transition-all group`}>
                  <div className="flex justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-full ${riskLevel.bg} ${riskLevel.color} flex items-center justify-center text-xs font-medium transition-all group-hover:scale-110`}>
                        {position.asset.substring(0, 2)}
                      </div>
                      <div>
                        <span className="font-medium group-hover:text-primary transition-colors">{position.protocol}</span>
                        <p className="text-xs text-muted">{position.asset}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`font-medium ${riskLevel.color} flex items-center gap-1`}>
                        {riskLevel.icon}
                        {riskLevel.level}
                      </span>
                      <p className="text-xs text-muted">
                        ${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        <span className="ml-1">({percentOfTotal.toFixed(1)}%)</span>
                      </p>
                    </div>
                  </div>

                  <div className="w-full h-2 bg-background rounded-full overflow-hidden mb-3">
                    <div
                      className={`h-full transition-all duration-500 ease-out group-hover:opacity-90`}
                      style={{
                        width: `${riskLevel.percent}%`,
                        background: `linear-gradient(90deg, ${riskLevel.percent < 30 ? "#16a34a" : riskLevel.percent < 70 ? "#f59e0b" : "#dc2626"} 0%, ${riskLevel.percent < 30 ? "#22c55e" : riskLevel.percent < 70 ? "#fbbf24" : "#ef4444"} 100%)`,
                      }}
                    ></div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {position.leverage && (
                      <span className={`px-2 py-1 text-xs rounded-md bg-background flex items-center gap-1 ${position.leverage > 1.5 ? "text-amber-500" : "text-muted"}`}>
                        <Zap className="h-3 w-3" />
                        杠杆率: <span className="font-medium">{position.leverage}x</span>
                      </span>
                    )}
                    {position.apy && (
                      <span className="px-2 py-1 text-xs rounded-md bg-background text-muted flex items-center gap-1">
                        <Percent className="h-3 w-3" />
                        APY: <span className="font-medium text-success">{(position.apy * 100).toFixed(2)}%</span>
                      </span>
                    )}
                    {marketData && (
                      <span className="px-2 py-1 text-xs rounded-md bg-background text-muted flex items-center gap-1">
                        <TrendingDown className="h-3 w-3" />
                        波动率: <span className="font-medium">{marketData.volatility_30d.toFixed(2)}%</span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskMonitor;
