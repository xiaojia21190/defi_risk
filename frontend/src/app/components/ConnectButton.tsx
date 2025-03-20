"use client";

import { useAccount, useConnect, useDisconnect } from "wagmi";
import { useState, useEffect } from "react";
import { Wallet, LogOut, ChevronDown, Copy, ExternalLink, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function ConnectButton() {
  const { address, isConnected } = useAccount();
  const { connect, connectors, isPending } = useConnect();
  const { disconnect } = useDisconnect();
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

  if (isConnected && address) {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="font-medium">{`${address.slice(0, 6)}...${address.slice(-4)}`}</span>
            <ChevronDown className="w-4 h-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-64">
          <DropdownMenuLabel className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">已连接钱包</span>
            <div className="w-2 h-2 bg-green-500 rounded-full" />
          </DropdownMenuLabel>
          <p className="text-sm font-medium truncate">{address}</p>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={copyAddress}>
            {copied ? <Check className="w-4 h-4 mr-2 text-green-500" /> : <Copy className="w-4 h-4 mr-2" />}
            {copied ? "已复制" : "复制地址"}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={viewOnExplorer}>
            <ExternalLink className="w-4 h-4 mr-2" />
            在区块浏览器中查看
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => disconnect()} className="text-destructive focus:text-destructive">
            <LogOut className="w-4 h-4 mr-2" />
            断开连接
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  return (
    <div className="flex gap-2">
      {demoMode && (
        <Button variant="outline" className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20">
          <Wallet className="w-4 h-4 mr-2" />
          演示模式
        </Button>
      )}

      {connectors.map((connector) => (
        <Button key={connector.uid} onClick={() => connect({ connector })} disabled={isPending} className="relative overflow-hidden group">
          <span className={cn("absolute inset-0 w-full h-full bg-gradient-to-r from-primary/0 via-primary-foreground/20 to-primary/0 -translate-x-full", "group-hover:animate-shimmer")} />
          <Wallet className="w-4 h-4 mr-2" />
          {isPending ? "连接中..." : `连接${connector.name}`}
        </Button>
      ))}
    </div>
  );
}
