import { createConfig, http } from 'wagmi'
import { sepolia } from 'viem/chains'
import { injected, metaMask, walletConnect } from 'wagmi/connectors'

// 获取环境变量
const projectId = process.env.NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID || ''

// wagmi config
export const config = createConfig({
  chains: [sepolia],
  transports: {
    [sepolia.id]: http()
  },
  connectors: [
    injected(),
    metaMask(),
    walletConnect({ projectId })
  ]
})
