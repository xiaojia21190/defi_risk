"use client";

import React, { useState, useEffect } from "react";
import { apiService, Protocol } from "../services/api";
import { Loader2, ExternalLink, Search, Filter, ArrowUpDown, Shield, AlertTriangle, X, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "./ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./ui/tabs";

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

export const ProtocolList: React.FC<ProtocolListProps> = ({
  walletAddress,
  title = "支持的DeFi协议"
}) => {
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
  const allAssets = Array.from(
    new Set(
      protocols.flatMap((protocol) => protocol.supported_assets || [])
    )
  ).sort();

  useEffect(() => {
    fetchProtocols();
  }, [walletAddress]);

  const fetchProtocols = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log(walletAddress
        ? `正在获取钱包 ${walletAddress} 的协议列表...`
        : "正在获取协议列表...");
      const data = await apiService.getProtocols(walletAddress);
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
      const matchesSearch = protocol.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (protocol.description && protocol.description.toLowerCase().includes(searchTerm.toLowerCase()));

      // 资产过滤
      const matchesAsset = !filterAsset || (protocol.supported_assets && protocol.supported_assets.includes(filterAsset));

      return matchesSearch && matchesAsset;
    })
    .sort((a, b) => {
      if (sortBy === "name") {
        return sortOrder === "asc"
          ? a.name.localeCompare(b.name)
          : b.name.localeCompare(a.name);
      } else {
        // 按支持的资产数量排序
        const assetsA = a.supported_assets?.length || 0;
        const assetsB = b.supported_assets?.length || 0;
        return sortOrder === "asc" ? assetsA - assetsB : assetsB - assetsA;
      }
    });

  // 渲染风险等级标签
  const renderRiskLevel = (level: string) => {
    const color = level === "高" ? "bg-destructive" :
                 level === "中等" ? "bg-amber-500" : "bg-green-500";
    return (
      <Badge className={color}>
        {level}
      </Badge>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          {walletAddress ? "您当前使用的DeFi协议" : "系统支持的所有DeFi协议"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* 搜索和过滤 */}
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索协议..."
              className="pl-8"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <div className="relative">
              <Button
                className="flex items-center gap-1"
                onClick={() => toggleSort("name")}
              >
                名称
                <ArrowUpDown className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="relative">
              <Button
                className="flex items-center gap-1"
                onClick={() => toggleSort("assets")}
              >
                资产数
                <ArrowUpDown className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>

        {/* 资产过滤器 */}
        {allAssets.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            <Badge
              className={`cursor-pointer ${!filterAsset ? "bg-primary" : "bg-secondary"}`}
              onClick={() => setFilterAsset(null)}
            >
              全部
            </Badge>
            {allAssets.map((asset) => (
              <Badge
                key={asset}
                className={`cursor-pointer ${filterAsset === asset ? "bg-primary" : "bg-secondary"}`}
                onClick={() => setFilterAsset(asset === filterAsset ? null : asset)}
              >
                {asset}
              </Badge>
            ))}
          </div>
        )}

        {/* 协议列表 */}
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <AlertTriangle className="h-8 w-8 text-destructive mx-auto mb-2" />
            <p className="text-muted-foreground">{error}</p>
            <Button className="mt-4" onClick={fetchProtocols}>
              重试
            </Button>
          </div>
        ) : filteredAndSortedProtocols.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground">未找到符合条件的协议</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAndSortedProtocols.map((protocol) => (
              <Card
                key={protocol.name}
                className="overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => openProtocolDetails(protocol)}
              >
                <CardContent className="p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium">{protocol.name}</h3>
                      {protocol.chain && (
                        <Badge className="mt-1 bg-secondary text-xs">
                          {protocol.chain}
                        </Badge>
                      )}
                    </div>
                    <Button
                      size="icon"
                      className="h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        openProtocolDetails(protocol);
                      }}
                    >
                      <Info className="h-4 w-4" />
                    </Button>
                  </div>
                  {protocol.description && (
                    <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                      {protocol.description}
                    </p>
                  )}
                  {protocol.supported_assets && protocol.supported_assets.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs text-muted-foreground mb-1">支持资产:</p>
                      <div className="flex flex-wrap gap-1">
                        {protocol.supported_assets.slice(0, 5).map((asset) => (
                          <Badge key={asset} className="bg-secondary text-xs">
                            {asset}
                          </Badge>
                        ))}
                        {protocol.supported_assets.length > 5 && (
                          <Badge className="bg-secondary text-xs">
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
                    {selectedProtocol.chain && (
                      <Badge className="bg-secondary">
                        {selectedProtocol.chain}
                      </Badge>
                    )}
                  </DialogTitle>
                  <DialogDescription>
                    {selectedProtocol.description || "暂无描述"}
                  </DialogDescription>
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
                          <h4 className="text-sm font-medium mb-1">总锁仓价值</h4>
                          <p className="text-2xl font-bold">
                            ${selectedProtocol.tvl.toLocaleString()}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* 支持的资产 */}
                    {selectedProtocol.supported_assets && selectedProtocol.supported_assets.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-sm font-medium mb-2">支持的资产</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedProtocol.supported_assets.map((asset) => (
                            <Badge key={asset} className="bg-secondary">
                              {asset}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 功能特性 */}
                    {selectedProtocol.features && selectedProtocol.features.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-sm font-medium mb-2">功能特性</h4>
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
                      <div className="flex justify-center items-center py-12">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                      </div>
                    ) : !protocolRisk ? (
                      <div className="text-center py-8">
                        <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
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
                            <h4 className="text-sm font-medium mb-1">风险评分</h4>
                            <div className="flex items-center gap-2">
                              <p className="text-2xl font-bold">{protocolRisk.risk_score}</p>
                              <span className="text-sm text-muted-foreground">/100</span>
                            </div>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium mb-1">风险等级</h4>
                            <div>
                              {renderRiskLevel(protocolRisk.risk_level)}
                            </div>
                          </div>
                        </div>

                        {/* 风险因素 */}
                        {protocolRisk.risk_factors && protocolRisk.risk_factors.length > 0 && (
                          <div className="mt-4">
                            <h4 className="text-sm font-medium mb-2">风险因素</h4>
                            <div className="space-y-3">
                              {protocolRisk.risk_factors.map((factor, index) => (
                                <div key={index} className="bg-secondary/50 p-3 rounded-md">
                                  <div className="flex justify-between items-center mb-1">
                                    <h5 className="font-medium">{factor.factor}</h5>
                                    <Badge className={
                                      factor.score > 80 ? "bg-green-500" :
                                      factor.score > 60 ? "bg-amber-500" : "bg-destructive"
                                    }>
                                      {factor.score}/100
                                    </Badge>
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
                            <h4 className="text-sm font-medium mb-2">AI建议</h4>
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
                  <Button onClick={closeProtocolDetails}>
                    关闭
                  </Button>
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
