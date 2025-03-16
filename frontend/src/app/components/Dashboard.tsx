"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import { apiService } from "../services/api";
import type { Portfolio, MarketPrediction } from "../services/api";
import { Loader2, RefreshCw, AlertTriangle, Fuel } from "lucide-react";
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
  const [activeTab, setActiveTab] = useState<"overview" | "market" | "protocols">("overview");
  const [apiHealthy, setApiHealthy] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [gasPrice, setGasPrice] = useState<number | null>(null);
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
  }, [address, isConnected]);

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
    if (!walletAddress && !address) return;

    setLoading(true);
    setError(null);

    try {
      // 获取投资组合数据
      console.log(`正在获取钱包地址 ${walletAddress || address!} 的投资组合数据...`);
      const portfolioData = await apiService.getPortfolio(walletAddress || address!);
      console.log("获取到投资组合数据:", portfolioData);
      setPortfolio(portfolioData);

      // 获取市场预测数据
      const assets = portfolioData.positions.length > 0
        ? [...new Set(portfolioData.positions.map(p => {
            // 从资产名称或tokenList中提取基础资产
            if (p.tokenList && p.tokenList.length > 0) {
              return p.tokenList[0].tokenSymbol.split('/')[0];
            }
            return p.asset.split('/')[0];
          }))]
        : ["ETH", "BTC", "USDC"];

      console.log("正在获取资产预测数据:", assets);
      const predictions: { [key: string]: MarketPrediction } = {};

      for (const asset of assets) {
        try {
          const prediction = await apiService.predictMarket(asset);
          predictions[asset] = prediction;
        } catch (err) {
          console.error(`获取${asset}市场预测失败:`, err);
        }
      }

      setMarketPredictions(predictions);
    } catch (err) {
      console.error("获取投资组合数据失败:", err);
      setError("获取数据失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (refreshing) return;

    setRefreshing(true);
    fetchPortfolioData()
      .then(() => {
        fetchGasPrice();
      })
      .finally(() => {
        setTimeout(() => {
          setRefreshing(false);
        }, 1000);
      });
  };

  if (!apiHealthy) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center text-destructive">
            <AlertTriangle className="mr-2 h-5 w-5" />
            API 服务不可用
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            无法连接到后端服务，请检查服务是否正常运行，或稍后再试。
          </p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => checkApiHealth()}
          >
            重试连接
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!isConnected) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>欢迎使用 DeFi 风险监控</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            请连接您的钱包以查看您的 DeFi 投资组合和风险分析。
          </p>
        </CardContent>
      </Card>
    );
  }

  if (loading && !portfolio) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-64">
        <Loader2 className="h-10 w-10 text-primary animate-spin mb-4" />
        <p className="text-muted-foreground">正在加载数据...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {!apiHealthy ? (
        <div className="text-center py-12">
          <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">API服务不可用</h2>
          <p className="text-muted-foreground mb-6">
            无法连接到后端服务，请稍后再试
          </p>
          <Button onClick={checkApiHealth}>重试连接</Button>
        </div>
      ) : !isConnected ? (
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold mb-4">连接钱包以查看您的DeFi仪表盘</h2>
          <p className="text-muted-foreground mb-6">
            连接您的钱包以查看您的投资组合、风险分析和市场预测
          </p>
        </div>
      ) : (
        <>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
            <div>
              <h1 className="text-3xl font-bold">DeFi风险仪表盘</h1>
              <p className="text-muted-foreground">
                查看您的投资组合、风险分析和市场预测
              </p>
            </div>

            <div className="flex items-center gap-4">
              {gasPrice !== null && (
                <div className="hidden md:flex items-center gap-2 bg-muted/50 px-3 py-1.5 rounded-lg text-sm">
                  <Fuel className="h-4 w-4 text-yellow-500" />
                  <span>Gas: {gasPrice.toFixed(0)} Gwei</span>
                </div>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2"
              >
                {refreshing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                刷新数据
              </Button>
            </div>
          </div>

          <Tabs defaultValue={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
            <TabsList className="mb-6">
              <TabsTrigger value="overview">投资组合概览</TabsTrigger>
              <TabsTrigger value="market">市场分析</TabsTrigger>
              <TabsTrigger value="protocols">我的协议</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              {/* 现有的概览内容 */}
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : error ? (
                <div className="text-center py-12">
                  <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
                  <h2 className="text-xl font-bold mb-2">获取数据出错</h2>
                  <p className="text-muted-foreground mb-6">{error}</p>
                  <Button onClick={() => fetchPortfolioData(address)}>重试</Button>
                </div>
              ) : (
                <>
                  {portfolio && (
                    <>
                      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                          <PortfolioOverview portfolio={portfolio} />
                        </div>
                        <div>
                          <RiskMonitor portfolio={portfolio} />
                        </div>
                      </div>

                      <AlertsList address={address} />
                    </>
                  )}
                </>
              )}
            </TabsContent>

            <TabsContent value="market">
              {/* 现有的市场分析内容 */}
              <MarketAnalysis
                marketPredictions={marketPredictions}
                selectedAsset={selectedAsset}
                onAssetChange={setSelectedAsset}
              />
            </TabsContent>

            <TabsContent value="protocols" className="space-y-6">
              {/* 新增的协议列表内容 */}
              <ProtocolList
                walletAddress={address}
                title="我的DeFi协议"
              />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
};

export default Dashboard;
