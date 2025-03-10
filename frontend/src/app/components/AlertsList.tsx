"use client";

import React, { useState, useEffect } from "react";
import { apiService } from "../services/api";
import { AlertTriangle, BarChart3, Lightbulb, CheckCircle, Bell, Wallet, Target, ArrowUpDown, Loader2 } from "lucide-react";

interface AlertsListProps {
  walletAddress: string;
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
    leverage?: number;
    current_apy?: number;
    previous_apy?: number;
    apy_change?: number;
    volatility?: number;
    price_change_24h?: number;
    ma7?: number;
    ma20?: number;
    correlation?: number;
    analysis?: string;
    [key: string]: any;
  };
}

interface AlertStats {
  total: number;
  high: number;
  medium: number;
  low: number;
  byType: Record<string, number>;
}

interface SeverityConfig {
  label: string;
  color: string;
  bg: string;
}

interface AlertTypeConfig {
  label: string;
  icon: React.ReactNode;
  color: string;
  bg: string;
}

interface SeverityConfigMap {
  [key: string]: SeverityConfig;
}

const severityOrder: Record<Alert["severity"], number> = {
  high: 0,
  medium: 1,
  low: 2,
};

const severityConfigMap: SeverityConfigMap = {
  high: {
    label: "高",
    color: "text-destructive",
    bg: "bg-destructive/10",
  },
  medium: {
    label: "中",
    color: "text-amber-500",
    bg: "bg-amber-500/10",
  },
  low: {
    label: "低",
    color: "text-success",
    bg: "bg-success/10",
  },
};

// 更新警报类型映射
const alertTypeConfig: Record<Alert["type"], AlertTypeConfig> = {
  liquidation: {
    label: "清算风险",
    icon: <Wallet className="h-4 w-4" />,
    color: "text-destructive",
    bg: "bg-destructive/10",
  },
  marketVolatility: {
    label: "市场波动",
    icon: <ArrowUpDown className="h-4 w-4" />,
    color: "text-amber-500",
    bg: "bg-amber-500/10",
  },
  technicalSignal: {
    label: "技术信号",
    icon: <BarChart3 className="h-4 w-4" />,
    color: "text-primary",
    bg: "bg-primary/10",
  },
  riskWarning: {
    label: "风险警告",
    icon: <AlertTriangle className="h-4 w-4" />,
    color: "text-destructive",
    bg: "bg-destructive/10",
  },
  opportunityAlert: {
    label: "机会提醒",
    icon: <Lightbulb className="h-4 w-4" />,
    color: "text-success",
    bg: "bg-success/10",
  },
};

// 更新后端警报类型到前端类型的映射
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

const AlertsList: React.FC<AlertsListProps> = ({ walletAddress }) => {
  const [filter, setFilter] = useState<Alert["type"] | "all">("all");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [severityFilter, setSeverityFilter] = useState<Alert["severity"] | "all">("all");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);

      // 获取市场警报
      const apiAlerts = await apiService.getAlerts(walletAddress);

      // 转换警报格式
      const formattedAlerts: Alert[] = apiAlerts.map(apiAlert => ({
        id: `${apiAlert.type}-${apiAlert.asset}-${apiAlert.timestamp}_${apiAlert.protocol}`,
        type: mapAlertType(apiAlert.type),
        severity: mapSeverity(apiAlert.severity),
        message: apiAlert.message,
        timestamp: new Date(apiAlert.timestamp * 1000).toISOString(),
        protocol: apiAlert.protocol,
        asset: apiAlert.asset,
        details: {
          recommendation: apiAlert.details?.recommendation,
          value: apiAlert.details?.value ||
                 apiAlert.details?.volatility ||
                 apiAlert.details?.leverage ||
                 apiAlert.details?.price_change_24h,
          threshold: apiAlert.details?.threshold ||
                    apiAlert.details?.safe_leverage,
          ...apiAlert.details,
        },
      }));

      setAlerts(formattedAlerts);
    } catch (error) {
      console.error("获取警报失败:", error);
      setError("获取警报数据失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  // 过滤和排序警报
  const filteredAlerts = alerts
    .filter((alert) => {
      const matchesType = filter === "all" || alert.type === filter;
      const matchesSeverity = severityFilter === "all" || alert.severity === severityFilter;
      return matchesType && matchesSeverity;
    })
    .sort((a, b) => {
      // 首先按严重程度排序
      const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
      if (severityDiff !== 0) return severityDiff;

      // 然后按时间戳排序（新的在前）
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });

  // 获取警报统计信息
  const alertStats: AlertStats = {
    total: alerts.length,
    high: alerts.filter(a => a.severity === "high").length,
    medium: alerts.filter(a => a.severity === "medium").length,
    low: alerts.filter(a => a.severity === "low").length,
    byType: Object.fromEntries(
      Object.keys(alertTypeConfig).map(type => [
        type,
        alerts.filter(a => a.type === type).length
      ])
    ),
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted">加载警报数据中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive mx-auto mb-4 flex items-center justify-center">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h3 className="text-lg font-medium mb-2">获取警报失败</h3>
        <p className="text-muted mb-4">{error}</p>
        <button
          onClick={fetchAlerts}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Bell className="h-5 w-5 text-primary" />
          风险警报
          <span className="ml-2 text-sm px-2 py-0.5 rounded-full bg-muted">
            {alertStats.total.toString()} 个警报
          </span>
        </h2>
        <div className="flex gap-2">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as Alert["severity"] | "all")}
            className="px-3 py-1 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="all">全部严重度</option>
            {Object.entries(severityConfigMap).map(([value, config]) => (
              <option key={value} value={value}>
                {config.label}级 ({alertStats[value as keyof AlertStats].toString()})
              </option>
            ))}
          </select>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as Alert["type"] | "all")}
            className="px-3 py-1 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="all">全部类型</option>
            {Object.entries(alertTypeConfig).map(([value, config]) => (
              <option key={value} value={value}>
                {config.label} ({alertStats.byType[value].toString()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 警报统计 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-3 rounded-lg bg-card border border-border">
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">高风险</span>
          </div>
          <p className="text-xl font-bold mt-1">{alertStats.high.toString()}</p>
        </div>
        <div className="p-3 rounded-lg bg-card border border-border">
          <div className="flex items-center gap-2 text-amber-500">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">中风险</span>
          </div>
          <p className="text-xl font-bold mt-1">{alertStats.medium.toString()}</p>
        </div>
        <div className="p-3 rounded-lg bg-card border border-border">
          <div className="flex items-center gap-2 text-success">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm font-medium">低风险</span>
          </div>
          <p className="text-xl font-bold mt-1">{alertStats.low.toString()}</p>
        </div>
        <div className="p-3 rounded-lg bg-card border border-border">
          <div className="flex items-center gap-2 text-primary">
            <Target className="h-4 w-4" />
            <span className="text-sm font-medium">总计</span>
          </div>
          <p className="text-xl font-bold mt-1">{alertStats.total.toString()}</p>
        </div>
      </div>

      {/* 警报列表 */}
      <div className="space-y-4">
        {filteredAlerts.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 rounded-full bg-muted mx-auto mb-4 flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-success" />
            </div>
            <h3 className="text-lg font-medium mb-2">暂无警报</h3>
            <p className="text-muted">当前没有符合筛选条件的警报</p>
          </div>
        ) : (
          filteredAlerts.map((alert) => {
            const typeConfig = alertTypeConfig[alert.type];
            const severityConfig = severityConfigMap[alert.severity];
            const isExpanded = expanded[alert.id];

            return (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border transition-all ${severityConfig.bg} ${severityConfig.color} hover:shadow-md`}
                onClick={() => setExpanded({ ...expanded, [alert.id]: !isExpanded })}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-1 ${typeConfig.color}`}>
                    {typeConfig.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${severityConfig.bg} ${severityConfig.color}`}>
                        {severityConfig.label}级
                      </span>
                      <span className="text-xs text-muted">
                        {new Date(alert.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="font-medium">{alert.message}</p>
                    <div className="flex items-center gap-2 mt-1 text-sm">
                      <span className="text-muted">{alert.protocol}</span>
                      <span className="text-muted">·</span>
                      <span className="text-muted">{alert.asset}</span>
                    </div>

                    {isExpanded && alert.details && (
                      <div className="mt-3 space-y-2 text-sm">
                        {alert.details.value !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">当前值</span>
                            <span>{alert.details.value.toFixed(2)}</span>
                          </div>
                        )}
                        {alert.details.threshold !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">阈值</span>
                            <span>{alert.details.threshold.toFixed(2)}</span>
                          </div>
                        )}
                        {alert.details.leverage !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">杠杆率</span>
                            <span className={alert.details.leverage > 1.5 ? "text-destructive" : "text-success"}>
                              {alert.details.leverage.toFixed(2)}x
                            </span>
                          </div>
                        )}
                        {alert.details.current_apy !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">当前APY</span>
                            <span className="text-success">{(alert.details.current_apy * 100).toFixed(2)}%</span>
                          </div>
                        )}
                        {alert.details.previous_apy !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">之前APY</span>
                            <span>{(alert.details.previous_apy * 100).toFixed(2)}%</span>
                          </div>
                        )}
                        {alert.details.apy_change !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">APY变化</span>
                            <span className={alert.details.apy_change > 0 ? "text-success" : "text-destructive"}>
                              {alert.details.apy_change > 0 ? "+" : ""}{(alert.details.apy_change * 100).toFixed(2)}%
                            </span>
                          </div>
                        )}
                        {alert.details.volatility !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">波动率</span>
                            <span className={alert.details.volatility > 20 ? "text-destructive" : "text-amber-500"}>
                              {alert.details.volatility.toFixed(2)}%
                            </span>
                          </div>
                        )}
                        {alert.details.price_change_24h !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">24h价格变化</span>
                            <span className={alert.details.price_change_24h > 0 ? "text-success" : "text-destructive"}>
                              {alert.details.price_change_24h > 0 ? "+" : ""}{alert.details.price_change_24h.toFixed(2)}%
                            </span>
                          </div>
                        )}
                        {alert.details.ma7 !== undefined && alert.details.ma20 !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">均线状态</span>
                            <span>
                              MA7: {alert.details.ma7.toFixed(2)} / MA20: {alert.details.ma20.toFixed(2)}
                            </span>
                          </div>
                        )}
                        {alert.details.correlation !== undefined && (
                          <div className="flex justify-between items-center">
                            <span className="text-muted">相关性</span>
                            <span>{alert.details.correlation.toFixed(2)}</span>
                          </div>
                        )}
                        {alert.details.recommendation && (
                          <div className="mt-3 p-3 rounded-lg bg-background/50">
                            <div className="flex items-center gap-2 mb-1">
                              <Lightbulb className="h-4 w-4 text-primary" />
                              <span className="font-medium">建议</span>
                            </div>
                            <p className="text-muted">{alert.details.recommendation}</p>
                          </div>
                        )}
                        {alert.details.analysis && (
                          <div className="mt-3 p-3 rounded-lg bg-background/50">
                            <div className="flex items-center gap-2 mb-1">
                              <BarChart3 className="h-4 w-4 text-primary" />
                              <span className="font-medium">分析</span>
                            </div>
                            <p className="text-muted">{alert.details.analysis}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default AlertsList;
