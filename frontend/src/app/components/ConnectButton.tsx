"use client";

import { useAccount, useConnect, useDisconnect } from "wagmi";
import { useState, useEffect } from "react";
import { LogOut, ChevronDown, Copy, ExternalLink, Check, Wallet, Coins, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { MetaMaskIcon, WalletConnectIcon } from "./WalletIcons";

// 定义组件属性类型
interface ConnectButtonProps {
  size?: "default" | "sm" | "lg"; // 按钮尺寸
  variant?: "default" | "outline" | "custom"; // 按钮变体
  className?: string; // 自定义类名
}

export function ConnectButton({ size = "default", variant = "outline", className }: ConnectButtonProps) {
  const { address, isConnected } = useAccount();
  const { connect, connectors, isPending } = useConnect();
  const { disconnect } = useDisconnect();
  const [copied, setCopied] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

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
      window.open(`https://etherscan.io/address/${address}`, "_blank");
    }
  };

  // 处理钱包连接
  const handleConnect = (connector: any) => {
    connect({ connector });
    setDialogOpen(false);
  };

  // 获取钱包图标
  const getWalletIcon = (name: string) => {
    switch (name) {
      case "MetaMask":
        return <MetaMaskIcon className="text-orange-500" />;
      case "WalletConnect":
        return <WalletConnectIcon className="text-blue-500" />;
      default:
        return <Coins className="w-5 h-5 text-primary" />;
    }
  };

  // 获取钱包背景色
  const getWalletBgColor = (name: string) => {
    switch (name) {
      case "MetaMask":
        return "bg-orange-500/10";
      case "WalletConnect":
        return "bg-blue-500/10";
      default:
        return "bg-primary/10";
    }
  };

  // 生成连接按钮样式
  const getConnectButtonStyles = () => {
    if (variant === "custom") {
      return "relative overflow-hidden font-medium text-white transition-all duration-300 shadow-lg group bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 hover:shadow-blue-500/30";
    }
    return variant === "outline" ? "relative overflow-hidden group" : "";
  };

  // 已连接状态
  if (isConnected && address) {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size={size} className={cn("gap-2", className)}>
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

  // 未连接状态
  return (
    <div className="flex gap-2">
      {demoMode && (
        <Button variant="outline" size={size} className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20">
          <Wallet className="w-4 h-4 mr-2" />
          演示模式
        </Button>
      )}

      <Button variant={variant === "custom" ? "default" : variant} size={size} className={cn(getConnectButtonStyles(), className)} onClick={() => setDialogOpen(true)}>
        {variant === "custom" && <span className="absolute inset-0 w-full h-full transition-all duration-300 opacity-0 bg-gradient-to-r from-blue-300/20 via-white/20 to-blue-300/20 group-hover:opacity-100 group-hover:animate-shimmer"></span>}
        <span className={cn("relative flex items-center", variant === "outline" && "z-10")}>
          {variant === "custom" ? <Shield className="w-5 h-5 mr-2 transition-transform duration-300 group-hover:scale-110" /> : <Wallet className="w-4 h-4 mr-2" />}
          连接钱包
        </span>
        {variant === "outline" && <span className={cn("absolute inset-0 w-full h-full bg-gradient-to-r from-primary/0 via-primary-foreground/20 to-primary/0 -translate-x-full", "group-hover:animate-shimmer")} />}
      </Button>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>选择钱包</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {connectors.map((connector) => (
              <Button key={connector.uid} onClick={() => handleConnect(connector)} disabled={isPending} className="flex items-center justify-start gap-3 h-auto py-3 px-4 transition-all duration-200 hover:scale-[1.02]" variant="outline">
                <div className={cn("flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full", getWalletBgColor(connector.name))}>{getWalletIcon(connector.name)}</div>
                <div className="flex flex-col items-start">
                  <span className="font-medium">{connector.name}</span>
                  <span className="text-xs text-muted-foreground">{connector.name === "MetaMask" ? "最受欢迎的以太坊钱包" : connector.name === "WalletConnect" ? "支持多种钱包的连接方式" : "连接您的钱包"}</span>
                </div>
              </Button>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
