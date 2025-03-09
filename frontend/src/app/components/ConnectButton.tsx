"use client";

import { useAccount, useConnect, useDisconnect } from "wagmi";
import { useState } from "react";

export function ConnectButton() {
  const { address, isConnected } = useAccount();
  const { connect, connectors } = useConnect();
  const { disconnect } = useDisconnect();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  if (isConnected && address) {
    return (
      <div className="relative">
        <button onClick={() => setIsDropdownOpen(!isDropdownOpen)} className="flex items-center gap-2 px-4 py-2 rounded-full bg-card border border-border shadow-sm hover:shadow-md transition-all">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
          <span className="font-medium">{`${address.slice(0, 6)}...${address.slice(-4)}`}</span>
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${isDropdownOpen ? "rotate-180" : ""}`}>
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>

        {isDropdownOpen && (
          <div className="absolute right-0 mt-2 w-48 py-2 bg-card rounded-lg shadow-lg border border-border z-10 animate-fade-in">
            <div className="px-4 py-2 border-b border-border">
              <p className="text-xs text-muted">已连接钱包</p>
              <p className="font-medium truncate">{address}</p>
            </div>
            <button
              onClick={() => {
                disconnect();
                setIsDropdownOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-error hover:bg-background/50 transition-colors"
            >
              断开连接
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      {connectors.map((connector) => (
        <button key={connector.uid} onClick={() => connect({ connector })} className="px-4 py-2 rounded-full bg-primary text-white font-medium hover:bg-primary-hover transition-colors shadow-sm hover:shadow-md">
          <span className="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
              <path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
              <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
            </svg>
            连接{connector.name}
          </span>
        </button>
      ))}
    </div>
  );
}
