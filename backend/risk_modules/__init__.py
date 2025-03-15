"""
风险模块包 - 包含各种投资类型的风险评估模块
"""

from risk_modules.save_risk import SaveRiskAnalyzer
from risk_modules.liquidity_pool_risk import LiquidityPoolRiskAnalyzer
from risk_modules.mining_risk import MiningRiskAnalyzer
from risk_modules.vault_risk import VaultRiskAnalyzer
from risk_modules.staking_risk import StakingRiskAnalyzer
from risk_modules.lending_risk import LendingRiskAnalyzer
from risk_modules.portfolio_risk import PortfolioRiskAnalyzer

__all__ = [
    "SaveRiskAnalyzer",
    "LiquidityPoolRiskAnalyzer",
    "MiningRiskAnalyzer",
    "VaultRiskAnalyzer",
    "StakingRiskAnalyzer",
    "LendingRiskAnalyzer",
    "PortfolioRiskAnalyzer",
]
