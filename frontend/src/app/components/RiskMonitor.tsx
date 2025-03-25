"use client";

import React from "react";
import { Portfolio, MarketPrediction } from "../services/api";
import { AlertTriangle, Shield, TrendingDown, Zap, BarChart3, DollarSign, Percent, ChartBar, Target, Wallet, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Position {
  protocol: string;
  asset: string;
  amount: number;
  leverage?: number;
  apy?: number;
}

interface RiskMonitorProps {
  portfolio: Portfolio;
  analyzing: boolean;
  completed: boolean;
  onAnalyze: () => Promise<void>;
}

const RiskMonitor: React.FC<RiskMonitorProps> = ({ portfolio, analyzing, completed, onAnalyze }) => {
  if (!portfolio) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>风险监控</CardTitle>
          <CardDescription>暂无数据</CardDescription>
        </CardHeader>
      </Card>
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

  const getRiskLevel = (score: number) => {
    if (score >= 0.7) return { level: "高", color: "destructive" };
    if (score >= 0.4) return { level: "中", color: "warning" };
    return { level: "低", color: "success" };
  };

  const riskScore = getRiskScore(portfolio.risk_level);
  const { level, color } = getRiskLevel(riskScore);

  // 计算风险因素
  const calculateRiskFactors = () => {
    const factors = [];

    // 检查高杠杆头寸
    const highLeveragePositions = portfolio.positions.filter((pos) => pos.leverage && pos.leverage > 2);
    if (highLeveragePositions.length > 0) {
      factors.push({
        name: "高杠杆头寸",
        description: `${highLeveragePositions.length}个头寸使用了超过2倍的杠杆`,
        severity: "high",
        icon: <Zap className="w-4 h-4" />,
      });
    }

    // 检查资产集中度
    const totalValue = portfolio.total_value;
    const largePositions = portfolio.positions.filter((pos) => {
      if (!pos.amount) return false;

      const asset = pos.asset.split("/")[0];
      const marketAnalysis = portfolio.market_analysis[asset];
      const currentPrice = marketAnalysis?.current_price ?? 0;
      const value = pos.amount * currentPrice;

      return value / totalValue > 0.3; // 单一资产超过30%
    });

    if (largePositions.length > 0) {
      factors.push({
        name: "资产集中度高",
        description: `${largePositions.length}个资产占比超过30%`,
        severity: "medium",
        icon: <Target className="w-4 h-4" />,
      });
    }

    // 检查高波动性资产
    const volatileAssets = portfolio.positions.filter((pos) => {
      const asset = pos.asset.split("/")[0];
      const marketAnalysis = portfolio.market_analysis[asset];
      return marketAnalysis?.volatility_30d && marketAnalysis.volatility_30d > 0.1; // 30天波动率超过10%
    });

    if (volatileAssets.length > 0) {
      factors.push({
        name: "高波动性资产",
        description: `${volatileAssets.length}个资产30天波动率超过10%`,
        severity: "medium",
        icon: <BarChart3 className="w-4 h-4" />,
      });
    }

    // 如果没有风险因素，添加一个默认的安全提示
    if (factors.length === 0) {
      factors.push({
        name: "风险较低",
        description: "当前投资组合风险较低",
        severity: "low",
        icon: <Shield className="w-4 h-4" />,
      });
    }

    return factors;
  };

  const riskFactors = calculateRiskFactors();

  return (
    <Card>
      <CardHeader>
        <CardTitle>风险监控</CardTitle>
        <CardDescription>
          当前风险等级: <Badge variant={color as any}>{level}</Badge>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-6">
          <div className="w-full bg-muted/30 rounded-full h-2.5 mb-2">
            <div className={`h-2.5 rounded-full ${color === "destructive" ? "bg-destructive" : color === "warning" ? "bg-warning" : "bg-success"}`} style={{ width: `${riskScore * 100}%` }} />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>低风险</span>
            <span>中风险</span>
            <span>高风险</span>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-medium">风险因素</h3>
            <Button onClick={onAnalyze} disabled={analyzing} variant="outline" size="sm" className="gap-2">
              {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
              {analyzing ? "分析中..." : completed ? "更新分析" : "开始分析"}
            </Button>
          </div>
          {riskFactors.map((factor, index) => (
            <div key={index} className={`p-3 rounded-lg border ${factor.severity === "high" ? "border-destructive/50 bg-destructive/10" : factor.severity === "medium" ? "border-warning/50 bg-warning/10" : "border-success/50 bg-success/10"}`}>
              <div className="flex gap-3 items-start">
                <div className={`p-1.5 rounded-full ${factor.severity === "high" ? "bg-destructive/20 text-destructive" : factor.severity === "medium" ? "bg-warning/20 text-warning" : "bg-success/20 text-success"}`}>{factor.icon}</div>
                <div>
                  <h4 className="text-sm font-medium">{factor.name}</h4>
                  <p className="mt-1 text-xs text-muted-foreground">{factor.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6">
          <h3 className="mb-3 text-sm font-medium">优化建议</h3>
          <ul className="space-y-2 text-sm">
            {portfolio.recommendations.map((recommendation, index) => (
              <li key={index} className="flex gap-2 items-start">
                <div className="min-w-4 mt-0.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                </div>
                <span className="text-muted-foreground">{recommendation}</span>
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};

export default RiskMonitor;
