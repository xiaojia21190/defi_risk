"use client";

import React, { useState, useEffect } from "react";
import { apiService } from "../services/api";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const ApiTest: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<"loading" | "connected" | "error">("loading");
  const [testResults, setTestResults] = useState<{ endpoint: string; status: "success" | "error"; message: string }[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    checkApiHealth();
  }, []);

  const checkApiHealth = async () => {
    try {
      setApiStatus("loading");
      const isHealthy = await apiService.checkApiHealth();
      setApiStatus(isHealthy ? "connected" : "error");
    } catch (error) {
      console.error("API健康检查失败:", error);
      setApiStatus("error");
    }
  };

  const runApiTests = async () => {
    setIsRunning(true);
    setTestResults([]);

    // 测试健康检查
    await testEndpoint("健康检查", async () => {
      const isHealthy = await apiService.checkApiHealth();
      return { success: isHealthy, message: isHealthy ? "API服务正常" : "API服务不可用" };
    });

    // 测试协议列表
    await testEndpoint("协议列表", async () => {
      const data = await apiService.getProtocols();
      return {
        success: data.protocols && data.protocols.length > 0,
        message: `获取到${data.protocols.length}个协议`,
      };
    });

    // 测试Gas价格
    await testEndpoint("Gas价格", async () => {
      const price = await apiService.getGasPrice();
      return { success: price !== undefined, message: `当前Gas价格: ${price}` };
    });

    // 测试市场数据
    await testEndpoint("市场数据 (ETH)", async () => {
      const data = await apiService.getMarketData("ETH");
      return {
        success: !!data,
        message: `ETH价格: $${data.price}`,
      };
    });

    setIsRunning(false);
  };

  const testEndpoint = async (name: string, testFn: () => Promise<{ success: boolean; message: string }>) => {
    try {
      const result = await testFn();
      setTestResults((prev) => [
        ...prev,
        {
          endpoint: name,
          status: result.success ? "success" : "error",
          message: result.message,
        },
      ]);
    } catch (error) {
      setTestResults((prev) => [
        ...prev,
        {
          endpoint: name,
          status: "error",
          message: error instanceof Error ? error.message : "未知错误",
        },
      ]);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          API连接测试
          {apiStatus === "loading" && (
            <Badge variant="outline" className="flex items-center gap-1">
              <Loader2 className="w-3 h-3 animate-spin" />
              检查中
            </Badge>
          )}
          {apiStatus === "connected" && (
            <Badge variant="default" className="flex items-center gap-1 bg-green-500">
              <CheckCircle className="w-3 h-3" />
              已连接
            </Badge>
          )}
          {apiStatus === "error" && (
            <Badge variant="destructive" className="flex items-center gap-1">
              <XCircle className="w-3 h-3" />
              连接失败
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">测试前端与后端API的连接状态</p>
            <Button onClick={runApiTests} disabled={isRunning || apiStatus === "loading"} size="sm">
              {isRunning && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              运行测试
            </Button>
          </div>

          {testResults.length > 0 && (
            <div className="mt-4 space-y-2">
              <h3 className="text-sm font-medium">测试结果:</h3>
              <div className="space-y-2">
                {testResults.map((result, index) => (
                  <div key={index} className="flex items-center justify-between pb-2 text-sm border-b">
                    <div className="flex items-center gap-2">
                      {result.status === "success" ? <CheckCircle className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                      <span>{result.endpoint}</span>
                    </div>
                    <span className={result.status === "success" ? "text-green-500" : "text-red-500"}>{result.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ApiTest;
