"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSupportedProtocols, Protocol } from "../services/protocols";
import { Shield, AlertTriangle, TrendingUp } from "lucide-react";

export function ProtocolList() {
  const {
    data: protocols,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["protocols"],
    queryFn: fetchSupportedProtocols,
  });

  if (isLoading) {
    return <div className="flex justify-center p-8">Loading protocols...</div>;
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-500 p-4">
        <AlertTriangle size={20} />
        <span>Failed to load protocols</span>
      </div>
    );
  }

  return (
    <div className="w-full">
      <h2 className="text-2xl font-bold mb-6">Supported DeFi Protocols</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {protocols?.map((protocol) => (
          <div key={protocol.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold">{protocol.name}</h3>
              <div className="flex items-center gap-2">
                <Shield className={`w-5 h-5 ${getRiskColor(protocol.riskScore)}`} />
                {protocol.riskScore && <span className="text-sm">Risk: {protocol.riskScore}</span>}
              </div>
            </div>
            <div className="text-gray-600 dark:text-gray-300 text-sm mb-4">{protocol.description || "No description available"}</div>
            <div className="flex items-center justify-between text-sm">
              <span className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-100 px-3 py-1 rounded-full">{protocol.category}</span>
              {protocol.tvl && (
                <div className="flex items-center gap-1">
                  <TrendingUp className="w-4 h-4" />
                  <span>TVL: ${formatTVL(protocol.tvl)}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function getRiskColor(riskScore?: number): string {
  if (!riskScore) return "text-gray-400";
  if (riskScore < 3) return "text-green-500";
  if (riskScore < 7) return "text-yellow-500";
  return "text-red-500";
}

function formatTVL(tvl: number): string {
  if (tvl >= 1e9) return `${(tvl / 1e9).toFixed(2)}B`;
  if (tvl >= 1e6) return `${(tvl / 1e6).toFixed(2)}M`;
  if (tvl >= 1e3) return `${(tvl / 1e3).toFixed(2)}K`;
  return tvl.toFixed(2);
}
