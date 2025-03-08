"use client";

import React from "react";

interface Alert {
  id: string;
  type: "liquidation" | "impermanentLoss" | "marketVolatility";
  severity: "high" | "medium" | "low";
  message: string;
  timestamp: string;
  protocol: string;
  asset: string;
}

interface AlertsListProps {
  alerts: Alert[];
}

const AlertsList: React.FC<AlertsListProps> = ({ alerts }) => {
  const getSeverityColor = (severity: Alert["severity"]) => {
    switch (severity) {
      case "high":
        return "bg-red-100 text-red-800";
      case "medium":
        return "bg-yellow-100 text-yellow-800";
      case "low":
        return "bg-green-100 text-green-800";
    }
  };

  const getAlertTypeIcon = (type: Alert["type"]) => {
    switch (type) {
      case "liquidation":
        return "⚠️";
      case "impermanentLoss":
        return "📉";
      case "marketVolatility":
        return "📊";
    }
  };

  const getAlertTypeText = (type: Alert["type"]) => {
    switch (type) {
      case "liquidation":
        return "清算风险";
      case "impermanentLoss":
        return "无常损失";
      case "marketVolatility":
        return "市场波动";
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">风险警报</h2>

      {alerts.length === 0 ? (
        <p className="text-gray-600">暂无警报</p>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <div key={alert.id} className={`p-4 rounded-lg ${getSeverityColor(alert.severity)}`}>
              <div className="flex items-start">
                <span className="text-2xl mr-3">{getAlertTypeIcon(alert.type)}</span>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold">{getAlertTypeText(alert.type)}</h3>
                    <span className="text-sm opacity-75">{new Date(alert.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="mt-1">{alert.message}</p>
                  <div className="mt-2 text-sm opacity-75">
                    {alert.protocol} - {alert.asset}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AlertsList;
