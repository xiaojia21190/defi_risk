"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import { apiService } from "../services/api";
import type { Portfolio, WalletRiskAssessment } from "../services/api";
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
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const initialized = useRef(false);
  const [marketPredictions, setMarketPredictions] = useState<{ [key: string]: any } | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");
  const [loadingMarketData, setLoadingMarketData] = useState(false);

  useEffect(() => {
    if (initialized.current) return;

    const init = async () => {
      if (isConnected && address) {
        initialized.current = true;
        fetchPortfolioData(address);
      }
    };

    init();
  }, [isConnected, address]);

  // 当钱包地址变化时重新获取数据
  useEffect(() => {
    if (isConnected && address) {
      fetchPortfolioData(address);
    } else {
      setPortfolio(null);
      setRiskAnalysis(null);
    }
  }, [isConnected, address]);

  // 获取市场分析数据
  useEffect(() => {
    if (portfolio) {
      fetchMarketData(selectedAsset);
    }
  }, [portfolio, selectedAsset]);

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

  // 获取市场分析数据
  const fetchMarketData = async (asset: string) => {
    try {
      setLoadingMarketData(true);

      // 调用市场预测API
      const prediction = await apiService.predictMarket(asset, "24h");

      // 扩展市场预测数据
      const extendedPrediction = {
        ...prediction,
        asset,
        time_frame: "24h",
        price_history: {
          timestamp: { "1": new Date().toISOString(), "2": new Date(Date.now() - 86400000).toISOString() },
          price: { "1": 1800, "2": 1750 }, // 示例数据，实际应从API获取
          volume: { "1": 3000000, "2": 2800000 },
          market_cap: { "1": 200000000, "2": 195000000 },
          source: { "1": "api", "2": "api" },
        },
        predictions: [
          {
            target: "price",
            timeframe: "24h",
            value: prediction.predicted_price_range["24h"][1],
            probability: 0.8,
            range: prediction.predicted_price_range["24h"],
          },
        ],
        insights: prediction.recommendations || [],
        timestamp: new Date().toISOString(),
        confidence: 0.75,
      };

      setMarketPredictions({
        ...marketPredictions,
        [asset]: extendedPrediction,
      });
    } catch (error) {
      console.error("获取市场分析数据失败:", error);
    } finally {
      setLoadingMarketData(false);
    }
  };

  // 选择资产处理函数
  const handleAssetSelect = (asset: string) => {
    setSelectedAsset(asset);
    if (!marketPredictions?.[asset]) {
      fetchMarketData(asset);
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
      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight">DeFi投资组合</h2>
          <p className="text-sm text-muted-foreground">
            实时监控您的DeFi资产
            {lastUpdateTime && <span className="ml-2">· 最后更新: {lastUpdateTime.toLocaleTimeString()}</span>}
          </p>
        </div>
        <div className="flex gap-2 items-center">
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
        <Card className="p-6 w-full">
          <div className="flex justify-center items-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        </Card>
      )}

      {!loading && !error && portfolio && (
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="overview">投资组合概览</TabsTrigger>
            <TabsTrigger value="alerts">风险警报</TabsTrigger>
            <TabsTrigger value="risk">风险分析</TabsTrigger>
            <TabsTrigger value="market">市场分析</TabsTrigger>
          </TabsList>

          {/* 投资组合概览标签页 */}
          <TabsContent value="overview" className="mt-0">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="md:col-span-2">
                <PortfolioOverview portfolio={adaptPortfolioForOverview(portfolio)} />
              </div>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle>风险分析摘要</CardTitle>
                  <CardDescription>您的DeFi投资组合风险概况</CardDescription>
                </CardHeader>
                <CardContent>
                  {!portfolio.risk_level ? (
                    <div className="flex flex-col justify-center items-center space-y-4">
                      <Shield className="w-12 h-12 text-muted-foreground" />
                      <Button onClick={analyzeWalletRisk} disabled={analyzing}>
                        {analyzing ? (
                          <>
                            <Loader2 className="mr-2 w-4 h-4 animate-spin" />
                            分析中...
                          </>
                        ) : (
                          "开始风险分析"
                        )}
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="text-sm font-medium">风险等级</p>
                          <div className="flex gap-2 items-center">
                            <h3 className="text-2xl font-bold">{portfolio.risk_level}</h3>
                            {riskAnalysis?.risk_score !== undefined && (
                              <Badge variant="outline" className="text-sm">
                                风险评分: {riskAnalysis.risk_score}/100
                              </Badge>
                            )}
                          </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={analyzeWalletRisk} disabled={analyzing}>
                          {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : "重新分析"}
                        </Button>
                      </div>

                      {/* 简化的风险信息 */}
                      {riskAnalysis?.risk_factors && riskAnalysis.risk_factors.length > 0 && (
                        <div>
                          <p className="mb-1 text-sm font-medium">主要风险因素</p>
                          <p className="text-sm text-destructive">• {riskAnalysis.risk_factors[0]}</p>
                          {riskAnalysis.risk_factors.length > 1 && <p className="mt-1 text-xs text-muted-foreground">还有 {riskAnalysis.risk_factors.length - 1} 个风险因素</p>}
                        </div>
                      )}

                      {/* 简化的建议措施 */}
                      {portfolio.recommendations && portfolio.recommendations.length > 0 && (
                        <div>
                          <p className="mb-1 text-sm font-medium">建议</p>
                          <p className="text-sm text-muted-foreground">• {portfolio.recommendations[0]}</p>
                          {portfolio.recommendations.length > 1 && <p className="mt-1 text-xs text-muted-foreground">还有 {portfolio.recommendations.length - 1} 个建议</p>}
                        </div>
                      )}

                      {/* 查看详情按钮 */}
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-2 w-full"
                        onClick={() => {
                          const riskTab = document.querySelector('[data-value="risk"]') as HTMLButtonElement;
                          if (riskTab) riskTab.click();
                        }}
                      >
                        查看详细风险分析
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
            <Card>
              <CardHeader>
                <CardTitle>详细风险分析</CardTitle>
                <CardDescription>分析您的DeFi投资组合风险</CardDescription>
              </CardHeader>
              <CardContent>
                {!portfolio.risk_level ? (
                  <div className="flex flex-col justify-center items-center space-y-4">
                    <Shield className="w-12 h-12 text-muted-foreground" />
                    <Button onClick={analyzeWalletRisk} disabled={analyzing}>
                      {analyzing ? (
                        <>
                          <Loader2 className="mr-2 w-4 h-4 animate-spin" />
                          分析中...
                        </>
                      ) : (
                        "开始风险分析"
                      )}
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="text-sm font-medium">风险等级</p>
                        <div className="flex gap-2 items-center">
                          <h3 className="text-2xl font-bold">{portfolio.risk_level}</h3>
                          {riskAnalysis?.risk_score !== undefined && (
                            <Badge variant="outline" className="text-sm">
                              风险评分: {riskAnalysis.risk_score}/100
                            </Badge>
                          )}
                        </div>
                      </div>
                      <Button variant="outline" size="sm" onClick={analyzeWalletRisk} disabled={analyzing}>
                        {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : "重新分析"}
                      </Button>
                    </div>

                    {/* 风险因素 */}
                    {riskAnalysis?.risk_factors && riskAnalysis.risk_factors.length > 0 && (
                      <div>
                        <p className="mb-2 text-sm font-medium">风险因素</p>
                        <ul className="space-y-1">
                          {riskAnalysis.risk_factors.map((factor, index) => (
                            <li key={index} className="text-sm text-destructive">
                              • {factor}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 风险指标 */}
                    {riskAnalysis?.risk_metrics && Object.keys(riskAnalysis.risk_metrics).length > 0 && (
                      <div>
                        <p className="mb-2 text-sm font-medium">风险指标</p>
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(riskAnalysis.risk_metrics).map(([key, value], index) => (
                            <div key={index} className="p-2 rounded-md border">
                              <p className="text-xs text-muted-foreground">{key}</p>
                              <p className="text-sm font-medium">{value}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 推荐措施 */}
                    {portfolio.recommendations && portfolio.recommendations.length > 0 && (
                      <div>
                        <p className="mb-2 text-sm font-medium">建议</p>
                        <ul className="space-y-1">
                          {portfolio.recommendations.map((rec, index) => (
                            <li key={index} className="text-sm text-muted-foreground">
                              • {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 预警信息 */}
                    {riskAnalysis?.warnings && riskAnalysis.warnings.length > 0 && (
                      <div>
                        <p className="mb-2 text-sm font-medium">预警信息</p>
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
                        <p className="mb-2 text-sm font-medium">监控点</p>
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
                        <p className="mb-2 text-sm font-medium">头寸摘要</p>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="p-2 rounded-md border">
                            <p className="text-xs text-muted-foreground">总价值</p>
                            <p className="text-sm font-medium">${riskAnalysis.positions_summary.total_value.toLocaleString()}</p>
                          </div>
                          <div className="p-2 rounded-md border">
                            <p className="text-xs text-muted-foreground">头寸数量</p>
                            <p className="text-sm font-medium">{riskAnalysis.positions_summary.position_count}</p>
                          </div>
                        </div>

                        {riskAnalysis.positions_summary.protocols.length > 0 && (
                          <div className="mt-2">
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
                          <div className="mt-2">
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
                          <Zap className="mr-1 w-3 h-3" />
                          AI增强分析
                        </Badge>
                      </div>
                    )}

                    {/* 分析时间戳 */}
                    {riskAnalysis?.analysis_timestamp && <div className="mt-4 text-xs text-muted-foreground">分析时间: {new Date(riskAnalysis.analysis_timestamp).toLocaleString()}</div>}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 市场分析标签页 */}
          <TabsContent value="market" className="mt-0">
            <MarketAnalysis marketPredictions={marketPredictions} loading={loadingMarketData} onAssetSelect={handleAssetSelect} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
};

export default Dashboard;
