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

export const Dashboard: React.FC = () => {
  const { address, isConnected } = useAccount();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [marketPredictions, setMarketPredictions] = useState<{ [key: string]: MarketPrediction }>({});
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "market">("overview");
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
    try {
      setLoading(true);
      setError(null);

      const targetAddress = walletAddress || address || "";
      if (!targetAddress) {
        setError("请连接钱包以查看数据");
        setLoading(false);
        return;
      }

      const data = await apiService.getPortfolio(targetAddress);
      setPortfolio(data);

      // 获取每个资产的市场预测
      const predictions: { [key: string]: MarketPrediction } = {};
      for (const position of data.positions) {
        const asset = position.asset.split("/")[0];
        if (!predictions[asset]) {
          try {
            const prediction = await apiService.predictMarket(asset);

            predictions[asset] = prediction;
          } catch (predictionError) {
            console.error(`获取${asset}预测失败:`, predictionError);
            // 继续处理其他资产
          }
        }
      }

      setMarketPredictions(predictions);

      // 设置默认选中的资产
      if (data.positions.length > 0 && !predictions[selectedAsset]) {
        const firstAsset = data.positions[0].asset.split("/")[0];
        setSelectedAsset(firstAsset);
      }
    } catch (error) {
      console.error("获取数据失败:", error);
      setError(typeof error === "object" && error !== null && "message" in error ? (error as Error).message : "获取数据失败，请稍后再试");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchPortfolioData();
  };

  if (!apiHealthy) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="bg-destructive/10 text-destructive p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-medium mb-2">API服务不可用</h3>
          <p className="text-muted">无法连接到后端服务，请检查服务是否运行</p>
          <button onClick={checkApiHealth} className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
            重试连接
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="bg-destructive/10 text-destructive p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-medium mb-2">出错了</h3>
          <p className="text-muted">{error}</p>
          <button onClick={() => fetchPortfolioData()} className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
            重试
          </button>
        </div>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="bg-muted p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
            <span className="text-2xl">💼</span>
          </div>
          <h3 className="text-lg font-medium mb-2">未连接钱包</h3>
          <p className="text-muted">请连接您的钱包以查看投资组合</p>
        </div>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="bg-muted p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
            <span className="text-2xl">📊</span>
          </div>
          <h3 className="text-lg font-medium mb-2">暂无数据</h3>
          <p className="text-muted">未找到投资组合数据</p>
          <button onClick={() => fetchPortfolioData(address)} className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
            刷新数据
          </button>
        </div>
      </div>
    );
  }

  // 确保portfolio不为null后再使用
  const { positions, total_value, risk_level } = portfolio;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">DeFi 投资组合</h1>
          <div className="flex gap-2 items-center">
            {gasPrice !== null && (
              <div className="px-3 py-1 rounded-lg bg-muted text-sm flex items-center gap-1 mr-2">
                <Fuel className="h-4 w-4 text-amber-500" />
                <span>Gas: {gasPrice.toFixed(0)} Gwei</span>
              </div>
            )}
            <button onClick={handleRefresh} disabled={refreshing} className="p-2 rounded-lg bg-muted hover:bg-muted/80 transition-colors" title="刷新数据">
              <RefreshCw className={`h-5 w-5 ${refreshing ? "animate-spin" : ""}`} />
            </button>
            <button onClick={() => setActiveTab("overview")} className={`px-4 py-2 rounded-lg transition-colors ${activeTab === "overview" ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}>
              总览
            </button>
            <button onClick={() => setActiveTab("market")} className={`px-4 py-2 rounded-lg transition-colors ${activeTab === "market" ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}>
              市场分析
            </button>
          </div>
        </div>
      </div>

      {activeTab === "overview" ? (
        <div className="grid grid-cols-1 gap-8 animate-fade-in">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-card rounded-xl border border-border p-6 shadow-sm hover:shadow-md transition-all">
              <PortfolioOverview portfolio={portfolio} />
            </div>
            <div className="bg-card rounded-xl border border-border p-6 shadow-sm hover:shadow-md transition-all">
              <RiskMonitor portfolio={portfolio} marketPredictions={marketPredictions} />
            </div>
          </div>
          <div className="bg-card rounded-xl border border-border p-6 shadow-sm hover:shadow-md transition-all">
            <AlertsList walletAddress={address || ""} />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 animate-fade-in">
          <div className="bg-card rounded-xl border border-border p-6 shadow-sm hover:shadow-md transition-all">
            <div className="mb-6">
              <label htmlFor="asset-select" className="block mb-2 text-sm font-medium">
                选择资产分析
              </label>
              <select id="asset-select" value={selectedAsset} onChange={(e) => setSelectedAsset(e.target.value)} className="block w-full md:w-64 px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all">
                {portfolio.positions.map((position) => {
                  const asset = position.asset.split("/")[0];
                  return (
                    <option key={position.asset} value={asset}>
                      {position.asset} - {position.protocol}
                    </option>
                  );
                })}
              </select>
            </div>
            {marketPredictions[selectedAsset] ? (
              <MarketAnalysis asset={selectedAsset} prediction={marketPredictions[selectedAsset]} marketAnalysis={portfolio.market_analysis[selectedAsset]} />
            ) : (
              <div className="text-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
                <p className="text-muted">加载市场数据中...</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
