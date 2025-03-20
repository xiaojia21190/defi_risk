# 处理Windows平台下的事件循环问题
import platform


if platform.system() == "Windows":
    import asyncio

    try:
        # 尝试使用SelectorEventLoop
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("Windows平台：已设置SelectorEventLoop策略，解决aiodns兼容性问题")
    except Exception as e:
        print(f"设置Windows事件循环失败: {e}")

from typing import Dict, List, Any, Optional
import aiohttp
import json
import os
import logging
from datetime import datetime
import uuid
from app.models.domain.ai import AiAnalysis, AiPrediction, AiInsight, AiRequest
from app.core.config import settings
import requests


logger = logging.getLogger("defi_risk.ai_service")


class AiService:
    """AI服务"""

    def __init__(self):
        """初始化AI服务"""
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = settings.OPENAI_API_URL
        self.model = settings.AI_MODEL
        self.max_tokens = 2000
        self.temperature = 0.7
        self.proxy_url = settings.PROXY_URL

    async def analyze(
        self,
        analysis_type: str,
        context: Dict[str, Any],
        parameters: Dict[str, Any] = None,
    ) -> AiAnalysis:
        """
        执行AI分析

        Args:
            analysis_type: 分析类型
            context: 上下文数据
            parameters: 参数

        Returns:
            AI分析结果
        """
        if parameters is None:
            parameters = {}

        logger.info(f"开始AI分析: {analysis_type}")

        # 构建请求
        request_data = self._build_request(analysis_type, context, parameters)

        try:
            # 调用AI API（现在是同步的）
            response_data = self._call_ai_api(request_data)

            # 解析响应
            analysis = self._parse_response(analysis_type, response_data)

            logger.info(f"AI分析完成: {analysis_type}, 置信度={analysis.confidence}")

            return analysis
        except Exception as e:
            logger.error(f"AI分析失败: {str(e)}")
            # 返回空分析结果
            return AiAnalysis(
                id=str(uuid.uuid4()),
                analysis_type=analysis_type,
                timestamp=datetime.utcnow(),
                confidence=0.0,
                predictions=[],
                insights=[f"分析失败: {str(e)}"],
                recommendations=[],
                supporting_data={},
            )

    def _build_request(
        self, analysis_type: str, context: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建AI请求"""
        try:
            # 根据分析类型构建提示
            prompt = self._get_prompt_template(analysis_type)

            # 将上下文和参数转换为字符串格式，确保正确的JSON格式
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            parameters_str = json.dumps(parameters, ensure_ascii=False, indent=2)

            # 填充提示模板
            prompt = prompt.format(context=context_str, parameters=parameters_str)

            return {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的DeFi风险分析AI助手，擅长分析市场趋势、协议风险和投资策略。请始终返回有效的JSON格式数据。",
                    },
                    {"role": "user", "content": prompt},
                ],
            }
        except Exception as e:
            logger.error(f"构建AI请求时出错: {str(e)}")
            raise Exception(f"构建AI请求失败: {str(e)}")

    def _call_ai_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用AI API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # 设置代理
        proxies = (
            {"http": self.proxy_url, "https": self.proxy_url}
            if self.proxy_url
            else None
        )

        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=request_data,
                proxies=proxies,
            )

            if response.status_code != 200:
                raise Exception(
                    f"AI API请求失败: {response.status_code}, {response.text}"
                )

            response_json = response.json()

            # 提取内容
            try:
                content = response_json["choices"][0]["message"]["content"]
                # 处理markdown代码块格式
                if content.startswith("```json"):
                    content = content[7:]  # 移除 ```json
                if content.endswith("```"):
                    content = content[:-3]  # 移除 ```
                content = content.strip()  # 移除首尾空白
                return json.loads(content)
            except (KeyError, json.JSONDecodeError) as e:
                raise Exception(f"解析AI响应失败: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"AI API请求异常: {str(e)}")

    def _parse_response(
        self, analysis_type: str, response_data: Dict[str, Any]
    ) -> AiAnalysis:
        """解析AI响应"""
        try:
            if not isinstance(response_data, dict):
                logger.error(f"AI响应格式错误: {response_data}")
                return self._create_error_analysis(analysis_type, "AI响应格式错误")

            # 提取预测
            predictions = []
            for pred_data in response_data.get("predictions", []):
                try:
                    # 确保range是有效的元组
                    range_data = pred_data.get("range", [0.0, 0.0])
                    if (
                        not isinstance(range_data, (list, tuple))
                        or len(range_data) != 2
                    ):
                        range_data = [0.0, 0.0]

                    predictions.append(
                        AiPrediction(
                            target=str(pred_data.get("target", "")),
                            timeframe=str(pred_data.get("timeframe", "")),
                            value=float(pred_data.get("value", 0.0)),
                            probability=float(pred_data.get("probability", 0.0)),
                            range=(float(range_data[0]), float(range_data[1])),
                        )
                    )
                except (ValueError, TypeError, IndexError) as e:
                    logger.error(f"解析预测数据时出错: {str(e)}, 数据: {pred_data}")
                    continue

            # 提取洞察
            insights = []
            for insight in response_data.get("insights", []):
                if isinstance(insight, str):
                    insights.append(insight)
                elif isinstance(insight, dict) and "content" in insight:
                    insights.append(str(insight["content"]))
                else:
                    logger.warning(f"跳过无效的洞察数据: {insight}")

            # 提取建议
            recommendations = []
            for rec in response_data.get("recommendations", []):
                if isinstance(rec, str):
                    recommendations.append(rec)
                elif isinstance(rec, dict) and "content" in rec:
                    recommendations.append(str(rec["content"]))
                else:
                    logger.warning(f"跳过无效的建议数据: {rec}")

            # 创建分析结果
            return AiAnalysis(
                id=str(uuid.uuid4()),
                analysis_type=analysis_type,
                timestamp=datetime.utcnow(),
                confidence=float(response_data.get("confidence", 0.0)),
                predictions=predictions,
                insights=insights,
                recommendations=recommendations,
                supporting_data=response_data.get("supporting_data", {}),
            )
        except Exception as e:
            logger.error(f"解析AI响应时出错: {str(e)}")
            return self._create_error_analysis(
                analysis_type, f"解析AI响应失败: {str(e)}"
            )

    def _get_prompt_template(self, analysis_type: str) -> str:
        """获取提示模板"""
        templates = {
            "market_prediction": """
请分析以下市场数据并提供预测:

上下文数据:
{context}

参数:
{parameters}

请提供以下格式的JSON响应:
1. 总体置信度 (0-1)
2. 预测列表 (包含目标、时间范围、预测值和概率)
3. 市场洞察 (字符串列表)
4. 投资建议 (字符串列表)

要求返回如下JSON格式(注意这只是示例):
{{
  "confidence": 0.85,
  "predictions": [
    {{
      "target": "price",
      "timeframe": "24h",
      "value": 3650.75,
      "probability": 0.75
    }}
  ],
  "insights": [
    "市场趋势分析显示上升动能减弱",
    "交易量持续下降",
    "短期可能出现回调"
  ],
  "recommendations": [
    "建议保持观望",
    "等待回调后再考虑入场",
    "关注重要支撑位"
  ]
}}

请确保返回的是有效的JSON格式。
""",
            "protocol_risk": """
请分析以下协议的风险:

上下文数据:
{context}

参数:
{parameters}

请提供以下格式的JSON响应:
1. 协议风险评估（0-100分）
2. 主要风险因素（至少3点）
3. 风险缓解建议（至少3点）
4. 支持数据

响应格式示例:
```json
{
  "confidence": 0.8,
  "protocol_risk_score": 65,
  "insights": [
    "该协议的智能合约已经过多家安全公司审计，但仍存在中等风险",
    "协议治理较为中心化，决策权集中在少数几个大持币者手中",
    "历史上发生过一次小型安全事件，但已及时修复"
  ],
  "recommendations": [
    "限制在该协议中的投资不超过总资产的10%",
    "密切关注协议的治理提案和代码更新",
    "考虑购买智能合约保险以降低风险"
  ],
  "supporting_data": {
    "audit_status": "已审计",
    "tvl_trend": "上升",
    "governance_score": 45,
    "security_incidents": 1
  }
}
```
            """,
            "portfolio_insights": """
请分析以下投资组合并提供洞察:

上下文数据:
{context}

参数:
{parameters}

请提供以下格式的JSON响应:
1. 投资组合洞察（至少5点）
2. 优化建议（至少3点）
3. 风险警告（如有）
4. 支持数据

响应格式示例:
```json
{
  "confidence": 0.9,
  "insights": [
    "您的投资组合过于集中在ETH，占总资产的75%，增加了单一资产风险",
    "流动性池投资比例较高，面临无常损失风险",
    "缺乏稳定币敞口，可能在市场下跌时缺乏缓冲",
    "借贷头寸的健康因子较低，面临清算风险",
    "整体风险评分处于中高水平，建议适当调整"
  ],
  "recommendations": [
    "考虑将部分ETH转换为BTC和稳定币，提高多样性",
    "减少高风险流动性池的敞口，特别是波动性较大的代币对",
    "增加稳定币比例至少20%，作为市场波动的缓冲"
  ],
  "warnings": [
    "Aave上的借贷头寸健康因子低于1.5，存在清算风险"
  ],
  "supporting_data": {
    "concentration_ratio": 0.75,
    "volatility_exposure": "高",
    "stablecoin_ratio": 0.05,
    "risk_adjusted_return": 0.8
  }
}
```
            """,
            "concentration_risk": """
请分析以下资产集中度风险:

上下文数据:
{context}

参数:
{parameters}

请提供以下格式的JSON响应:
1. 风险评分（0-100分，越高风险越大）
2. 风险描述
3. 风险趋势（上升/稳定/下降）
4. 数据点（资产分布情况）

响应格式示例:
```json
{
  "risk_score": 75,
  "description": "投资组合过于集中在ETH，占比超过60%，存在较高的单一资产风险",
  "trend": "上升",
  "data_points": [
    {
      "asset": "ETH",
      "percentage": 0.65,
      "risk_contribution": 0.75
    },
    {
      "asset": "BTC",
      "percentage": 0.20,
      "risk_contribution": 0.15
    },
    {
      "asset": "USDC",
      "percentage": 0.15,
      "risk_contribution": 0.10
    }
  ],
  "hhi_index": 4850,
  "max_drawdown_estimate": 0.35
}
```
            """,
            "correlation_risk": """
请分析以下资产相关性风险:

上下文数据:
{context}

参数:
{parameters}

请提供以下格式的JSON响应:
1. 风险评分（0-100分，越高风险越大）
2. 风险描述
3. 风险趋势（上升/稳定/下降）
4. 数据点（资产相关性情况）

响应格式示例:
```json
{
  "risk_score": 65,
  "description": "投资组合中的主要资产相关性较高，多样化效果有限",
  "trend": "稳定",
  "data_points": [
    {
      "asset_pair": "ETH-BTC",
      "correlation": 0.85,
      "weight": 0.6
    },
    {
      "asset_pair": "ETH-SOL",
      "correlation": 0.75,
      "weight": 0.3
    },
    {
      "asset_pair": "BTC-SOL",
      "correlation": 0.70,
      "weight": 0.1
    }
  ],
  "avg_correlation": 0.78,
  "diversification_score": 0.35
}
```
            """,
            "market_risk_recommendations": """
请根据以下风险因子生成市场风险建议:

上下文数据:
{context}

参数:
{parameters}

请提供以下格式的JSON响应:
1. 建议列表（至少5条具体、可操作的建议）
2. 优先级排序（高/中/低）

响应格式示例:
```json
{
  "recommendations": [
    "将ETH持仓比例从当前的65%降低至40%以下，减少单一资产风险",
    "增加稳定币比例至少20%，作为市场波动的缓冲",
    "考虑在当前价格区间设置分批止盈点，锁定部分收益",
    "对于高波动性资产如SOL，设置15%的止损位，控制下行风险",
    "增加低相关性资产如LINK或DOT，提高投资组合的多样性",
    "关注市场整体趋势变化，避免在下跌趋势中追加投资"
  ],
  "priority_recommendations": [
    {
      "recommendation": "将ETH持仓比例从当前的65%降低至40%以下，减少单一资产风险",
      "priority": "高",
      "rationale": "当前集中度风险评分为75，远高于安全阈值"
    },
    {
      "recommendation": "增加稳定币比例至少20%，作为市场波动的缓冲",
      "priority": "高",
      "rationale": "当前波动性风险评分为68，市场波动加剧"
    }
  ]
}
```
            """,
            "market_risk_monitoring_points": """
请根据以下风险因子生成市场风险监控点:

上下文数据:
{context}

参数:
{parameters}

请提供以下格式的JSON响应:
1. 监控点列表（至少5条具体、可量化的监控点）
2. 优先级排序（高/中/低）

响应格式示例:
```json
{
  "monitoring_points": [
    "每日监控ETH价格变动，如单日下跌超过10%，考虑减仓",
    "关注投资组合中最大资产ETH的市值占比，保持在40%以下",
    "监控市场恐惧与贪婪指数，当指数低于20或高于80时重新评估仓位",
    "追踪主要资产间的相关性变化，特别是ETH-BTC对的相关系数",
    "关注主要持仓资产的交易量变化，交易量突增可能预示价格波动",
    "定期评估投资组合的整体波动率，与市场基准进行比较"
  ],
  "priority_monitoring_points": [
    {
      "point": "每日监控ETH价格变动，如单日下跌超过10%，考虑减仓",
      "priority": "高",
      "frequency": "每日",
      "threshold": "10%下跌"
    },
    {
      "point": "关注投资组合中最大资产ETH的市值占比，保持在40%以下",
      "priority": "高",
      "frequency": "每周",
      "threshold": "40%占比"
    }
  ]
}
```
            """,
            # 添加更多模板...
        }

        return templates.get(
            analysis_type,
            """
请分析提供的数据并给出洞察:

上下文数据:
{context}

参数:
{parameters}

请提供JSON格式的分析结果，包含洞察、建议和支持数据。
        """,
        )

    async def batch_analyze(self, requests: List[AiRequest]) -> List[AiAnalysis]:
        """
        批量执行AI分析

        Args:
            requests: AI分析请求列表

        Returns:
            AI分析结果列表
        """
        tasks = []
        for request in requests:
            tasks.append(
                self.analyze(request.analysis_type, request.context, request.parameters)
            )

        return await asyncio.gather(*tasks)

    async def is_available(self) -> bool:
        """
        检查AI服务是否可用

        Returns:
            bool: 服务是否可用
        """
        logger.info("检查AI服务可用性")
        try:
            # 构建一个简单的请求来测试服务
            test_request = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的DeFi风险分析AI助手。",
                    },
                    {"role": "user", "content": "测试连接"},
                ],
                "max_tokens": 10,
                "temperature": 0.7,
            }

            # 设置代理
            proxy = self.proxy_url if self.proxy_url else None

            # 设置超时时间
            timeout = aiohttp.ClientTimeout(total=5)  # 5秒超时

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json=test_request,
                    proxy=proxy,
                ) as response:
                    if response.status == 200:
                        logger.info("AI服务可用")
                        return True
                    else:
                        logger.warning(f"AI服务不可用，状态码: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"检查AI服务可用性时出错: {str(e)}")
            return False

    async def analyze_with_predictor(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        parameters: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        使用AI预测器进行分析

        Args:
            analysis_type: 分析类型 (protocol_risk, market_trend, portfolio_risk,
                          concentration_risk, correlation_risk, market_risk_recommendations,
                          market_risk_monitoring_points)
            data: 分析数据
            parameters: 分析参数

        Returns:
            Dict: 分析结果
        """
        if parameters is None:
            parameters = {}

        logger.info(f"开始AI预测器分析: {analysis_type}")

        # 定义分析类型到方法的映射
        ANALYSIS_METHOD_MAPPING = {
            "protocol_risk": "analyze_defi_protocol_risk",
            "market_trend": "analyze_market_trend",
            "portfolio_risk": "analyze_portfolio_risk",
            "concentration_risk": "analyze_concentration_risk",
            "correlation_risk": "analyze_correlation_risk",
            "market_risk_recommendations": "generate_market_risk_recommendations",
            "market_risk_monitoring_points": "generate_market_risk_monitoring_points",
        }

        # 定义相关性分析类型集合
        CORRELATION_ANALYSIS_TYPES = {
            "correlation_risk",
            "asset_correlation",
            "investment_type_correlation",
            "protocol_correlation",
        }

        try:
            # 导入AI预测器
            from app.services.ai_predictor import AiPredictor

            predictor = AiPredictor()

            result = None

            # 检查是否是相关性分析
            if analysis_type in CORRELATION_ANALYSIS_TYPES:
                # 将分析类型传递给数据
                correlation_data = data.copy()
                correlation_data["correlation_type"] = analysis_type
                result = predictor.analyze_correlation_risk(correlation_data)

            # 检查是否有直接映射的方法
            elif analysis_type in ANALYSIS_METHOD_MAPPING:
                method_name = ANALYSIS_METHOD_MAPPING[analysis_type]
                if hasattr(predictor, method_name) and callable(
                    getattr(predictor, method_name)
                ):
                    method = getattr(predictor, method_name)
                    result = method(data)

            # 处理协议历史分析
            elif analysis_type == "protocol_history":
                if hasattr(predictor, "analyze_defi_protocol_risk"):
                    # 添加分析类型标记
                    protocol_data = data.copy()
                    protocol_data["analysis_focus"] = "history"
                    result = predictor.analyze_defi_protocol_risk(protocol_data)
                else:
                    result = self._get_default_result(analysis_type)

            # 尝试使用通用分析
            elif hasattr(predictor, "analyze_generic") and callable(
                getattr(predictor, "analyze_generic")
            ):
                result = predictor.analyze_generic(analysis_type, data)

            # 如果没有合适的方法，使用OpenAI API
            else:
                # 将AiAnalysis转换为字典
                ai_analysis = await self._analyze_with_openai(
                    analysis_type, data, parameters
                )
                return ai_analysis.supporting_data

            logger.info(f"AI预测器分析完成: {analysis_type}")

            # 处理分析结果，但不返回AiAnalysis对象，直接返回字典
            analysis = self._process_predictor_result(analysis_type, result)
            return analysis.supporting_data

        except Exception as e:
            error_message = f"AI预测器分析失败: {str(e)}"
            logger.error(error_message)
            # 返回带有错误信息的字典
            return {
                "error": error_message,
                "risk_score": 0,
                "confidence": 0.0,
                "recommendations": ["无法完成分析，请检查数据"],
            }

    def _process_predictor_result(
        self, analysis_type: str, result: Dict[str, Any]
    ) -> AiAnalysis:
        """
        处理AI预测器的结果，统一格式

        Args:
            analysis_type: 分析类型
            result: 预测器返回的结果

        Returns:
            AiAnalysis: 格式化的分析结果
        """
        insights = []
        recommendations = []
        monitoring_points = []

        # 提取风险评分
        risk_score = result.get("risk_score")

        # 提取洞察
        if "insights" in result:
            insights = result["insights"]
        elif "risk_metrics" in result:
            for key, value in result["risk_metrics"].items():
                if isinstance(value, (int, float)):
                    insights.append(f"{key}: {value:.2f}")
                else:
                    insights.append(f"{key}: {value}")
        elif "description" in result:
            insights.append(result["description"])

        # 提取建议
        if "recommendations" in result:
            recommendations = result["recommendations"]

        # 提取监控点
        if "monitoring_points" in result:
            monitoring_points = result["monitoring_points"]

        # 创建分析结果
        return AiAnalysis(
            id=str(uuid.uuid4()),
            analysis_type=analysis_type,
            timestamp=datetime.utcnow(),
            confidence=result.get("confidence", 0.0),
            predictions=[],
            insights=insights,
            recommendations=recommendations,
            monitoring_points=monitoring_points,
            supporting_data=result,
        )

    def _create_error_analysis(
        self, analysis_type: str, error_message: str
    ) -> AiAnalysis:
        """
        创建错误分析结果

        Args:
            analysis_type: 分析类型
            error_message: 错误信息

        Returns:
            AiAnalysis: 错误分析结果
        """
        return AiAnalysis(
            id=str(uuid.uuid4()),
            analysis_type=analysis_type,
            timestamp=datetime.utcnow(),
            confidence=0.0,
            predictions=[],
            insights=[f"分析失败: {error_message}"],
            recommendations=[],
            monitoring_points=[],
            supporting_data={},
        )

    def _get_default_result(self, analysis_type: str) -> Dict[str, Any]:
        """
        获取默认分析结果

        Args:
            analysis_type: 分析类型

        Returns:
            Dict: 默认分析结果
        """
        return {
            "risk_score": 50,
            "description": f"{analysis_type}分析 (默认结果)",
            "trend": "稳定",
            "data_points": [],
            "recommendations": [f"建议收集更多{analysis_type}数据以获得更准确分析"],
            "monitoring_points": [f"监控{analysis_type}相关指标的变化"],
        }

    async def _analyze_with_openai(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        parameters: Dict[str, Any] = None,
    ) -> AiAnalysis:
        """
        使用OpenAI API进行分析

        Args:
            analysis_type: 分析类型
            data: 分析数据
            parameters: 分析参数

        Returns:
            AiAnalysis: 分析结果
        """
        logger.info(f"使用OpenAI API进行分析: {analysis_type}")

        # 构建请求
        request_data = self._build_request(analysis_type, data, parameters)

        # 调用AI API (同步)
        response_data = self._call_ai_api(request_data)

        # 解析响应
        analysis = self._parse_response(analysis_type, response_data)

        logger.info(f"OpenAI API分析完成: {analysis_type}")

        return analysis
