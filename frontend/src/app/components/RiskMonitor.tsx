"use client";

import React, { useState, useMemo, useEffect } from "react";
import { Portfolio, WalletRiskAssessment } from "../services/api";
import { AlertTriangle, Shield, Zap, BarChart3, Target, Loader2, ChevronDown, Info, TrendingUp, TrendingDown, ArrowRight, Wallet, Lightbulb } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { PieChart, Pie, Cell, Sector, ResponsiveContainer } from "recharts";

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

// 仪表盘图表组件
interface GaugeChartProps {
  score: number; // 0-1范围的分数
  riskLevel: string;
  riskScore?: number; // 可选的0-100范围的分数
}

// Recharts仪表盘组件
const GaugeChart: React.FC<GaugeChartProps> = ({ score, riskLevel, riskScore }) => {
  // 确定颜色（基于分数）
  const color = score >= 0.7 ? "#ef4444" : score >= 0.4 ? "#f59e0b" : "#10b981";
  const colorClass = score >= 0.7 ? "text-destructive" : score >= 0.4 ? "text-amber-500" : "text-green-500";
  const displayScore = riskScore !== undefined ? Number(riskScore) : Math.round(score * 100);

  // 创建仪表盘数据 - 不同风险区域
  const data = [
    { name: "低风险", value: 33.33, color: "#10b981" },
    { name: "中风险", value: 33.33, color: "#f59e0b" },
    { name: "高风险", value: 33.34, color: "#ef4444" },
  ];

  // 添加指针动画
  const [animatedAngle, setAnimatedAngle] = useState(180); // 起始位置为最左侧
  const [animatedScore, setAnimatedScore] = useState(0);

  // 计算指针角度
  const targetAngle = 180 - score * 180; // 将0-1的分数映射到180-0度范围

  // 为指针创建数据 - 使用动画角度
  const needleData = [{ value: animatedScore, color: color }];

  // 创建阴影效果指针数据
  const shadowNeedleData = [{ value: animatedScore, color: "rgba(0,0,0,0.2)" }];

  // 添加分数和角度动画效果
  useEffect(() => {
    // 如果目标值和当前值相等，则不需要动画
    if (Math.round(displayScore) === animatedScore && Math.abs(targetAngle - animatedAngle) < 0.1) {
      return;
    }

    // 使用setTimeout来确保组件完全挂载
    const timer = setTimeout(() => {
      // 使用requestAnimationFrame进行平滑动画
      let start = 0;
      let startAngle = animatedAngle; // 使用当前角度作为起始点
      let startScore = animatedScore; // 使用当前分数作为起始点
      const duration = 800; // 动画持续时间（毫秒）

      const animate = (timestamp: number) => {
        if (!start) start = timestamp;
        const progress = Math.min((timestamp - start) / duration, 1);

        // 使用easeOutQuad缓动函数
        const easeProgress = 1 - (1 - progress) * (1 - progress);

        // 计算当前角度和分数
        const currentAngle = startAngle - (startAngle - targetAngle) * easeProgress;
        const currentScore = startScore + (displayScore - startScore) * easeProgress;

        setAnimatedAngle(currentAngle);
        setAnimatedScore(Math.round(currentScore));

        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      };

      requestAnimationFrame(animate);
    }, 100);

    return () => clearTimeout(timer);
  }, [displayScore, targetAngle, animatedAngle, animatedScore]);

  // 优化后的活跃形状渲染函数 - 用于指针
  const renderNeedleShape = (props: any) => {
    const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;

    // 根据分数计算指针角度（180度到0度的范围）
    const RADIAN = Math.PI / 180;
    const sin = Math.sin(-RADIAN * endAngle);
    const cos = Math.cos(-RADIAN * endAngle);

    // 计算指针终点坐标
    const sx = cx + (outerRadius - 8) * cos;
    const sy = cy + (outerRadius - 8) * sin;

    // 创建指针形状
    return (
      <g>
        <circle cx={cx} cy={cy} r={5} fill={fill} stroke="none" />
        <path d={`M${cx},${cy}L${sx},${sy}`} stroke={fill} strokeWidth={3} strokeLinecap="round" fill="none" />
        <circle cx={sx} cy={sy} r={2.5} fill={fill} stroke="none" />
      </g>
    );
  };

  // 指针阴影效果渲染函数
  const renderShadowShape = (props: any) => {
    const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;

    const RADIAN = Math.PI / 180;
    const sin = Math.sin(-RADIAN * endAngle);
    const cos = Math.cos(-RADIAN * endAngle);

    const sx = cx + (outerRadius - 8) * cos;
    const sy = cy + (outerRadius - 8) * sin;

    return (
      <g>
        <circle cx={cx} cy={cy} r={7} fill={fill} stroke="none" opacity={0.3} />
        <path d={`M${cx},${cy}L${sx},${sy}`} stroke={fill} strokeWidth={5} strokeLinecap="round" fill="none" opacity={0.3} />
      </g>
    );
  };

  return (
    <div className="relative w-full mb-1">
      {/* 背景光晕效果 */}
      <motion.div
        className={`absolute top-10 left-1/2 -translate-x-1/2 w-20 h-20 rounded-full -z-10 opacity-10 blur-md ${score >= 0.7 ? "bg-red-500" : score >= 0.4 ? "bg-amber-500" : "bg-green-500"}`}
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.1, 0.2, 0.1],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          repeatType: "reverse",
        }}
      />

      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          {/* 仪表盘背景 */}
          <Pie data={data} cx="50%" cy={105} startAngle={180} endAngle={0} innerRadius={60} outerRadius={80} paddingAngle={0} dataKey="value" stroke="none" isAnimationActive={false}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} fillOpacity={0.7} />
            ))}
          </Pie>

          {/* 指针阴影 */}
          <Pie data={shadowNeedleData} cx="50%" cy={105} startAngle={animatedAngle + 1} endAngle={animatedAngle + 1} innerRadius={0} outerRadius={58} dataKey="value" stroke="none" isAnimationActive={true} activeIndex={0} activeShape={renderShadowShape} fill="rgba(0,0,0,0.2)" />

          {/* 仪表盘指针 */}
          <Pie data={needleData} cx="50%" cy={105} startAngle={animatedAngle} endAngle={animatedAngle} innerRadius={0} outerRadius={60} dataKey="value" stroke="none" isAnimationActive={true} activeIndex={0} activeShape={renderNeedleShape} fill={color} />

          {/* 刻度线 - 更精细的刻度 */}
          <Pie data={[{ value: 100 }]} cx="50%" cy={105} startAngle={180} endAngle={0} innerRadius={84} outerRadius={85} dataKey="value" stroke="#e5e7eb" fill="none" strokeDasharray="1.5 3" />
        </PieChart>
      </ResponsiveContainer>

      {/* 风险级别标签 */}
      <div className="flex justify-between w-full px-4 mt-1 text-xs font-medium">
        <span className="text-green-500">低风险</span>
        <span className="text-amber-500">中风险</span>
        <span className="text-red-500">高风险</span>
      </div>

      {/* 中心分数显示 */}
      <div className="absolute left-0 right-0 text-center" style={{ bottom: "50%" }}>
        <p className="text-sm font-medium text-muted-foreground">得分</p>
        <motion.p className={`text-2xl font-bold ${colorClass}`} initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.3, duration: 0.3 }}>
          <motion.span
            initial={{ opacity: 0 }}
            animate={{
              opacity: 1,
              transition: { delay: 0.5 },
            }}
          >
            {animatedScore}
          </motion.span>
          {riskScore !== undefined && <span className="text-sm font-normal ml-0.5">/100</span>}
        </motion.p>
      </div>
    </div>
  );
};

// 风险评分组件
interface RiskScoreProps {
  score: number;
  riskLevel: string;
  riskScore?: number;
}

const RiskScore: React.FC<RiskScoreProps> = ({ score, riskLevel, riskScore }) => {
  const [animatedScore, setAnimatedScore] = useState(0);
  const color = score >= 0.7 ? "destructive" : score >= 0.4 ? "warning" : "success";
  const colorClass = color === "destructive" ? "text-destructive" : color === "warning" ? "text-amber-500" : "text-green-500";
  const bgColorClass = color === "destructive" ? "bg-destructive" : color === "warning" ? "bg-amber-500" : "bg-green-500";

  // 直接指定颜色值而不是CSS变量
  const strokeColor = score >= 0.7 ? "#ef4444" : score >= 0.4 ? "#f59e0b" : "#10b981";

  const displayScore = riskScore !== undefined ? Number(riskScore) : Math.round(score * 100);

  // 添加分数动画效果
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedScore(displayScore);
    }, 500);

    return () => clearTimeout(timer);
  }, [displayScore]);

  return (
    <motion.div className="p-4 transition-shadow duration-300 border rounded-lg shadow-sm bg-background hover:shadow-md" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="flex items-center text-lg font-semibold">
            <Shield className="w-4 h-4 mr-1.5 text-primary" />
            风险评分
          </h3>
          <p className="text-sm text-muted-foreground">综合风险分析结果</p>
        </div>
        <Badge variant={color === "destructive" ? "destructive" : color === "warning" ? "outline" : "secondary"} className={`${color !== "destructive" ? colorClass : ""} shadow-sm`}>
          {riskLevel}
        </Badge>
      </div>

      <div className="flex flex-col items-center justify-center mt-2">
        {/* 使用新的基于recharts的仪表盘组件 */}
        <GaugeChart score={score} riskLevel={riskLevel} riskScore={displayScore} />
      </div>
    </motion.div>
  );
};

// 风险因素卡片组件
interface RiskFactorCardProps {
  factor: {
    name: string;
    description: string;
    severity: string;
    icon: React.ReactNode;
    score: number;
    weight: number;
    trend?: string;
  };
  index: number;
}

const RiskFactorCard: React.FC<RiskFactorCardProps> = ({ factor, index }) => {
  const [expanded, setExpanded] = useState(false);

  const severityColor = factor.severity === "high" ? "destructive" : factor.severity === "medium" ? "warning" : "success";

  const bgColorClass = factor.severity === "high" ? "bg-destructive/10 border-destructive/50" : factor.severity === "medium" ? "bg-warning/10 border-warning/50" : "bg-success/10 border-success/50";

  const iconBgClass = factor.severity === "high" ? "bg-destructive/20 text-destructive" : factor.severity === "medium" ? "bg-warning/20 text-warning" : "bg-success/20 text-success";

  const scoreClass = factor.score > 60 ? "border-destructive text-destructive" : factor.score > 30 ? "border-amber-500 text-amber-500" : "border-green-500 text-green-500";

  const trendIcon = factor.trend === "上升" ? <TrendingUp className="w-3 h-3" /> : factor.trend === "下降" ? <TrendingDown className="w-3 h-3" /> : <ArrowRight className="w-3 h-3" />;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.3,
        delay: index * 0.05,
        layout: { duration: 0.2 },
      }}
      className={`rounded-lg border shadow-sm overflow-hidden ${bgColorClass}`}
    >
      <div className="p-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className={`p-1.5 rounded-full ${iconBgClass}`}>{factor.icon}</div>
            <div>
              <div className="flex items-center">
                <h4 className="text-sm font-medium">{factor.name}</h4>
                <ChevronDown className={`w-4 h-4 ml-1 text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{factor.description}</p>
            </div>
          </div>
          <div className="flex flex-col items-end">
            <Badge variant="outline" className={scoreClass}>
              {factor.score}/100
            </Badge>
            <p className="mt-1 text-xs text-muted-foreground">权重: {(factor.weight * 100).toFixed(0)}%</p>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="px-3 pt-0 pb-3">
            <div className="pt-2 mt-2 border-t">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1">
                  <Info className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground">影响范围</span>
                </span>
                <Badge variant="secondary" className="text-xs">
                  {factor.severity === "high" ? "广泛" : factor.severity === "medium" ? "中等" : "有限"}
                </Badge>
              </div>

              {factor.trend && (
                <div className="flex items-center justify-between mt-2 text-sm">
                  <span className="flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="text-muted-foreground">趋势</span>
                  </span>
                  <Badge variant="outline" className="flex items-center gap-1 text-xs">
                    {trendIcon}
                    {factor.trend}
                  </Badge>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// 工具提示包装组件
interface InfoTooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
}

const InfoTooltip: React.FC<InfoTooltipProps> = ({ content, children }) => {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="cursor-help">{children}</span>
        </TooltipTrigger>
        <TooltipContent side="top" align="center" className="max-w-[300px] text-xs">
          {content}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

// AI置信度徽章组件
interface ConfidenceBadgeProps {
  confidence: number; // 0-1范围
}

const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ confidence }) => {
  // 根据置信度值确定颜色
  const getColor = () => {
    if (confidence >= 0.8) return "text-green-500 border-green-500";
    if (confidence >= 0.5) return "text-amber-500 border-amber-500";
    return "text-red-500 border-red-500";
  };

  const getText = () => {
    if (confidence >= 0.8) return "高";
    if (confidence >= 0.5) return "中";
    return "低";
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge variant="outline" className={`ml-2 ${getColor()}`}>
            置信度: {getText()} ({(confidence * 100).toFixed(0)}%)
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" align="center" className="max-w-[300px] text-xs">
          AI分析结果的置信度，反映模型对当前分析结论的确信程度
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

// 可折叠卡片组件
interface CollapsibleCardProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  tooltip?: string;
  initiallyExpanded?: boolean;
  accentColor?: string;
  badge?: React.ReactNode;
}

const CollapsibleCard: React.FC<CollapsibleCardProps> = ({ title, icon, children, tooltip, initiallyExpanded = true, accentColor = "primary", badge }) => {
  const [expanded, setExpanded] = useState(initiallyExpanded);

  return (
    <motion.div layout className={`border rounded-lg overflow-hidden shadow-sm`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div className={`flex items-center justify-between p-4 cursor-pointer border-l-4 ${accentColor === "primary" ? "border-l-primary" : `border-l-${accentColor}`}`} onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-2">
          {icon && <div className="text-muted-foreground">{icon}</div>}
          <div className="flex items-center gap-1.5">
            <h3 className="text-lg font-medium">{title}</h3>
            {tooltip && (
              <InfoTooltip content={tooltip}>
                <Info className="w-3.5 h-3.5 text-muted-foreground" />
              </InfoTooltip>
            )}
            {badge}
          </div>
        </div>
        <ChevronDown className={`w-5 h-5 text-muted-foreground transition-transform duration-200 ${expanded ? "rotate-180" : ""}`} />
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}>
            <div className="px-4 pb-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// 添加加载状态动画组件
const LoadingState = () => (
  <motion.div className="flex flex-col items-center justify-center py-10" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
    <motion.div
      animate={{
        rotate: 360,
        scale: [1, 1.1, 1],
      }}
      transition={{
        rotate: { repeat: Infinity, duration: 1.5, ease: "linear" },
        scale: { repeat: Infinity, duration: 1.5, repeatType: "reverse" },
      }}
      className="relative mb-6 text-primary"
    >
      <Loader2 className="w-16 h-16" />
      <motion.div
        className="absolute inset-0 border-2 rounded-full border-primary/20"
        animate={{ scale: [1, 1.5], opacity: [1, 0] }}
        transition={{
          repeat: Infinity,
          duration: 1.5,
          ease: "easeOut",
        }}
      />
    </motion.div>
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.3 }} className="text-center">
      <h3 className="mb-2 text-lg font-medium">分析投资组合风险中</h3>
      <p className="max-w-sm text-sm text-muted-foreground">我们正在深入分析您的DeFi投资组合，识别潜在风险因素和优化机会...</p>
    </motion.div>
  </motion.div>
);

interface EmptyStateProps {
  onAnalyze: () => Promise<void>;
  analyzing: boolean;
}

const EmptyState: React.FC<EmptyStateProps> = ({ onAnalyze, analyzing }) => (
  <motion.div className="flex flex-col items-center justify-center py-10 space-y-6" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
    <motion.div
      animate={{
        boxShadow: ["0px 0px 0px rgba(0,0,0,0)", "0px 0px 20px rgba(0,100,255,0.1)", "0px 0px 0px rgba(0,0,0,0)"],
      }}
      transition={{
        repeat: Infinity,
        duration: 2.5,
        repeatType: "mirror",
      }}
      className="p-4 rounded-full bg-muted/10"
    >
      <Shield className="w-20 h-20 text-muted-foreground" />
    </motion.div>

    <div className="max-w-md text-center">
      <h3 className="mb-2 text-xl font-medium">了解您的投资组合风险</h3>
      <p className="mb-6 text-sm text-muted-foreground">通过深度分析您的DeFi投资组合，获取专业风险评估和优化建议，提升您的投资安全性。</p>
      <Button onClick={onAnalyze} disabled={analyzing} size="lg" className="relative px-8 overflow-hidden group">
        {analyzing ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            分析中...
          </>
        ) : (
          <>
            <Target className="relative z-10 w-4 h-4 mr-2" />
            <span className="relative z-10">开始风险分析</span>
            <motion.div className="absolute inset-0 bg-primary/10" initial={{ x: "-100%" }} whileHover={{ x: 0 }} transition={{ duration: 0.3 }} />
          </>
        )}
      </Button>
    </div>
  </motion.div>
);

const RiskMonitor: React.FC<RiskMonitorProps> = ({ portfolio, riskAnalysis, analyzing, completed, onAnalyze }) => {
  if (!portfolio) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>风险监控</CardTitle>
          <CardDescription>暂无数据</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState onAnalyze={onAnalyze} analyzing={analyzing} />
        </CardContent>
      </Card>
    );
  }

  // 使用useMemo缓存计算结果
  const riskScore = useMemo(() => {
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
  }, [riskAnalysis?.risk_score, portfolio.risk_level]);

  const riskLevelInfo = useMemo(() => {
    if (portfolio.risk_level) {
      return {
        level: portfolio.risk_level,
        color: riskScore >= 0.7 ? "destructive" : riskScore >= 0.4 ? "warning" : "success",
      };
    }
    return riskScore >= 0.7 ? { level: "高", color: "destructive" } : riskScore >= 0.4 ? { level: "中", color: "warning" } : { level: "低", color: "success" };
  }, [portfolio.risk_level, riskScore]);

  // 处理风险因素数据 - 使用useMemo缓存
  const riskFactors = useMemo(() => {
    // 如果有来自API的风险因素，使用这些数据
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
  }, [riskAnalysis?.risk_factors, portfolio.positions, portfolio.market_analysis, portfolio.total_value]);

  // 获取监控点 - 使用useMemo缓存
  const monitoringPoints = useMemo(() => {
    if (riskAnalysis?.monitoring_points && riskAnalysis.monitoring_points.length > 0) {
      return riskAnalysis.monitoring_points;
    }

    return ["定期评估投资组合风险", "关注资产相关性变化", "监控市场波动情况", "关注杠杆头寸风险"];
  }, [riskAnalysis?.monitoring_points]);

  // 获取AI洞察 - 使用useMemo缓存
  const aiInsights = useMemo(() => {
    if (riskAnalysis?.ai_insights && riskAnalysis.ai_insights.length > 0) {
      return riskAnalysis.ai_insights;
    }
    return [];
  }, [riskAnalysis?.ai_insights]);

  // 获取AI警告 - 使用useMemo缓存
  const aiWarnings = useMemo(() => {
    if (riskAnalysis?.ai_warnings && riskAnalysis.ai_warnings.length > 0) {
      return riskAnalysis.ai_warnings;
    }
    return [];
  }, [riskAnalysis?.ai_warnings]);

  // 获取AI置信度 - 使用useMemo缓存
  const aiConfidence = useMemo(() => {
    return riskAnalysis?.ai_confidence || 0;
  }, [riskAnalysis?.ai_confidence]);

  // 获取建议 - 使用useMemo缓存
  const recommendations = useMemo(() => {
    if (riskAnalysis?.recommendations && riskAnalysis.recommendations.length > 0) {
      return riskAnalysis.recommendations;
    }

    if (portfolio?.recommendations && portfolio.recommendations.length > 0) {
      return portfolio.recommendations;
    }

    return [];
  }, [riskAnalysis?.recommendations, portfolio?.recommendations]);

  if (!portfolio.risk_level) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>详细风险分析</CardTitle>
          <CardDescription>分析您的DeFi投资组合风险</CardDescription>
        </CardHeader>
        <CardContent>{analyzing ? <LoadingState /> : <EmptyState onAnalyze={onAnalyze} analyzing={analyzing} />}</CardContent>
      </Card>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
      <Card className="overflow-hidden">
        <CardHeader>
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              详细风险分析
            </CardTitle>
            <CardDescription>投资组合综合风险分析</CardDescription>
          </motion.div>
        </CardHeader>
        <CardContent className="space-y-6 sm:space-y-8">
          {/* 风险分数和等级 */}
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5">
                <p className="text-sm font-medium">风险等级</p>
                <InfoTooltip content="基于投资组合的多种风险因素综合评估得出的风险等级">
                  <Info className="w-3.5 h-3.5 text-muted-foreground" />
                </InfoTooltip>
              </div>
              <div className="flex items-center gap-2">
                <motion.h3 className={`text-2xl font-bold ${riskLevelInfo.color === "destructive" ? "text-destructive" : riskLevelInfo.color === "warning" ? "text-amber-500" : "text-green-500"}`} initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.3 }}>
                  {riskLevelInfo.level}
                </motion.h3>
                {/* {riskAnalysis?.risk_score !== undefined && (
                  <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3, delay: 0.1 }}>
                    <Badge
                      variant={riskLevelInfo.color === "destructive" ? "destructive" : riskLevelInfo.color === "warning" ? "outline" : "secondary"}
                      className={`text-sm ${riskLevelInfo.color !== "destructive" && `${riskLevelInfo.color === "warning" ? "text-amber-500 border-amber-500" : "text-green-500"}`}`}
                    >
                      <span className="flex items-center gap-1">
                        <Target className="w-3 h-3" />
                        风险评分: {riskAnalysis.risk_score}/100
                      </span>
                    </Badge>
                  </motion.div>
                )} */}
              </div>
            </div>
            <Button onClick={onAnalyze} disabled={analyzing} variant="outline" size="sm" className="transition-all duration-300 hover:shadow-md">
              {analyzing ? (
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }} className="text-primary">
                  <Loader2 className="w-4 h-4" />
                </motion.div>
              ) : (
                <Shield className="w-4 h-4 mr-2" />
              )}
              {analyzing ? "分析中..." : "重新分析"}
            </Button>
          </div>

          {/* 使用新的RiskScore组件替换原始风险进度条 */}
          <RiskScore score={riskScore} riskLevel={portfolio.risk_level} riskScore={riskAnalysis?.risk_score} />

          {/* 风险因素 */}
          {riskFactors.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-3">
                <h3 className="text-sm font-medium">风险因素</h3>
                <InfoTooltip content="影响投资组合安全性的关键风险因素，点击每个卡片可查看详情">
                  <Info className="w-3.5 h-3.5 text-muted-foreground" />
                </InfoTooltip>
              </div>
              <div className="space-y-3">
                {riskFactors.map((factor, index) => (
                  <RiskFactorCard key={index} factor={factor} index={index} />
                ))}
              </div>
            </div>
          )}

          {/* 风险指标 */}
          {riskAnalysis?.risk_metrics && Object.keys(riskAnalysis.risk_metrics).length > 0 && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }}>
              <div className="flex items-center gap-1.5 mb-3">
                <h3 className="text-sm font-medium">风险指标</h3>
                <InfoTooltip content="投资组合的关键风险测量指标，如波动率、夏普比率等">
                  <Info className="w-3.5 h-3.5 text-muted-foreground" />
                </InfoTooltip>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
                {Object.entries(riskAnalysis.risk_metrics).map(([key, value], index) => (
                  <motion.div key={index} className="p-3 transition-colors border rounded-md hover:bg-muted/5" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.2, delay: index * 0.05 }}>
                    <p className="text-xs text-muted-foreground">{key}</p>
                    <p className="text-sm font-medium">{value}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* 风险监控点 - 使用CollapsibleCard */}
          <CollapsibleCard
            title="关键监控点"
            icon={<Target className="w-5 h-5" />}
            tooltip="需持续监控的关键风险指标和事件"
            accentColor="primary"
            initiallyExpanded={true}
            badge={
              <Badge variant="secondary" className="text-xs">
                最新
              </Badge>
            }
          >
            <ul className="pl-5 space-y-2 list-disc">
              {monitoringPoints.map((point, index) => (
                <motion.li key={index} className="text-sm" initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.2, delay: index * 0.05 }}>
                  {point}
                </motion.li>
              ))}
            </ul>
          </CollapsibleCard>

          {/* AI警告 - 使用CollapsibleCard，仅在有数据时显示 */}
          {aiWarnings.length > 0 && (
            <CollapsibleCard
              title="AI 风险警告"
              icon={<AlertTriangle className="w-5 h-5" />}
              tooltip="AI检测到的潜在高风险因素"
              accentColor="destructive"
              badge={
                <Badge variant="destructive" className="text-xs">
                  重要
                </Badge>
              }
              initiallyExpanded={true}
            >
              <ul className="pl-5 space-y-2 list-disc">
                {aiWarnings.map((warning, index) => (
                  <motion.li key={index} className="text-sm font-medium text-destructive" initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.2, delay: index * 0.05 }}>
                    {warning}
                  </motion.li>
                ))}
              </ul>
            </CollapsibleCard>
          )}

          {/* 风险建议 - 使用CollapsibleCard */}
          <CollapsibleCard title="AI风险管理建议" icon={<Zap className="w-5 h-5" />} tooltip="基于AI分析的投资组合风险管理建议" accentColor="primary" badge={<ConfidenceBadge confidence={aiConfidence} />}>
            <ul className="pl-5 space-y-2 list-disc">
              {recommendations.map((recommendation, index) => (
                <motion.li key={index} className="text-sm" initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.2, delay: index * 0.05 }}>
                  {recommendation}
                </motion.li>
              ))}
            </ul>
          </CollapsibleCard>

          {/* AI洞察 - 使用CollapsibleCard，仅在有数据时显示 */}
          {aiInsights.length > 0 && (
            <CollapsibleCard title="AI 洞察" icon={<Lightbulb className="w-5 h-5" />} tooltip="AI模型针对投资组合的深度洞察" accentColor="blue-600" badge={<ConfidenceBadge confidence={aiConfidence} />}>
              <ul className="pl-5 space-y-2 list-disc">
                {aiInsights.map((insight, index) => (
                  <motion.li key={index} className="text-sm" initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.2, delay: index * 0.05 }}>
                    {insight}
                  </motion.li>
                ))}
              </ul>
            </CollapsibleCard>
          )}

          {/* 头寸摘要信息 */}
          {riskAnalysis?.positions_summary && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 }}>
              <div className="flex items-center gap-1.5 mb-3">
                <h3 className="text-sm font-medium">头寸摘要</h3>
                <InfoTooltip content="投资组合中的资产和协议分布概况">
                  <Info className="w-3.5 h-3.5 text-muted-foreground" />
                </InfoTooltip>
              </div>

              <div className="grid grid-cols-1 gap-3 mb-4 sm:grid-cols-2">
                <motion.div className="p-4 border rounded-md bg-muted/5" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}>
                  <div className="flex items-center gap-2 mb-1">
                    <Wallet className="w-4 h-4 text-primary" />
                    <p className="text-sm font-medium">总价值</p>
                  </div>
                  <p className="text-lg font-bold">${riskAnalysis.positions_summary.total_value.toLocaleString()}</p>
                </motion.div>

                <motion.div className="p-4 border rounded-md bg-muted/5" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}>
                  <div className="flex items-center gap-2 mb-1">
                    <Target className="w-4 h-4 text-primary" />
                    <p className="text-sm font-medium">头寸数量</p>
                  </div>
                  <p className="text-lg font-bold">{riskAnalysis.positions_summary.position_count}</p>
                </motion.div>
              </div>

              {riskAnalysis.positions_summary.protocols.length > 0 && (
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-muted-foreground">协议分布 ({riskAnalysis.positions_summary.protocols.length})</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {riskAnalysis.positions_summary.protocols.map((protocol, index) => {
                      // 尝试查找该协议的资产，以获取其图标
                      let protocolLogo = "";
                      if (portfolio && portfolio.positions) {
                        const protocolPosition = portfolio.positions.find((pos) => pos.protocol === protocol);
                        if (protocolPosition && protocolPosition.tokenList && protocolPosition.tokenList.length > 0) {
                          protocolLogo = protocolPosition.tokenList[0].tokenLogo;
                        }
                      }

                      // 协议图标的颜色映射
                      const protocolColors: { [key: string]: string } = {
                        Aethir: "bg-blue-100",
                        "Data Ownership Protocol": "bg-green-100",
                        sophon: "bg-purple-100",
                      };

                      return (
                        <motion.div key={index} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.2, delay: index * 0.03 }}>
                          <Badge variant="secondary" className={`text-xs flex items-center gap-1 py-1 px-2 ${!protocolLogo ? protocolColors[protocol] || "" : ""}`}>
                            {protocolLogo ? (
                              <img
                                src={protocolLogo}
                                alt={`${protocol} logo`}
                                className="w-4 h-4 rounded-full"
                                onError={(e) => {
                                  // 如果图片加载失败，隐藏图片元素
                                  (e.target as HTMLImageElement).style.display = "none";
                                }}
                              />
                            ) : (
                              <div className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${protocolColors[protocol] || "bg-gray-100"}`}>{protocol.charAt(0)}</div>
                            )}
                            {protocol}
                          </Badge>
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              )}

              {riskAnalysis.positions_summary.assets.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-muted-foreground">资产分布 ({riskAnalysis.positions_summary.assets.length})</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {riskAnalysis.positions_summary.assets.map((asset, index) => {
                      // 尝试查找资产的Logo
                      let assetLogo = "";
                      if (portfolio && portfolio.positions) {
                        for (const position of portfolio.positions) {
                          if (position.tokenList) {
                            const token = position.tokenList.find((t) => t.tokenSymbol === asset);
                            if (token && token.tokenLogo) {
                              assetLogo = token.tokenLogo;
                              break;
                            }
                          }
                        }
                      }

                      return (
                        <motion.div key={index} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.2, delay: index * 0.02 }}>
                          <Badge variant="outline" className="flex items-center gap-1 px-2 py-1 text-xs transition-colors hover:bg-muted/10">
                            {assetLogo && (
                              <img
                                src={assetLogo}
                                alt={`${asset} logo`}
                                className="w-4 h-4 rounded-full"
                                onError={(e) => {
                                  // 如果图片加载失败，隐藏图片元素
                                  (e.target as HTMLImageElement).style.display = "none";
                                }}
                              />
                            )}
                            {asset}
                          </Badge>
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* 分析时间戳 */}
          {riskAnalysis?.analysis_timestamp && (
            <motion.div className="mt-4 text-xs text-muted-foreground" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3, delay: 0.3 }}>
              分析时间: {new Date(riskAnalysis.analysis_timestamp).toLocaleString()}
            </motion.div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default RiskMonitor;
