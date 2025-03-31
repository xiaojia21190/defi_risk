"use client";

import React from "react";
import { Portfolio, MarketPrediction, WalletRiskAssessment } from "../services/api";
import { AlertTriangle, Shield, TrendingDown, Zap, BarChart3, DollarSign, Percent, ChartBar, Target, Wallet, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Table, TableBody, TableRow, TableCell } from "@/components/ui/table";

interface Position {
  protocol: string;
  asset: string;
  amount: number;
  leverage?: number;
  apy?: number;
}

interface RiskMonitorProps {
  portfolio: Portfolio;
  riskAnalysis?: WalletRiskAssessment | null;
  analyzing: boolean;
  completed: boolean;
  onAnalyze: () => Promise<void>;
}

const RiskMonitor: React.FC<RiskMonitorProps> = ({ portfolio, riskAnalysis, analyzing, completed, onAnalyze }) => {
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

  const getRiskScore = (): number => {
    if (riskAnalysis?.risk_score !== undefined) {
      return riskAnalysis.risk_score / 100; // 转换为0-1范围
    }

    switch (portfolio.risk_level.toUpperCase()) {
      case "HIGH":
      case "高风险":
      case "高":
        return 0.8;
      case "MEDIUM":
      case "中等风险":
      case "中":
        return 0.5;
      case "LOW":
      case "低风险":
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

  const riskScore = getRiskScore();
  const { level, color } = portfolio.risk_level ? { level: portfolio.risk_level, color: riskScore >= 0.7 ? "destructive" : riskScore >= 0.4 ? "warning" : "success" } : getRiskLevel(riskScore);

  // 处理风险因素数据
  const getRiskFactors = () => {
    // 如果有来自API的风险因素，优先使用这些数据
    if (riskAnalysis?.risk_factors && riskAnalysis.risk_factors.length > 0) {
      return riskAnalysis.risk_factors.map((factor) => {
        const severity = factor.score > 60 ? "high" : factor.score > 30 ? "medium" : "low";
        const icon = severity === "high" ? <AlertTriangle className="w-4 h-4" /> : severity === "medium" ? <BarChart3 className="w-4 h-4" /> : <Shield className="w-4 h-4" />;

        return {
          name: factor.name,
          description: factor.description,
          severity,
          icon,
          score: factor.score,
          weight: factor.weight,
          trend: factor.trend,
        };
      });
    }

    // 后备计算逻辑，如果没有API数据
    const factors = [];

    // 检查高杠杆头寸
    const highLeveragePositions = portfolio.positions.filter((pos) => pos.leverage && pos.leverage > 2);
    if (highLeveragePositions.length > 0) {
      factors.push({
        name: "高杠杆头寸",
        description: `${highLeveragePositions.length}个头寸使用了超过2倍的杠杆`,
        severity: "high",
        icon: <Zap className="w-4 h-4" />,
        score: 70,
        weight: 0.3,
        trend: "稳定",
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
        score: 50,
        weight: 0.2,
        trend: "稳定",
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
        score: 40,
        weight: 0.2,
        trend: "稳定",
      });
    }

    // 如果没有风险因素，添加一个默认的安全提示
    if (factors.length === 0) {
      factors.push({
        name: "风险较低",
        description: "当前投资组合风险较低",
        severity: "low",
        icon: <Shield className="w-4 h-4" />,
        score: 20,
        weight: 0.1,
        trend: "稳定",
      });
    }

    return factors;
  };

  const riskFactors = getRiskFactors();

  if (!portfolio.risk_level) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>详细风险分析</CardTitle>
          <CardDescription>分析您的DeFi投资组合风险</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center space-y-4">
            <Shield className="w-12 h-12 text-muted-foreground" />
            <Button onClick={onAnalyze} disabled={analyzing}>
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  分析中...
                </>
              ) : (
                "开始风险分析"
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>详细风险分析</CardTitle>
        <CardDescription>
          当前风险等级: <Badge variant={color as any}>{level}</Badge>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* 风险分数和等级 */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">风险等级</p>
              <div className="flex items-center gap-2">
                <h3 className="text-2xl font-bold">{portfolio.risk_level}</h3>
                {riskAnalysis?.risk_score !== undefined && (
                  <Badge variant="outline" className="text-sm">
                    风险评分: {riskAnalysis.risk_score}/100
                  </Badge>
                )}
              </div>
            </div>
            <Button onClick={onAnalyze} disabled={analyzing} variant="outline" size="sm">
              {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4 mr-2" />}
              {analyzing ? "分析中..." : "重新分析"}
            </Button>
          </div>

          {/* 风险进度条 */}
          <div className="mb-4">
            <div className="w-full bg-muted/30 rounded-full h-2.5 mb-2">
              <div className={`h-2.5 rounded-full ${color === "destructive" ? "bg-destructive" : color === "warning" ? "bg-warning" : "bg-success"}`} style={{ width: `${riskScore * 100}%` }} />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>低风险</span>
              <span>中风险</span>
              <span>高风险</span>
            </div>
          </div>

          {/* 风险因素 */}
          {riskFactors.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-medium">风险因素</h3>
              <div className="space-y-3">
                {riskFactors.map((factor, index) => (
                  <div key={index} className={`p-3 rounded-lg border ${factor.severity === "high" ? "border-destructive/50 bg-destructive/10" : factor.severity === "medium" ? "border-warning/50 bg-warning/10" : "border-success/50 bg-success/10"}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex gap-3 items-start">
                        <div className={`p-1.5 rounded-full ${factor.severity === "high" ? "bg-destructive/20 text-destructive" : factor.severity === "medium" ? "bg-warning/20 text-warning" : "bg-success/20 text-success"}`}>{factor.icon}</div>
                        <div>
                          <h4 className="text-sm font-medium">{factor.name}</h4>
                          <p className="mt-1 text-xs text-muted-foreground">{factor.description}</p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end">
                        <Badge variant="outline" className={`${factor.score > 60 ? "border-destructive text-destructive" : factor.score > 30 ? "border-amber-500 text-amber-500" : "border-green-500 text-green-500"}`}>
                          {factor.score}/100
                        </Badge>
                        <p className="mt-1 text-xs text-muted-foreground">权重: {(factor.weight * 100).toFixed(0)}%</p>
                        {factor.trend && (
                          <Badge variant="outline" className="mt-1">
                            {factor.trend === "上升" ? "↑ " : factor.trend === "下降" ? "↓ " : "→ "}
                            {factor.trend}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 风险指标 */}
          {riskAnalysis?.risk_metrics && Object.keys(riskAnalysis.risk_metrics).length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-medium">风险指标</h3>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(riskAnalysis.risk_metrics).map(([key, value], index) => (
                  <div key={index} className="p-3 rounded-md border">
                    <p className="text-xs text-muted-foreground">{key}</p>
                    <p className="text-sm font-medium">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 优化建议 */}
          {portfolio.recommendations && portfolio.recommendations.length > 0 && (
            <div>
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
          )}

          {/* 预警信息 */}
          {riskAnalysis?.warnings && riskAnalysis.warnings.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-medium">预警信息</h3>
              <div className="space-y-2">
                {riskAnalysis.warnings.map((warning, index) => (
                  <Alert key={index} variant="destructive" className="py-2">
                    <AlertTriangle className="w-4 h-4" />
                    <AlertDescription>{warning}</AlertDescription>
                  </Alert>
                ))}
              </div>
            </div>
          )}

          {/* 监控点 */}
          {riskAnalysis?.monitoring_points && riskAnalysis.monitoring_points.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-medium">监控点</h3>
              <Table>
                <TableBody>
                  {riskAnalysis.monitoring_points.map((point, index) => (
                    <TableRow key={index}>
                      <TableCell className="text-sm">{point}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* 头寸摘要信息 */}
          {riskAnalysis?.positions_summary && (
            <div>
              <h3 className="mb-3 text-sm font-medium">头寸摘要</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-md border">
                  <p className="text-xs text-muted-foreground">总价值</p>
                  <p className="text-sm font-medium">${riskAnalysis.positions_summary.total_value.toLocaleString()}</p>
                </div>
                <div className="p-3 rounded-md border">
                  <p className="text-xs text-muted-foreground">头寸数量</p>
                  <p className="text-sm font-medium">{riskAnalysis.positions_summary.position_count}</p>
                </div>
              </div>

              {riskAnalysis.positions_summary.protocols.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs text-muted-foreground">协议 ({riskAnalysis.positions_summary.protocols.length})</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {riskAnalysis.positions_summary.protocols.map((protocol, index) => (
                      <Badge key={index} variant="secondary" className="text-xs">
                        {protocol}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {riskAnalysis.positions_summary.assets.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs text-muted-foreground">资产 ({riskAnalysis.positions_summary.assets.length})</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {riskAnalysis.positions_summary.assets.map((asset, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {asset}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* AI增强标记 */}
          {riskAnalysis?.ai_enhanced && (
            <div className="mt-4">
              <Badge className="bg-blue-600 hover:bg-blue-700">
                <Zap className="w-3 h-3 mr-1" />
                AI增强分析
              </Badge>
            </div>
          )}

          {/* 分析时间戳 */}
          {riskAnalysis?.analysis_timestamp && <div className="mt-4 text-xs text-muted-foreground">分析时间: {new Date(riskAnalysis.analysis_timestamp).toLocaleString()}</div>}
        </div>
      </CardContent>
    </Card>
  );
};

export default RiskMonitor;
