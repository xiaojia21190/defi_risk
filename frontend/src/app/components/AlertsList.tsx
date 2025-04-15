"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback, memo } from "react";
import { apiService } from "../services/api";
import { AlertTriangle, BarChart3, Lightbulb, CheckCircle, Bell, Wallet, Target, ArrowUpDown, Loader2, Filter, RefreshCw, Clock, ArrowDownUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface AlertsListProps {
  address?: string;
}

interface Alert {
  id: string;
  type: "liquidation" | "marketVolatility" | "technicalSignal" | "riskWarning" | "opportunityAlert" | "infoNotice";
  severity: "high" | "medium" | "low" | "info";
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
  info: number;
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
  info: {
    label: "信息",
    color: "outline",
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
  infoNotice: {
    label: "信息通知",
    icon: <CheckCircle className="w-4 h-4" />,
  },
};

// 映射后端警报类型到前端类型
const mapAlertType = (type: string): Alert["type"] => {
  const typeMap: Record<string, Alert["type"]> = {
    liquidation_risk: "liquidation",
    market_volatility: "marketVolatility",
    price_volatility: "marketVolatility",
    technical_signal: "technicalSignal",
    risk_warning: "riskWarning",
    opportunity: "opportunityAlert",
    info: "infoNotice",
  };

  return typeMap[type] || "riskWarning";
};

// 映射后端严重性到前端严重性
const mapSeverity = (severity: string): Alert["severity"] => {
  const severityMap: Record<string, Alert["severity"]> = {
    high: "high",
    medium: "medium",
    low: "low",
    info: "info",
  };

  return severityMap[severity] || "medium";
};

// 提取为子组件: 警报卡片
const AlertCard = memo(({ alert, index }: { alert: Alert; index: number }) => {
  const [expanded, setExpanded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const severityConfig = severityConfigs[alert.severity];
  const typeConfig = typeConfigs[alert.type];

  // 格式化时间戳
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch (e) {
      return timestamp;
    }
  };

  const toggleExpand = () => {
    setExpanded(!expanded);
  };

  const hasDetails = alert.details && Object.keys(alert.details).some((key) => key !== "recommendation" && alert.details?.[key] !== undefined);

  // 根据严重性获取背景图案类
  const getSeverityPatternClass = () => {
    switch (alert.severity) {
      case "high":
        return "bg-risk-pattern-red";
      case "medium":
        return "bg-risk-pattern-amber";
      case "low":
        return "bg-risk-pattern-green";
      default:
        return "";
    }
  };

  return (
    <motion.div
      layout
      key={alert.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.3,
        delay: index * 0.05,
        layout: { duration: 0.3, type: "spring" },
      }}
      className={cn(
        "relative overflow-hidden p-4 rounded-lg border shadow-sm",
        "transition-all duration-300 hover:shadow-md group",
        "bg-background",
        expanded ? "bg-opacity-100" : "bg-opacity-90",
        getSeverityPatternClass(),
        alert.severity === "high" ? "border-destructive/50 hover:border-destructive/80" : alert.severity === "medium" ? "border-warning/50 hover:border-warning/80" : "border-success/50 hover:border-success/80"
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 装饰性边栏 */}
      <div className={cn("absolute left-0 top-0 bottom-0 w-1.5", alert.severity === "high" ? "bg-destructive" : alert.severity === "medium" ? "bg-amber-500" : "bg-green-500", expanded && "w-2")} />

      <div className="flex items-start justify-between gap-4 ml-2">
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <Badge variant={severityConfig.color} className={cn("flex items-center gap-1 transition-all duration-300", isHovered && "shadow-sm")}>
              <motion.span animate={{ rotate: isHovered && alert.severity === "high" ? [0, -5, 5, -5, 5, 0] : 0 }} transition={{ duration: 0.5 }}>
                {severityConfig.icon}
              </motion.span>
              <span>{severityConfig.label}</span>
            </Badge>
            <Badge variant="secondary" className={cn("flex items-center gap-1 transition-all duration-300", isHovered && "shadow-sm")}>
              {typeConfig.icon}
              <span>{typeConfig.label}</span>
            </Badge>
            <span className={cn("ml-auto text-xs text-muted-foreground", "transition-opacity duration-300", expanded ? "opacity-70" : "opacity-100")}>{formatTimestamp(alert.timestamp)}</span>
          </div>

          <motion.h4 className={cn("font-medium transition-all duration-300", expanded ? "text-base mb-3" : "text-sm mb-2", alert.severity === "high" && "text-destructive/90")} layout>
            {alert.message}
          </motion.h4>

          <div className="flex flex-wrap gap-2 mt-2">
            <Badge variant="outline" className="text-xs bg-background/70 backdrop-blur-sm">
              协议: {alert.protocol}
            </Badge>
            <Badge variant="outline" className="text-xs bg-background/70 backdrop-blur-sm">
              资产: {alert.asset}
            </Badge>
          </div>

          {alert.details?.recommendation && (
            <motion.div layout className={cn("mt-3 text-sm", expanded ? "text-foreground" : "text-muted-foreground", "p-2 rounded-md bg-background/50 backdrop-blur-sm border border-border/50")}>
              <span className="font-medium">建议: </span>
              {alert.details.recommendation}
            </motion.div>
          )}

          {/* 详细信息部分 */}
          <AnimatePresence>
            {expanded && hasDetails && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3, type: "spring", stiffness: 100 }} className="pt-3 mt-4 border-t">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {alert.details?.value !== undefined && (
                    <div className="p-2 text-sm rounded-md bg-background/50 backdrop-blur-sm">
                      <span className="font-medium">当前值: </span>
                      {alert.details.value}
                    </div>
                  )}
                  {alert.details?.threshold !== undefined && (
                    <div className="p-2 text-sm rounded-md bg-background/50 backdrop-blur-sm">
                      <span className="font-medium">阈值: </span>
                      {alert.details.threshold}
                    </div>
                  )}
                  {alert.details?.leverage !== undefined && (
                    <div className="p-2 text-sm rounded-md bg-background/50 backdrop-blur-sm">
                      <span className="font-medium">杠杆率: </span>
                      {alert.details.leverage}x
                    </div>
                  )}
                  {alert.details?.current_apy !== undefined && (
                    <div className="p-2 text-sm rounded-md bg-background/50 backdrop-blur-sm">
                      <span className="font-medium">当前 APY: </span>
                      {alert.details.current_apy}%
                    </div>
                  )}
                  {alert.details?.previous_apy !== undefined && (
                    <div className="p-2 text-sm rounded-md bg-background/50 backdrop-blur-sm">
                      <span className="font-medium">之前 APY: </span>
                      {alert.details.previous_apy}%
                    </div>
                  )}
                  {alert.details?.apy_change !== undefined && (
                    <div className="p-2 text-sm rounded-md bg-background/50 backdrop-blur-sm">
                      <span className="font-medium">APY 变化: </span>
                      <span className={alert.details.apy_change > 0 ? "text-green-500" : "text-destructive"}>
                        {alert.details.apy_change > 0 ? "+" : ""}
                        {alert.details.apy_change}%
                      </span>
                    </div>
                  )}
                  {alert.details?.volatility !== undefined && (
                    <div className="p-2 text-sm rounded-md bg-background/50 backdrop-blur-sm">
                      <span className="font-medium">波动率: </span>
                      {alert.details.volatility}%
                    </div>
                  )}
                  {alert.details?.price_change_24h !== undefined && (
                    <div className="p-2 text-sm rounded-md bg-background/50 backdrop-blur-sm">
                      <span className="font-medium">24小时价格变化: </span>
                      <span className={alert.details.price_change_24h > 0 ? "text-green-500" : "text-destructive"}>
                        {alert.details.price_change_24h > 0 ? "+" : ""}
                        {alert.details.price_change_24h}%
                      </span>
                    </div>
                  )}
                </div>
                {alert.details?.analysis && (
                  <div className="p-3 mt-3 text-sm border rounded-md bg-background/70 backdrop-blur-sm border-border/50">
                    <span className="block mb-1 font-medium">分析: </span>
                    {alert.details.analysis}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* 展开按钮 */}
      {hasDetails && (
        <Button variant="ghost" size="sm" className={cn("absolute bottom-2 right-2", "transition-all duration-300", isHovered ? "opacity-90" : "opacity-60", "hover:opacity-100", expanded && "bg-background/80 backdrop-blur-sm")} onClick={toggleExpand}>
          <motion.span animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.3 }} className="mr-1">
            {expanded ? "↑" : "↓"}
          </motion.span>
          {expanded ? "收起" : "详情"}
        </Button>
      )}
    </motion.div>
  );
});
AlertCard.displayName = "AlertCard";

// 提取为子组件: 头部组件
const AlertHeader = memo(
  ({
    stats,
    lastRefreshTime,
    refreshing,
    loading,
    handleRefresh,
    autoRefresh,
    toggleAutoRefresh,
    refreshInterval,
    handleIntervalChange,
  }: {
    stats: AlertStats;
    lastRefreshTime: string;
    refreshing: boolean;
    loading: boolean;
    handleRefresh: () => void;
    autoRefresh: boolean;
    toggleAutoRefresh: () => void;
    refreshInterval: number;
    handleIntervalChange: (value: string) => void;
  }) => {
    return (
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
    );
  }
);
AlertHeader.displayName = "AlertHeader";

// 提取为子组件: 筛选器
const AlertFilters = memo(({ filter, setFilter }: { filter: { severity: string | null; type: string | null; sortBy?: string }; setFilter: React.Dispatch<React.SetStateAction<{ severity: string | null; type: string | null; sortBy?: string }>> }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasActiveFilters = filter.severity || filter.type || (filter.sortBy && filter.sortBy !== "time");

  // 获取筛选状态标签文本
  const getFilterStatusText = () => {
    const parts = [];

    if (filter.severity) {
      const label =
        {
          high: "高风险",
          medium: "中风险",
          low: "低风险",
        }[filter.severity] || filter.severity;
      parts.push(`严重性: ${label}`);
    }

    if (filter.type) {
      const config = typeConfigs[filter.type];
      parts.push(`类型: ${config?.label || filter.type}`);
    }

    if (filter.sortBy && filter.sortBy !== "time") {
      const sortLabel =
        {
          severity: "按严重性",
          type: "按类型",
          time: "按时间",
        }[filter.sortBy] || filter.sortBy;
      parts.push(`排序: ${sortLabel}`);
    }

    return parts.length > 0 ? parts.join(" · ") : "全部警报";
  };

  return (
    <motion.div layout transition={{ duration: 0.2 }} className={cn("mb-6 border rounded-lg transition-all overflow-hidden", hasActiveFilters ? "bg-muted/20 border-muted shadow-sm" : "bg-muted/10 hover:bg-muted/30", isExpanded && "shadow-md")}>
      {/* 折叠/展开头部 */}
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="flex items-center gap-2">
          <Filter className={cn("w-4 h-4 transition-colors", hasActiveFilters ? "text-primary" : "text-muted-foreground")} />
          <div className="flex flex-col">
            <h3 className="flex items-center gap-1 text-sm font-medium">
              筛选警报
              {hasActiveFilters && (
                <Badge variant="secondary" className="h-5 px-1 ml-2 bg-background">
                  {Object.values(filter).filter(Boolean).length}
                </Badge>
              )}
            </h3>
            {hasActiveFilters && <p className="max-w-md text-xs truncate text-muted-foreground">{getFilterStatusText()}</p>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              className="px-2 text-xs h-7"
              onClick={(e) => {
                e.stopPropagation();
                setFilter({ severity: null, type: null, sortBy: "time" });
              }}
            >
              重置
            </Button>
          )}
          <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <Button
              variant="ghost"
              size="sm"
              className="p-0 h-7 w-7"
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
            >
              <ArrowDownUp size={14} />
            </Button>
          </motion.div>
        </div>
      </div>

      {/* 筛选控件 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}>
            <div className="px-4 pt-3 pb-4 border-t">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">严重性</label>
                  <Select value={filter.severity || "all"} onValueChange={(value: string) => setFilter({ ...filter, severity: value === "all" ? null : value })}>
                    <SelectTrigger className="w-full h-9">
                      <SelectValue placeholder="所有严重性" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all" className="flex items-center gap-1">
                        <span className="w-3 h-3 rounded-full bg-primary/20"></span>
                        全部严重性
                      </SelectItem>
                      <SelectItem value="high" className="flex items-center gap-1">
                        <span className="w-3 h-3 rounded-full bg-destructive"></span>
                        高风险
                      </SelectItem>
                      <SelectItem value="medium" className="flex items-center gap-1">
                        <span className="w-3 h-3 rounded-full bg-amber-500"></span>
                        中风险
                      </SelectItem>
                      <SelectItem value="low" className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                        低风险
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">警报类型</label>
                  <Select value={filter.type || "all"} onValueChange={(value: string) => setFilter({ ...filter, type: value === "all" ? null : value })}>
                    <SelectTrigger className="w-full h-9">
                      <SelectValue placeholder="所有类型" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部类型</SelectItem>
                      {Object.entries(typeConfigs).map(([type, config]) => (
                        <SelectItem key={type} value={type} className="flex items-center gap-1">
                          <span className="flex items-center justify-center">{config.icon}</span>
                          {config.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">排序方式</label>
                  <Select value={filter.sortBy || "time"} onValueChange={(value: string) => setFilter({ ...filter, sortBy: value })}>
                    <SelectTrigger className="w-full h-9">
                      <SelectValue placeholder="时间" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="time" className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        时间 (最新)
                      </SelectItem>
                      <SelectItem value="severity" className="flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        严重性
                      </SelectItem>
                      <SelectItem value="type" className="flex items-center gap-1">
                        <Filter className="w-3.5 h-3.5" />
                        警报类型
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
});
AlertFilters.displayName = "AlertFilters";

// 提取为子组件: 统计卡片
const AlertStats = memo(({ stats }: { stats: AlertStats }) => {
  if (stats.total === 0) return null;

  const statCards = [
    {
      label: "总警报",
      count: stats.total,
      icon: <Bell className="w-8 h-8 opacity-80 text-primary" />,
      color: "bg-secondary/30",
      textColor: stats.total > 0 ? "text-primary" : "",
      borderColor: "border-border/50",
      animate: false,
    },
    {
      label: "高风险",
      count: stats.high,
      icon: <AlertTriangle className={cn("h-8 w-8 opacity-80", stats.high > 0 ? "text-destructive" : "text-muted-foreground")} />,
      color: stats.high > 0 ? "bg-destructive/10" : "bg-secondary/30",
      textColor: stats.high > 0 ? "text-destructive" : "",
      borderColor: stats.high > 0 ? "border-destructive/30" : "border-border/50",
      animate: stats.high > 0,
    },
    {
      label: "中风险",
      count: stats.medium,
      icon: <Bell className={cn("h-8 w-8 opacity-80", stats.medium > 0 ? "text-amber-500" : "text-muted-foreground")} />,
      color: stats.medium > 0 ? "bg-amber-500/10" : "bg-secondary/30",
      textColor: stats.medium > 0 ? "text-amber-500" : "",
      borderColor: stats.medium > 0 ? "border-amber-500/30" : "border-border/50",
      animate: stats.medium > 0,
    },
    {
      label: "低风险",
      count: stats.low,
      icon: <CheckCircle className={cn("h-8 w-8 opacity-80", stats.low > 0 ? "text-green-500" : "text-muted-foreground")} />,
      color: stats.low > 0 ? "bg-green-500/10" : "bg-secondary/30",
      textColor: stats.low > 0 ? "text-green-500" : "",
      borderColor: stats.low > 0 ? "border-green-500/30" : "border-border/50",
      animate: stats.low > 0,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 mb-6 md:grid-cols-4">
      {statCards.map((card, index) => (
        <motion.div key={card.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: index * 0.1 }} className="relative">
          <Card className={cn("transition-all duration-300 hover:shadow-md border", card.color, card.borderColor, card.animate && "hover:-translate-y-1")}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{card.label}</p>
                  <motion.p
                    className={cn("text-2xl font-bold", card.textColor)}
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    transition={{
                      type: "spring",
                      stiffness: 200,
                      damping: 10,
                      delay: 0.2 + index * 0.1,
                    }}
                  >
                    {card.count}
                  </motion.p>
                </div>
                <motion.div
                  animate={
                    card.animate
                      ? {
                          rotate: [0, -5, 5, -5, 5, 0],
                          scale: [1, 1.1, 1],
                        }
                      : {}
                  }
                  transition={{
                    duration: 1.5,
                    repeat: 0,
                    delay: 0.5 + index * 0.2,
                  }}
                >
                  {card.icon}
                </motion.div>
              </div>
            </CardContent>

            {/* 装饰性条纹 */}
            {card.count > 0 && <motion.div className={cn("absolute bottom-0 left-0 right-0 h-1", card.textColor.replace("text-", "bg-"))} initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: 0.8, delay: 0.2 + index * 0.1 }} />}
          </Card>
        </motion.div>
      ))}
    </div>
  );
});
AlertStats.displayName = "AlertStats";

// 骨架屏加载组件
const AlertSkeleton = memo(() => {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="p-4 border rounded-lg shadow-sm bg-background animate-pulse">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-20 h-6 rounded-md bg-muted"></div>
            <div className="w-24 h-6 rounded-md bg-muted"></div>
            <div className="w-32 h-4 ml-auto rounded-md bg-muted"></div>
          </div>
          <div className="w-3/4 h-4 mb-4 rounded-md bg-muted"></div>
          <div className="flex gap-2 mb-2">
            <div className="w-24 h-5 rounded-md bg-muted"></div>
            <div className="w-24 h-5 rounded-md bg-muted"></div>
          </div>
        </div>
      ))}
    </div>
  );
});
AlertSkeleton.displayName = "AlertSkeleton";

// 提取为子组件: 空态和加载状态
const AlertsState = memo(({ loading, error, filteredAlerts, handleRefresh, stats }: { loading: boolean; error: string | null; filteredAlerts: Alert[]; handleRefresh: () => void; stats: AlertStats }) => {
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex flex-col items-center justify-center py-6 mb-4 border border-dashed rounded-lg bg-muted/20">
          <Loader2 className="w-8 h-8 mb-4 animate-spin text-primary" />
          <p className="text-muted-foreground">正在加载警报数据...</p>
        </div>
        <AlertSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-10 text-center border rounded-lg bg-destructive/5 border-destructive/20">
        <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-destructive" />
        <h3 className="mb-2 text-lg font-medium text-destructive/90">加载失败</h3>
        <p className="max-w-md mx-auto mb-4 text-muted-foreground">{error}</p>
        <Button onClick={handleRefresh} className="gap-2 shadow-sm">
          <RefreshCw className="w-4 h-4" />
          重试
        </Button>
      </motion.div>
    );
  }

  // 检查是否只有信息通知类型的警报
  const hasOnlyInfoAlerts = filteredAlerts.length > 0 && filteredAlerts.every((alert) => alert.type === "infoNotice" || alert.severity === "info");

  if (filteredAlerts.length === 0 || hasOnlyInfoAlerts) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={cn("py-12 text-center rounded-lg border border-dashed", stats.total > 0 && !hasOnlyInfoAlerts ? "bg-muted/20 border-muted" : "glass-effect bg-success/5")}>
        {stats.total > 0 && !hasOnlyInfoAlerts ? (
          <>
            <Filter className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-70" />
            <h3 className="mb-2 text-lg font-medium">没有匹配结果</h3>
            <p className="max-w-md mx-auto text-muted-foreground">没有符合当前筛选条件的警报，请尝试调整筛选条件</p>
          </>
        ) : (
          <>
            <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }} transition={{ duration: 0.5, type: "spring" }}>
              <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500 opacity-80" />
            </motion.div>
            <h3 className="mb-2 text-xl font-medium">一切安好</h3>
            <p className="max-w-md mx-auto text-muted-foreground">{hasOnlyInfoAlerts && filteredAlerts[0]?.message ? filteredAlerts[0].message : "您的投资组合目前没有任何风险警报，我们将持续监控市场变化"}</p>
            {hasOnlyInfoAlerts && filteredAlerts[0]?.details?.recommendation && <p className="max-w-md mx-auto mt-2 text-sm text-muted-foreground">{filteredAlerts[0].details.recommendation}</p>}
          </>
        )}
      </motion.div>
    );
  }

  return null;
});
AlertsState.displayName = "AlertsState";

const AlertsList: React.FC<AlertsListProps> = ({ address }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<AlertStats>({ total: 0, high: 0, medium: 0, low: 0, info: 0, byType: {} });
  const [filter, setFilter] = useState<{ severity: string | null; type: string | null; sortBy?: string }>({
    severity: null,
    type: null,
    sortBy: "time",
  });
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(60); // 默认60秒
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [lastRefreshTime, setLastRefreshTime] = useState<string>("");

  // 只在address变化时获取数据
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
  }, [address]); // 依赖数组中移除了fetchAlerts

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
  }, [autoRefresh, refreshInterval, address]); // 依赖数组中移除了fetchAlerts

  // 使用useCallback优化函数以防止不必要的重新渲染
  const fetchAlerts = useCallback(async () => {
    if (!address) return;

    setRefreshing(true);
    setError(null);

    try {
      const response = await apiService.getAlerts(address);

      // 处理后端返回的数据结构
      // 期望的数据结构: { wallet_address, alerts, alert_count, timestamp, is_demo_data }
      // 或者直接是一个警报数组
      const alertsData = Array.isArray(response) ? response : (response as any).alerts || [];

      // 转换后端数据格式为前端格式
      const formattedAlerts: Alert[] = alertsData.map((alert: any) => ({
        id: alert.id || Math.random().toString(36).substring(2),
        type: mapAlertType(alert.type),
        severity: mapSeverity(alert.severity),
        message: alert.message,
        timestamp: alert.timestamp || new Date().toISOString(),
        protocol: alert.protocol || "Ethereum",
        asset: alert.asset || "未知资产",
        details: alert.details || {},
      }));

      setAlerts(formattedAlerts);
      setLastRefreshTime(new Date().toLocaleTimeString());

      // 计算统计数据 - 排除info类型警报
      const alertsWithoutInfo = formattedAlerts.filter((a) => a.severity !== "info");
      const newStats: AlertStats = {
        total: alertsWithoutInfo.length,
        high: alertsWithoutInfo.filter((a) => a.severity === "high").length,
        medium: alertsWithoutInfo.filter((a) => a.severity === "medium").length,
        low: alertsWithoutInfo.filter((a) => a.severity === "low").length,
        info: formattedAlerts.filter((a) => a.severity === "info").length,
        byType: {},
      };

      alertsWithoutInfo.forEach((alert) => {
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
  }, [address]);

  // 使用useCallback优化事件处理函数
  const handleRefresh = useCallback(() => {
    if (refreshing || !address) return;
    fetchAlerts();
  }, [refreshing, address, fetchAlerts]);

  // 使用useCallback优化事件处理函数
  const toggleAutoRefresh = useCallback(() => {
    setAutoRefresh((prev) => !prev);
  }, []);

  // 使用useCallback优化事件处理函数
  const handleIntervalChange = useCallback((value: string) => {
    setRefreshInterval(parseInt(value));
  }, []);

  // 使用useMemo优化过滤和排序逻辑
  const filteredAlerts = useMemo(() => {
    // 过滤警报
    const filtered = alerts.filter((alert) => {
      const matchesSeverity = !filter.severity || alert.severity === filter.severity;
      const matchesType = !filter.type || alert.type === filter.type;
      return matchesSeverity && matchesType;
    });

    // 根据排序选项对过滤后的警报进行排序
    if (filter.sortBy === "severity") {
      const severityWeight: Record<Alert["severity"], number> = { high: 3, medium: 2, low: 1, info: 0 };
      return [...filtered].sort((a, b) => severityWeight[b.severity] - severityWeight[a.severity]);
    } else if (filter.sortBy === "type") {
      return [...filtered].sort((a, b) => a.type.localeCompare(b.type));
    } else {
      // 默认按时间排序（最新的在前）
      return [...filtered].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    }
  }, [alerts, filter.severity, filter.type, filter.sortBy]);

  return (
    <Card className="transition-all duration-300 hover:shadow-md">
      <AlertHeader stats={stats} lastRefreshTime={lastRefreshTime} refreshing={refreshing} loading={loading} handleRefresh={handleRefresh} autoRefresh={autoRefresh} toggleAutoRefresh={toggleAutoRefresh} refreshInterval={refreshInterval} handleIntervalChange={handleIntervalChange} />

      <CardContent>
        <AlertFilters filter={filter} setFilter={setFilter} />

        <AlertStats stats={stats} />

        <AlertsState loading={loading} error={error} filteredAlerts={filteredAlerts} handleRefresh={handleRefresh} stats={stats} />

        {filteredAlerts.length > 0 && (
          <div className="space-y-4">
            {filteredAlerts.map((alert, index) => (
              <AlertCard key={alert.id} alert={alert} index={index} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AlertsList;
