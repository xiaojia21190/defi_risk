"use client";

import React, { useState, useEffect } from "react";
import { apiService } from "../services/api";
import { AlertTriangle, BarChart3, Lightbulb, CheckCircle, Bell, Wallet, Target, ArrowUpDown, Loader2, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

interface AlertsListProps {
  address?: string;
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
  variant: string;
}

interface AlertTypeConfig {
  label: string;
  icon: React.ReactNode;
  color: string;
  variant: string;
}

interface SeverityConfigMap {
  [key: string]: SeverityConfig;
}

interface AlertTypeConfigMap {
  [key: string]: AlertTypeConfig;
}

const severityConfig: SeverityConfigMap = {
  high: {
    label: "高风险",
    color: "text-destructive",
    variant: "destructive",
  },
  medium: {
    label: "中风险",
    color: "text-warning",
    variant: "warning",
  },
  low: {
    label: "低风险",
    color: "text-success",
    variant: "success",
  },
};

const alertTypeConfig: AlertTypeConfigMap = {
  liquidation: {
    label: "清算风险",
    icon: <AlertTriangle className="h-4 w-4" />,
    color: "text-destructive",
    variant: "destructive",
  },
  marketVolatility: {
    label: "市场波动",
    icon: <BarChart3 className="h-4 w-4" />,
    color: "text-warning",
    variant: "warning",
  },
  technicalSignal: {
    label: "技术信号",
    icon: <ArrowUpDown className="h-4 w-4" />,
    color: "text-primary",
    variant: "default",
  },
  riskWarning: {
    label: "风险警告",
    icon: <Target className="h-4 w-4" />,
    color: "text-destructive",
    variant: "destructive",
  },
  opportunityAlert: {
    label: "机会提醒",
    icon: <Lightbulb className="h-4 w-4" />,
    color: "text-success",
    variant: "success",
  },
};

const mapAlertType = (backendType: string): Alert["type"] => {
  const typeMap: Record<string, Alert["type"]> = {
    "liquidation_risk": "liquidation",
    "market_volatility": "marketVolatility",
    "technical_signal": "technicalSignal",
    "risk_warning": "riskWarning",
    "opportunity": "opportunityAlert",
  };

  return typeMap[backendType] || "riskWarning";
};

const mapSeverity = (backendSeverity: string): Alert["severity"] => {
  if (backendSeverity === "high") return "high";
  if (backendSeverity === "medium") return "medium";
  return "low";
};

const AlertsList: React.FC<AlertsListProps> = ({ address }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<AlertStats>({ total: 0, high: 0, medium: 0, low: 0, byType: {} });
  const [filter, setFilter] = useState<{ severity: string | null; type: string | null }>({
    severity: null,
    type: null,
  });

  useEffect(() => {
    if (address) {
      fetchAlerts();
    } else {
      setLoading(false);
    }
  }, [address]);

  const fetchAlerts = async () => {
    if (!address) return;

    setLoading(true);
    setError(null);

    try {
      const data = await apiService.getAlerts(address);

      // 转换后端数据格式为前端格式
      const formattedAlerts: Alert[] = data.map((alert: any) => ({
        id: alert.id || Math.random().toString(36).substring(2),
        type: mapAlertType(alert.type),
        severity: mapSeverity(alert.severity),
        message: alert.message,
        timestamp: alert.timestamp,
        protocol: alert.protocol || "未知协议",
        asset: alert.asset || "未知资产",
        details: alert.details || {},
      }));

      setAlerts(formattedAlerts);

      // 计算统计数据
      const newStats: AlertStats = {
        total: formattedAlerts.length,
        high: formattedAlerts.filter(a => a.severity === "high").length,
        medium: formattedAlerts.filter(a => a.severity === "medium").length,
        low: formattedAlerts.filter(a => a.severity === "low").length,
        byType: {},
      };

      formattedAlerts.forEach(alert => {
        newStats.byType[alert.type] = (newStats.byType[alert.type] || 0) + 1;
      });

      setStats(newStats);
    } catch (err) {
      console.error("获取警报失败:", err);
      setError("无法获取警报数据，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (timestamp: string | number) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp);
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const filteredAlerts = alerts.filter(alert => {
    if (filter.severity && alert.severity !== filter.severity) return false;
    if (filter.type && alert.type !== filter.type) return false;
    return true;
  });

  const clearFilter = () => {
    setFilter({ severity: null, type: null });
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>风险警报</CardTitle>
          <CardDescription>加载中...</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>风险警报</CardTitle>
          <CardDescription className="text-destructive">{error}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={fetchAlerts} variant="outline">
            重试
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!address) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>风险警报</CardTitle>
          <CardDescription>请连接钱包以查看警报</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (alerts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>风险警报</CardTitle>
          <CardDescription>暂无警报</CardDescription>
        </CardHeader>
        <CardContent className="text-center py-8">
          <CheckCircle className="h-12 w-12 text-success mx-auto mb-4" />
          <p className="text-muted-foreground">您的投资组合目前没有风险警报</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>风险警报</CardTitle>
            <CardDescription>
              共 {stats.total} 条警报
              {filter.severity || filter.type ? " (已筛选)" : ""}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            {(filter.severity || filter.type) && (
              <Button
                variant="outline"
                size="sm"
                onClick={clearFilter}
                className="flex items-center gap-1"
              >
                <Filter className="h-3 w-3" />
                清除筛选
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={fetchAlerts}
              className="flex items-center gap-1"
            >
              <Bell className="h-3 w-3" />
              刷新
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-6 flex flex-wrap gap-2">
          <Badge
            variant={filter.severity === null ? "default" : "outline"}
            className="cursor-pointer"
            onClick={() => setFilter({ ...filter, severity: null })}
          >
            全部 ({stats.total})
          </Badge>
          <Badge
            variant={filter.severity === "high" ? "destructive" : "outline"}
            className="cursor-pointer"
            onClick={() => setFilter({ ...filter, severity: "high" })}
          >
            高风险 ({stats.high})
          </Badge>
          <Badge
            variant={filter.severity === "medium" ? "warning" : "outline"}
            className="cursor-pointer"
            onClick={() => setFilter({ ...filter, severity: "medium" })}
          >
            中风险 ({stats.medium})
          </Badge>
          <Badge
            variant={filter.severity === "low" ? "success" : "outline"}
            className="cursor-pointer"
            onClick={() => setFilter({ ...filter, severity: "low" })}
          >
            低风险 ({stats.low})
          </Badge>
        </div>

        <div className="space-y-4">
          {filteredAlerts.map((alert) => {
            const typeInfo = alertTypeConfig[alert.type];
            const severityInfo = severityConfig[alert.severity];

            return (
              <div
                key={alert.id}
                className="p-4 rounded-lg border bg-card/50 hover:bg-card/80 transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded-full bg-${typeInfo.variant}/10 ${typeInfo.color}`}>
                      {typeInfo.icon}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{typeInfo.label}</span>
                        <Badge variant={severityInfo.variant as any}>
                          {severityInfo.label}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {alert.protocol} · {alert.asset} · {formatDate(alert.timestamp)}
                      </div>
                    </div>
                  </div>
                </div>

                <p className="text-sm mb-3">{alert.message}</p>

                {alert.details && alert.details.recommendation && (
                  <div className="text-xs bg-muted/20 p-2 rounded-md">
                    <span className="font-medium">建议: </span>
                    {alert.details.recommendation}
                  </div>
                )}

                {alert.details && (
                  <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    {alert.details.value !== undefined && (
                      <div className="p-1.5 rounded bg-muted/10">
                        <span className="text-muted-foreground">当前值: </span>
                        <span className="font-medium">{alert.details.value.toFixed(2)}</span>
                      </div>
                    )}
                    {alert.details.threshold !== undefined && (
                      <div className="p-1.5 rounded bg-muted/10">
                        <span className="text-muted-foreground">阈值: </span>
                        <span className="font-medium">{alert.details.threshold.toFixed(2)}</span>
                      </div>
                    )}
                    {alert.details.leverage !== undefined && (
                      <div className="p-1.5 rounded bg-muted/10">
                        <span className="text-muted-foreground">杠杆: </span>
                        <span className="font-medium">{alert.details.leverage.toFixed(2)}x</span>
                      </div>
                    )}
                    {alert.details.volatility !== undefined && (
                      <div className="p-1.5 rounded bg-muted/10">
                        <span className="text-muted-foreground">波动率: </span>
                        <span className="font-medium">{alert.details.volatility.toFixed(2)}%</span>
                      </div>
                    )}
                    {alert.details.price_change_24h !== undefined && (
                      <div className="p-1.5 rounded bg-muted/10">
                        <span className="text-muted-foreground">24h变化: </span>
                        <span className={`font-medium ${alert.details.price_change_24h >= 0 ? 'text-success' : 'text-destructive'}`}>
                          {alert.details.price_change_24h >= 0 ? '+' : ''}
                          {alert.details.price_change_24h.toFixed(2)}%
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {filteredAlerts.length === 0 && (
          <div className="text-center py-8">
            <p className="text-muted-foreground">没有符合筛选条件的警报</p>
            <Button
              variant="outline"
              size="sm"
              onClick={clearFilter}
              className="mt-2"
            >
              清除筛选
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AlertsList;
