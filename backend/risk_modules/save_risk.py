"""
存币风险分析模块 - 用于分析存币类型投资的风险
"""

from typing import Dict, List, Optional
import logging
import asyncio
import pandas as pd

logger = logging.getLogger("defi_risk.save_risk")


class SaveRiskAnalyzer:
    """存币风险分析器"""

    def __init__(self, ai_predictor=None, blockchain_service=None):
        """
        初始化存币风险分析器

        Args:
            ai_predictor: AI预测器实例
            blockchain_service: 区块链服务实例
        """
        self.ai_predictor = ai_predictor
        self.blockchain_service = blockchain_service

    def monitor_save_risk(self, save_data: Dict) -> Dict:
        """
        监测存币风险

        Args:
            save_data: 存币投资数据

        Returns:
            Dict: 风险分析结果
        """
        try:
            # 初始化风险分析结果
            risk_analysis = {
                "invest_type": 1,  # 存币
                "invest_type_name": "存币",
                "platform_name": save_data.get("investmentName", "未知平台"),
                "risk_score": 0,
                "risk_level": "",
                "risk_factors": [],
                "recommendations": [],
                "monitoring_points": [],
                "detailed_risks": {},
            }

            # 提取基础信息
            assets = save_data.get("assetsTokenList", [])
            if not assets:
                risk_analysis["risk_factors"].append("无法获取资产信息，风险评估不完整")
                risk_analysis["risk_score"] = 0.7  # 信息不完整，默认较高风险
                risk_analysis["risk_level"] = "HIGH"
                return risk_analysis

            # 1. 平台安全风险分析
            platform_risk = self._analyze_platform_security(save_data)
            risk_analysis["detailed_risks"]["platform_risk"] = platform_risk
            risk_analysis["risk_factors"].extend(platform_risk["risk_factors"])
            risk_analysis["recommendations"].extend(platform_risk["recommendations"])

            # 2. 资产风险分析
            asset_risk = self._analyze_asset_risk(assets)
            risk_analysis["detailed_risks"]["asset_risk"] = asset_risk
            risk_analysis["risk_factors"].extend(asset_risk["risk_factors"])
            risk_analysis["recommendations"].extend(asset_risk["recommendations"])

            # 3. 收益风险分析
            yield_risk = self._analyze_yield_risk(save_data)
            risk_analysis["detailed_risks"]["yield_risk"] = yield_risk
            risk_analysis["risk_factors"].extend(yield_risk["risk_factors"])
            risk_analysis["recommendations"].extend(yield_risk["recommendations"])

            # 计算综合风险分数（加权平均）
            weights = {
                "platform_risk": 0.5,  # 平台安全是存币最重要的风险因素
                "asset_risk": 0.3,
                "yield_risk": 0.2,
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
                "平台安全审计状态",
                "资产价格变化",
                "存币收益率变化",
                "平台总锁仓量变化",
                "提款限制变更",
            ]

            # 去重
            risk_analysis["risk_factors"] = list(set(risk_analysis["risk_factors"]))
            risk_analysis["recommendations"] = list(
                set(risk_analysis["recommendations"])
            )

            return risk_analysis

        except Exception as e:
            logger.error(f"监测存币风险时出错: {e}")
            return {
                "invest_type": 1,
                "invest_type_name": "存币",
                "platform_name": save_data.get("investmentName", "未知平台"),
                "risk_score": 0.5,  # 出错时默认中等风险
                "risk_level": "MEDIUM",
                "risk_factors": ["风险分析过程中出错"],
                "recommendations": ["建议手动评估风险"],
                "monitoring_points": ["系统错误修复状态"],
                "error": str(e),
            }

    def _analyze_platform_security(self, save_data: Dict) -> Dict:
        """分析平台安全风险"""
        platform_name = save_data.get("investmentName", "")

        # 初始化平台风险分析
        platform_risk = {
            "score": 0.3,  # 默认中低风险
            "risk_factors": [],
            "recommendations": [],
        }

        # 根据平台名称调整风险评分
        platform_risk_map = {
            "Binance": 0.2,
            "Coinbase": 0.2,
            "OKX": 0.25,
            "Aave": 0.3,
            "Compound": 0.3,
            "MakerDAO": 0.3,
        }

        # 查找平台名称（模糊匹配）
        matched_platform = None
        for known_platform in platform_risk_map:
            if known_platform.lower() in platform_name.lower():
                matched_platform = known_platform
                break

        if matched_platform:
            platform_risk["score"] = platform_risk_map[matched_platform]

            # 添加平台特定的风险因素
            if platform_risk["score"] < 0.3:
                platform_risk["risk_factors"].append(
                    f"{matched_platform}是较为成熟的平台，平台风险相对较低"
                )
            else:
                platform_risk["risk_factors"].append(
                    f"{matched_platform}平台存在一定的安全风险"
                )

            # 添加平台特定的建议
            platform_risk["recommendations"].append(
                f"定期关注{matched_platform}平台的安全状态"
            )
        else:
            # 未知平台，风险较高
            platform_risk["score"] = 0.6
            platform_risk["risk_factors"].append(
                "未能识别的平台，可能存在较高的安全风险"
            )
            platform_risk["recommendations"].append(
                "建议深入研究该平台的安全历史和审计状态"
            )

        # 使用AI预测器进行更深入的分析（如果可用）
        if self.ai_predictor:
            try:
                ai_platform_analysis = self.ai_predictor.analyze_platform_security(
                    platform_name
                )
                if ai_platform_analysis:
                    # 整合AI分析结果
                    if "risk_score" in ai_platform_analysis:
                        # 将AI风险评分(0-100)转换为0-1范围
                        ai_risk_score = ai_platform_analysis["risk_score"] / 100
                        # 综合基础风险和AI风险评分
                        platform_risk["score"] = (
                            platform_risk["score"] + ai_risk_score
                        ) / 2

                    if "risk_factors" in ai_platform_analysis:
                        platform_risk["risk_factors"].extend(
                            ai_platform_analysis["risk_factors"]
                        )

                    if "recommendations" in ai_platform_analysis:
                        platform_risk["recommendations"].extend(
                            ai_platform_analysis["recommendations"]
                        )
            except Exception as e:
                logger.error(f"使用AI分析平台安全风险时出错: {e}")

        return platform_risk

    def _analyze_asset_risk(self, assets: List[Dict]) -> Dict:
        """分析资产风险"""
        # 初始化资产风险分析
        asset_risk = {
            "score": 0.3,  # 默认中低风险
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
                asset_risk["recommendations"].append("关注稳定币发行方的储备状况")
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

        return asset_risk

    def _analyze_yield_risk(self, save_data: Dict) -> Dict:
        """分析收益风险"""
        # 初始化收益风险分析
        yield_risk = {
            "score": 0.3,  # 默认中低风险
            "risk_factors": [],
            "recommendations": [],
        }

        # 提取APY信息
        apy = 0
        try:
            apy_str = save_data.get("apy", "0")
            if isinstance(apy_str, str) and "%" in apy_str:
                apy_str = apy_str.replace("%", "")
            apy = float(apy_str)
        except (ValueError, TypeError):
            apy = 0

        # 根据APY调整风险评分
        if apy > 20:
            yield_risk["score"] = 0.7
            yield_risk["risk_factors"].append(
                f"APY高达{apy}%，远高于市场平均水平，可能存在可持续性风险"
            )
            yield_risk["recommendations"].append("高收益通常伴随高风险，建议控制仓位")
        elif apy > 10:
            yield_risk["score"] = 0.5
            yield_risk["risk_factors"].append(
                f"APY为{apy}%，高于市场平均水平，存在一定风险"
            )
            yield_risk["recommendations"].append("关注收益率变化趋势，警惕突然下降")
        else:
            yield_risk["score"] = 0.2
            yield_risk["risk_factors"].append(
                f"APY为{apy}%，处于合理范围，风险相对较低"
            )

        return yield_risk

    def monitor_save_risk_with_ai(self, save_data: Dict) -> Dict:
        """
        使用AI增强的存币风险监测

        Args:
            save_data: 存币投资数据

        Returns:
            Dict: 增强的风险分析结果，包含AI预测
        """
        # 获取基础风险分析
        base_risk = self.monitor_save_risk(save_data)

        # 提取资产信息
        asset = save_data.get("assetsTokenList", [{}])[0].get("tokenSymbol", "")
        protocol_name = self._extract_protocol_name(save_data)
        amount = float(save_data.get("totalValue", 0))

        # 创建临时Position对象（如果有Position类的定义）
        if hasattr(self, "create_position"):
            temp_position = self.create_position(
                protocol=protocol_name,
                asset=asset,
                amount=amount,
                invest_type=1,  # 存币类型
            )

            # 使用AI预测器进行协议风险分析
            try:
                if self.ai_predictor and hasattr(
                    self.ai_predictor, "analyze_protocol_risk_from_position"
                ):
                    protocol_analysis = (
                        self.ai_predictor.analyze_protocol_risk_from_position(
                            temp_position
                        )
                    )
                    if protocol_analysis:
                        # 整合AI分析结果
                        base_risk["ai_analysis"] = protocol_analysis

                        # 更新风险评分
                        if (
                            "ai_risk_analysis" in protocol_analysis
                            and "risk_score" in protocol_analysis["ai_risk_analysis"]
                        ):
                            ai_risk_score = (
                                protocol_analysis["ai_risk_analysis"]["risk_score"]
                                / 100
                            )
                            # 综合基础风险和AI风险评分
                            base_risk["risk_score"] = (
                                base_risk["risk_score"] + ai_risk_score
                            ) / 2

                        # 添加AI建议
                        if (
                            "ai_risk_analysis" in protocol_analysis
                            and "recommendations"
                            in protocol_analysis["ai_risk_analysis"]
                        ):
                            base_risk["recommendations"].extend(
                                protocol_analysis["ai_risk_analysis"]["recommendations"]
                            )

                        # 添加风险因素
                        if (
                            "ai_risk_analysis" in protocol_analysis
                            and "risk_factors" in protocol_analysis["ai_risk_analysis"]
                        ):
                            for risk_type, risk_info in protocol_analysis[
                                "ai_risk_analysis"
                            ]["risk_factors"].items():
                                if "factors" in risk_info:
                                    base_risk["risk_factors"].extend(
                                        risk_info["factors"]
                                    )

                        # 添加监控点
                        if (
                            "ai_risk_analysis" in protocol_analysis
                            and "monitoring_points"
                            in protocol_analysis["ai_risk_analysis"]
                        ):
                            base_risk["monitoring_points"].extend(
                                protocol_analysis["ai_risk_analysis"][
                                    "monitoring_points"
                                ]
                            )
            except Exception as e:
                logger.error(f"使用AI分析协议风险时出错: {e}")

        # 获取AI市场预测
        try:
            if self.ai_predictor and hasattr(self.ai_predictor, "analyze_market_trend"):
                # 获取历史数据
                historical_data = None
                if hasattr(self, "_get_asset_historical_data"):
                    if asyncio.iscoroutinefunction(self._get_asset_historical_data):
                        historical_data = asyncio.run(
                            self._get_asset_historical_data(asset)
                        )
                    else:
                        historical_data = self._get_asset_historical_data(asset)

                if historical_data is not None and not isinstance(
                    historical_data, pd.DataFrame
                ):
                    historical_data = None

                if historical_data is not None and not historical_data.empty:
                    market_analysis = self.ai_predictor.analyze_market_trend(
                        historical_data=historical_data, asset=asset
                    )

                    if market_analysis:
                        # 添加市场分析
                        base_risk["market_analysis"] = market_analysis

                        # 更新风险因素
                        if "risk_factors" in market_analysis:
                            base_risk["risk_factors"].extend(
                                market_analysis["risk_factors"]
                            )

                        # 添加交易信号
                        if "trading_signals" in market_analysis:
                            base_risk["trading_signals"] = market_analysis[
                                "trading_signals"
                            ]
        except Exception as e:
            logger.error(f"获取{asset}市场分析时出错: {e}")

        # 去重
        base_risk["risk_factors"] = list(set(base_risk["risk_factors"]))
        base_risk["recommendations"] = list(set(base_risk["recommendations"]))
        base_risk["monitoring_points"] = list(set(base_risk["monitoring_points"]))

        return base_risk

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
