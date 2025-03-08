import { useReadContract, useWriteContract } from 'wagmi';

const RISK_MONITOR_ADDRESS = process.env.NEXT_PUBLIC_RISK_MONITOR_ADDRESS || '';

const RISK_MONITOR_ABI = [
  {
    "inputs": [
      { "internalType": "address", "name": "protocol", "type": "address" },
      { "internalType": "address", "name": "asset", "type": "address" },
      { "internalType": "uint256", "name": "amount", "type": "uint256" },
      { "internalType": "uint256", "name": "leverage", "type": "uint256" },
      { "internalType": "uint256", "name": "liquidationThreshold", "type": "uint256" }
    ],
    "name": "addPosition",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [{ "internalType": "address", "name": "user", "type": "address" }],
    "name": "getUserPositions",
    "outputs": [
      {
        "components": [
          { "internalType": "address", "name": "protocol", "type": "address" },
          { "internalType": "address", "name": "asset", "type": "address" },
          { "internalType": "uint256", "name": "amount", "type": "uint256" },
          { "internalType": "uint256", "name": "leverage", "type": "uint256" },
          { "internalType": "uint256", "name": "liquidationThreshold", "type": "uint256" }
        ],
        "internalType": "struct RiskMonitor.Position[]",
        "name": "",
        "type": "tuple[]"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{ "internalType": "address", "name": "user", "type": "address" }],
    "name": "getUserAlerts",
    "outputs": [
      {
        "components": [
          { "internalType": "address", "name": "user", "type": "address" },
          { "internalType": "address", "name": "protocol", "type": "address" },
          { "internalType": "address", "name": "asset", "type": "address" },
          { "internalType": "uint256", "name": "riskLevel", "type": "uint256" },
          { "internalType": "uint256", "name": "timestamp", "type": "uint256" }
        ],
        "internalType": "struct RiskMonitor.RiskAlert[]",
        "name": "",
        "type": "tuple[]"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  }
] as const;

export function useRiskMonitor() {
  const { writeContractAsync } = useWriteContract();

  // 读取用户头寸
  const usePositions = (address: string) => {
    return useReadContract({
      address: RISK_MONITOR_ADDRESS as `0x${string}`,
      abi: RISK_MONITOR_ABI,
      functionName: 'getUserPositions',
      args: [address as `0x${string}`],
      query: {
        enabled: !!address,
      },
    });
  };

  // 读取用户警报
  const useAlerts = (address: string) => {
    return useReadContract({
      address: RISK_MONITOR_ADDRESS as `0x${string}`,
      abi: RISK_MONITOR_ABI,
      functionName: 'getUserAlerts',
      args: [address as `0x${string}`],
      query: {
        enabled: !!address,
      },
    });
  };

  // 添加新头寸
  const addPosition = async (
    protocol: `0x${string}`,
    asset: `0x${string}`,
    amount: bigint,
    leverage: bigint,
    liquidationThreshold: bigint
  ) => {
    if (!RISK_MONITOR_ADDRESS) {
      throw new Error('RiskMonitor contract address not configured');
    }

    return writeContractAsync({
      address: RISK_MONITOR_ADDRESS as `0x${string}`,
      abi: RISK_MONITOR_ABI,
      functionName: 'addPosition',
      args: [protocol, asset, amount, leverage, liquidationThreshold],
    });
  };

  return {
    usePositions,
    useAlerts,
    addPosition,
  };
}
