import { createConfig, http } from 'wagmi'
import { mainnet } from 'viem/chains'
import { metaMask, walletConnect } from 'wagmi/connectors'

// 获取环境变量
const projectId = process.env.NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID || ''
const providerUrl = process.env.NEXT_PUBLIC_WEB3_PROVIDER_URL || ''

// wagmi config
export const config = createConfig({
  chains: [mainnet],
  transports: {
    [mainnet.id]: http(providerUrl)
  },
  connectors: [
    metaMask(),
    walletConnect({
      projectId,
    }),
  ],
})
