"use client";

import React, { useState, useEffect } from "react";
import { apiService, HackathonGuide as GuideType } from "../services/api";

export const HackathonGuide: React.FC = () => {
  const [guide, setGuide] = useState<GuideType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<any>(null);
  const [testLoading, setTestLoading] = useState(false);

  useEffect(() => {
    const fetchGuide = async () => {
      try {
        setLoading(true);
        const data = await apiService.getHackathonGuide();
        setGuide(data);
        setError(null);
      } catch (error) {
        console.error("Error fetching hackathon guide:", error);
        setError("无法获取黑客松指南");
      } finally {
        setLoading(false);
      }
    };

    fetchGuide();
  }, []);

  const runQuickTest = async () => {
    try {
      setTestLoading(true);
      const result = await apiService.quickTest();
      setTestResult(result);
    } catch (error) {
      console.error("Error running quick test:", error);
      setTestResult({ status: "error", message: "测试失败" });
    } finally {
      setTestLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-[50vh] animate-fade-in">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute top-0 w-12 h-12 rounded-full border-4 border-primary/30 animate-ping"></div>
            <div className="absolute top-2 left-2 w-12 h-12 rounded-full border-4 border-t-primary border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
          </div>
          <p className="text-lg font-medium">加载中...</p>
          <p className="text-sm text-muted mt-2">正在获取黑客松指南</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-xl bg-error/10 border border-error/20 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-error/20 flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-error">
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </div>
        <p className="text-error font-medium mb-2">获取指南失败</p>
        <p className="text-sm text-muted">{error}</p>
      </div>
    );
  }

  if (!guide) {
    return null;
  }

  return (
    <div className="container mx-auto px-4 py-8 animate-fade-in">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent mb-4">{guide.title}</h1>
          <p className="text-muted">{guide.description}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="p-6 rounded-xl bg-card border border-border shadow-sm">
            <h2 className="text-lg font-medium mb-3">网络信息</h2>
            <div className="space-y-2">
              <div>
                <span className="text-sm text-muted block">网络名称</span>
                <span className="font-medium">{guide.network.name}</span>
              </div>
              <div>
                <span className="text-sm text-muted block">链ID</span>
                <span className="font-medium">{guide.network.chainId}</span>
              </div>
              <div>
                <span className="text-sm text-muted block">区块浏览器</span>
                <a href={guide.network.blockExplorer} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  {guide.network.blockExplorer.split("//")[1]}
                </a>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-xl bg-card border border-border shadow-sm">
            <h2 className="text-lg font-medium mb-3">演示账户</h2>
            <div className="space-y-2">
              {guide.demoAccounts.map((account, index) => (
                <div key={index}>
                  <span className="text-sm text-muted block">{account.description}</span>
                  <span className="font-mono text-sm bg-background px-2 py-1 rounded">{account.address}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-6 rounded-xl bg-card border border-border shadow-sm">
            <h2 className="text-lg font-medium mb-3">支持的资产</h2>
            <div className="flex flex-wrap gap-2">
              {guide.supportedAssets.map((asset, index) => (
                <span key={index} className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">
                  {asset}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">演示步骤</h2>
            <div className="flex items-center">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${guide.demoMode ? "bg-success/10 text-success" : "bg-warning/10 text-warning"}`}>{guide.demoMode ? "演示模式已启用" : "演示模式未启用"}</span>
            </div>
          </div>

          <div className="space-y-4">
            {guide.steps.map((step) => (
              <div key={step.step} className="p-6 rounded-xl bg-card border border-border shadow-sm">
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold flex-shrink-0">{step.step}</div>
                  <div className="flex-1">
                    <h3 className="text-lg font-medium mb-2">{step.title}</h3>
                    <p className="text-muted mb-3">{step.description}</p>

                    <div className="bg-background p-3 rounded-lg font-mono text-sm mb-3">{step.endpoint}</div>

                    {step.parameters && step.parameters.length > 0 && (
                      <div>
                        <span className="text-sm text-muted block mb-2">可用参数:</span>
                        <div className="flex flex-wrap gap-2">
                          {step.parameters.map((param, index) => (
                            <span key={index} className="px-2 py-1 rounded bg-background text-xs">
                              {param}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">快速测试</h2>
            <button onClick={runQuickTest} disabled={testLoading} className="px-4 py-2 rounded-full bg-primary text-white text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center">
              {testLoading ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-t-white border-r-transparent border-b-transparent border-l-transparent animate-spin mr-2"></div>
                  测试中...
                </>
              ) : (
                <>运行测试</>
              )}
            </button>
          </div>

          {testResult && (
            <div className={`p-6 rounded-xl border ${testResult.status === "healthy" ? "bg-success/10 border-success/20" : "bg-error/10 border-error/20"}`}>
              <div className="flex items-start gap-4">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${testResult.status === "healthy" ? "bg-success/20 text-success" : "bg-error/20 text-error"}`}>
                  {testResult.status === "healthy" ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M18 6 6 18" />
                      <path d="m6 6 12 12" />
                    </svg>
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-medium mb-2">测试结果</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <span className="text-sm text-muted block">Web3连接</span>
                      <span className={testResult.tests?.web3_connection ? "text-success" : "text-error"}>{testResult.tests?.web3_connection ? "成功" : "失败"}</span>
                    </div>
                    <div>
                      <span className="text-sm text-muted block">风险计算</span>
                      <span>{testResult.tests?.risk_calculation || "N/A"}</span>
                    </div>
                    <div>
                      <span className="text-sm text-muted block">市场分析</span>
                      <span>{testResult.tests?.market_analysis || "N/A"}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HackathonGuide;
