"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import { apiService } from "../services/api";
import type { Portfolio, MarketPrediction, Position } from "../services/api";
import { Loader2, RefreshCw, AlertTriangle, Fuel, Shield, BarChart3, Settings, History, TrendingUp, Wallet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";

// 风险分析结果接口
interface RiskAnalysis {
  risk_level: string;
  recommendations: string[];
  market_analysis?: {
    [key: string]: {
      current_price: number;
      volume_24h: number;
      market_cap: number;
      price_change_24h: number;
      volatility_30d: number;
    };
  };
}

export const Dashboard: React.FC = () => {
  const { address, isConnected } = useAccount();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [riskAnalysis, setRiskAnalysis] = useState<RiskAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const initialized = useRef(false);

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

      // 更新portfolio的风险相关数据
      if (portfolio) {
        const updatedPortfolio: Portfolio = {
          ...portfolio,
          risk_level: riskAnalysisData.risk_level,
          recommendations: riskAnalysisData.recommendations,
          market_analysis: riskAnalysisData.market_analysis || {},
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
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
          <PortfolioOverview portfolio={portfolio} />
          <Card>
            <CardHeader>
              <CardTitle>风险分析</CardTitle>
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
                      <h3 className="text-2xl font-bold">{portfolio.risk_level}</h3>
                    </div>
                    <Button variant="outline" size="sm" onClick={analyzeWalletRisk} disabled={analyzing}>
                      {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : "重新分析"}
                    </Button>
                  </div>
                  {portfolio.recommendations && portfolio.recommendations.length > 0 && (
                    <div>
                      <p className="mb-2 text-sm font-medium">建议</p>
                      <ul className="space-y-2">
                        {portfolio.recommendations.map((rec, index) => (
                          <li key={index} className="text-sm text-muted-foreground">
                            • {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
