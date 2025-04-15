"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import ApiTest from "./ApiTest";
import { ConnectButton } from "./ConnectButton";
import { apiService } from "../services/api";
import type { Portfolio, WalletRiskAssessment, WalletMarketRisk } from "../services/api";
import { Loader2, RefreshCw, AlertTriangle, Shield, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableBody, TableRow, TableCell } from "@/components/ui/table";

// 风险分析结果接口使用API中定义的WalletRiskAssessment

// 将Portfolio类型转换为PortfolioOverview组件所需的格式
const adaptPortfolioForOverview = (portfolio: Portfolio) => {
  if (!portfolio) return null;

  // 转换为PortfolioOverview所需的格式
  const adaptedPortfolio = {
    wallet_address: portfolio.wallet_address,
    total_value: portfolio.total_value,
    total_value_usd: portfolio.total_value_usd,
    position_count: portfolio.position_count,
    protocol_count: portfolio.protocol_count,
    positions: portfolio.positions.reduce(
      (protocolPositions, position) => {
        // 查找此协议是否已经存在于转换结果中
        let protocolPosition = protocolPositions.find((p) => p.protocol === position.protocol);

        // 如果不存在，创建一个新的协议位置
        if (!protocolPosition) {
          protocolPosition = {
            protocol: position.protocol,
            total_assets: 0,
            total_debts: 0,
            leverage: position.leverage || 1,
            positions: [],
          };
          protocolPositions.push(protocolPosition);
        }

        // 添加位置到协议位置中
        protocolPosition.positions.push({
          protocol: position.protocol,
          asset: position.asset,
          amount: position.amount || 0,
          invest_type: position.invest_type || 0,
          apy: position.apy || null,
          tokenList: position.tokenList || [],
        });

        // 累加资产总值
        protocolPosition.total_assets += position.amount || 0;

        return protocolPositions;
      },
      [] as Array<{
        protocol: string;
        total_assets: number;
        total_debts: number;
        leverage: number;
        positions: Array<{
          protocol: string;
          asset: string;
          amount: number;
          invest_type: number;
          apy: number | null;
          tokenList: any[];
        }>;
      }>
    ),
    // 转换 Protocol 数组为所需的格式
    protocols: portfolio.protocols.map((protocol) => ({
      name: protocol.name,
      chain: protocol.chain || "",
      tvl: protocol.tvl || 0,
      supported_assets: protocol.supported_assets || [],
      features: protocol.features || [],
      description: protocol.description || "",
      contract_addresses: protocol.contract_addresses || "",
    })),
    timestamp: portfolio.timestamp,
    is_demo_data: portfolio.is_demo_data,
  };

  return adaptedPortfolio;
};

export const Dashboard: React.FC = () => {
  const { address, isConnected } = useAccount();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [riskAnalysis, setRiskAnalysis] = useState<WalletRiskAssessment | null>(null);
  const [marketRisk, setMarketRisk] = useState<WalletMarketRisk | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const initialized = useRef(false);
  const [activeTab, setActiveTab] = useState<string>("overview");

  // 当钱包地址变化时重新获取数据
  useEffect(() => {
    if (isConnected && address) {
      fetchPortfolioData(address);
    } else {
      setPortfolio(null);
      setRiskAnalysis(null);
    }
  }, [isConnected, address]);

  const fetchPortfolioData = async (walletAddress?: string) => {
    if (!walletAddress) return;

    try {
      setLoading(true);
      setError(null);

      // 获取投资组合数据
      const portfolioData = await apiService.getPortfolio(walletAddress);
      setPortfolio(portfolioData);
      setLastUpdateTime(new Date());
    } catch (error) {
      console.error("获取投资组合数据失败:", error);
      setError("无法加载投资组合数据");
    } finally {
      setLoading(false);
    }
  };

  // 分析钱包风险
  const analyzeWalletRisk = async () => {
    if (!address) return;

    try {
      setAnalyzing(true);
      setError(null);

      // 调用风险分析API
      const riskAnalysisData = await apiService.getWalletRiskAssessment(address);

      // 获取市场风险数据
      // try {
      //   const marketRiskData = await apiService.getWalletMarketRisk(address);
      //   setMarketRisk(marketRiskData);
      // } catch (marketError) {
      //   console.error("获取市场风险数据失败:", marketError);
      //   // 市场风险获取失败不影响主流程
      // }

      // 更新状态
      setRiskAnalysis(riskAnalysisData);

      // 更新portfolio的风险相关数据
      if (portfolio) {
        const updatedPortfolio: Portfolio = {
          ...portfolio,
          risk_level: riskAnalysisData.risk_level,
          recommendations: riskAnalysisData.recommendations,
        };
        setPortfolio(updatedPortfolio);
      }
    } catch (error) {
      console.error("分析钱包风险失败:", error);
      setError("无法完成风险分析");
    } finally {
      setAnalyzing(false);
    }
  };

  // 刷新数据
  const handleRefresh = useCallback(async () => {
    if (loading || !address) return;
    await fetchPortfolioData(address);
  }, [address, loading]);

  if (!isConnected) {
    return (
      <div className="space-y-8">
        {/* 欢迎卡片 */}
        <Card className="relative overflow-hidden border shadow-xl rounded-xl border-slate-200/60 dark:border-slate-800/60 backdrop-blur-sm">
          {/* 背景装饰元素 */}
          <div className="absolute top-0 right-0 -mt-20 -mr-20 rounded-full w-96 h-96 opacity-20 bg-gradient-to-br from-blue-400 to-purple-600 blur-3xl"></div>
          <div className="absolute bottom-0 left-0 -mb-20 -ml-20 rounded-full w-96 h-96 opacity-20 bg-gradient-to-tr from-green-400 to-cyan-500 blur-3xl"></div>

          <div className="relative z-10 p-8 md:p-12">
            <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
              <div className="max-w-3xl space-y-4">
                <div className="space-y-2">
                  <h1 className="text-3xl font-bold tracking-tight text-transparent md:text-4xl bg-clip-text bg-gradient-to-r from-slate-900 to-slate-600 dark:from-slate-100 dark:to-slate-400">DeFi风险监控仪表板</h1>
                  <p className="text-lg md:text-xl text-slate-600 dark:text-slate-300">实时监控您的DeFi投资组合，分析风险暴露，保护您的加密资产安全</p>
                </div>

                <div className="pt-2">
                  {/* 使用ConnectButton组件替换无功能按钮，添加自定义样式 */}
                  <ConnectButton size="lg" variant="custom" />
                </div>
              </div>

              <div className="flex items-center justify-center p-5 border shadow-lg bg-white/80 dark:bg-slate-800/80 rounded-xl border-slate-200/60 dark:border-slate-700/60 backdrop-blur-md">
                <div className="relative w-20 h-20 md:w-32 md:h-32">
                  {/* 安全盾牌图标 */}
                  <div className="absolute inset-0 flex items-center justify-center text-blue-500 dark:text-blue-400 animate-pulse">
                    <Shield className="w-16 h-16 md:w-24 md:h-24" />
                  </div>
                  {/* 旋转的外环 */}
                  <div className="absolute inset-0 border-4 rounded-full border-t-transparent border-blue-400/30 dark:border-blue-500/30 animate-spin"></div>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* 功能预览卡片 */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* 功能卡片1：投资组合跟踪 */}
          <Card className="relative overflow-hidden transition-all duration-300 border shadow-md rounded-xl border-slate-200/60 dark:border-slate-800/60 hover:shadow-lg hover:translate-y-[-5px]">
            <div className="absolute top-0 right-0 w-32 h-32 -mt-8 -mr-8 rounded-full opacity-10 bg-gradient-to-br from-blue-300 to-blue-600 blur-2xl"></div>
            <CardHeader>
              <div className="flex items-center justify-center w-12 h-12 mb-4 bg-blue-100 rounded-lg dark:bg-blue-900/40">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                </svg>
              </div>
              <CardTitle>投资组合跟踪</CardTitle>
              <CardDescription>实时监控您的DeFi资产分布、收益和表现</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  跨协议资产聚合
                </li>
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  实时价格和APY更新
                </li>
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  历史表现分析
                </li>
              </ul>
            </CardContent>
          </Card>

          {/* 功能卡片2：风险分析 */}
          <Card className="relative overflow-hidden transition-all duration-300 border shadow-md rounded-xl border-slate-200/60 dark:border-slate-800/60 hover:shadow-lg hover:translate-y-[-5px]">
            <div className="absolute top-0 right-0 w-32 h-32 -mt-8 -mr-8 rounded-full opacity-10 bg-gradient-to-br from-amber-300 to-amber-600 blur-2xl"></div>
            <CardHeader>
              <div className="flex items-center justify-center w-12 h-12 mb-4 rounded-lg bg-amber-100 dark:bg-amber-900/40">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <CardTitle>风险分析</CardTitle>
              <CardDescription>全面评估您的DeFi投资风险暴露</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  协议风险评估
                </li>
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  流动性和波动性分析
                </li>
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  智能合约风险监控
                </li>
              </ul>
            </CardContent>
          </Card>

          {/* 功能卡片3：智能警报 */}
          <Card className="relative overflow-hidden transition-all duration-300 border shadow-md rounded-xl border-slate-200/60 dark:border-slate-800/60 hover:shadow-lg hover:translate-y-[-5px]">
            <div className="absolute top-0 right-0 w-32 h-32 -mt-8 -mr-8 rounded-full opacity-10 bg-gradient-to-br from-red-300 to-red-600 blur-2xl"></div>
            <CardHeader>
              <div className="flex items-center justify-center w-12 h-12 mb-4 bg-red-100 rounded-lg dark:bg-red-900/40">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
              </div>
              <CardTitle>智能警报</CardTitle>
              <CardDescription>获取重要风险事件的实时通知</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  价格异常波动提醒
                </li>
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  流动性危机预警
                </li>
                <li className="flex items-center">
                  <span className="mr-2 text-green-500">✓</span>
                  智能合约漏洞警报
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* 试用选项 */}
        {/* <div className="flex justify-center mt-8">
          <Button variant="outline" className="relative overflow-hidden font-medium transition-all duration-300 bg-white border shadow-sm group hover:shadow-md border-slate-200 dark:border-slate-700 dark:bg-slate-900">
            <span className="absolute inset-0 w-full h-full transition-all duration-300 opacity-0 bg-gradient-to-r from-slate-200/20 via-white/20 to-slate-200/20 group-hover:opacity-100 group-hover:animate-shimmer"></span>
            <span className="relative flex items-center">
              <Loader2 className="w-4 h-4 mr-2 transition-transform duration-300 group-hover:animate-spin" />
              查看演示数据
            </span>
          </Button>
        </div> */}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight">DeFi投资组合</h2>
          <p className="text-sm text-muted-foreground">
            实时监控您的DeFi资产
            {lastUpdateTime && <span className="ml-2">· 最后更新: {lastUpdateTime.toLocaleTimeString()}</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleRefresh} disabled={loading} variant="outline" size="icon">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="w-4 h-4" />
          <AlertTitle>错误</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && (
        <Card className="w-full p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        </Card>
      )}

      {!loading && !error && portfolio && (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="overview">投资组合概览</TabsTrigger>
            <TabsTrigger value="risk">风险分析</TabsTrigger>
            <TabsTrigger value="alerts">风险警报</TabsTrigger>
            <TabsTrigger value="market">市场分析</TabsTrigger>
            <TabsTrigger value="api">API测试</TabsTrigger>
          </TabsList>

          {/* 投资组合概览标签页 */}
          <TabsContent value="overview" className="mt-0">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="md:col-span-2">
                <PortfolioOverview portfolio={adaptPortfolioForOverview(portfolio)} />
              </div>

              <Card className="relative overflow-hidden transition-all duration-300 border shadow-lg rounded-xl border-slate-200/60 dark:border-slate-800/60 hover:shadow-xl backdrop-blur-sm group">
                {/* 背景装饰元素 */}
                <div className="absolute top-0 right-0 w-32 h-32 -mt-8 -mr-8 transition-opacity duration-500 rounded-full opacity-10 bg-gradient-to-br from-blue-300 to-purple-600 blur-2xl group-hover:opacity-20"></div>
                <div className="absolute bottom-0 left-0 w-24 h-24 -mb-6 -ml-6 transition-opacity duration-500 rounded-full opacity-10 bg-gradient-to-tr from-green-300 to-cyan-600 blur-2xl group-hover:opacity-15"></div>

                <CardHeader className="relative pb-3 overflow-hidden border-b bg-gradient-to-r from-slate-50/90 via-white/90 to-slate-50/90 dark:from-slate-900/90 dark:via-slate-800/90 dark:to-slate-900/90 border-slate-100 dark:border-slate-800/50">
                  <div className="absolute inset-0 bg-grid-slate-100 dark:bg-grid-slate-800/20 opacity-10"></div>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-slate-900 to-slate-700 dark:from-slate-100 dark:to-slate-300">风险分析摘要</CardTitle>
                      <CardDescription className="mt-1 font-medium text-slate-500 dark:text-slate-400">您的DeFi投资组合风险概况</CardDescription>
                    </div>
                    <div>
                      <Button variant="outline" size="sm" onClick={analyzeWalletRisk} disabled={analyzing} className="transition-all duration-300 bg-white border shadow-sm hover:shadow-md border-slate-200 dark:border-slate-700 dark:bg-slate-900">
                        {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : "重新分析"}
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-5">
                  {!portfolio.risk_level ? (
                    <div className="flex flex-col items-center justify-center py-8 space-y-5">
                      <div className="p-4 transition-all duration-300 border rounded-full shadow-inner bg-slate-50 dark:bg-slate-900/50 border-slate-200 dark:border-slate-800">
                        <Shield className="w-14 h-14 text-slate-400 dark:text-slate-500" />
                      </div>
                      <Button onClick={analyzeWalletRisk} disabled={analyzing} className="font-medium text-white transition-all duration-300 shadow bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 hover:shadow-md">
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
                  ) : (
                    <div className="space-y-5">
                      {/* 重新设计的风险评分展示区域 */}
                      <div className="p-4 overflow-hidden transition-all duration-300 border rounded-xl bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800 border-slate-200/70 dark:border-slate-700/30 hover:shadow-md">
                        <div className="flex items-center justify-between">
                          {/* 风险等级和评分文本信息 */}
                          <div className="space-y-2">
                            <div className="space-y-1">
                              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">风险等级</p>
                              <p className={`text-3xl font-bold tracking-tight ${portfolio.risk_level === "高等风险" ? "text-red-500 dark:text-red-400" : portfolio.risk_level === "中等风险" ? "text-amber-500 dark:text-amber-400" : "text-emerald-500 dark:text-emerald-400"}`}>
                                {portfolio.risk_level}
                              </p>
                            </div>

                            {riskAnalysis?.risk_score !== undefined && (
                              <div className="pt-1">
                                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">风险评分</p>
                                <div className="flex items-baseline">
                                  <span className={`text-3xl font-bold tracking-tight ${riskAnalysis.risk_score > 60 ? "text-red-500 dark:text-red-400" : riskAnalysis.risk_score > 30 ? "text-amber-500 dark:text-amber-400" : "text-emerald-500 dark:text-emerald-400"}`}>
                                    {Math.round(riskAnalysis.risk_score)}
                                  </span>
                                  <span className="ml-1 text-sm text-slate-400 dark:text-slate-500">/100</span>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* 环形进度指示器替代原来的简单圆形 */}
                          {riskAnalysis?.risk_score !== undefined && (
                            <div className="relative flex items-center justify-center">
                              {/* 背景圆环 */}
                              <svg className="w-24 h-24" viewBox="0 0 100 100">
                                <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="8" className="text-slate-200 dark:text-slate-700" />
                                {/* 计算进度的圆弧，使用strokeDasharray和strokeDashoffset */}
                                <circle
                                  cx="50"
                                  cy="50"
                                  r="40"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="8"
                                  strokeLinecap="round"
                                  strokeDasharray="251.2"
                                  strokeDashoffset={251.2 - (251.2 * riskAnalysis.risk_score) / 100}
                                  transform="rotate(-90 50 50)"
                                  className={`transition-all duration-700 ease-out ${riskAnalysis.risk_score > 60 ? "text-red-500 dark:text-red-400" : riskAnalysis.risk_score > 30 ? "text-amber-500 dark:text-amber-400" : "text-emerald-500 dark:text-emerald-400"}`}
                                />
                              </svg>
                              {/* 中间的数字 */}
                              <div className="absolute flex flex-col items-center justify-center">
                                <span className={`text-2xl font-bold ${riskAnalysis.risk_score > 60 ? "text-red-500 dark:text-red-400" : riskAnalysis.risk_score > 30 ? "text-amber-500 dark:text-amber-400" : "text-emerald-500 dark:text-emerald-400"}`}>{Math.round(riskAnalysis.risk_score)}</span>
                                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">评分</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* 重新设计的风险因素警报 */}
                      {riskAnalysis?.risk_factors && riskAnalysis.risk_factors.length > 0 && (
                        <div className="relative overflow-hidden transition-all duration-300 rounded-lg group/risk hover:shadow-md">
                          <Alert
                            variant="default"
                            className={`
                              relative z-10 border overflow-hidden backdrop-blur-sm
                              transition-all duration-300 group-hover/risk:translate-y-0
                              ${
                                riskAnalysis.risk_factors[0].score > 60
                                  ? "bg-red-50/90 dark:bg-red-950/30 border-red-200 dark:border-red-800/40"
                                  : riskAnalysis.risk_factors[0].score > 30
                                  ? "bg-amber-50/90 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800/40"
                                  : "bg-emerald-50/90 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/40"
                              }
                            `}
                          >
                            {/* 背景装饰 */}
                            <div
                              className={`
                              absolute inset-0 opacity-10 dark:opacity-20
                              ${riskAnalysis.risk_factors[0].score > 60 ? "bg-risk-pattern-red" : riskAnalysis.risk_factors[0].score > 30 ? "bg-risk-pattern-amber" : "bg-risk-pattern-green"}
                            `}
                            ></div>

                            {/* 左侧彩色指示条 */}
                            <div
                              className={`
                              absolute left-0 top-0 bottom-0 w-1 transition-all duration-500 group-hover/risk:w-1.5
                              ${
                                riskAnalysis.risk_factors[0].score > 60
                                  ? "bg-gradient-to-b from-red-400 to-red-600 dark:from-red-500 dark:to-red-700"
                                  : riskAnalysis.risk_factors[0].score > 30
                                  ? "bg-gradient-to-b from-amber-400 to-amber-600 dark:from-amber-500 dark:to-amber-700"
                                  : "bg-gradient-to-b from-emerald-400 to-emerald-600 dark:from-emerald-500 dark:to-emerald-700"
                              }
                            `}
                            ></div>

                            {/* 警告图标 - 带脉动动画（高风险时） */}
                            <div
                              className={`
                              flex items-center justify-center w-9 h-9 mr-3 rounded-full transition-transform duration-300
                              ${
                                riskAnalysis.risk_factors[0].score > 60
                                  ? "text-red-500 dark:text-red-400 bg-red-100 dark:bg-red-950/50 group-hover/risk:scale-110"
                                  : riskAnalysis.risk_factors[0].score > 30
                                  ? "text-amber-500 dark:text-amber-400 bg-amber-100 dark:bg-amber-950/50 group-hover/risk:scale-105"
                                  : "text-emerald-500 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/50 group-hover/risk:scale-105"
                              }
                              ${riskAnalysis.risk_factors[0].score > 60 ? "animate-pulse" : ""}
                            `}
                            >
                              <AlertTriangle className="w-5 h-5" />
                            </div>

                            <div className="ml-2">
                              <AlertTitle
                                className={`
                                font-bold text-base transition-all duration-300 group-hover/risk:translate-x-0.5
                                ${riskAnalysis.risk_factors[0].score > 60 ? "text-red-700 dark:text-red-300" : riskAnalysis.risk_factors[0].score > 30 ? "text-amber-700 dark:text-amber-300" : "text-emerald-700 dark:text-emerald-300"}
                              `}
                              >
                                {riskAnalysis.risk_factors[0].name}
                              </AlertTitle>

                              <AlertDescription className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                                {riskAnalysis.risk_factors[0].description}
                                {riskAnalysis.risk_factors.length > 1 && (
                                  <div className="flex items-center mt-2 space-x-1">
                                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">还有 {riskAnalysis.risk_factors.length - 1} 个风险因素</span>
                                    <Badge
                                      variant="outline"
                                      className={`
                                      text-xs px-1.5 py-0 h-4 transition-colors duration-300
                                      ${
                                        riskAnalysis.risk_factors[0].score > 60
                                          ? "border-red-200 bg-red-100/50 text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400"
                                          : riskAnalysis.risk_factors[0].score > 30
                                          ? "border-amber-200 bg-amber-100/50 text-amber-600 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400"
                                          : "border-emerald-200 bg-emerald-100/50 text-emerald-600 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400"
                                      }
                                    `}
                                    >
                                      {riskAnalysis.risk_factors.length - 1}
                                    </Badge>
                                  </div>
                                )}
                              </AlertDescription>
                            </div>
                          </Alert>
                        </div>
                      )}

                      {/* 重新设计的建议警报 */}
                      {portfolio.recommendations && portfolio.recommendations.length > 0 && (
                        <div className="relative overflow-hidden transition-all duration-300 rounded-lg group/rec hover:shadow-md">
                          <Alert className="relative z-10 overflow-hidden transition-all duration-300 border border-blue-200 backdrop-blur-sm bg-blue-50/90 dark:bg-blue-950/30 dark:border-blue-800/40 group-hover/rec:translate-y-0">
                            {/* 背景装饰 */}
                            <div className="absolute inset-0 opacity-10 dark:opacity-20 bg-rec-pattern"></div>

                            {/* 左侧彩色指示条 */}
                            <div className="absolute left-0 top-0 bottom-0 w-1 transition-all duration-500 group-hover/rec:w-1.5 bg-gradient-to-b from-blue-400 to-blue-600 dark:from-blue-500 dark:to-blue-700"></div>

                            {/* 建议图标 - 带微妙的悬停动画 */}
                            <div className="flex items-center justify-center mr-3 text-blue-500 transition-transform duration-300 bg-blue-100 rounded-full w-9 h-9 dark:text-blue-400 dark:bg-blue-950/50 group-hover/rec:scale-105">
                              <Shield className="w-5 h-5" />
                            </div>

                            <div className="ml-2">
                              <AlertTitle className="font-bold text-base text-blue-700 dark:text-blue-300 transition-all duration-300 group-hover/rec:translate-x-0.5">建议优化</AlertTitle>

                              <AlertDescription className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                                {portfolio.recommendations[0]}
                                {portfolio.recommendations.length > 1 && (
                                  <div className="flex items-center mt-2 space-x-1">
                                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">还有 {portfolio.recommendations.length - 1} 条建议</span>
                                    <Badge variant="outline" className="text-xs px-1.5 py-0 h-4 border-blue-200 bg-blue-100/50 text-blue-600 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400">
                                      {portfolio.recommendations.length - 1}
                                    </Badge>
                                  </div>
                                )}
                              </AlertDescription>
                            </div>
                          </Alert>
                        </div>
                      )}

                      {/* 重新设计的详细查看按钮 */}
                      <Button
                        variant="outline"
                        size="sm"
                        className="relative w-full mt-6 overflow-hidden font-medium text-white transition-all duration-300 shadow-sm group/btn bg-gradient-to-r from-blue-400 to-blue-600 hover:from-blue-500 hover:to-blue-700 hover:shadow-md dark:shadow-blue-900/20"
                        onClick={() => {
                          setActiveTab("risk");
                        }}
                      >
                        {/* 按钮背景动画效果 */}
                        <span className="absolute inset-0 w-full h-full transition-all duration-300 opacity-0 bg-gradient-to-r from-blue-300/20 via-white/20 to-blue-300/20 group-hover/btn:opacity-100 group-hover/btn:animate-shimmer"></span>
                        <span className="relative flex items-center justify-center">
                          <Zap className="w-3.5 h-3.5 mr-1.5 transition-transform duration-300 group-hover/btn:scale-110" />
                          查看详细风险分析
                        </span>
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* 风险警报标签页 */}
          <TabsContent value="alerts" className="mt-0">
            <AlertsList address={address} />
          </TabsContent>

          {/* 风险分析标签页 */}
          <TabsContent value="risk" className="mt-0">
            <RiskMonitor portfolio={portfolio} riskAnalysis={riskAnalysis} analyzing={analyzing} completed={riskAnalysis !== null} onAnalyze={analyzeWalletRisk} />
          </TabsContent>

          {/* 市场分析标签页 */}
          <TabsContent value="market" className="mt-0">
            <MarketAnalysis portfolio={portfolio} />
          </TabsContent>

          {/* API测试标签页 */}
          <TabsContent value="api" className="mt-0">
            <ApiTest />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
};

export default Dashboard;
