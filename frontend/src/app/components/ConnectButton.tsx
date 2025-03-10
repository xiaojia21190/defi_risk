"use client";

import { useAccount, useConnect, useDisconnect } from "wagmi";
import { useState, useEffect } from "react";
import { Wallet, LogOut, ChevronDown, Copy, ExternalLink, Check } from "lucide-react";

export function ConnectButton() {
  const { address, isConnected } = useAccount();
  const { connect, connectors, isPending } = useConnect();
  const { disconnect } = useDisconnect();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [demoMode, setDemoMode] = useState(false);

  // 检查是否处于演示模式
  useEffect(() => {
    const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
    setDemoMode(isDemoMode);
  }, []);

  // 复制地址到剪贴板
  const copyAddress = () => {
    if (address) {
      navigator.clipboard.writeText(address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // 在外部浏览器查看地址
  const viewOnExplorer = () => {
    if (address) {
      window.open(`https://sepolia.etherscan.io/address/${address}`, "_blank");
    }
  };

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isDropdownOpen) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isDropdownOpen]);

  if (isConnected && address) {
    return (
      <div className="relative">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsDropdownOpen(!isDropdownOpen);
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-full bg-card border border-border shadow-sm hover:shadow-md transition-all group"
        >
          <span className="w-2 h-2 rounded-full bg-success animate-pulse"></span>
          <span className="font-medium group-hover:text-primary transition-colors">{`${address.slice(0, 6)}...${address.slice(-4)}`}</span>
          <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${isDropdownOpen ? "rotate-180" : ""}`} />
        </button>

        {isDropdownOpen && (
          <div className="absolute right-0 mt-2 w-64 py-2 bg-card rounded-lg shadow-lg border border-border z-10 animate-in fade-in slide-in-from-top-5 duration-200" onClick={(e) => e.stopPropagation()}>
            <div className="px-4 py-3 border-b border-border">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted">已连接钱包</p>
                <div className="w-2 h-2 rounded-full bg-success"></div>
              </div>
              <p className="font-medium truncate mt-1">{address}</p>
            </div>

            <div className="px-4 py-2 space-y-1">
              <button onClick={copyAddress} className="w-full text-left px-3 py-2 text-sm rounded-md flex items-center gap-2 hover:bg-background/80 transition-colors">
                {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                {copied ? "已复制" : "复制地址"}
              </button>

              <button onClick={viewOnExplorer} className="w-full text-left px-3 py-2 text-sm rounded-md flex items-center gap-2 hover:bg-background/80 transition-colors">
                <ExternalLink className="h-4 w-4" />
                在区块浏览器中查看
              </button>
            </div>

            <div className="border-t border-border mt-2 pt-2 px-4">
              <button
                onClick={() => {
                  disconnect();
                  setIsDropdownOpen(false);
                }}
                className="w-full text-left px-3 py-2 text-sm rounded-md flex items-center gap-2 text-destructive hover:bg-destructive/10 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                断开连接
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      {demoMode && (
        <button className="px-4 py-2 rounded-full bg-amber-500/10 text-amber-500 font-medium hover:bg-amber-500/20 transition-colors shadow-sm hover:shadow-md flex items-center gap-2">
          <Wallet className="h-4 w-4" />
          演示模式
        </button>
      )}

      {connectors.map((connector) => (
        <button key={connector.uid} onClick={() => connect({ connector })} disabled={isPending} className="px-4 py-2 rounded-full bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors shadow-sm hover:shadow-md flex items-center gap-2 relative overflow-hidden group">
          <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-primary/0 via-primary-foreground/20 to-primary/0 -translate-x-full group-hover:animate-shimmer"></span>
          <Wallet className="h-4 w-4" />
          {isPending ? "连接中..." : `连接${connector.name}`}
        </button>
      ))}
    </div>
  );
}
