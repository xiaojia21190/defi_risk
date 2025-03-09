"use client";

import React from "react";
import { Portfolio, MarketPrediction, Alert as ApiAlert } from "../services/api";

interface AlertsListProps {
  portfolio: Portfolio;
  predictions: { [key: string]: MarketPrediction };
}

interface Alert {
  id: string;
  type: "liquidation" | "marketVolatility" | "technicalSignal" | "riskWarning" | "opportunityAlert";
  severity: "high" | "medium" | "low";
  message: string;
  timestamp: string;
  protocol: string;
  asset: string;
  details?: {
    value?: number;
    threshold?: number;
    recommendation?: string;
  };
}

const severityOrder: Record<Alert["severity"], number> = {
  high: 0,
  medium: 1,
  low: 2,
};

// 映射后端警报类型到前端类型
const mapAlertType = (backendType: string): Alert["type"] => {
  const typeMap: Record<string, Alert["type"]> = {
    LIQUIDATION_RISK: "liquidation",
    HIGH_VOLATILITY: "marketVolatility",
    PRICE_CHANGE: "marketVolatility",
    OVERBOUGHT: "technicalSignal",
    OVERSOLD: "technicalSignal",
    MA_CROSS: "technicalSignal",
    APY_CHANGE: "opportunityAlert",
    CORRELATION_CHANGE: "riskWarning",
  };

  return typeMap[backendType] || "riskWarning";
};

// 映射后端严重程度到前端严重程度
const mapSeverity = (backendSeverity: string): Alert["severity"] => {
  if (backendSeverity === "HIGH") return "high";
  if (backendSeverity === "MEDIUM") return "medium";
  return "low";
};

const AlertsList: React.FC<AlertsListProps> = ({ portfolio, predictions }) => {
  // 生成警报列表
  const generateAlerts = () => {
    const alerts: Alert[] = [];

    // 从市场预测中获取警报
    for (const asset in predictions) {
      const prediction = predictions[asset];
      if (prediction.alerts && prediction.alerts.length > 0) {
        for (const apiAlert of prediction.alerts) {
          alerts.push({
            id: `${apiAlert.type}-${apiAlert.asset}-${apiAlert.timestamp}`,
            type: mapAlertType(apiAlert.type),
            severity: mapSeverity(apiAlert.severity),
            message: apiAlert.message,
            timestamp: new Date(apiAlert.timestamp * 1000).toISOString(),
            protocol: apiAlert.protocol,
            asset: apiAlert.asset,
            details: {
              recommendation: apiAlert.details?.recommendation,
              value: apiAlert.details?.value || apiAlert.details?.volatility || apiAlert.details?.leverage,
              threshold: apiAlert.details?.threshold || apiAlert.details?.safe_leverage,
            },
          });
        }
      }
    }

    // 保留原有的警报生成逻辑作为备份
    if (alerts.length === 0) {
      // 检查每个资产的风险
      for (const position of portfolio.positions) {
        const asset = position.asset.split("/")[0];
        const prediction = predictions[asset];
        const marketAnalysis = portfolio.market_analysis[asset];
        const aiPrediction = portfolio.ai_predictions[asset];

        if (!marketAnalysis || !aiPrediction) continue;

        // 价格波动警报
        if (Math.abs(marketAnalysis.price_change_24h) > 5) {
          alerts.push({
            id: `price-${asset}`,
            type: "marketVolatility" as const,
            severity: Math.abs(marketAnalysis.price_change_24h) > 10 ? ("high" as const) : ("medium" as const),
            message: `${asset} 价格在24小时内${marketAnalysis.price_change_24h > 0 ? "上涨" : "下跌"}了 ${Math.abs(marketAnalysis.price_change_24h).toFixed(2)}%`,
            timestamp: new Date().toISOString(),
            protocol: position.protocol,
            asset: asset,
            details: {
              value: marketAnalysis.price_change_24h,
              threshold: 5,
              recommendation: marketAnalysis.price_change_24h > 0 ? "考虑获利了结部分头寸" : "关注支撑位，可能是买入机会",
            },
          });
        }

        // 杠杆风险警报
        if (position.leverage && position.leverage > 1.5) {
          alerts.push({
            id: `leverage-${asset}`,
            type: "liquidation" as const,
            severity: position.leverage > 1.8 ? ("high" as const) : ("medium" as const),
            message: `${position.protocol} 上的 ${asset} 头寸杠杆率较高 (${position.leverage.toFixed(2)}x)`,
            timestamp: new Date().toISOString(),
            protocol: position.protocol,
            asset: asset,
            details: {
              value: position.leverage,
              threshold: 1.5,
              recommendation: "考虑降低杠杆率以减少清算风险",
            },
          });
        }

        // AI预测警报
        if (aiPrediction.risk_level === "HIGH") {
          alerts.push({
            id: `ai-${asset}`,
            type: "riskWarning" as const,
            severity: "high" as const,
            message: `AI预测 ${asset} 存在高风险，建议关注`,
            timestamp: new Date().toISOString(),
            protocol: position.protocol,
            asset: asset,
            details: {
              recommendation: "考虑减少敞口或设置止损",
            },
          });
        }

        // 波动率警报
        if (marketAnalysis.volatility_30d > 15) {
          alerts.push({
            id: `volatility-${asset}`,
            type: "riskWarning" as const,
            severity: marketAnalysis.volatility_30d > 25 ? ("high" as const) : ("medium" as const),
            message: `${asset} 30天波动率较高 (${marketAnalysis.volatility_30d.toFixed(2)}%)`,
            timestamp: new Date().toISOString(),
            protocol: position.protocol,
            asset: asset,
            details: {
              value: marketAnalysis.volatility_30d,
              threshold: 15,
              recommendation: "高波动率可能带来更大风险，建议减少头寸或对冲风险",
            },
          });
        }

        // 技术指标警报
        if (prediction && prediction.signals && prediction.signals.length > 0) {
          const signalAlert = prediction.signals.find((signal) => signal.includes("买入") || signal.includes("卖出") || signal.includes("突破"));

          if (signalAlert) {
            alerts.push({
              id: `signal-${asset}`,
              type: "technicalSignal" as const,
              severity: "medium" as const,
              message: `${asset} 技术指标: ${signalAlert}`,
              timestamp: new Date().toISOString(),
              protocol: position.protocol,
              asset: asset,
              details: {
                recommendation: signalAlert.includes("买入") ? "考虑增加头寸" : "考虑减少头寸",
              },
            });
          }
        }

        // 机会警报
        if (aiPrediction.trend === "bullish" && aiPrediction.trend_strength === "strong") {
          const predictedGain = (aiPrediction.predicted_price_range["24h"][1] / marketAnalysis.current_price - 1) * 100;
          if (predictedGain > 5) {
            alerts.push({
              id: `opportunity-${asset}`,
              type: "opportunityAlert" as const,
              severity: "low" as const,
              message: `${asset} 可能有上涨机会，AI预测24小时内可能上涨${predictedGain.toFixed(2)}%`,
              timestamp: new Date().toISOString(),
              protocol: position.protocol,
              asset: asset,
              details: {
                value: predictedGain,
                threshold: 5,
                recommendation: "考虑增加头寸或设置止盈位置",
              },
            });
          }
        }
      }
    }

    return alerts.sort((a, b) => {
      return severityOrder[a.severity as keyof typeof severityOrder] - severityOrder[b.severity as keyof typeof severityOrder];
    });
  };

  const alerts = generateAlerts();

  if (alerts.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 rounded-full bg-success/10 text-success mx-auto mb-4 flex items-center justify-center">
          <span className="text-2xl">✓</span>
        </div>
        <h3 className="text-lg font-medium mb-2">暂无风险警报</h3>
        <p className="text-muted">您的投资组合目前运行正常</p>
      </div>
    );
  }

  // 获取警报类型的图标和颜色
  const getAlertTypeInfo = (type: Alert["type"], severity: Alert["severity"]) => {
    const severityColor = severity === "high" ? "destructive" : severity === "medium" ? "warning" : "success";

    switch (type) {
      case "liquidation":
        return {
          icon: "!",
          title: "清算风险",
          bgColor: `bg-${severityColor}/20`,
          textColor: `text-${severityColor}`,
        };
      case "marketVolatility":
        return {
          icon: "⚠",
          title: "市场波动",
          bgColor: `bg-${severityColor}/20`,
          textColor: `text-${severityColor}`,
        };
      case "technicalSignal":
        return {
          icon: "📊",
          title: "技术信号",
          bgColor: `bg-${severityColor}/20`,
          textColor: `text-${severityColor}`,
        };
      case "riskWarning":
        return {
          icon: "⚠",
          title: "风险警告",
          bgColor: `bg-${severityColor}/20`,
          textColor: `text-${severityColor}`,
        };
      case "opportunityAlert":
        return {
          icon: "💡",
          title: "机会提示",
          bgColor: `bg-${severityColor}/20`,
          textColor: `text-${severityColor}`,
        };
      default:
        return {
          icon: "⚠",
          title: "警报",
          bgColor: `bg-${severityColor}/20`,
          textColor: `text-${severityColor}`,
        };
    }
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">风险警报</h2>
      <div className="space-y-4">
        {alerts.map((alert) => {
          const { icon, title, bgColor, textColor } = getAlertTypeInfo(alert.type, alert.severity);
          const severityText = alert.severity === "high" ? "高风险" : alert.severity === "medium" ? "中等风险" : "低风险";
          const severityBg = alert.severity === "high" ? "bg-destructive/20 text-destructive" : alert.severity === "medium" ? "bg-warning/20 text-warning" : "bg-success/20 text-success";

          return (
            <div key={alert.id} className={`p-4 rounded-lg border ${alert.severity === "high" ? "border-destructive/50 bg-destructive/10" : alert.severity === "medium" ? "border-warning/50 bg-warning/10" : "border-success/50 bg-success/10"}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${bgColor} ${textColor}`}>{icon}</div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium">{title}</h4>
                      <span className="text-xs text-muted">- {alert.protocol}</span>
                    </div>
                    <p className="text-sm text-muted">{alert.asset}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${severityBg}`}>{severityText}</span>
              </div>
              <p className="text-sm mb-2">{alert.message}</p>
              {alert.details?.recommendation && <p className="text-xs text-muted italic mt-1">建议: {alert.details.recommendation}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AlertsList;
