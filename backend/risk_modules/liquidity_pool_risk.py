"""
流动性池风险分析模块 - 用于分析流动性池类型投资的风险
"""

from typing import Dict, List, Optional
import logging
import pandas as pd

logger = logging.getLogger("defi_risk.liquidity_pool_risk")


class LiquidityPoolRiskAnalyzer:
    """流动性池风险分析器"""

    def __init__(self, ai_predictor=None, blockchain_service=None):
        """
        初始化流动性池风险分析器

        Args:
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service

    def monitor_liquidity_pool_risk(self, pool_data: Dict) -> Dict:
        """
        监测流动性池风险

        Args:
            pool_data: 流动性池投资数据

        Returns:
            Dict: 风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_analysis = {
                "invest_type": 2,  # 流动性池
                "invest_type_name": "流动性池",
                "pool_name": pool_data.get("investmentName", "未知池子"),
                "risk_score": 0,
                "risk_level": "",
                "risk_factors": [],
                "recommendations": [],
                "monitoring_points": [],
                "detailed_risks": {},
            }

            # 提取基础信息
            assets = pool_data.get("assetsTokenList", [])
            if not assets:
                risk_analysis["risk_factors"].append("无法获取资产信息，风险评估不完整")
                risk_analysis["risk_score"] = 0.7  # 信息不完整，默认较高风险
                risk_analysis["risk_level"] = "HIGH"
                return risk_analysis

            # 1. 价格范围风险分析
            price_range_risk = self._analyze_price_range_risk(assets)
            risk_analysis["detailed_risks"]["price_range_risk"] = price_range_risk
            risk_analysis["risk_factors"].extend(price_range_risk["risk_factors"])
            risk_analysis["recommendations"].extend(price_range_risk["recommendations"])

            # 2. 资产组合风险分析
            asset_risk = self._analyze_asset_combination_risk(assets)
            risk_analysis["detailed_risks"]["asset_risk"] = asset_risk
            risk_analysis["risk_factors"].extend(asset_risk["risk_factors"])
            risk_analysis["recommendations"].extend(asset_risk["recommendations"])

            # 3. 手续费风险分析
            fee_risk = self._analyze_fee_risk(pool_data)
            risk_analysis["detailed_risks"]["fee_risk"] = fee_risk
            risk_analysis["risk_factors"].extend(fee_risk["risk_factors"])
            risk_analysis["recommendations"].extend(fee_risk["recommendations"])

            # 4. 无常损失风险分析
            impermanent_loss_risk = self._analyze_impermanent_loss_risk(assets)
            risk_analysis["detailed_risks"][
                "impermanent_loss_risk"
            ] = impermanent_loss_risk
            risk_analysis["risk_factors"].extend(impermanent_loss_risk["risk_factors"])
            risk_analysis["recommendations"].extend(
                impermanent_loss_risk["recommendations"]
            )

            # 5. 智能合约风险分析
            contract_risk = self._analyze_contract_risk(pool_data)
            risk_analysis["detailed_risks"]["contract_risk"] = contract_risk
            risk_analysis["risk_factors"].extend(contract_risk["risk_factors"])
            risk_analysis["recommendations"].extend(contract_risk["recommendations"])

            # 计算综合风险分数（加权平均）
            weights = {
                "price_range_risk": 0.25,
                "asset_risk": 0.25,
                "fee_risk": 0.1,
                "impermanent_loss_risk": 0.25,
                "contract_risk": 0.15,
            }

            total_score = sum(
                risk_analysis["detailed_risks"][risk_type]["score"] * weight
                for risk_type, weight in weights.items()
            )

            risk_analysis["risk_score"] = round(total_score, 2)

            # 确定风险等级
            if risk_analysis["risk_score"] >= 0.65:
                risk_analysis["risk_level"] = "HIGH"
            elif risk_analysis["risk_score"] <= 0.35:
                risk_analysis["risk_level"] = "LOW"
            else:
                risk_analysis["risk_level"] = "MEDIUM"

            # 添加监控点
            risk_analysis["monitoring_points"] = [
                "价格是否接近或超出设定范围",
                "资产价格相对变化",
                "池子总流动性变化",
                "交易费收益率变化",
                "协议安全状态更新",
            ]

            # 去重
            risk_analysis["risk_factors"] = list(set(risk_analysis["risk_factors"]))
            risk_analysis["recommendations"] = list(
                set(risk_analysis["recommendations"])
            )

            return risk_analysis

        except Exception as e:
            logger.error(f"监测流动性池风险时出错: {e}")
            return {
                "invest_type": 2,
                "invest_type_name": "流动性池",
                "pool_name": pool_data.get("investmentName", "未知池子"),
                "risk_score": 0.7,  # 出错时默认较高风险
                "risk_level": "HIGH",
                "risk_factors": ["风险分析过程中出错"],
                "recommendations": ["建议手动评估风险"],
                "monitoring_points": ["系统错误修复状态"],
                "error": str(e),
            }

    def _analyze_price_range_risk(self, assets: List[Dict]) -> Dict:
        """分析价格范围风险"""
        # 初始化价格范围风险分析
        price_range_risk = {
            "score": 0.4,  # 默认中等风险
            "risk_factors": [],
            "recommendations": [],
        }

        if len(assets) < 2:
            price_range_risk["score"] = 0.6
            price_range_risk["risk_factors"].append(
                "资产信息不完整，无法准确评估价格范围风险"
            )
            return price_range_risk

        # 提取资产符号
        asset_symbols = [asset.get("tokenSymbol", "") for asset in assets]

        # 检查是否包含稳定币对
        stablecoins = ["USDT", "USDC", "DAI", "BUSD", "TUSD"]
        stable_pair = False

        if len(asset_symbols) == 2:
            if asset_symbols[0] in stablecoins and asset_symbols[1] in stablecoins:
                stable_pair = True

        if stable_pair:
            price_range_risk["score"] = 0.2
            price_range_risk["risk_factors"].append("稳定币对的价格范围风险较低")
            price_range_risk["recommendations"].append("稳定币对适合长期持有")
        else:
            # 检查是否包含高波动性资产
            volatile_assets = ["BTC", "ETH", "BNB", "SOL", "AVAX"]
            volatile_count = sum(
                1 for symbol in asset_symbols if symbol in volatile_assets
            )

            if volatile_count > 0:
                price_range_risk["score"] = 0.6
                price_range_risk["risk_factors"].append(
                    "包含波动性较大的资产，价格范围风险较高"
                )
                price_range_risk["recommendations"].append(
                    "定期监控价格变化，及时调整仓位"
                )

            # 检查是否包含小市值代币
            unknown_assets = [
                symbol
                for symbol in asset_symbols
                if symbol not in stablecoins and symbol not in volatile_assets
            ]
            if unknown_assets:
                price_range_risk["score"] = 0.7
                price_range_risk["risk_factors"].append(
                    f"包含可能的小市值代币({', '.join(unknown_assets)})，价格波动风险更高"
                )
                price_range_risk["recommendations"].append(
                    "小市值代币波动性大，建议控制仓位"
                )

        return price_range_risk

    def _analyze_asset_combination_risk(self, assets: List[Dict]) -> Dict:
        """分析资产组合风险"""
        # 初始化资产组合风险分析
        asset_risk = {
            "score": 0.4,  # 默认中等风险
            "risk_factors": [],
            "recommendations": [],
        }

        if len(assets) < 2:
            asset_risk["score"] = 0.6
            asset_risk["risk_factors"].append(
                "资产信息不完整，无法准确评估资产组合风险"
            )
            return asset_risk

        # 提取资产符号
        asset_symbols = [asset.get("tokenSymbol", "") for asset in assets]

        # 检查是否包含稳定币对
        stablecoins = ["USDT", "USDC", "DAI", "BUSD", "TUSD"]
        stable_pair = False

        if len(asset_symbols) == 2:
            if asset_symbols[0] in stablecoins and asset_symbols[1] in stablecoins:
                stable_pair = True

        if stable_pair:
            asset_risk["score"] = 0.2
            asset_risk["risk_factors"].append("稳定币对的资产组合风险较低")
            asset_risk["recommendations"].append("稳定币对适合保守投资者")
        else:
            # 检查是否包含相关性高的资产
            correlated_pairs = [
                ("BTC", "ETH"),
                ("ETH", "BNB"),
                ("AVAX", "SOL"),
            ]

            for pair in correlated_pairs:
                if pair[0] in asset_symbols and pair[1] in asset_symbols:
                    asset_risk["score"] = 0.5
                    asset_risk["risk_factors"].append(
                        f"{pair[0]}和{pair[1]}相关性较高，可能增加无常损失风险"
                    )
                    asset_risk["recommendations"].append(
                        "相关性高的资产对可能导致更大的无常损失"
                    )
                    break

            # 检查是否包含小市值代币
            major_tokens = stablecoins + [
                "BTC",
                "ETH",
                "BNB",
                "SOL",
                "AVAX",
                "MATIC",
                "DOT",
            ]
            unknown_assets = [
                symbol for symbol in asset_symbols if symbol not in major_tokens
            ]

            if unknown_assets:
                asset_risk["score"] = 0.7
                asset_risk["risk_factors"].append(
                    f"包含可能的小市值代币({', '.join(unknown_assets)})，资产组合风险更高"
                )
                asset_risk["recommendations"].append(
                    "小市值代币可能存在流动性问题，建议控制仓位"
                )

        return asset_risk

    def _analyze_fee_risk(self, pool_data: Dict) -> Dict:
        """分析手续费风险"""
        # 初始化手续费风险分析
        fee_risk = {
            "score": 0.3,  # 默认中低风险
            "risk_factors": [],
            "recommendations": [],
        }

        # 提取APY信息
        apy = 0
        try:
            apy_str = pool_data.get("apy", "0")
            if isinstance(apy_str, str) and "%" in apy_str:
                apy_str = apy_str.replace("%", "")
            apy = float(apy_str)
        except (ValueError, TypeError):
            apy = 0

        # 根据APY调整风险评分
        if apy > 50:
            fee_risk["score"] = 0.7
            fee_risk["risk_factors"].append(
                f"APY高达{apy}%，远高于市场平均水平，可能不可持续"
            )
            fee_risk["recommendations"].append("高收益通常伴随高风险，建议控制仓位")
        elif apy > 20:
            fee_risk["score"] = 0.5
            fee_risk["risk_factors"].append(
                f"APY为{apy}%，高于市场平均水平，存在一定风险"
            )
            fee_risk["recommendations"].append("关注收益率变化趋势，警惕突然下降")
        else:
            fee_risk["score"] = 0.3
            fee_risk["risk_factors"].append(f"APY为{apy}%，处于合理范围，风险相对较低")

        # 提取交易量信息（如果有）
        volume = pool_data.get("volume24h", 0)
        if volume:
            try:
                volume_value = float(volume)
                if volume_value < 10000:  # 假设低于1万美元的交易量较低
                    fee_risk["score"] += 0.2
                    fee_risk["risk_factors"].append(
                        "24小时交易量较低，可能影响手续费收入"
                    )
                    fee_risk["recommendations"].append("低交易量池子的收益可能不稳定")
            except (ValueError, TypeError):
                pass

        return fee_risk

    def _analyze_impermanent_loss_risk(self, assets: List[Dict]) -> Dict:
        """分析无常损失风险"""
        # 初始化无常损失风险分析
        il_risk = {
            "score": 0.5,  # 默认中等风险
            "risk_factors": [],
            "recommendations": [],
        }

        if len(assets) < 2:
            il_risk["score"] = 0.6
            il_risk["risk_factors"].append("资产信息不完整，无法准确评估无常损失风险")
            return il_risk

        # 提取资产符号
        asset_symbols = [asset.get("tokenSymbol", "") for asset in assets]

        # 检查是否包含稳定币对
        stablecoins = ["USDT", "USDC", "DAI", "BUSD", "TUSD"]
        stable_pair = False

        if len(asset_symbols) == 2:
            if asset_symbols[0] in stablecoins and asset_symbols[1] in stablecoins:
                stable_pair = True

        if stable_pair:
            il_risk["score"] = 0.1
            il_risk["risk_factors"].append("稳定币对的无常损失风险极低")
            il_risk["recommendations"].append("稳定币对是避免无常损失的好选择")
        else:
            # 检查是否包含高波动性资产
            volatile_assets = ["BTC", "ETH", "BNB", "SOL", "AVAX"]
            volatile_count = sum(
                1 for symbol in asset_symbols if symbol in volatile_assets
            )

            if volatile_count > 0:
                il_risk["score"] = 0.7
                il_risk["risk_factors"].append("包含波动性较大的资产，无常损失风险较高")
                il_risk["recommendations"].append(
                    "波动性资产对可能导致显著的无常损失，建议设置止损策略"
                )

            # 检查是否包含小市值代币
            unknown_assets = [
                symbol
                for symbol in asset_symbols
                if symbol not in stablecoins and symbol not in volatile_assets
            ]
            if unknown_assets:
                il_risk["score"] = 0.8
                il_risk["risk_factors"].append(
                    f"包含可能的小市值代币({', '.join(unknown_assets)})，无常损失风险更高"
                )
                il_risk["recommendations"].append(
                    "小市值代币价格波动大，无常损失风险高，建议控制仓位"
                )

        return il_risk

    def _analyze_contract_risk(self, pool_data: Dict) -> Dict:
        """分析智能合约风险"""
        # 初始化合约风险分析
        contract_risk = {
            "score": 0.4,  # 默认中等风险
            "risk_factors": [],
            "recommendations": [],
        }

        # 提取协议名称
        protocol_name = self._extract_protocol_name(pool_data)

        # 根据协议名称调整风险评分
        protocol_risk_map = {
            "Uniswap": 0.3,
            "Curve": 0.3,
            "Balancer": 0.35,
            "SushiSwap": 0.4,
            "PancakeSwap": 0.4,
            "Trader Joe": 0.45,
        }

        # 查找协议名称（模糊匹配）
        matched_protocol = None
        for known_protocol in protocol_risk_map:
            if known_protocol.lower() in protocol_name.lower():
                matched_protocol = known_protocol
                break

        if matched_protocol:
            contract_risk["score"] = protocol_risk_map[matched_protocol]

            # 添加协议特定的风险因素
            if contract_risk["score"] < 0.4:
                contract_risk["risk_factors"].append(
                    f"{matched_protocol}是较为成熟的协议，合约风险相对较低"
                )
            else:
                contract_risk["risk_factors"].append(
                    f"{matched_protocol}协议存在一定的合约风险"
                )

            # 添加协议特定的建议
            contract_risk["recommendations"].append(
                f"关注{matched_protocol}协议的安全状态和更新"
            )
        else:
            # 未知协议，风险较高
            contract_risk["score"] = 0.6
            contract_risk["risk_factors"].append(
                "未能识别的协议，可能存在较高的合约风险"
            )
            contract_risk["recommendations"].append(
                "建议深入研究该协议的安全历史和审计状态"
            )

        # 使用AI预测器进行更深入的分析（如果可用）
        if self.ai_predictor and hasattr(
            self.ai_predictor, "analyze_protocol_security"
        ):
            try:
                ai_protocol_analysis = self.ai_predictor.analyze_protocol_security(
                    protocol_name
                )
                if ai_protocol_analysis:
                    # 整合AI分析结果
                    if "risk_score" in ai_protocol_analysis:
                        # 将AI风险评分(0-100)转换为0-1范围
                        ai_risk_score = ai_protocol_analysis["risk_score"] / 100
                        # 综合基础风险和AI风险评分
                        contract_risk["score"] = (
                            contract_risk["score"] + ai_risk_score
                        ) / 2

                    if "risk_factors" in ai_protocol_analysis:
                        contract_risk["risk_factors"].extend(
                            ai_protocol_analysis["risk_factors"]
                        )

                    if "recommendations" in ai_protocol_analysis:
                        contract_risk["recommendations"].extend(
                            ai_protocol_analysis["recommendations"]
                        )
            except Exception as e:
                logger.error(f"使用AI分析协议安全风险时出错: {e}")

        return contract_risk

    def _extract_protocol_name(self, investment_data: Dict) -> str:
        """从投资数据中提取协议名称"""
        # 尝试从不同字段提取协议名称
        protocol_name = ""

        if "investmentName" in investment_data:
            protocol_name = investment_data["investmentName"]
            # 尝试提取协议名称（通常是第一个单词）
            if " " in protocol_name:
                protocol_name = protocol_name.split(" ")[0]

        return protocol_name
