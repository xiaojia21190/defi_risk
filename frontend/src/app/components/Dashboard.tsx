"use client";

import React, { useState, useEffect } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import { apiService } from "../services/api";
import { useRiskMonitor } from "../services/contract";
import { Portfolio, MarketPrediction } from "../services/api";
import { Loader2 } from "lucide-react";

export const Dashboard: React.FC = () => {
  const { address, isConnected } = useAccount();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [marketPredictions, setMarketPredictions] = useState<{ [key: string]: MarketPrediction }>({});
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "market">("overview");

  // 获取合约数据
  const riskMonitor = useRiskMonitor();

  useEffect(() => {
    if (isConnected && address) {
      fetchPortfolioData();
    }
  }, [address, isConnected]);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await apiService.getPortfolio(address || "");
      setPortfolio(data);

      // 获取每个资产的市场预测
      const predictions: { [key: string]: MarketPrediction } = {};
      for (const position of data.positions) {
        const asset = position.asset.split("/")[0];
        if (!predictions[asset]) {
          const prediction = await apiService.predictMarket(asset);

          // 确保警报数据存在
          if (!prediction.alerts || prediction.alerts.length === 0) {
            // 尝试获取市场警报
            try {
              const alerts = await apiService.getMarketAlerts(address || "");
              // 过滤出与当前资产相关的警报
              const assetAlerts = alerts.filter((alert) => alert.asset === asset);
              prediction.alerts = assetAlerts;
            } catch (alertError) {
              console.error("Error fetching market alerts:", alertError);
              prediction.alerts = [];
            }
          }

          predictions[asset] = prediction;
        }
      }
      setMarketPredictions(predictions);
    } catch (error) {
      console.error("Error fetching data:", error);
      setError("获取数据失败");
    } finally {
      setLoading(false);
    }
  };

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
            <span className="text-2xl">!</span>
          </div>
          <h3 className="text-lg font-medium mb-2">出错了</h3>
          <p className="text-muted">{error}</p>
          <button onClick={fetchPortfolioData} className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
            重试
          </button>
        </div>
      </div>
    );
  }

  if (!portfolio) {
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

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">DeFi 投资组合</h1>
          <div className="flex gap-2">
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
              <RiskMonitor portfolio={portfolio} />
            </div>
          </div>
          <div className="bg-card rounded-xl border border-border p-6 shadow-sm hover:shadow-md transition-all">
            <AlertsList portfolio={portfolio} predictions={marketPredictions} />
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
                {portfolio.positions.map((position) => (
                  <option key={position.asset} value={position.asset.split("/")[0]}>
                    {position.asset} - {position.protocol}
                  </option>
                ))}
              </select>
            </div>
            <MarketAnalysis asset={selectedAsset} prediction={marketPredictions[selectedAsset]} marketAnalysis={portfolio.market_analysis[selectedAsset]} aiPrediction={portfolio.ai_predictions[selectedAsset]} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
