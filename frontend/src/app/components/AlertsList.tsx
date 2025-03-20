"use client";

import React, { useState, useEffect, useRef } from "react";
import { apiService } from "../services/api";
import { AlertTriangle, BarChart3, Lightbulb, CheckCircle, Bell, Wallet, Target, ArrowUpDown, Loader2, Filter, RefreshCw, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

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
  color: "destructive" | "secondary" | "default" | "outline";
  icon: React.ReactNode;
}

const severityConfigs: Record<string, SeverityConfig> = {
  high: {
    label: "高",
    color: "destructive",
    icon: <AlertTriangle className="w-4 h-4" />,
  },
  medium: {
    label: "中",
    color: "secondary",
    icon: <Bell className="w-4 h-4" />,
  },
  low: {
    label: "低",
    color: "default",
    icon: <CheckCircle className="w-4 h-4" />,
  },
};

const typeConfigs: Record<string, { label: string; icon: React.ReactNode }> = {
  liquidation: {
    label: "清算风险",
    icon: <Target className="w-4 h-4" />,
  },
  marketVolatility: {
    label: "市场波动",
    icon: <BarChart3 className="w-4 h-4" />,
  },
  technicalSignal: {
    label: "技术信号",
    icon: <ArrowUpDown className="w-4 h-4" />,
  },
  riskWarning: {
    label: "风险警告",
    icon: <AlertTriangle className="w-4 h-4" />,
  },
  opportunityAlert: {
    label: "机会提示",
    icon: <Lightbulb className="w-4 h-4" />,
  },
};

// 映射后端警报类型到前端类型
const mapAlertType = (type: string): Alert["type"] => {
  const typeMap: Record<string, Alert["type"]> = {
    liquidation_risk: "liquidation",
    market_volatility: "marketVolatility",
    technical_signal: "technicalSignal",
    risk_warning: "riskWarning",
    opportunity: "opportunityAlert",
  };

  return typeMap[type] || "riskWarning";
};

// 映射后端严重性到前端严重性
const mapSeverity = (severity: string): Alert["severity"] => {
  const severityMap: Record<string, Alert["severity"]> = {
    high: "high",
    medium: "medium",
    low: "low",
  };

  return severityMap[severity] || "medium";
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
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(60); // 默认60秒
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [lastRefreshTime, setLastRefreshTime] = useState<string>("");

  useEffect(() => {
    if (address) {
      fetchAlerts();
    } else {
      setLoading(false);
    }

    // 组件卸载时清除定时器
    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [address]);

  // 处理自动刷新
  useEffect(() => {
    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }

    if (autoRefresh && address) {
      refreshTimerRef.current = setInterval(() => {
        fetchAlerts();
      }, refreshInterval * 1000);
    }

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, address]);

  const fetchAlerts = async () => {
    if (!address) return;

    setRefreshing(true);
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
      setLastRefreshTime(new Date().toLocaleTimeString());

      // 计算统计数据
      const newStats: AlertStats = {
        total: formattedAlerts.length,
        high: formattedAlerts.filter((a) => a.severity === "high").length,
        medium: formattedAlerts.filter((a) => a.severity === "medium").length,
        low: formattedAlerts.filter((a) => a.severity === "low").length,
        byType: {},
      };

      formattedAlerts.forEach((alert) => {
        newStats.byType[alert.type] = (newStats.byType[alert.type] || 0) + 1;
      });

      setStats(newStats);
    } catch (err) {
      console.error("获取警报失败:", err);
      setError("无法获取警报数据，请稍后重试");
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  };

  // 手动刷新警报
  const handleRefresh = () => {
    if (refreshing || !address) return;
    fetchAlerts();
  };

  // 切换自动刷新
  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  };

  // 更改刷新间隔
  const handleIntervalChange = (value: string) => {
    setRefreshInterval(parseInt(value));
  };

  // 过滤警报
  const filteredAlerts = alerts.filter((alert) => {
    const matchesSeverity = !filter.severity || alert.severity === filter.severity;
    const matchesType = !filter.type || alert.type === filter.type;
    return matchesSeverity && matchesType;
  });

  // 格式化时间戳
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch (e) {
      return timestamp;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              风险警报
              {stats.total > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {stats.total}
                </Badge>
              )}
            </CardTitle>
            <CardDescription>监控您的DeFi投资风险和市场变化</CardDescription>
          </div>

          <div className="flex items-center gap-4">
            {lastRefreshTime && <span className="hidden text-xs text-muted-foreground sm:inline-block">上次更新: {lastRefreshTime}</span>}

            <div className="flex items-center gap-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="outline" size="sm" className="gap-1" onClick={handleRefresh} disabled={refreshing || loading}>
                      {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                      <span className="hidden sm:inline-block">刷新</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>手动刷新警报</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                      <Switch checked={autoRefresh} onCheckedChange={toggleAutoRefresh} />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>自动刷新警报</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {autoRefresh && (
                <Select value={refreshInterval.toString()} onValueChange={handleIntervalChange}>
                  <SelectTrigger className="h-7 w-[90px]">
                    <SelectValue placeholder="刷新间隔" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="30">30秒</SelectItem>
                    <SelectItem value="60">1分钟</SelectItem>
                    <SelectItem value="300">5分钟</SelectItem>
                    <SelectItem value="600">10分钟</SelectItem>
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* 过滤器 */}
        <div className="flex flex-wrap gap-2 mb-4">
          <div>
            <span className="mr-2 text-xs text-muted-foreground">严重性:</span>
            <div className="flex gap-1 mt-1">
              <Badge variant={!filter.severity ? "default" : "secondary"} className="cursor-pointer" onClick={() => setFilter({ ...filter, severity: null })}>
                全部
              </Badge>
              {Object.entries(severityConfigs).map(([key, config]) => (
                <Badge key={key} variant={filter.severity === key ? (key === "high" ? "destructive" : key === "medium" ? "secondary" : "default") : "outline"} className="cursor-pointer" onClick={() => setFilter({ ...filter, severity: key as Alert["severity"] })}>
                  <div className="flex items-center gap-1">
                    {config.icon}
                    <span>{config.label}</span>
                  </div>
                </Badge>
              ))}
            </div>
          </div>

          <div className="ml-auto">
            <span className="mr-2 text-xs text-muted-foreground">类型:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              <Badge variant={!filter.type ? "default" : "secondary"} className="cursor-pointer" onClick={() => setFilter({ ...filter, type: null })}>
                全部
              </Badge>
              {Object.entries(typeConfigs).map(([key, config]) => (
                <Badge key={key} variant={filter.type === key ? "default" : "secondary"} className="cursor-pointer" onClick={() => setFilter({ ...filter, type: key as Alert["type"] })}>
                  <div className="flex items-center gap-1">
                    {config.icon}
                    <span>{config.label}</span>
                  </div>
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {/* 警报统计 */}
        {stats.total > 0 && (
          <div className="grid grid-cols-2 gap-4 mb-6 md:grid-cols-4">
            <Card className="bg-secondary/30">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">总警报</p>
                    <p className="text-2xl font-bold">{stats.total}</p>
                  </div>
                  <Bell className="w-8 h-8 text-primary opacity-80" />
                </div>
              </CardContent>
            </Card>

            <Card className={cn("transition-colors", stats.high > 0 ? "bg-destructive/10" : "bg-secondary/30")}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">高风险</p>
                    <p className={cn("text-2xl font-bold", stats.high > 0 && "text-destructive")}>{stats.high}</p>
                  </div>
                  <AlertTriangle className={cn("h-8 w-8 opacity-80", stats.high > 0 ? "text-destructive" : "text-muted-foreground")} />
                </div>
              </CardContent>
            </Card>

            <Card className={cn("transition-colors", stats.medium > 0 ? "bg-amber-500/10" : "bg-secondary/30")}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">中风险</p>
                    <p className={cn("text-2xl font-bold", stats.medium > 0 && "text-amber-500")}>{stats.medium}</p>
                  </div>
                  <Bell className={cn("h-8 w-8 opacity-80", stats.medium > 0 ? "text-amber-500" : "text-muted-foreground")} />
                </div>
              </CardContent>
            </Card>

            <Card className={cn("transition-colors", stats.low > 0 ? "bg-green-500/10" : "bg-secondary/30")}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">低风险</p>
                    <p className={cn("text-2xl font-bold", stats.low > 0 && "text-green-500")}>{stats.low}</p>
                  </div>
                  <CheckCircle className={cn("h-8 w-8 opacity-80", stats.low > 0 ? "text-green-500" : "text-muted-foreground")} />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 警报列表 */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="py-8 text-center">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-destructive" />
            <p className="text-muted-foreground">{error}</p>
            <Button className="mt-4" onClick={handleRefresh}>
              重试
            </Button>
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="py-12 text-center">
            <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500 opacity-80" />
            <h3 className="mb-2 text-lg font-medium">暂无警报</h3>
            <p className="text-muted-foreground">{stats.total > 0 ? "没有符合当前筛选条件的警报" : "您的投资组合目前没有任何风险警报"}</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAlerts.map((alert) => {
              const severityConfig = severityConfigs[alert.severity];
              const typeConfig = typeConfigs[alert.type];

              return (
                <Card key={alert.id} className="overflow-hidden">
                  <div className={cn("h-1", severityConfig.color)} />
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant={severityConfig.color} className="flex items-center gap-1">
                            {severityConfig.icon}
                            <span>{severityConfig.label}</span>
                          </Badge>
                          <Badge variant="secondary" className="flex items-center gap-1">
                            {typeConfig.icon}
                            <span>{typeConfig.label}</span>
                          </Badge>
                          <span className="ml-auto text-xs text-muted-foreground">{formatTimestamp(alert.timestamp)}</span>
                        </div>

                        <h4 className="mb-1 font-medium">{alert.message}</h4>

                        <div className="flex flex-wrap gap-2 mt-2">
                          <Badge variant="secondary" className="text-xs">
                            协议: {alert.protocol}
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            资产: {alert.asset}
                          </Badge>
                        </div>

                        {alert.details?.recommendation && (
                          <div className="mt-3 text-sm text-muted-foreground">
                            <span className="font-medium">建议: </span>
                            {alert.details.recommendation}
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AlertsList;
