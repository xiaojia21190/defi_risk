from typing import List, Dict, Optional
from web3 import Web3
from eth_typing import Address
import json
import os
import pandas as pd
import aiohttp
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np

# Risk Monitor ABI
RISK_MONITOR_ABI = [
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
]

# Aave lending pool ABI (简化版)
AAVE_LENDING_POOL_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"internalType": "uint256", "name": "totalCollateralETH", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDebtETH", "type": "uint256"},
            {"internalType": "uint256", "name": "availableBorrowsETH", "type": "uint256"},
            {"internalType": "uint256", "name": "currentLiquidationThreshold", "type": "uint256"},
            {"internalType": "uint256", "name": "ltv", "type": "uint256"},
            {"internalType": "uint256", "name": "healthFactor", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V2 Pair ABI (简化版)
UNISWAP_V2_PAIR_ABI = [
    {
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Sepolia Testnet Addresses
AAVE_LENDING_POOL_SEPOLIA = "0x6Ae43d3271ff6888e7Fc43Fd7321a503ff738951"  # Aave V3 Sepolia
UNISWAP_V2_FACTORY_SEPOLIA = "0x7E0987E5b3a30e3f2828572Bb659E526E7BE02Cd"  # Example address

# Common token addresses on Sepolia
WETH_SEPOLIA = "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9"
USDC_SEPOLIA = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
DAI_SEPOLIA = "0x68194a729C2450ad26072b3D33ADaCbcef39D574"
WBTC_SEPOLIA = "0xf864F011C5A97fD8Da6308dFB5CfB5d05Af8D3D8"

@dataclass
class ProtocolPosition:
    protocol: str
    asset: str
    amount: float
    leverage: Optional[float] = None
    apy: Optional[float] = None

class BlockchainService:
    def __init__(self, web3_provider: str):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))

        # 获取合约地址
        self.risk_monitor_address = os.getenv("RISK_MONITOR_ADDRESS")
        if not self.risk_monitor_address:
            raise ValueError("RISK_MONITOR_ADDRESS environment variable is not set")

        # 初始化 RiskMonitor 合约
        self.risk_monitor_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.risk_monitor_address),
            abi=RISK_MONITOR_ABI
        )

        # 协议合约地址 (Sepolia)
        self.aave_lending_pool = AAVE_LENDING_POOL_SEPOLIA
        self.uniswap_factory = UNISWAP_V2_FACTORY_SEPOLIA

        # 初始化其他合约
        self.aave_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.aave_lending_pool),
            abi=AAVE_LENDING_POOL_ABI
        )

        # 价格 API 配置 (使用 Sepolia 测试网的价格源)
        self.supported_assets = {
            "ETH": WETH_SEPOLIA,
            "WBTC": WBTC_SEPOLIA,
            "USDC": USDC_SEPOLIA,
            "DAI": DAI_SEPOLIA
        }

    async def get_chain_positions(self, address: str) -> List[Dict]:
        """从 RiskMonitor 合约获取用户的链上头寸"""
        try:
            positions = await self.risk_monitor_contract.functions.getUserPositions(
                self.w3.to_checksum_address(address)
            ).call()

            return [
                {
                    "protocol": pos[0],
                    "asset": pos[1],
                    "amount": self.w3.from_wei(pos[2], 'ether'),
                    "leverage": pos[3],
                    "liquidationThreshold": pos[4]
                }
                for pos in positions
            ]
        except Exception as e:
            print(f"Error fetching chain positions: {e}")
            return []

    async def get_chain_alerts(self, address: str) -> List[Dict]:
        """从 RiskMonitor 合约获取用户的警报"""
        try:
            alerts = await self.risk_monitor_contract.functions.getUserAlerts(
                self.w3.to_checksum_address(address)
            ).call()

            return [
                {
                    "timestamp": alert[4],  # timestamp
                    "protocol": alert[1],   # protocol address
                    "asset": alert[2],      # asset address
                    "risk_level": alert[3], # risk level
                    "user": alert[0]        # user address
                }
                for alert in alerts
            ]
        except Exception as e:
            print(f"Error fetching chain alerts: {e}")
            return []

    async def add_position_to_monitor(self,
                                    protocol_address: str,
                                    asset_address: str,
                                    amount: int,
                                    leverage: int,
                                    liquidation_threshold: int,
                                    from_address: str) -> Dict:
        """添加头寸到风险监控合约"""
        try:
            # 构建交易
            transaction = self.risk_monitor_contract.functions.addPosition(
                protocol_address,
                asset_address,
                amount,
                leverage,
                liquidation_threshold
            ).build_transaction({
                'from': self.w3.to_checksum_address(from_address),
                'gas': 200000,  # 预估 gas 限制
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(from_address),
            })

            return transaction

        except Exception as e:
            print(f"Error adding position to monitor: {e}")
            return None

    async def get_asset_historical_data(self, asset: str) -> pd.DataFrame:
        """获取资产的历史价格数据 (使用测试网数据)"""
        try:
            # 为测试网创建模拟数据
            dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
            base_price = {
                "ETH": 2000.0,
                "WBTC": 40000.0,
                "USDC": 1.0,
                "DAI": 1.0
            }.get(asset, 100.0)

            # 生成模拟价格数据
            np.random.seed(42)  # 保持结果一致性
            price_changes = np.random.normal(0, 0.02, size=30)  # 2% 标准差
            prices = base_price * (1 + np.cumsum(price_changes))
            volumes = np.random.uniform(1000000, 5000000, size=30)

            df = pd.DataFrame({
                "timestamp": dates,
                "price": prices,
                "volume": volumes,
                "market_cap": prices * volumes
            })

            return df
        except Exception as e:
            print(f"Error generating test data: {e}")
            return pd.DataFrame()

    async def get_aave_position(self, user_address: str) -> Dict:
        """获取用户在 Aave 的头寸信息"""
        try:
            account_data = await self.aave_contract.functions.getUserAccountData(
                self.w3.to_checksum_address(user_address)
            ).call()

            position_data = {
                "totalCollateralETH": self.w3.from_wei(account_data[0], 'ether'),
                "totalDebtETH": self.w3.from_wei(account_data[1], 'ether'),
                "availableBorrowsETH": self.w3.from_wei(account_data[2], 'ether'),
                "currentLiquidationThreshold": account_data[3] / 10000,  # Convert basis points
                "ltv": account_data[4] / 10000,  # Convert basis points
                "healthFactor": account_data[5] / 1e18
            }

            # 如果有头寸，添加到风险监控合约
            if float(position_data["totalCollateralETH"]) > 0:
                await self.add_position_to_monitor(
                    protocol_address=self.aave_lending_pool,
                    asset_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH address
                    amount=account_data[0],  # totalCollateralETH in wei
                    leverage=int(float(position_data["totalDebtETH"]) / float(position_data["totalCollateralETH"]) * 100),
                    liquidation_threshold=account_data[3],  # currentLiquidationThreshold in basis points
                    from_address=user_address
                )

            return position_data
        except Exception as e:
            print(f"Error fetching Aave position: {e}")
            return None

    async def get_uniswap_position(self, pool_address: str, user_address: str) -> Dict:
        """获取用户在 Uniswap 的流动性头寸信息"""
        try:
            pair_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(pool_address),
                abi=UNISWAP_V2_PAIR_ABI
            )

            reserves = await pair_contract.functions.getReserves().call()
            total_supply = await pair_contract.functions.totalSupply().call()
            user_balance = await pair_contract.functions.balanceOf(
                self.w3.to_checksum_address(user_address)
            ).call()

            # 计算用户份额
            user_share = user_balance / total_supply

            return {
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "user_share": user_share,
                "user_token0": reserves[0] * user_share,
                "user_token1": reserves[1] * user_share
            }
        except Exception as e:
            print(f"Error fetching Uniswap position: {e}")
            return None

    async def get_all_positions(self, user_address: str) -> List[ProtocolPosition]:
        """获取用户在所有支持协议中的头寸"""
        positions = []

        # 首先获取链上记录的头寸
        chain_positions = await self.get_chain_positions(user_address)
        for pos in chain_positions:
            positions.append(ProtocolPosition(
                protocol=pos["protocol"],
                asset=pos["asset"],
                amount=float(pos["amount"]),
                leverage=float(pos["leverage"]),
            ))

        # 获取 Aave 头寸
        aave_position = await self.get_aave_position(user_address)
        if aave_position and float(aave_position["totalCollateralETH"]) > 0:
            positions.append(ProtocolPosition(
                protocol="Aave",
                asset="ETH",
                amount=float(aave_position["totalCollateralETH"]),
                leverage=float(aave_position["totalDebtETH"]) / float(aave_position["totalCollateralETH"]) if float(aave_position["totalCollateralETH"]) > 0 else 0
            ))

        # 获取常见 Uniswap 池的头寸
        common_pools = [
            ("0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc", "USDC-ETH"),  # USDC-ETH pool
            ("0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852", "ETH-USDT"),  # ETH-USDT pool
        ]

        for pool_address, pool_name in common_pools:
            position = await self.get_uniswap_position(pool_address, user_address)
            if position and position["user_share"] > 0:
                positions.append(ProtocolPosition(
                    protocol="Uniswap",
                    asset=pool_name,
                    amount=float(position["user_token0"]),  # 简化，只使用 token0 的数量
                ))

        return positions

    async def get_gas_price(self) -> float:
        """获取当前 gas 价格"""
        try:
            return float(self.w3.eth.gas_price)
        except Exception as e:
            print(f"Error fetching gas price: {e}")
            return 0

    def is_contract(self, address: str) -> bool:
        """检查地址是否为合约"""
        try:
            code = self.w3.eth.get_code(self.w3.to_checksum_address(address))
            return len(code) > 0
        except Exception as e:
            print(f"Error checking contract: {e}")
            return False
