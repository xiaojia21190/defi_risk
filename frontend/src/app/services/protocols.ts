import { Protocol } from './api';

// 演示协议数据
export const demoProtocols: Protocol[] = [
  {
    name: "Aave V3",
    description: "去中心化借贷协议",
    supported_assets: ["ETH", "USDC", "DAI", "WBTC"],
    features: ["存款", "借贷", "抵押"],
  },
  {
    name: "Compound V3",
    description: "去中心化借贷协议",
    supported_assets: ["ETH", "USDC", "DAI"],
    features: ["存款", "借贷"],
  },
  {
    name: "Curve",
    description: "稳定币交易协议",
    supported_assets: ["USDC", "DAI", "USDT"],
    features: ["流动性挖矿", "稳定币交换"],
  },
  {
    name: "Uniswap V3",
    description: "去中心化交易所",
    supported_assets: ["ETH", "USDC", "WBTC", "DAI"],
    features: ["流动性提供", "交易"],
  },
  {
    name: "MakerDAO",
    description: "去中心化稳定币协议",
    supported_assets: ["ETH", "WBTC"],
    features: ["抵押", "稳定币铸造"],
  },
  {
    name: "Balancer",
    description: "多资产流动性池",
    supported_assets: ["ETH", "USDC", "DAI", "WBTC"],
    features: ["流动性挖矿", "交易"],
  },
  {
    name: "Yearn Finance",
    description: "收益聚合器",
    supported_assets: ["ETH", "USDC", "DAI", "WBTC"],
    features: ["收益优化", "自动复投"],
  },
  {
    name: "dYdX",
    description: "去中心化衍生品交易所",
    supported_assets: ["ETH", "USDC"],
    features: ["杠杆交易", "永续合约"],
  },
  {
    name: "Synthetix",
    description: "合成资产协议",
    supported_assets: ["ETH", "SNX"],
    features: ["合成资产", "抵押"],
  },
];
