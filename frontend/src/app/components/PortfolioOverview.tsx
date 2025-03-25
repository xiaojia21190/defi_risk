"use client";

import React, { useState } from "react";
import { TrendingUp, Wallet, BarChart3, Percent, ChartBar, Target, DollarSign, ArrowUpDown, Loader2, Shield, Network, Coins, Info, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { apiService } from "../services/api";

// 增强SimplePieChart组件，添加悬停效果
const SimplePieChart: React.FC<{
  data: Array<{
    title: string;
    value: number;
    color: string;
  }>;
  total: number;
}> = ({ data, total }) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const totalValue = total || data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="relative w-full h-full">
      <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
        {data.map((item, index) => {
          const previousItems = data.slice(0, index);
          const startAngle = (previousItems.reduce((sum, prev) => sum + prev.value, 0) / totalValue) * 360;
          const angle = (item.value / totalValue) * 360;

          const x1 = 50 + 40 * Math.cos((startAngle * Math.PI) / 180);
          const y1 = 50 + 40 * Math.sin((startAngle * Math.PI) / 180);
          const x2 = 50 + 40 * Math.cos(((startAngle + angle) * Math.PI) / 180);
          const y2 = 50 + 40 * Math.sin(((startAngle + angle) * Math.PI) / 180);

          const largeArcFlag = angle > 180 ? 1 : 0;

          const pathData = [`M 50 50`, `L ${x1} ${y1}`, `A 40 40 0 ${largeArcFlag} 1 ${x2} ${y2}`, `L 50 50`].join(" ");

          return (
            <path
              key={item.title}
              d={pathData}
              fill={item.color}
              stroke="white"
              strokeWidth="0.5"
              className="transition-all duration-300 cursor-pointer"
              style={{
                transform: activeIndex === index ? "translate(2px, 2px)" : "none",
                filter: activeIndex === index ? "drop-shadow(0 0 5px rgba(0,0,0,0.3))" : "none",
                opacity: activeIndex !== null && activeIndex !== index ? 0.7 : 1,
              }}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
            />
          );
        })}
      </svg>
      <div className="flex absolute inset-0 flex-col justify-center items-center text-center">
        {activeIndex !== null ? (
          <div className="text-sm font-medium">
            {data[activeIndex].title}
            <br />
            {((data[activeIndex].value / totalValue) * 100).toFixed(1)}%
          </div>
        ) : (
          data.map((item) => {
            const percentage = (item.value / totalValue) * 100;
            if (percentage > 5) {
              return (
                <div key={item.title} className="text-xs font-medium text-white" style={{ textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}>
                  {item.title}
                  <br />
                  {percentage.toFixed(1)}%
                </div>
              );
            }
            return null;
          })
        )}
      </div>
    </div>
  );
};

interface PortfolioOverviewProps {
  portfolio: {
    wallet_address: string;
    total_value: number;
    total_value_usd: number;
    position_count: number;
    protocol_count: number;
    positions: Array<{
      protocol: string;
      total_assets: number;
      total_debts: number;
      leverage: number;
      positions: Array<{
        protocol: string;
        asset: string;
        amount: number;
        invest_type: number;
        apy: number | null;
        tokenList: Array<{
          tokenSymbol: string;
          tokenLogo: string;
          coinAmount: string;
          currencyAmount: string;
          tokenPrecision: number;
          tokenAddress: string;
          network: string;
        }>;
      }>;
    }>;
    protocols: Array<{
      name: string;
      chain: string;
      tvl: number;
      supported_assets: string[];
      features: string[];
      description: string;
    }>;
    timestamp: string;
    is_demo_data: boolean;
  } | null;
  loading?: boolean;
  error?: string | null;
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

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ portfolio, loading, error }) => {
  const [selectedProtocol, setSelectedProtocol] = useState<{
    name: string;
    chain: string;
    tvl: number;
    supported_assets: string[];
    features: string[];
    description: string;
  } | null>(null);
  const [protocolRisk, setProtocolRisk] = useState<ProtocolRiskAnalysis | null>(null);
  const [loadingRisk, setLoadingRisk] = useState(false);
  const [activeTab, setActiveTab] = useState<"info" | "risk">("info");

  // 计算平均APY
  const calculateAverageApy = (portfolio: any) => {
    if (!portfolio || !portfolio.positions) return 0;

    let totalApy = 0;
    let validPositionsCount = 0;

    portfolio.positions.forEach((protocolPos: any) => {
      protocolPos.positions.forEach((position: any) => {
        if (position.apy && !isNaN(position.apy)) {
          totalApy += position.apy;
          validPositionsCount++;
        }
      });
    });

    return validPositionsCount > 0 ? (totalApy / validPositionsCount).toFixed(2) : 0;
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>投资组合概览</CardTitle>
          <CardDescription>加载中...</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center items-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>投资组合概览</CardTitle>
          <CardDescription className="text-destructive">{error}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!portfolio) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>投资组合概览</CardTitle>
          <CardDescription>暂无数据</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // 生成协议分布饼图数据
  const protocolData = portfolio.positions.map((protocolPos, index) => ({
    title: protocolPos.protocol,
    value: protocolPos.total_assets,
    color: [
      "#2563eb", // blue-600
      "#16a34a", // green-600
      "#dc2626", // red-600
      "#9333ea", // purple-600
      "#ea580c", // orange-600
      "#0891b2", // cyan-600
      "#4f46e5", // indigo-600
      "#db2777", // pink-600
    ][index % 8],
  }));

  // 生成资产类型分布数据
  const assetTypeData = portfolio.positions.reduce((acc, protocolPos) => {
    protocolPos.positions.forEach((position) => {
      const type = getInvestTypeName(position.invest_type);
      acc[type] = (acc[type] || 0) + position.amount;
    });
    return acc;
  }, {} as { [key: string]: number });

  const assetTypeChartData = Object.entries(assetTypeData).map(([type, value], index) => ({
    title: type,
    value,
    color: [
      "#2563eb", // blue-600
      "#16a34a", // green-600
      "#dc2626", // red-600
      "#9333ea", // purple-600
      "#ea580c", // orange-600
      "#0891b2", // cyan-600
      "#4f46e5", // indigo-600
      "#db2777", // pink-600
    ][index % 8],
  }));

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("zh-CN", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const getInvestTypeName = (type: number) => {
    switch (type) {
      case 1:
        return "存币";
      case 2:
        return "流动性池";
      case 3:
        return "挖矿";
      case 4:
        return "机枪池";
      case 5:
        return "质押";
      case 6:
        return "借贷";
      default:
        return "其他";
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
  const openProtocolDetails = (protocol: any) => {
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

  // 渲染风险等级标签
  const renderRiskLevel = (level: string) => {
    let variant: "default" | "secondary" | "destructive" | "outline" = "default";
    if (level === "高") variant = "destructive";
    else if (level === "中等") variant = "secondary";

    return <Badge variant={variant}>{level}</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 mb-6 sm:grid-cols-4">
        <Card className="bg-gradient-to-br from-primary/20 to-primary/5">
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">总资产价值</p>
                <h3 className="mt-1 text-2xl font-bold">${formatCurrency(portfolio.total_value_usd)}</h3>
              </div>
              <div className="p-2 rounded-full bg-primary/10">
                <DollarSign className="w-5 h-5 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/20 to-blue-500/5">
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">协议数量</p>
                <h3 className="mt-1 text-2xl font-bold">{portfolio.protocol_count}</h3>
              </div>
              <div className="p-2 rounded-full bg-blue-500/10">
                <Network className="w-5 h-5 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-amber-500/20 to-amber-500/5">
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">头寸数量</p>
                <h3 className="mt-1 text-2xl font-bold">{portfolio.position_count}</h3>
              </div>
              <div className="p-2 rounded-full bg-amber-500/10">
                <Coins className="w-5 h-5 text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500/20 to-green-500/5">
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">平均APY</p>
                <h3 className="mt-1 text-2xl font-bold">{calculateAverageApy(portfolio)}%</h3>
              </div>
              <div className="p-2 rounded-full bg-green-500/10">
                <Percent className="w-5 h-5 text-green-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>投资组合概览</CardTitle>
          <CardDescription>总资产价值: {formatCurrency(portfolio.total_value_usd)}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div>
              <h3 className="mb-4 text-lg font-medium">协议分布</h3>
              <div className="w-full aspect-square max-w-[300px] mx-auto relative bg-slate-900 rounded-full">
                <SimplePieChart data={protocolData} total={portfolio.total_value_usd} />
              </div>
            </div>
            <div>
              <h3 className="mb-4 text-lg font-medium">资产类型分布</h3>
              <div className="w-full aspect-square max-w-[300px] mx-auto relative bg-slate-900 rounded-full">
                <SimplePieChart data={assetTypeChartData} total={portfolio.total_value_usd} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>持仓详情</CardTitle>
          <CardDescription>
            共 {portfolio.position_count} 个持仓，{portfolio.protocol_count} 个协议
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {portfolio.positions.map((protocolPos) => (
              <div key={protocolPos.protocol} className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="flex gap-2 items-center">
                    <h4 className="text-lg font-medium">{protocolPos.protocol}</h4>
                    <Badge variant="outline">杠杆率: {protocolPos.leverage}x</Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">总资产: {formatCurrency(protocolPos.total_assets)}</div>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>资产</TableHead>
                      <TableHead>数量</TableHead>
                      <TableHead>价值</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>APY</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {protocolPos.positions.map((position) => (
                      <TableRow key={`${position.protocol}-${position.asset}`}>
                        <TableCell>
                          <div className="flex gap-2 items-center">
                            {position.tokenList[0]?.tokenLogo && <img src={position.tokenList[0].tokenLogo} alt={position.asset} className="w-6 h-6 rounded-full" />}
                            <span>{position.asset}</span>
                          </div>
                        </TableCell>
                        <TableCell>{parseFloat(position.tokenList[0]?.coinAmount || "0").toFixed(4)}</TableCell>
                        <TableCell>{formatCurrency(parseFloat(position.tokenList[0]?.currencyAmount || "0"))}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">{getInvestTypeName(position.invest_type)}</Badge>
                        </TableCell>
                        <TableCell>{position.apy ? <Badge variant="default">{formatPercentage(position.apy)}</Badge> : <span className="text-muted-foreground">-</span>}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>协议信息</CardTitle>
          <CardDescription>支持的协议和功能</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {portfolio.protocols.map((protocol) => (
              <div key={protocol.name} className="p-4 rounded-lg border transition-colors cursor-pointer bg-card/50 hover:bg-card/80" onClick={() => openProtocolDetails(protocol)}>
                <div className="flex justify-between items-center mb-2">
                  <div className="flex gap-2 items-center">
                    <h4 className="font-medium">{protocol.name}</h4>
                    <Badge variant="outline">{protocol.chain}</Badge>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="w-8 h-8"
                    onClick={(e) => {
                      e.stopPropagation();
                      openProtocolDetails(protocol);
                    }}
                  >
                    <Info className="w-4 h-4" />
                  </Button>
                </div>
                <p className="mb-3 text-sm text-muted-foreground line-clamp-2">{protocol.description}</p>
                <div className="space-y-2">
                  <div className="flex gap-2 items-center text-sm">
                    <Coins className="w-4 h-4" />
                    <span>支持资产: {protocol.supported_assets.join(", ")}</span>
                  </div>
                  <div className="flex gap-2 items-center text-sm">
                    <BarChart3 className="w-4 h-4" />
                    <span>TVL: {formatCurrency(protocol.tvl)}</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {protocol.features.map((feature) => (
                      <Badge key={feature} variant="secondary" className="text-xs">
                        {feature}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 协议详情弹窗 */}
      <Dialog open={selectedProtocol !== null} onOpenChange={(open: boolean) => !open && closeProtocolDetails()}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          {selectedProtocol && (
            <>
              <DialogHeader>
                <DialogTitle className="flex justify-between items-center">
                  <span>{selectedProtocol.name}</span>
                  {selectedProtocol.chain && <Badge variant="secondary">{selectedProtocol.chain}</Badge>}
                </DialogTitle>
                <DialogDescription>{selectedProtocol.description || "暂无描述"}</DialogDescription>
              </DialogHeader>

              <Tabs defaultValue={activeTab} onValueChange={(value: string) => setActiveTab(value as "info" | "risk")} className="mt-4">
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
                        <p className="text-2xl font-bold">{formatCurrency(selectedProtocol.tvl)}</p>
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
                          <li key={index} className="flex gap-2 items-start">
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
                      <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                  ) : !protocolRisk ? (
                    <div className="py-8 text-center">
                      <AlertTriangle className="mx-auto mb-2 w-8 h-8 text-amber-500" />
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
                          <div className="flex gap-2 items-center">
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
                                <div className="flex justify-between items-center mb-1">
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
                              <li key={index} className="flex gap-2 items-start">
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
    </div>
  );
};

export default PortfolioOverview;
