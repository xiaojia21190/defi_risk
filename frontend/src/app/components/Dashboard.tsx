"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import { apiService } from "../services/api";
import type { Portfolio, MarketPrediction } from "../services/api";
import { Loader2, RefreshCw, AlertTriangle, Fuel, Shield, BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./ui/tabs";
import { Badge } from "./ui/badge";
import ProtocolList from "./ProtocolList";

export const Dashboard: React.FC = () => {
  const { address, isConnected } = useAccount();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [marketPredictions, setMarketPredictions] = useState<{ [key: string]: MarketPrediction }>({});
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "market" | "protocols" | "alerts">("overview");
  const [apiHealthy, setApiHealthy] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [gasPrice, setGasPrice] = useState<number | null>(null);
  const [analyzingRisk, setAnalyzingRisk] = useState<boolean>(false);
  const [riskAnalysisCompleted, setRiskAnalysisCompleted] = useState<boolean>(false);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;

    const init = async () => {
      const isHealthy = await checkApiHealth();

      if (!isHealthy) {
        return;
      }

      // 获取当前gas价格
      fetchGasPrice();

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
      setRiskAnalysisCompleted(false);
    }
  }, [isConnected, address]);

  const checkApiHealth = async () => {
    const isHealthy = await apiService.checkApiHealth();
    setApiHealthy(isHealthy);
    return isHealthy;
  };

  const fetchGasPrice = async () => {
    try {
      const price = await apiService.getGasPrice();
      setGasPrice(price);
    } catch (error) {
      console.error("获取Gas价格失败:", error);
    }
  };

  const fetchPortfolioData = async (walletAddress?: string) => {
    if (!walletAddress) return;

    try {
      setLoading(true);
      setError(null);

      // 获取投资组合数据
      const portfolioData = await apiService.getPortfolio(walletAddress);
      setPortfolio(portfolioData);

      // 获取市场预测数据
      const assets = Array.from(
        new Set(portfolioData.positions.map((pos) => pos.asset.split("/")[0]))
      );

      const predictions: { [key: string]: MarketPrediction } = {};
      for (const asset of assets) {
        try {
          const prediction = await apiService.predictMarket(asset);
          predictions[asset] = prediction;
        } catch (error) {
          console.error(`获取${asset}市场预测失败:`, error);
        }
      }

      setMarketPredictions(predictions);
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
      setAnalyzingRisk(true);
      setError(null);

      // 调用风险分析API
      const riskAnalysis = await apiService.analyzeWalletRisk(address);

      // 更新投资组合数据，包含风险分析结果
      if (portfolio) {
        setPortfolio({
          ...portfolio,
          risk_level: riskAnalysis.risk_level,
          recommendations: riskAnalysis.recommendations || []
        });
      }

      setRiskAnalysisCompleted(true);
    } catch (error) {
      console.error("分析钱包风险失败:", error);
      setError("无法完成风险分析");
    } finally {
      setAnalyzingRisk(false);
    }
  };

  const handleRefresh = () => {
    if (refreshing || !address) return;

    setRefreshing(true);
    fetchPortfolioData(address)
      .then(() => fetchGasPrice())
      .finally(() => {
        setRefreshing(false);
      });
  };

  if (!apiHealthy) {
    return (
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            API服务不可用
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            无法连接到后端API服务。请检查服务器状态或稍后再试。
          </p>
          <Button
            className="mt-4"
            onClick={checkApiHealth}
          >
            重试连接
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!isConnected) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>连接钱包</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            请连接您的钱包以查看DeFi投资组合和风险分析。
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">DeFi投资组合</h2>
        <div className="flex items-center gap-2">
          {gasPrice !== null && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground bg-background/50 px-3 py-1 rounded-full border border-border">
              <Fuel className="h-3.5 w-3.5" />
              <span>Gas: {gasPrice.toFixed(0)} Gwei</span>
            </div>
          )}
          <Button
            onClick={handleRefresh}
            disabled={refreshing || loading}
          >
            {refreshing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span className="ml-2">刷新数据</span>
          </Button>
        </div>
      </div>

      {loading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-8">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">正在加载投资组合数据...</p>
            </div>
          </CardContent>
        </Card>
      ) : error ? (
        <Card className="border-destructive">
          <CardContent className="py-6">
            <div className="flex items-center gap-2 text-destructive mb-2">
              <AlertTriangle className="h-5 w-5" />
              <p className="font-medium">加载失败</p>
            </div>
            <p className="text-muted-foreground">{error}</p>
            <Button
              className="mt-4"
              onClick={() => fetchPortfolioData(address)}
            >
              重试
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 投资组合概览 */}
          <PortfolioOverview portfolio={portfolio} />

          {/* 风险分析按钮 */}
          <div className="flex justify-center mt-6">
            <Button
              className="gap-2"
              onClick={analyzeWalletRisk}
              disabled={analyzingRisk || !portfolio}
            >
              {analyzingRisk ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Shield className="h-5 w-5" />
              )}
              {analyzingRisk ? "正在分析风险..." : riskAnalysisCompleted ? "更新风险分析" : "开始风险分析"}
            </Button>
          </div>

          {/* 风险分析结果 */}
          {riskAnalysisCompleted && portfolio && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  风险分析结果
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">风险等级:</span>
                    <Badge className={
                      portfolio.risk_level === "高" ? "bg-destructive" :
                      portfolio.risk_level === "中等" ? "bg-amber-500" : "bg-green-500"
                    }>
                      {portfolio.risk_level}
                    </Badge>
                  </div>

                  {portfolio.recommendations && portfolio.recommendations.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">建议:</h4>
                      <ul className="space-y-1 text-sm text-muted-foreground">
                        {portfolio.recommendations.map((rec, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 标签页 */}
          <Tabs defaultValue={activeTab} onValueChange={(value) => setActiveTab(value as any)} className="mt-6">
            <TabsList className="grid grid-cols-3 mb-4">
              <TabsTrigger value="overview" className="flex items-center gap-1">
                <BarChart3 className="h-4 w-4" />
                <span>市场分析</span>
              </TabsTrigger>
              <TabsTrigger value="protocols" className="flex items-center gap-1">
                <Shield className="h-4 w-4" />
                <span>协议列表</span>
              </TabsTrigger>
              <TabsTrigger value="alerts" className="flex items-center gap-1">
                <AlertTriangle className="h-4 w-4" />
                <span>警报</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              <MarketAnalysis
                marketPredictions={marketPredictions}
                selectedAsset={selectedAsset}
                onAssetChange={setSelectedAsset}
              />
            </TabsContent>

            <TabsContent value="protocols" className="space-y-4">
              <ProtocolList walletAddress={address} title="您使用的DeFi协议" />
            </TabsContent>

            <TabsContent value="alerts" className="space-y-4">
              <AlertsList address={address} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
};

export default Dashboard;
