"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import ApiTest from "./ApiTest";
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
      <Card>
        <CardHeader>
          <CardTitle>连接钱包</CardTitle>
          <CardDescription>请连接您的钱包以查看DeFi投资组合和风险分析。</CardDescription>
        </CardHeader>
      </Card>
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
