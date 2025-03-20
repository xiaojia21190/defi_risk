"use client";

import React, { useState, useEffect } from "react";
import { apiService, Protocol } from "../services/api";
import { Loader2, ExternalLink, Search, Filter, ArrowUpDown, Shield, AlertTriangle, X, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAccount } from "wagmi";
import { cn } from "@/lib/utils";

interface ProtocolListProps {
  walletAddress?: string;
  title?: string;
}

interface ProtocolRiskAnalysis {
  protocol: string;
  risk_score: number;
  risk_level: string;
  risk_factors: Array<{
    factor: string;
    score: number;
    description: string;
  }>;
  recommendations: string[];
}

export const ProtocolList: React.FC<ProtocolListProps> = ({ title = "支持的DeFi协议" }) => {
  const { address, isConnected } = useAccount();
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"name" | "assets">("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [filterAsset, setFilterAsset] = useState<string | null>(null);
  const [selectedProtocol, setSelectedProtocol] = useState<Protocol | null>(null);
  const [protocolRisk, setProtocolRisk] = useState<ProtocolRiskAnalysis | null>(null);
  const [loadingRisk, setLoadingRisk] = useState(false);
  const [activeTab, setActiveTab] = useState<"info" | "risk">("info");

  // 获取所有支持的资产
  const allAssets = Array.from(new Set(protocols.flatMap((protocol) => protocol.supported_assets || []))).sort();

  useEffect(() => {
    fetchProtocols();
  }, [address]);

  const fetchProtocols = async () => {
    try {
      debugger;
      setLoading(true);
      setError(null);
      console.log(address ? `正在获取钱包 ${address} 的协议列表...` : "正在获取协议列表...");
      const data = await apiService.getProtocols(address);
      console.log("获取到协议列表:", data.protocols);
      setProtocols(data.protocols);
    } catch (error) {
      console.error("获取协议列表失败:", error);
      setError("无法加载协议列表");
    } finally {
      setLoading(false);
    }
  };

  // 获取协议风险分析
  const fetchProtocolRisk = async (protocolName: string) => {
    try {
      setLoadingRisk(true);
      const riskData = await apiService.analyzeProtocolRisk(protocolName);
      setProtocolRisk(riskData);
    } catch (error) {
      console.error(`获取协议 ${protocolName} 风险分析失败:`, error);
      setProtocolRisk(null);
    } finally {
      setLoadingRisk(false);
    }
  };

  // 打开协议详情
  const openProtocolDetails = (protocol: Protocol) => {
    setSelectedProtocol(protocol);
    setActiveTab("info");
    // 获取风险分析
    fetchProtocolRisk(protocol.name);
  };

  // 关闭协议详情
  const closeProtocolDetails = () => {
    setSelectedProtocol(null);
    setProtocolRisk(null);
  };

  const toggleSort = (field: "name" | "assets") => {
    if (sortBy === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("asc");
    }
  };

  // 过滤和排序协议
  const filteredAndSortedProtocols = protocols
    .filter((protocol) => {
      // 搜索过滤
      const matchesSearch = protocol.name.toLowerCase().includes(searchTerm.toLowerCase()) || (protocol.description && protocol.description.toLowerCase().includes(searchTerm.toLowerCase()));

      // 资产过滤
      const matchesAsset = !filterAsset || (protocol.supported_assets && protocol.supported_assets.includes(filterAsset));

      return matchesSearch && matchesAsset;
    })
    .sort((a, b) => {
      if (sortBy === "name") {
        return sortOrder === "asc" ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
      } else {
        // 按支持的资产数量排序
        const assetsA = a.supported_assets?.length || 0;
        const assetsB = b.supported_assets?.length || 0;
        return sortOrder === "asc" ? assetsA - assetsB : assetsB - assetsA;
      }
    });

  // 渲染风险等级标签
  const renderRiskLevel = (level: string) => {
    let variant: "default" | "secondary" | "destructive" | "outline" = "default";
    if (level === "高") variant = "destructive";
    else if (level === "中等") variant = "secondary";

    return <Badge variant={variant}>{level}</Badge>;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{address ? "您当前使用的DeFi协议" : "系统支持的所有DeFi协议"}</CardDescription>
      </CardHeader>
      <CardContent>
        {/* 搜索和过滤 */}
        <div className="flex flex-col gap-3 mb-4 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input placeholder="搜索协议..." className="pl-8" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <div className="relative">
              <Button className="flex items-center gap-1" onClick={() => toggleSort("name")}>
                名称
                <ArrowUpDown className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="relative">
              <Button className="flex items-center gap-1" onClick={() => toggleSort("assets")}>
                资产数
                <ArrowUpDown className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>

        {/* 资产过滤器 */}
        {allAssets.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            <Badge variant={!filterAsset ? "default" : "secondary"} className="cursor-pointer" onClick={() => setFilterAsset(null)}>
              全部
            </Badge>
            {allAssets.map((asset) => (
              <Badge key={asset} variant={filterAsset === asset ? "default" : "secondary"} className="cursor-pointer" onClick={() => setFilterAsset(asset === filterAsset ? null : asset)}>
                {asset}
              </Badge>
            ))}
          </div>
        )}

        {/* 协议列表 */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="py-8 text-center">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-destructive" />
            <p className="text-muted-foreground">{error}</p>
            <Button className="mt-4" onClick={fetchProtocols}>
              重试
            </Button>
          </div>
        ) : filteredAndSortedProtocols.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-muted-foreground">未找到符合条件的协议</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredAndSortedProtocols.map((protocol) => (
              <Card key={protocol.name} className="overflow-hidden transition-shadow cursor-pointer hover:shadow-md" onClick={() => openProtocolDetails(protocol)}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-medium">{protocol.name}</h3>
                      {protocol.chain && (
                        <Badge variant="secondary" className="mt-1 text-xs">
                          {protocol.chain}
                        </Badge>
                      )}
                    </div>
                    <Button
                      size="icon"
                      className="w-8 h-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        openProtocolDetails(protocol);
                      }}
                    >
                      <Info className="w-4 h-4" />
                    </Button>
                  </div>
                  {protocol.description && <p className="mt-2 text-sm text-muted-foreground line-clamp-2">{protocol.description}</p>}
                  {protocol.supported_assets && protocol.supported_assets.length > 0 && (
                    <div className="mt-3">
                      <p className="mb-1 text-xs text-muted-foreground">支持资产:</p>
                      <div className="flex flex-wrap gap-1">
                        {protocol.supported_assets.slice(0, 5).map((asset) => (
                          <Badge key={asset} variant="secondary" className="text-xs">
                            {asset}
                          </Badge>
                        ))}
                        {protocol.supported_assets.length > 5 && (
                          <Badge variant="secondary" className="text-xs">
                            +{protocol.supported_assets.length - 5}
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* 协议详情弹窗 */}
        <Dialog open={selectedProtocol !== null} onOpenChange={(open) => !open && closeProtocolDetails()}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            {selectedProtocol && (
              <>
                <DialogHeader>
                  <DialogTitle className="flex items-center justify-between">
                    <span>{selectedProtocol.name}</span>
                    {selectedProtocol.chain && <Badge variant="secondary">{selectedProtocol.chain}</Badge>}
                  </DialogTitle>
                  <DialogDescription>{selectedProtocol.description || "暂无描述"}</DialogDescription>
                </DialogHeader>

                <Tabs defaultValue={activeTab} onValueChange={(value) => setActiveTab(value as any)} className="mt-4">
                  <TabsList className="grid grid-cols-2 mb-4">
                    <TabsTrigger value="info">协议信息</TabsTrigger>
                    <TabsTrigger value="risk">风险分析</TabsTrigger>
                  </TabsList>

                  <TabsContent value="info" className="space-y-4">
                    {/* 协议基本信息 */}
                    <div className="grid grid-cols-2 gap-4">
                      {selectedProtocol.tvl !== undefined && (
                        <div>
                          <h4 className="mb-1 text-sm font-medium">总锁仓价值</h4>
                          <p className="text-2xl font-bold">${selectedProtocol.tvl.toLocaleString()}</p>
                        </div>
                      )}
                    </div>

                    {/* 支持的资产 */}
                    {selectedProtocol.supported_assets && selectedProtocol.supported_assets.length > 0 && (
                      <div className="mt-4">
                        <h4 className="mb-2 text-sm font-medium">支持的资产</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedProtocol.supported_assets.map((asset) => (
                            <Badge key={asset} variant="secondary">
                              {asset}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 功能特性 */}
                    {selectedProtocol.features && selectedProtocol.features.length > 0 && (
                      <div className="mt-4">
                        <h4 className="mb-2 text-sm font-medium">功能特性</h4>
                        <ul className="space-y-1 text-sm">
                          {selectedProtocol.features.map((feature, index) => (
                            <li key={index} className="flex items-start gap-2">
                              <span className="text-primary">•</span>
                              <span>{feature}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="risk" className="space-y-4">
                    {loadingRisk ? (
                      <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 animate-spin text-primary" />
                      </div>
                    ) : !protocolRisk ? (
                      <div className="py-8 text-center">
                        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
                        <p className="text-muted-foreground">无法获取风险分析数据</p>
                        <Button className="mt-4" onClick={() => fetchProtocolRisk(selectedProtocol.name)}>
                          重试
                        </Button>
                      </div>
                    ) : (
                      <>
                        {/* 风险评分 */}
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <h4 className="mb-1 text-sm font-medium">风险评分</h4>
                            <div className="flex items-center gap-2">
                              <p className="text-2xl font-bold">{protocolRisk.risk_score}</p>
                              <span className="text-sm text-muted-foreground">/100</span>
                            </div>
                          </div>
                          <div>
                            <h4 className="mb-1 text-sm font-medium">风险等级</h4>
                            <div>{renderRiskLevel(protocolRisk.risk_level)}</div>
                          </div>
                        </div>

                        {/* 风险因素 */}
                        {protocolRisk.risk_factors && protocolRisk.risk_factors.length > 0 && (
                          <div className="mt-4">
                            <h4 className="mb-2 text-sm font-medium">风险因素</h4>
                            <div className="space-y-3">
                              {protocolRisk.risk_factors.map((factor, index) => (
                                <div key={index} className="p-3 rounded-md bg-secondary/50">
                                  <div className="flex items-center justify-between mb-1">
                                    <h5 className="font-medium">{factor.factor}</h5>
                                    <Badge variant={factor.score > 80 ? "default" : factor.score > 60 ? "secondary" : "destructive"}>{factor.score}/100</Badge>
                                  </div>
                                  <p className="text-sm text-muted-foreground">{factor.description}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* AI建议 */}
                        {protocolRisk.recommendations && protocolRisk.recommendations.length > 0 && (
                          <div className="mt-4">
                            <h4 className="mb-2 text-sm font-medium">AI建议</h4>
                            <ul className="space-y-1 text-sm">
                              {protocolRisk.recommendations.map((rec, index) => (
                                <li key={index} className="flex items-start gap-2">
                                  <span className="text-primary">•</span>
                                  <span>{rec}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    )}
                  </TabsContent>
                </Tabs>

                <DialogFooter className="mt-6">
                  <Button onClick={closeProtocolDetails}>关闭</Button>
                </DialogFooter>
              </>
            )}
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};

export default ProtocolList;
