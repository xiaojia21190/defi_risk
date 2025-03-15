"""
挖矿风险分析模块 - 用于分析挖矿类型投资的风险
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger("defi_risk.mining_risk")


class MiningRiskAnalyzer:
    """挖矿风险分析器"""

    def __init__(self, ai_predictor=None, blockchain_service=None):
        """
        初始化挖矿风险分析器

        Args:
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service

    def monitor_mining_risk(self, mining_data: Dict) -> Dict:
        """
        监测挖矿风险

        Args:
            mining_data: 挖矿投资数据

        Returns:
            Dict: 风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_analysis = {
                "invest_type": 3,  # 挖矿
                "invest_type_name": "挖矿",
                "pool_name": mining_data.get("investmentName", "未知挖矿池"),
                "risk_score": 0,
                "risk_level": "",
                "risk_factors": [],
                "recommendations": [],
                "monitoring_points": [],
                "detailed_risks": {},
            }

            # 提取基础信息
            assets = mining_data.get("assetsTokenList", [])
            rewards = mining_data.get("rewardDefiTokenInfo", [])
            total_value = float(mining_data.get("totalValue", "0"))

            if not assets:
                risk_analysis["risk_factors"].append("无法获取资产信息，风险评估不完整")
                risk_analysis["risk_score"] = 0.7  # 信息不完整，默认较高风险
                risk_analysis["risk_level"] = "HIGH"
                return risk_analysis

            # 1. 资产组合风险分析
            asset_risk = self._analyze_mining_asset_risk(assets)
            risk_analysis["detailed_risks"]["asset_risk"] = asset_risk
            risk_analysis["risk_factors"].extend(asset_risk["risk_factors"])
            risk_analysis["recommendations"].extend(asset_risk["recommendations"])

            # 2. 奖励代币风险分析
            reward_risk = self._analyze_mining_reward_risk(rewards, total_value)
            risk_analysis["detailed_risks"]["reward_risk"] = reward_risk
            risk_analysis["risk_factors"].extend(reward_risk["risk_factors"])
            risk_analysis["recommendations"].extend(reward_risk["recommendations"])

            # 3. 协议安全风险分析
            protocol_risk = self._analyze_mining_protocol_risk(mining_data)
            risk_analysis["detailed_risks"]["protocol_risk"] = protocol_risk
            risk_analysis["risk_factors"].extend(protocol_risk["risk_factors"])
            risk_analysis["recommendations"].extend(protocol_risk["recommendations"])

            # 4. 收益递减风险分析
            yield_risk = self._analyze_mining_yield_risk(mining_data)
            risk_analysis["detailed_risks"]["yield_risk"] = yield_risk
            risk_analysis["risk_factors"].extend(yield_risk["risk_factors"])
            risk_analysis["recommendations"].extend(yield_risk["recommendations"])

            # 5. 智能合约风险分析
            contract_risk = {
                "score": 0.4,  # 挖矿合约通常风险中高
                "risk_factors": [
                    "挖矿智能合约固有风险",
                    "复杂的奖励分配机制可能存在漏洞",
                ],
                "recommendations": [
                    "关注协议安全审计状态",
                    "定期检查合约地址的异常交易",
                    "关注社区对该挖矿项目的评价",
                ],
            }
            risk_analysis["detailed_risks"]["contract_risk"] = contract_risk
            risk_analysis["risk_factors"].extend(contract_risk["risk_factors"])
            risk_analysis["recommendations"].extend(contract_risk["recommendations"])

            # 计算综合风险分数（加权平均）
            weights = {
                "asset_risk": 0.2,
                "reward_risk": 0.25,
                "protocol_risk": 0.15,
                "yield_risk": 0.25,
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
                "奖励代币价格变化",
                "挖矿APY变化趋势",
                "协议TVL变化",
                "奖励发放是否正常",
                "协议治理变更",
                "资产价格相对变化",
            ]

            # 去重
            risk_analysis["risk_factors"] = list(set(risk_analysis["risk_factors"]))
            risk_analysis["recommendations"] = list(
                set(risk_analysis["recommendations"])
            )

            return risk_analysis

        except Exception as e:
            logger.error(f"监测挖矿风险时出错: {e}")
            return {
                "invest_type": 3,
                "invest_type_name": "挖矿",
                "pool_name": mining_data.get("investmentName", "未知挖矿池"),
                "risk_score": 0.7,  # 出错时默认较高风险
                "risk_level": "HIGH",
                "risk_factors": ["风险分析过程中出错"],
                "recommendations": ["建议手动评估风险"],
                "monitoring_points": ["系统错误修复状态"],
                "error": str(e),
            }

    def _analyze_mining_asset_risk(self, assets: List[Dict]) -> Dict:
        """分析挖矿资产风险"""
        # 初始化资产风险分析
        asset_risk = {
            "score": 0.4,  # 默认中等风险
            "risk_factors": [],
            "recommendations": [],
        }

        if not assets:
            asset_risk["score"] = 0.7
            asset_risk["risk_factors"].append("无法获取资产信息，风险评估不完整")
            return asset_risk

        # 提取主要资产
        main_asset = assets[0].get("tokenSymbol", "")

        # 根据资产类型调整风险评分
        asset_risk_map = {
            "USDT": 0.2,
            "USDC": 0.15,
            "DAI": 0.25,
            "ETH": 0.3,
            "BTC": 0.3,
            "BNB": 0.35,
        }

        if main_asset in asset_risk_map:
            asset_risk["score"] = asset_risk_map[main_asset]

            # 添加资产特定的风险因素
            if main_asset in ["USDT", "USDC", "DAI"]:
                asset_risk["risk_factors"].append(
                    f"{main_asset}是稳定币，价格波动风险较低"
                )
                asset_risk["recommendations"].append(
                    "稳定币挖矿通常收益较低，但风险也较低"
                )
            else:
                asset_risk["risk_factors"].append(
                    f"{main_asset}是波动性资产，存在价格波动风险"
                )
                asset_risk["recommendations"].append(
                    f"关注{main_asset}的市场走势，设置止损策略"
                )
        else:
            # 未知资产，风险较高
            asset_risk["score"] = 0.6
            asset_risk["risk_factors"].append(
                f"{main_asset}是较小众的资产，可能存在较高的价格波动风险"
            )
            asset_risk["recommendations"].append(
                f"密切关注{main_asset}的价格变化，控制仓位"
            )

        # 检查是否是LP代币挖矿
        is_lp_token = False
        for asset in assets:
            token_symbol = asset.get("tokenSymbol", "")
            if "-" in token_symbol or "LP" in token_symbol:
                is_lp_token = True
                break

        if is_lp_token:
            asset_risk["score"] += 0.1  # LP代币挖矿风险更高
            asset_risk["risk_factors"].append("LP代币挖矿同时面临无常损失风险")
            asset_risk["recommendations"].append(
                "LP代币挖矿需要同时关注无常损失和挖矿收益"
            )

        return asset_risk

    def _analyze_mining_reward_risk(
        self, rewards: List[Dict], total_value: float
    ) -> Dict:
        """分析挖矿奖励代币风险"""
        # 初始化奖励代币风险分析
        reward_risk = {
            "score": 0.5,  # 默认中等风险
            "risk_factors": [],
            "recommendations": [],
        }

        if not rewards:
            reward_risk["risk_factors"].append("无法获取奖励代币信息，风险评估不完整")
            return reward_risk

        # 提取主要奖励代币
        main_reward = rewards[0].get("tokenSymbol", "")

        # 根据奖励代币类型调整风险评分
        reward_risk_map = {
            "USDT": 0.2,
            "USDC": 0.15,
            "DAI": 0.25,
            "ETH": 0.3,
            "BTC": 0.3,
            "BNB": 0.35,
        }

        if main_reward in reward_risk_map:
            reward_risk["score"] = reward_risk_map[main_reward]

            # 添加奖励代币特定的风险因素
            if main_reward in ["USDT", "USDC", "DAI"]:
                reward_risk["risk_factors"].append(
                    f"奖励代币{main_reward}是稳定币，价格稳定"
                )
                reward_risk["recommendations"].append(
                    "稳定币奖励可以降低挖矿收益的波动性"
                )
            else:
                reward_risk["risk_factors"].append(
                    f"奖励代币{main_reward}是主流代币，流动性较好"
                )
                reward_risk["recommendations"].append(
                    f"关注{main_reward}的市场走势，选择合适时机兑现收益"
                )
        else:
            # 未知奖励代币，风险较高
            reward_risk["score"] = 0.7
            reward_risk["risk_factors"].append(
                f"奖励代币{main_reward}是小众代币，可能存在价格和流动性风险"
            )
            reward_risk["recommendations"].append(
                f"建议定期将{main_reward}兑换为主流代币或稳定币"
            )

        # 检查奖励代币价值占比
        if total_value > 0 and len(rewards) > 0:
            try:
                reward_value = 0
                for reward in rewards:
                    reward_value += float(reward.get("value", "0"))

                reward_ratio = reward_value / total_value

                if reward_ratio > 0.3:  # 奖励价值超过总价值的30%
                    reward_risk["risk_factors"].append(
                        "奖励代币价值占比较高，可能存在价格下跌风险"
                    )
                    reward_risk["recommendations"].append(
                        "建议定期收获并兑换奖励，避免积累过多"
                    )
            except (ValueError, TypeError):
                pass

        return reward_risk

    def _analyze_mining_protocol_risk(self, mining_data: Dict) -> Dict:
        """分析挖矿协议风险"""
        # 初始化协议风险分析
        protocol_risk = {
            "score": 0.4,  # 默认中等风险
            "risk_factors": [],
            "recommendations": [],
        }

        # 提取协议名称
        protocol_name = self._extract_protocol_name(mining_data)

        # 根据协议名称调整风险评分
        protocol_risk_map = {
            "Curve": 0.3,
            "Convex": 0.35,
            "Aave": 0.3,
            "Compound": 0.3,
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
            protocol_risk["score"] = protocol_risk_map[matched_protocol]

            # 添加协议特定的风险因素
            if protocol_risk["score"] < 0.4:
                protocol_risk["risk_factors"].append(
                    f"{matched_protocol}是较为成熟的协议，安全风险相对较低"
                )
            else:
                protocol_risk["risk_factors"].append(
                    f"{matched_protocol}协议存在一定的安全风险"
                )

            # 添加协议特定的建议
            protocol_risk["recommendations"].append(
                f"关注{matched_protocol}协议的安全状态和更新"
            )
        else:
            # 未知协议，风险较高
            protocol_risk["score"] = 0.6
            protocol_risk["risk_factors"].append(
                "未能识别的协议，可能存在较高的安全风险"
            )
            protocol_risk["recommendations"].append(
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
                        protocol_risk["score"] = (
                            protocol_risk["score"] + ai_risk_score
                        ) / 2

                    if "risk_factors" in ai_protocol_analysis:
                        protocol_risk["risk_factors"].extend(
                            ai_protocol_analysis["risk_factors"]
                        )

                    if "recommendations" in ai_protocol_analysis:
                        protocol_risk["recommendations"].extend(
                            ai_protocol_analysis["recommendations"]
                        )
            except Exception as e:
                logger.error(f"使用AI分析协议安全风险时出错: {e}")

        return protocol_risk

    def _analyze_mining_yield_risk(self, mining_data: Dict) -> Dict:
        """分析挖矿收益递减风险"""
        # 初始化收益风险分析
        yield_risk = {
            "score": 0.5,  # 默认中等风险
            "risk_factors": [],
            "recommendations": [],
        }

        # 提取APY信息
        apy = 0
        try:
            apy_str = mining_data.get("apy", "0")
            if isinstance(apy_str, str) and "%" in apy_str:
                apy_str = apy_str.replace("%", "")
            apy = float(apy_str)
        except (ValueError, TypeError):
            apy = 0

        # 根据APY调整风险评分
        if apy > 100:
            yield_risk["score"] = 0.8
            yield_risk["risk_factors"].append(
                f"APY高达{apy}%，远高于市场平均水平，可能不可持续"
            )
            yield_risk["recommendations"].append(
                "超高收益通常伴随高风险和快速递减，建议短期参与并密切关注"
            )
        elif apy > 50:
            yield_risk["score"] = 0.7
            yield_risk["risk_factors"].append(
                f"APY为{apy}%，显著高于市场平均水平，存在收益递减风险"
            )
            yield_risk["recommendations"].append(
                "高收益挖矿项目通常会随着参与人数增加而收益递减，建议设置收益目标"
            )
        elif apy > 20:
            yield_risk["score"] = 0.5
            yield_risk["risk_factors"].append(
                f"APY为{apy}%，高于市场平均水平，存在一定收益递减风险"
            )
            yield_risk["recommendations"].append("关注收益率变化趋势，警惕突然下降")
        else:
            yield_risk["score"] = 0.3
            yield_risk["risk_factors"].append(
                f"APY为{apy}%，处于合理范围，收益递减风险相对较低"
            )
            yield_risk["recommendations"].append("收益率处于合理范围，可能更为可持续")

        # 检查是否有挖矿结束时间信息
        end_time = mining_data.get("endTime", "")
        if end_time:
            yield_risk["risk_factors"].append(
                "该挖矿项目有明确的结束时间，到期后将无法继续获得收益"
            )
            yield_risk["recommendations"].append(
                "关注挖矿结束时间，提前规划资金退出策略"
            )

        return yield_risk

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
