"use client";

import React, { useState, useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { apiService } from "../services/api";
import { Loader2, Fuel } from "lucide-react";

export const GasPrice = () => {
  // 状态管理
  const [gasPrice, setGasPrice] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<boolean>(false);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 获取gas价格
  const fetchGasPrice = async () => {
    try {
      setError(false);
      const price = await apiService.getGasPrice();
      setGasPrice(price);
    } catch (err) {
      console.error("获取Gas价格失败:", err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时获取数据
  useEffect(() => {
    fetchGasPrice();

    // 设置定时器每30秒刷新一次
    refreshTimerRef.current = setInterval(fetchGasPrice, 30000);

    // 组件卸载时清除定时器
    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, []);

  // 根据gas价格返回对应的颜色
  const getGasPriceColor = (price: number): "default" | "secondary" | "destructive" | "outline" => {
    if (price > 100) return "destructive"; // 高gas
    if (price > 50) return "outline"; // 中gas
    return "secondary"; // 低gas
  };

  // 渲染组件
  return (
    <Badge variant={loading || error || gasPrice === null ? "outline" : getGasPriceColor(gasPrice)} className="flex gap-1 items-center">
      {loading ? (
        <>
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>Gas: 加载中</span>
        </>
      ) : error ? (
        <>
          <Fuel className="w-3 h-3" />
          <span>Gas: 无数据</span>
        </>
      ) : (
        <>
          <Fuel className="w-3 h-3" />
          <span>Gas: {gasPrice} Gwei</span>
        </>
      )}
    </Badge>
  );
};

export default GasPrice;
