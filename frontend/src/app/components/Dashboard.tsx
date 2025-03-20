"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import { apiService } from "../services/api";
import type { Portfolio, MarketPrediction } from "../services/api";
import { Loader2, RefreshCw, AlertTriangle, Fuel, Shield, BarChart3, Settings, History, TrendingUp, Wallet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import ProtocolList from "./ProtocolList";

export const Dashboard: React.FC = () => {
  const { address, isConnected } = useAccount();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [marketPredictions, setMarketPredictions] = useState<{ [key: string]: MarketPrediction }>({});
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"market" | "protocols" | "alerts" | "history" | "settings">("market");
  const [apiHealthy, setApiHealthy] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [gasPrice, setGasPrice] = useState<number | null>(null);
  const [analyzingRisk, setAnalyzingRisk] = useState<boolean>(false);
  const [riskAnalysisCompleted, setRiskAnalysisCompleted] = useState<boolean>(false);
  const [loadingMarketData, setLoadingMarketData] = useState<boolean>(false);
  const [marketDataLoaded, setMarketDataLoaded] = useState<boolean>(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(300000); // 5分钟
  const [portfolioHistory, setPortfolioHistory] = useState<Portfolio[]>([]);
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

  // 添加自动刷新逻辑
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (autoRefreshEnabled && address) {
      intervalId = setInterval(() => {
        handleRefresh();
      }, refreshInterval);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [autoRefreshEnabled, refreshInterval, address]);

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

      // 只获取投资组合基础数据（头寸信息）
      const portfolioData = await apiService.getPortfolio(walletAddress);
      setPortfolio(portfolioData);

      // 重置分析状态
      setRiskAnalysisCompleted(false);
      setMarketDataLoaded(false);
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
      const riskAnalysis = await apiService.getWalletRiskAssessment(address);

      // 更新投资组合数据，包含风险分析结果
      if (portfolio) {
        setPortfolio({
          ...portfolio,
          risk_level: riskAnalysis.risk_level,
          recommendations: riskAnalysis.recommendations || [],
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

  // 获取市场数据
  const fetchMarketData = async () => {
    if (!portfolio || portfolio.positions.length === 0) return;

    try {
      setLoadingMarketData(true);

      // 提取资产列表
      const assets = Array.from(
        new Set(
          portfolio.positions.map((pos) => {
            // 从资产名称或tokenList中提取基础资产
            if (pos.tokenList && pos.tokenList.length > 0) {
              return pos.tokenList[0].tokenSymbol.split("/")[0];
            }
            return pos.asset.split("/")[0];
          })
        )
      );

      if (assets.length === 0) {
        setMarketDataLoaded(true);
        return;
      }

      // 获取市场分析数据
      const marketAnalysis = await apiService.getPortfolioMarketAnalysis(assets);

      // 更新投资组合数据，包含市场分析结果
      if (portfolio) {
        setPortfolio({
          ...portfolio,
          market_analysis: marketAnalysis,
        });
      }

      // 获取市场预测数据
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
      setMarketDataLoaded(true);
    } catch (error) {
      console.error("获取市场数据失败:", error);
      setError("无法加载市场数据");
    } finally {
      setLoadingMarketData(false);
    }
  };

  // 优化刷新函数
  const handleRefresh = useCallback(async () => {
    if (refreshing || !address) return;

    try {
      setRefreshing(true);
      setError(null);

      // 并行获取数据
      const [portfolioData, gasPrice] = await Promise.all([apiService.getPortfolio(address), apiService.getGasPrice()]);

      // 添加时间戳
      const portfolioWithTimestamp = {
        ...portfolioData,
        timestamp: new Date().toISOString(),
      };

      setPortfolio(portfolioWithTimestamp);
      setGasPrice(gasPrice);
      setLastUpdateTime(new Date());

      // 更新历史数据
      setPortfolioHistory((prev) => [...prev, portfolioWithTimestamp].slice(-10));
    } catch (error) {
      console.error("刷新数据失败:", error);
      setError("刷新数据失败，请稍后重试");
    } finally {
      setRefreshing(false);
    }
  }, [address, refreshing]);

  // 添加设置面板组件
  const SettingsPanel = () => (
    <Card>
      <CardHeader>
        <CardTitle>设置</CardTitle>
        <CardDescription>自定义您的DeFi监控面板</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">自动刷新</div>
              <div className="text-sm text-muted-foreground">每 {refreshInterval / 60000} 分钟自动更新数据</div>
            </div>
            <Button variant={autoRefreshEnabled ? "default" : "outline"} onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}>
              {autoRefreshEnabled ? "已启用" : "已禁用"}
            </Button>
          </div>
          <div className="space-y-2">
            <div className="text-sm font-medium">刷新间隔</div>
            <select className="w-full p-2 border rounded-md bg-background" value={refreshInterval} onChange={(e) => setRefreshInterval(Number(e.target.value))}>
              <option value={60000}>1分钟</option>
              <option value={300000}>5分钟</option>
              <option value={900000}>15分钟</option>
              <option value={1800000}>30分钟</option>
            </select>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  // 添加历史记录组件
  const HistoryPanel = () => (
    <Card>
      <CardHeader>
        <CardTitle>历史记录</CardTitle>
        <CardDescription>最近10次投资组合变化</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>总资产</TableHead>
                <TableHead>风险等级</TableHead>
                <TableHead>头寸数量</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {portfolioHistory.map((hist, index) => (
                <TableRow key={index}>
                  <TableCell>{new Date(hist.timestamp || "").toLocaleString()}</TableCell>
                  <TableCell>${hist.total_value.toFixed(2)}</TableCell>
                  <TableCell>
                    <Badge variant={hist.risk_level === "高" ? "destructive" : hist.risk_level === "中" ? "secondary" : "outline"}>{hist.risk_level}</Badge>
                  </TableCell>
                  <TableCell>{hist.positions.length}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );

  if (!apiHealthy) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="w-4 h-4" />
        <AlertTitle>API服务不可用</AlertTitle>
        <AlertDescription>
          无法连接到后端API服务。请检查服务器状态或稍后再试。
          <Button className="mt-4" onClick={checkApiHealth}>
            重试连接
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

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
            实时监控您的DeFi资产和风险状况
            {lastUpdateTime && <span className="ml-2">· 最后更新: {lastUpdateTime.toLocaleTimeString()}</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {gasPrice !== null && (
            <Badge variant="outline" className="flex items-center gap-1">
              <Fuel className="h-3.5 w-3.5" />
              <span>Gas: {gasPrice.toFixed(0)} Gwei</span>
            </Badge>
          )}
          <Button onClick={handleRefresh} disabled={refreshing} variant="outline" size="icon">
            {refreshing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {loading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
          <Card className="min-h-[400px] flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </Card>
          <Card className="min-h-[400px] flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </Card>
        </div>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="w-4 h-4" />
          <AlertTitle>错误</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!loading && !error && portfolio && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
          <PortfolioOverview portfolio={portfolio} loading={loadingMarketData} error={error} />
          <RiskMonitor portfolio={portfolio} analyzing={analyzingRisk} completed={riskAnalysisCompleted} onAnalyze={analyzeWalletRisk} />
        </div>
      )}

      <Tabs defaultValue="market" className="space-y-4">
        <TabsList>
          <TabsTrigger value="market" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            市场分析
          </TabsTrigger>
          <TabsTrigger value="protocols" className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            协议风险
          </TabsTrigger>
          <TabsTrigger value="alerts" className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            风险提醒
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="w-4 h-4" />
            历史记录
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            设置
          </TabsTrigger>
        </TabsList>

        <TabsContent value="market" className="space-y-4">
          <MarketAnalysis portfolio={portfolio} marketPredictions={marketPredictions} loading={loadingMarketData} onAssetSelect={setSelectedAsset} />
        </TabsContent>

        <TabsContent value="protocols" className="space-y-4">
          <ProtocolList />
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          <AlertsList />
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <HistoryPanel />
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <SettingsPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Dashboard;
