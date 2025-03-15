from typing import Dict, List, Any, Optional
import aiohttp
import json
import os
import logging
from datetime import datetime
import uuid
import asyncio
from app.models.domain.ai import AiAnalysis, AiPrediction, AiInsight, AiRequest
from app.core.config import settings


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
            # 调用AI API
            response_data = await self._call_ai_api(request_data)

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
        # 根据分析类型构建提示
        prompt = self._get_prompt_template(analysis_type)

        # 将上下文和参数转换为字符串格式
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        parameters_str = json.dumps(parameters, ensure_ascii=False, indent=2)

        # 填充提示模板
        prompt = prompt.format(context=context_str, parameters=parameters_str)

        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的DeFi风险分析AI助手，擅长分析市场趋势、协议风险和投资策略。",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

    async def _call_ai_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用AI API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # 设置代理
        proxy = self.proxy_url if self.proxy_url else None

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=request_data,
                proxy=proxy,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"AI API请求失败: {response.status}, {error_text}")

                response_json = await response.json()

                # 提取内容
                try:
                    content = response_json["choices"][0]["message"]["content"]
                    return json.loads(content)
                except (KeyError, json.JSONDecodeError) as e:
                    raise Exception(f"解析AI响应失败: {str(e)}")

    def _parse_response(
        self, analysis_type: str, response_data: Dict[str, Any]
    ) -> AiAnalysis:
        """解析AI响应"""
        # 提取预测
        predictions = []
        for pred_data in response_data.get("predictions", []):
            predictions.append(
                AiPrediction(
                    target=pred_data.get("target", ""),
                    timeframe=pred_data.get("timeframe", ""),
                    value=pred_data.get("value", 0.0),
                    probability=pred_data.get("probability", 0.0),
                    range=pred_data.get("range", [0.0, 0.0]),
                )
            )

        # 提取洞察
        insights = response_data.get("insights", [])

        # 提取建议
        recommendations = response_data.get("recommendations", [])

        # 创建分析结果
        return AiAnalysis(
            id=str(uuid.uuid4()),
            analysis_type=analysis_type,
            timestamp=datetime.utcnow(),
            confidence=response_data.get("confidence", 0.0),
            predictions=predictions,
            insights=insights,
            recommendations=recommendations,
            supporting_data=response_data.get("supporting_data", {}),
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
1. 未来价格预测（24小时和7天）
2. 市场洞察（至少3点）
3. 投资建议（至少3点）
4. 支持数据（技术指标和情绪分析）

响应格式示例:
```json
{
  "confidence": 0.85,
  "predictions": [
    {
      "target": "price",
      "timeframe": "24h",
      "value": 3650.75,
      "probability": 0.75,
      "range": [3550.25, 3750.25]
    }
  ],
  "insights": [
    "ETH价格正处于上升趋势，技术指标显示强劲的买入信号",
    "市场情绪积极，机构投资者持仓增加",
    "短期内可能面临阻力位3700美元"
  ],
  "recommendations": [
    "考虑在3550-3600区间增加ETH持仓",
    "设置止损在3450以防市场反转",
    "关注美联储政策变化可能带来的波动"
  ],
  "supporting_data": {
    "technical_indicators": {
      "trend_strength": 0.75,
      "support_levels": [3400, 3300, 3200],
      "resistance_levels": [3700, 3850, 4000]
    },
    "sentiment_analysis": {
      "overall": 0.65,
      "social_media": 0.70,
      "news": 0.60
    }
  }
}
```
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

    async def analyze_with_predictor(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        parameters: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        使用AI预测器进行分析

        Args:
            analysis_type: 分析类型 (protocol_risk, market_trend, portfolio_risk)
            data: 分析数据
            parameters: 分析参数

        Returns:
            Dict: 分析结果
        """
        if parameters is None:
            parameters = {}

        logger.info(f"开始AI预测器分析: {analysis_type}")

        try:
            # 导入AI预测器
            from app.services.ai_predictor import AiPredictor

            predictor = AiPredictor()

            # 根据分析类型调用不同的分析方法
            if analysis_type == "protocol_risk":
                result = predictor.analyze_defi_protocol_risk(data)
            elif analysis_type == "market_trend":
                result = predictor.analyze_market_trend(data)
            elif analysis_type == "portfolio_risk":
                result = predictor.analyze_portfolio_risk(data)
            else:
                raise ValueError(f"不支持的分析类型: {analysis_type}")

            logger.info(f"AI预测器分析完成: {analysis_type}")

            # 将结果转换为AiAnalysis格式
            insights = []
            recommendations = []

            # 提取洞察
            if "risk_metrics" in result:
                for key, value in result["risk_metrics"].items():
                    if isinstance(value, (int, float)):
                        insights.append(f"{key}: {value:.2f}")
                    else:
                        insights.append(f"{key}: {value}")

            # 提取建议
            if "recommendations" in result:
                recommendations = result["recommendations"]

            # 创建分析结果
            analysis = AiAnalysis(
                id=str(uuid.uuid4()),
                analysis_type=analysis_type,
                timestamp=datetime.utcnow(),
                confidence=result.get("confidence", 0.0),
                predictions=[],
                insights=insights,
                recommendations=recommendations,
                supporting_data=result,
            )

            return analysis
        except Exception as e:
            logger.error(f"AI预测器分析失败: {str(e)}")
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
