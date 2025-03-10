"use client";

import React, { useState } from "react";
import { Portfolio, MarketPrediction, Alert as ApiAlert } from "../services/api";
import { AlertTriangle, TrendingDown, TrendingUp, Zap, BarChart3, Lightbulb, CheckCircle, Filter } from "lucide-react";

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
    [key: string]: any; // 添加索引签名以支持后端返回的其他详情字段
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
    PRICE_VOLATILITY: "marketVolatility",
    PRICE_CHANGE: "marketVolatility",
    OVERBOUGHT: "technicalSignal",
    OVERSOLD: "technicalSignal",
    MA_CROSS: "technicalSignal",
    APY_CHANGE: "opportunityAlert",
    CORRELATION_CHANGE: "riskWarning",
    MARKET_TREND: "riskWarning",
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
  const [filter, setFilter] = useState<Alert["type"] | "all">("all");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // 切换警报展开状态
  const toggleExpand = (id: string) => {
    setExpanded((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  // 生成警报列表
  const generateAlerts = () => {
    const alerts: Alert[] = [];

    // 从市场预测中获取警报
    for (const asset in predictions) {
      const prediction = predictions[asset];
      if (prediction.alerts && prediction.alerts.length > 0) {
        for (const apiAlert of prediction.alerts) {
          alerts.push({
            id: `${apiAlert.type}-${apiAlert.asset}-${apiAlert.timestamp}_${apiAlert.protocol}`,
            type: mapAlertType(apiAlert.type),
            severity: mapSeverity(apiAlert.severity),
            message: apiAlert.message,
            timestamp: new Date(apiAlert.timestamp * 1000).toISOString(),
            protocol: apiAlert.protocol,
            asset: apiAlert.asset,
            details: {
              recommendation: apiAlert.details?.recommendation,
              value: apiAlert.details?.value || apiAlert.details?.volatility || apiAlert.details?.leverage || apiAlert.details?.price_change || apiAlert.details?.price_change_24h,
              threshold: apiAlert.details?.threshold || apiAlert.details?.safe_leverage || apiAlert.details?.liquidation_threshold,
              // 保存所有详情字段以便在展开视图中使用
              ...apiAlert.details,
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
            type: "marketVolatility",
            severity: Math.abs(marketAnalysis.price_change_24h) > 10 ? "high" : "medium",
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

        // 波动率警报
        if (marketAnalysis.volatility_30d > 20) {
          alerts.push({
            id: `volatility-${asset}`,
            type: "marketVolatility",
            severity: marketAnalysis.volatility_30d > 30 ? "high" : "medium",
            message: `${asset} 30天波动率达到 ${marketAnalysis.volatility_30d.toFixed(2)}%，高于正常水平`,
            timestamp: new Date().toISOString(),
            protocol: position.protocol,
            asset: asset,
            details: {
              value: marketAnalysis.volatility_30d,
              threshold: 20,
              recommendation: "考虑减少头寸或设置止损",
            },
          });
        }

        // 杠杆风险警报
        if (position.leverage && position.leverage > 1.5) {
          alerts.push({
            id: `leverage-${asset}`,
            type: "liquidation",
            severity: position.leverage > 2 ? "high" : "medium",
            message: `${asset} 头寸使用了 ${position.leverage}x 杠杆，存在清算风险`,
            timestamp: new Date().toISOString(),
            protocol: position.protocol,
            asset: asset,
            details: {
              value: position.leverage,
              threshold: 1.5,
              recommendation: "考虑降低杠杆或增加抵押品",
            },
          });
        }

        // 技术指标警报
        if (aiPrediction.technical_analysis) {
          const { ma_trend, macd_signal } = aiPrediction.technical_analysis;

          if (ma_trend === "bearish" || ma_trend === "看跌") {
            alerts.push({
              id: `ma-${asset}`,
              type: "technicalSignal",
              severity: "medium",
              message: `${asset} 均线呈${ma_trend === "bearish" ? "看跌" : ma_trend}趋势`,
              timestamp: new Date().toISOString(),
              protocol: position.protocol,
              asset: asset,
              details: {
                recommendation: "考虑减少头寸或设置止损",
              },
            });
          }

          if (macd_signal === "sell" || macd_signal === "卖出") {
            alerts.push({
              id: `macd-${asset}`,
              type: "technicalSignal",
              severity: "medium",
              message: `${asset} MACD指标显示${macd_signal === "sell" ? "卖出" : macd_signal}信号`,
              timestamp: new Date().toISOString(),
              protocol: position.protocol,
              asset: asset,
              details: {
                recommendation: "考虑减少头寸",
              },
            });
          }
        }

        // 机会提示
        if (aiPrediction.trend === "bullish" || aiPrediction.trend === "看涨") {
          alerts.push({
            id: `opportunity-${asset}`,
            type: "opportunityAlert",
            severity: "low",
            message: `${asset} 趋势${aiPrediction.trend === "bullish" ? "看涨" : aiPrediction.trend}，可能存在投资机会`,
            timestamp: new Date().toISOString(),
            protocol: position.protocol,
            asset: asset,
            details: {
              recommendation: "考虑增加头寸或设置止盈",
            },
          });
        }
      }
    }

    return alerts.sort((a, b) => {
      return severityOrder[a.severity] - severityOrder[b.severity];
    });
  };

  const alerts = generateAlerts();
  const filteredAlerts = filter === "all" ? alerts : alerts.filter((alert) => alert.type === filter);

  // 获取每种类型的警报数量
  const alertCounts = {
    all: alerts.length,
    liquidation: alerts.filter((a) => a.type === "liquidation").length,
    marketVolatility: alerts.filter((a) => a.type === "marketVolatility").length,
    technicalSignal: alerts.filter((a) => a.type === "technicalSignal").length,
    riskWarning: alerts.filter((a) => a.type === "riskWarning").length,
    opportunityAlert: alerts.filter((a) => a.type === "opportunityAlert").length,
  };

  if (alerts.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 rounded-full bg-success/10 text-success mx-auto mb-4 flex items-center justify-center">
          <CheckCircle className="h-6 w-6" />
        </div>
        <h3 className="text-lg font-medium mb-2">暂无风险警报</h3>
        <p className="text-muted">您的投资组合目前运行正常</p>
      </div>
    );
  }

  // 获取警报类型的图标和颜色
  const getAlertTypeInfo = (type: Alert["type"], severity: Alert["severity"]) => {
    const severityColor = severity === "high" ? "destructive" : severity === "medium" ? "amber-500" : "success";

    switch (type) {
      case "liquidation":
        return {
          icon: <Zap className="h-4 w-4" />,
          title: "清算风险",
          bgColor: `bg-${severityColor}/10`,
          textColor: `text-${severityColor}`,
        };
      case "marketVolatility":
        return {
          icon: <TrendingDown className="h-4 w-4" />,
          title: "市场波动",
          bgColor: `bg-${severityColor}/10`,
          textColor: `text-${severityColor}`,
        };
      case "technicalSignal":
        return {
          icon: <BarChart3 className="h-4 w-4" />,
          title: "技术信号",
          bgColor: `bg-${severityColor}/10`,
          textColor: `text-${severityColor}`,
        };
      case "riskWarning":
        return {
          icon: <AlertTriangle className="h-4 w-4" />,
          title: "风险警告",
          bgColor: `bg-${severityColor}/10`,
          textColor: `text-${severityColor}`,
        };
      case "opportunityAlert":
        return {
          icon: <Lightbulb className="h-4 w-4" />,
          title: "机会提示",
          bgColor: `bg-${severityColor}/10`,
          textColor: `text-${severityColor}`,
        };
      default:
        return {
          icon: <AlertTriangle className="h-4 w-4" />,
          title: "警报",
          bgColor: `bg-${severityColor}/10`,
          textColor: `text-${severityColor}`,
        };
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-primary" />
          风险警报
          <span className="ml-2 text-sm px-2 py-0.5 rounded-full bg-primary/10 text-primary">{alerts.length}</span>
        </h2>

        <div className="flex items-center gap-1 bg-muted/30 p-1 rounded-lg">
          <button onClick={() => setFilter("all")} className={`px-3 py-1 text-xs rounded-lg transition-colors flex items-center gap-1 ${filter === "all" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
            <Filter className="h-3 w-3" />
            全部
            <span className="ml-1 text-xs">{alertCounts.all}</span>
          </button>
          <button onClick={() => setFilter("liquidation")} className={`px-3 py-1 text-xs rounded-lg transition-colors flex items-center gap-1 ${filter === "liquidation" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
            <Zap className="h-3 w-3" />
            清算
            {alertCounts.liquidation > 0 && <span className="ml-1 text-xs">{alertCounts.liquidation}</span>}
          </button>
          <button onClick={() => setFilter("marketVolatility")} className={`px-3 py-1 text-xs rounded-lg transition-colors flex items-center gap-1 ${filter === "marketVolatility" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
            <TrendingDown className="h-3 w-3" />
            波动
            {alertCounts.marketVolatility > 0 && <span className="ml-1 text-xs">{alertCounts.marketVolatility}</span>}
          </button>
          <button onClick={() => setFilter("technicalSignal")} className={`px-3 py-1 text-xs rounded-lg transition-colors flex items-center gap-1 ${filter === "technicalSignal" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
            <BarChart3 className="h-3 w-3" />
            技术
            {alertCounts.technicalSignal > 0 && <span className="ml-1 text-xs">{alertCounts.technicalSignal}</span>}
          </button>
          <button onClick={() => setFilter("opportunityAlert")} className={`px-3 py-1 text-xs rounded-lg transition-colors flex items-center gap-1 ${filter === "opportunityAlert" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
            <Lightbulb className="h-3 w-3" />
            机会
            {alertCounts.opportunityAlert > 0 && <span className="ml-1 text-xs">{alertCounts.opportunityAlert}</span>}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {filteredAlerts.map((alert) => {
          const { icon, title, bgColor: alertBgColor, textColor } = getAlertTypeInfo(alert.type, alert.severity);
          const severityText = alert.severity === "high" ? "高风险" : alert.severity === "medium" ? "中等风险" : "低风险";
          const severityBg = alert.severity === "high" ? "bg-destructive/10 text-destructive" : alert.severity === "medium" ? "bg-amber-500/10 text-amber-500" : "bg-success/10 text-success";

          const borderColor = alert.severity === "high" ? "border-destructive/30" : alert.severity === "medium" ? "border-amber-500/30" : "border-success/30";

          const cardBgColor = alert.severity === "high" ? "bg-destructive/5" : alert.severity === "medium" ? "bg-amber-500/5" : "bg-success/5";

          return (
            <div key={alert.id} className={`p-4 rounded-lg border ${borderColor} ${cardBgColor} hover:shadow-md transition-all group cursor-pointer`} onClick={() => toggleExpand(alert.id)}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${severityBg} group-hover:scale-110 transition-transform`}>{icon}</div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium group-hover:text-primary transition-colors">{title}</h4>
                      <span className="text-xs text-muted">- {alert.protocol}</span>
                    </div>
                    <p className="text-sm text-muted">{alert.asset}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 text-xs rounded-full ${severityBg}`}>{severityText}</span>
                  <span className="text-xs text-muted">{new Date(alert.timestamp).toLocaleDateString()}</span>
                </div>
              </div>
              <p className="text-sm mb-2">{alert.message}</p>

              {expanded[alert.id] && (
                <div className="mt-3 pt-3 border-t border-border animate-fadeIn">
                  {alert.details?.recommendation && (
                    <div className="flex items-start gap-2 mt-2 p-2 rounded-lg bg-muted/30">
                      <Lightbulb className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                      <p className="text-xs">
                        <span className="font-medium">建议: </span>
                        {alert.details.recommendation}
                      </p>
                    </div>
                  )}

                  {/* 显示RSI值 */}
                  {alert.details?.rsi !== undefined && (
                    <div className="mt-2 p-2 rounded-lg bg-muted/30">
                      <p className="text-xs">
                        <span className="font-medium">RSI: </span>
                        {alert.details.rsi.toFixed(2)}
                      </p>
                    </div>
                  )}

                  {/* 显示波动率 */}
                  {alert.details?.volatility !== undefined && (
                    <div className="mt-2 p-2 rounded-lg bg-muted/30">
                      <p className="text-xs">
                        <span className="font-medium">波动率: </span>
                        {alert.details.volatility.toFixed(2)}%
                      </p>
                    </div>
                  )}

                  {/* 显示APY变化 */}
                  {alert.details?.current_apy !== undefined && alert.details?.previous_apy !== undefined && (
                    <div className="mt-2 p-2 rounded-lg bg-muted/30">
                      <p className="text-xs">
                        <span className="font-medium">当前APY: </span>
                        {(alert.details.current_apy * 100).toFixed(2)}%
                      </p>
                      <p className="text-xs">
                        <span className="font-medium">之前APY: </span>
                        {(alert.details.previous_apy * 100).toFixed(2)}%
                      </p>
                      <p className="text-xs">
                        <span className="font-medium">变化: </span>
                        {(alert.details.apy_change ? alert.details.apy_change * 100 : ((alert.details.current_apy - alert.details.previous_apy) / alert.details.previous_apy) * 100).toFixed(2)}%
                      </p>
                    </div>
                  )}

                  {/* 显示移动平均线信息 */}
                  {alert.details?.ma7 !== undefined && alert.details?.ma20 !== undefined && (
                    <div className="mt-2 p-2 rounded-lg bg-muted/30">
                      <p className="text-xs">
                        <span className="font-medium">7日均线: </span>
                        {alert.details.ma7.toFixed(2)}
                      </p>
                      <p className="text-xs">
                        <span className="font-medium">20日均线: </span>
                        {alert.details.ma20.toFixed(2)}
                      </p>
                      {alert.details?.analysis && (
                        <p className="text-xs">
                          <span className="font-medium">分析: </span>
                          {alert.details.analysis}
                        </p>
                      )}
                    </div>
                  )}

                  {/* 显示相关性信息 */}
                  {alert.details?.correlation !== undefined && (
                    <div className="mt-2 p-2 rounded-lg bg-muted/30">
                      <p className="text-xs">
                        <span className="font-medium">相关性: </span>
                        {alert.details.correlation.toFixed(2)}
                      </p>
                      {alert.details?.period && (
                        <p className="text-xs">
                          <span className="font-medium">周期: </span>
                          {alert.details.period}
                        </p>
                      )}
                    </div>
                  )}

                  {/* 显示杠杆信息 */}
                  {alert.details?.leverage !== undefined && (
                    <div className="mt-2 p-2 rounded-lg bg-muted/30">
                      <p className="text-xs">
                        <span className="font-medium">当前杠杆: </span>
                        {alert.details.leverage.toFixed(2)}x
                      </p>
                      {alert.details?.safe_leverage && (
                        <p className="text-xs">
                          <span className="font-medium">安全杠杆: </span>
                          {alert.details.safe_leverage.toFixed(2)}x
                        </p>
                      )}
                      {alert.details?.liquidation_threshold && (
                        <p className="text-xs">
                          <span className="font-medium">清算阈值: </span>
                          {alert.details.liquidation_threshold.toFixed(2)}x
                        </p>
                      )}
                      {alert.details?.risk_ratio && (
                        <p className="text-xs">
                          <span className="font-medium">风险比率: </span>
                          {alert.details.risk_ratio.toFixed(2)}
                        </p>
                      )}
                    </div>
                  )}

                  {/* 显示价格信息 */}
                  {alert.details?.current_price !== undefined && (
                    <div className="mt-2 p-2 rounded-lg bg-muted/30">
                      <p className="text-xs">
                        <span className="font-medium">当前价格: </span>${alert.details.current_price.toFixed(2)}
                      </p>
                      {alert.details?.previous_price && (
                        <p className="text-xs">
                          <span className="font-medium">之前价格: </span>${alert.details.previous_price.toFixed(2)}
                        </p>
                      )}
                      {alert.details?.price_change_24h && (
                        <p className="text-xs">
                          <span className="font-medium">24小时变化: </span>
                          {alert.details.price_change_24h.toFixed(2)}%
                        </p>
                      )}
                    </div>
                  )}

                  {alert.details?.value !== undefined && alert.details?.threshold !== undefined && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-muted mb-1">
                        <span>当前值: {alert.details.value.toFixed(2)}</span>
                        <span>阈值: {alert.details.threshold.toFixed(2)}</span>
                      </div>
                      <div className="w-full h-1.5 bg-muted/30 rounded-full overflow-hidden">
                        <div className={`h-full ${alert.severity === "high" ? "bg-destructive" : alert.severity === "medium" ? "bg-amber-500" : "bg-success"}`} style={{ width: `${Math.min(100, (alert.details.value / alert.details.threshold) * 100)}%` }}></div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-center mt-2">
                <button
                  className="text-xs text-muted hover:text-primary transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleExpand(alert.id);
                  }}
                >
                  {expanded[alert.id] ? "收起" : "查看详情"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AlertsList;
