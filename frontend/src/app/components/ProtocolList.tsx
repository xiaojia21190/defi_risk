"use client";

import React, { useState, useEffect } from "react";
import { apiService, Protocol } from "../services/api";
import { Loader2, ExternalLink, Search, Filter, ArrowUpDown } from "lucide-react";

export const ProtocolList: React.FC = () => {
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"name" | "assets">("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [filterAsset, setFilterAsset] = useState<string | null>(null);

  // 获取所有支持的资产
  const allAssets = Array.from(
    new Set(
      protocols.flatMap((protocol) => protocol.supported_assets)
    )
  ).sort();

  useEffect(() => {
    fetchProtocols();
  }, []);

  const fetchProtocols = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getProtocols();
      setProtocols(data.protocols);
    } catch (error) {
      console.error("获取协议列表失败:", error);
      setError("无法加载协议列表");
    } finally {
      setLoading(false);
    }
  };

  // 排序和过滤协议
  const filteredAndSortedProtocols = protocols
    .filter((protocol) => {
      // 搜索过滤
      const matchesSearch =
        searchTerm === "" ||
        protocol.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        protocol.description.toLowerCase().includes(searchTerm.toLowerCase());

      // 资产过滤
      const matchesAsset =
        !filterAsset ||
        protocol.supported_assets.includes(filterAsset);

      return matchesSearch && matchesAsset;
    })
    .sort((a, b) => {
      // 排序
      if (sortBy === "name") {
        return sortOrder === "asc"
          ? a.name.localeCompare(b.name)
          : b.name.localeCompare(a.name);
      } else {
        return sortOrder === "asc"
          ? a.supported_assets.length - b.supported_assets.length
          : b.supported_assets.length - a.supported_assets.length;
      }
    });

  // 切换排序顺序
  const toggleSort = (field: "name" | "assets") => {
    if (sortBy === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("asc");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-destructive/10 text-destructive p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
          <span className="text-2xl">!</span>
        </div>
        <h3 className="text-lg font-medium mb-2">出错了</h3>
        <p className="text-muted">{error}</p>
        <button onClick={fetchProtocols} className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
      <h2 className="text-2xl font-bold mb-6">支持的DeFi协议</h2>

      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted" />
          <input
            type="text"
            placeholder="搜索协议..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
          />
        </div>

        <div className="flex gap-2">
          <div className="relative">
            <button
              onClick={() => setFilterAsset(null)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 ${!filterAsset ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'} transition-colors`}
            >
              <Filter className="h-4 w-4" />
              全部资产
            </button>
          </div>

          <select
            value={filterAsset || ""}
            onChange={(e) => setFilterAsset(e.target.value || null)}
            className="px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
          >
            <option value="">按资产筛选</option>
            {allAssets.map((asset) => (
              <option key={asset} value={asset}>
                {asset}
              </option>
            ))}
          </select>
        </div>
      </div>

      {filteredAndSortedProtocols.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-muted">没有找到匹配的协议</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAndSortedProtocols.map((protocol) => (
            <div key={protocol.name} className="border border-border rounded-lg overflow-hidden hover:shadow-md transition-all group">
              <div className="p-5">
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-lg font-bold group-hover:text-primary transition-colors">{protocol.name}</h3>
                  <div className="bg-primary/10 text-primary px-2 py-1 rounded-full text-xs">
                    {protocol.supported_assets.length} 资产
                  </div>
                </div>
                <p className="text-muted text-sm mb-4">{protocol.description}</p>

                <div className="mb-4">
                  <h4 className="text-sm font-medium mb-2">支持资产</h4>
                  <div className="flex flex-wrap gap-2">
                    {protocol.supported_assets.map((asset) => (
                      <span
                        key={asset}
                        className="px-2 py-1 bg-muted rounded-full text-xs hover:bg-muted/80 transition-colors cursor-pointer"
                        onClick={() => setFilterAsset(asset)}
                      >
                        {asset}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">功能</h4>
                  <div className="flex flex-wrap gap-2">
                    {protocol.features.map((feature) => (
                      <span key={feature} className="px-2 py-1 bg-background rounded-full text-xs">
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="border-t border-border p-3 bg-muted/20 flex justify-between items-center">
                <span className="text-xs text-muted">风险评级: 中等</span>
                <a
                  href="#"
                  className="text-xs text-primary flex items-center gap-1 hover:underline"
                  onClick={(e) => e.preventDefault()}
                >
                  查看详情
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between items-center mt-6 text-sm text-muted">
        <div>
          显示 {filteredAndSortedProtocols.length} 个协议 (共 {protocols.length} 个)
        </div>

        <div className="flex gap-4">
          <button
            onClick={() => toggleSort("name")}
            className="flex items-center gap-1 hover:text-primary transition-colors"
          >
            按名称排序
            <ArrowUpDown className={`h-3 w-3 ${sortBy === "name" ? "text-primary" : ""}`} />
          </button>

          <button
            onClick={() => toggleSort("assets")}
            className="flex items-center gap-1 hover:text-primary transition-colors"
          >
            按资产数量排序
            <ArrowUpDown className={`h-3 w-3 ${sortBy === "assets" ? "text-primary" : ""}`} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProtocolList;
