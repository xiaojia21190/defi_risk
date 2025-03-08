"use client";

import React, { useState, useEffect } from "react";
import { useAccount } from "wagmi";
import RiskMonitor from "./RiskMonitor";
import PortfolioOverview from "./PortfolioOverview";
import AlertsList from "./AlertsList";
import MarketAnalysis from "./MarketAnalysis";
import { apiService } from "../services/api";
import { useRiskMonitor } from "../services/contract";

type OnChainPosition = {
  protocol: `0x${string}`;
  asset: `0x${string}`;
  amount: bigint;
  leverage: bigint;
  liquidationThreshold: bigint;
};

type OnChainAlert = {
  user: `0x${string}`;
  protocol: `0x${string}`;
  asset: `0x${string}`;
  riskLevel: bigint;
  timestamp: bigint;
};

export const Dashboard: React.FC = () => {
  const { address, isConnected } = useAccount();
  const [portfolio, setPortfolio] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<string>("ETH");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 获取合约数据
  const riskMonitor = useRiskMonitor();
  const { data: onchainPositions } = riskMonitor.usePositions(address || "");
  const { data: onchainAlerts } = riskMonitor.useAlerts(address || "");

  useEffect(() => {
    if (isConnected && address) {
      fetchPortfolioData();
      fetchAlerts();
    }
  }, [address, isConnected]);

  // 当链上数据更新时，更新本地状态
  useEffect(() => {
    if (onchainPositions) {
      // 将链上数据转换为前端格式
      const positions = onchainPositions.map((pos: OnChainPosition) => ({
        protocol: pos.protocol,
        asset: pos.asset,
        amount: Number(pos.amount),
        leverage: Number(pos.leverage),
        liquidationThreshold: Number(pos.liquidationThreshold),
      }));

      // 更新投资组合数据
      if (portfolio) {
        setPortfolio({
          ...portfolio,
          positions: [...portfolio.positions, ...positions],
        });
      }
    }
  }, [onchainPositions, portfolio]);

  useEffect(() => {
    if (onchainAlerts) {
      // 将链上警报转换为前端格式
      const chainAlerts = onchainAlerts.map((alert: OnChainAlert, index) => ({
        id: `chain-${index}`,
        type: "liquidation",
        severity: Number(alert.riskLevel) > 70 ? "high" : "medium",
        message: `风险等级: ${Number(alert.riskLevel)}`,
        timestamp: new Date(Number(alert.timestamp) * 1000).toISOString(),
        protocol: alert.protocol,
        asset: alert.asset,
      }));

      // 更新警报数据
      setAlerts((prev) => [...prev, ...chainAlerts]);
    }
  }, [onchainAlerts]);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getPortfolio(address as string);
      setPortfolio(data);
    } catch (error) {
      console.error("Error fetching portfolio:", error);
      setError("获取投资组合数据失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    try {
      const data = await apiService.getAlerts(address as string);
      setAlerts(data);
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  };

  if (!isConnected) {
    return (
      <div className="flex justify-center items-center h-full w-full">
        <div className="text-center">
          <h2 className="mb-4 text-2xl font-bold">请连接钱包</h2>
          <p className="text-gray-600">连接您的钱包以查看投资组合风险分析</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full w-full">
        <div className="text-center">
          <div className="mb-4 w-12 h-12 rounded-full border-b-2 border-blue-600 animate-spin"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-full w-full">
        <div className="text-center">
          <h2 className="mb-4 text-2xl font-bold text-red-600">出错了</h2>
          <p className="mb-4 text-gray-600">{error}</p>
          <button onClick={fetchPortfolioData} className="px-4 py-2 text-white bg-blue-600 rounded-lg transition-colors hover:bg-blue-700">
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container px-4 py-8 mx-auto">
      <h1 className="mb-8 text-3xl font-bold">DeFi 风险监控仪表板</h1>

      <div className="grid grid-cols-1 gap-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          <PortfolioOverview portfolio={portfolio} />
          <RiskMonitor portfolio={portfolio} />
        </div>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          <AlertsList alerts={alerts} />
          <div className="space-y-4">
            <div className="p-4 bg-white rounded-lg shadow">
              <label htmlFor="asset-select" className="block mb-2 text-sm font-medium text-gray-700">
                选择资产
              </label>
              <select id="asset-select" value={selectedAsset} onChange={(e) => setSelectedAsset(e.target.value)} className="block px-3 py-2 w-full rounded-md border border-gray-300 shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                <option value="ETH">ETH</option>
                <option value="WBTC">WBTC</option>
                <option value="USDC">USDC</option>
                <option value="DAI">DAI</option>
              </select>
            </div>
            <MarketAnalysis asset={selectedAsset} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
