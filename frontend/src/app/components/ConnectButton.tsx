"use client";

import { useAccount, useConnect, useDisconnect } from "wagmi";

export function ConnectButton() {
  const { address, isConnected } = useAccount();
  const { connect, connectors } = useConnect();
  const { disconnect } = useDisconnect();

  if (isConnected) {
    return (
      <button onClick={() => disconnect()} className="px-4 py-2 text-white bg-blue-600 rounded-lg transition-colors hover:bg-blue-700">
        {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : "已连接"}
      </button>
    );
  }

  return (
    <div className="flex gap-2">
      {connectors.map((connector) => (
        <button key={connector.uid} onClick={() => connect({ connector })} className="px-4 py-2 text-white bg-blue-600 rounded-lg transition-colors hover:bg-blue-700">
          连接 {connector.name}
        </button>
      ))}
    </div>
  );
}
