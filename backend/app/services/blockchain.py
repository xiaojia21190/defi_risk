"""
区块链服务模块 - 用于与区块链交互
"""

import base64
import hashlib
import hmac
import random
import time
import pandas as pd
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import requests
import json
import numpy as np
import urllib3
from web3 import Web3
from app.core.config import settings
from dataclasses import dataclass
from cachetools import TTLCache
from app.models.domain.risk import (
    RiskAnalysisResult,
    RiskMetrics,
    RiskAnalysis,
    RiskFactor,
)


logger = logging.getLogger("defi_risk.blockchain_service")

# 使用settings中的代理设置
proxies = {"http": settings.PROXY_URL, "https": settings.PROXY_URL} if settings.PROXY_URL else None

from defillama import DefiLlama


class HistoricalDataCache:
    """历史数据缓存类，用于缓存不同时间周期的数据"""

    def __init__(self):
        """初始化不同时间周期的缓存"""
        # 为不同时间周期创建独立的TTLCache
        # 缓存时间设置为数据周期的2倍，确保数据时效性
        self.cache_map = {
            "1m": TTLCache(maxsize=1000, ttl=120),  # 2分钟
            "5m": TTLCache(maxsize=1000, ttl=600),  # 10分钟
            "15m": TTLCache(maxsize=1000, ttl=1800),  # 30分钟
            "1h": TTLCache(maxsize=1000, ttl=7200),  # 2小时
            "4h": TTLCache(maxsize=500, ttl=28800),  # 8小时
            "1d": TTLCache(maxsize=500, ttl=172800),  # 48小时
        }
        self.logger = logger

    def get_cache(self, interval: str) -> TTLCache:
        """
        获取对应时间周期的缓存

        Args:
            interval: 时间周期

        Returns:
            对应的TTLCache实例
        """
        # 确保 interval 是字符串类型
        interval_str = str(interval)

        # 打印调试信息
        self.logger.info(f"获取缓存：interval={interval_str}, 类型={type(interval)}")
        self.logger.info(f"可用的缓存键：{list(self.cache_map.keys())}")

        # 检查 interval 是否在 cache_map 中
        if interval_str not in self.cache_map:
            self.logger.warning(f"未找到间隔为 {interval_str} 的缓存")
            return None

        return self.cache_map[interval_str]

    def get(self, key: str, interval: str):
        """
        获取缓存数据

        Args:
            key: 缓存键
            interval: 时间周期

        Returns:
            缓存的数据，如果不存在则返回None
        """
        try:
            # 确保 interval 是字符串类型
            interval_str = str(interval)

            # 打印调试信息
            self.logger.info(
                f"获取缓存：key={key}, interval={interval_str}, 类型={type(interval)}"
            )

            # 检查 interval 是否在 cache_map 中
            if interval_str not in self.cache_map:
                self.logger.warning(f"获取缓存失败：未找到间隔为 {interval_str} 的缓存")
                return None

            # 获取缓存
            value = self.cache_map[interval_str].get(key)
            if value is None:
                self.logger.info(f"缓存未命中：key={key}, interval={interval_str}")
            else:
                self.logger.info(f"缓存命中：key={key}, interval={interval_str}")
            return value
        except Exception as e:
            self.logger.error(
                f"获取缓存时出错：key={key}, interval={interval_str}, error={e}"
            )
            return None

    def set(self, key: str, value, interval: str):
        """
        设置缓存数据

        Args:
            key: 缓存键
            value: 要缓存的数据
            interval: 时间周期
        """
        try:
            # 确保 interval 是字符串类型
            interval_str = str(interval)

            # 打印调试信息
            self.logger.info(
                f"设置缓存：key={key}, interval={interval_str}, 类型={type(interval)}"
            )

            # 检查 interval 是否在 cache_map 中
            if interval_str not in self.cache_map:
                self.logger.warning(f"设置缓存失败：未找到间隔为 {interval_str} 的缓存")
                return

            # 设置缓存
            self.cache_map[interval_str][key] = value
            self.logger.info(f"成功设置缓存：key={key}, interval={interval_str}")
        except Exception as e:
            self.logger.error(
                f"设置缓存时出错：key={key}, interval={interval_str}, error={e}"
            )


@dataclass
class PlatformAsset:
    """平台资产数据类"""

    protocol: str
    asset: str
    amount: float
    invest_type: int
    apy: Optional[float] = None
    tokenList: Optional[List[Dict[str, Any]]] = None


@dataclass
class ProtocolPosition:
    """协议头寸数据类"""

    total_assets: float
    total_debts: float
    leverage: float
    positions: List[PlatformAsset]


class BlockchainService:
    """区块链服务"""

    def __init__(self):
        """初始化区块链服务"""
        self.provider_url = settings.WEB3_PROVIDER_URL
        self.web3 = Web3(Web3.HTTPProvider(self.provider_url))
        self.proxy_url = settings.PROXY_URL
        self.logger = logger
        self.historical_data_cache = HistoricalDataCache()
        self.defi_llama_client = DefiLlama()
        # OKX API 配置
        self.okx_api_config = {
            "api_key": "af83a6eb-080f-4287-af07-a5038a75f552",
            "secret_key": "52BCC8FDDA57E991F917C58DE9A3186F",
            "passphrase": "Jiashuai2190@",
            "project": "",  # 此处仅适用于 WaaS APIs
        }
        # OKX API 基础 URL
        self.okx_api_base_url = "https://www.okx.com"
        self.okx_api_defi_path = "/api/v5/defi"
        self.okx_api_wallet_path = "/api/v5/wallet"

        # 添加HTTP会话属性
        self._http_session = None

        self._load_contract_abis()

        logger.info("区块链服务初始化完成")

    async def close(self):
        """
        关闭区块链服务，释放资源
        """
        logger.info("关闭区块链服务")

        # 关闭HTTP会话
        if self._http_session is not None:
            await self._http_session.close()
            self._http_session = None

        # 关闭web3连接
        if hasattr(self.web3.provider, 'close'):
            self.web3.provider.close()

        # 关闭DeFi Llama客户端
        if hasattr(self.defi_llama_client, 'close'):
            await self.defi_llama_client.close()

        logger.info("区块链服务已关闭")

    def _load_contract_abis(self):
        """加载合约ABI"""
        # 基础ERC20 ABI
        self.erc20_abi = json.loads(
            '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}]'
        )

    async def get_gas_price(self) -> float:
        """获取当前gas价格（单位：Gwei）

        Returns:
            float: 当前gas价格，单位为Gwei
        """
        try:
            gas_price = self.historical_data_cache.get("gas_price", "1m")
            if gas_price is not None:
                return gas_price
            try:
                # 尝试从ETH API获取ETH gas价格
                url = "https://api.etherscan.io/v2/api?chainid=1&module=gastracker&action=gasoracle"
                """
                {
                    "status": "1",
                    "message": "OK-Missing/Invalid API Key, rate limit of 1/5sec applied",
                    "result": {
                        "LastBlock": "22027483",
                        "SafeGasPrice": "0.638579654",
                        "ProposeGasPrice": "0.639519654",
                        "FastGasPrice": "0.703471619",
                        "suggestBaseFee": "0.638579654",
                        "gasUsedRatio": "0.798531,0.483220166666667,0.492903416666667,0.982302996161946,0.451882105996492"
                    }
                }
                """

                response = requests.get(url, proxies=proxies)
                if response.status_code == 200:
                    data = response.json()
                    gas_price = float(data["result"]["suggestBaseFee"])
                    self.historical_data_cache.set("gas_price", gas_price, "1m")
                    logger.info(f"从ETH API估算gas价格: {gas_price:.2f} Gwei")
                    return gas_price
                else:
                    logger.error(f"ETH API返回错误: {response.status_code}")
            except Exception as e:
                logger.error(f"从ETH API获取gas价格失败: {e}")

            # 如果都失败了，返回一个合理的默认值
            default_gas_price = 0.5  # 0.5 Gwei
            logger.warning(f"无法获取实时gas价格，使用默认值: {default_gas_price} Gwei")
            return default_gas_price

        except Exception as e:
            logger.error(f"获取gas价格时出错: {e}")
            return 30.0  # 返回默认值

    async def get_token_price(self, asset: Dict[str, str]) -> float:
        """
        获取代币价格，使用OKX API作为唯一数据源

        Args:
            token_address: 代币合约地址或代币符号

        Returns:
            代币价格（USD）
        """
        try:
            # 缓存检查
            cache_key = f"token_price_{asset['symbol']}_{asset['chain']}"
            cache_interval = "1m"  # 1分钟缓存
            cached_price = self.historical_data_cache.get(cache_key, cache_interval)
            if cached_price is not None:
                self.logger.info(f"从缓存获取代币价格: {asset['symbol']}")
                return cached_price

            # 尝试使用OKX API获取价格
            okx_price = await self._get_okx_token_price(asset)
            if okx_price > 0:
                self.logger.info(f"从OKX获取到{asset['symbol']}的价格: {okx_price}")
                self.historical_data_cache.set(cache_key, okx_price, cache_interval)
                return okx_price

            # 如果所有方法都失败，返回默认价格
            self.logger.warning(
                f"无法从OKX获取代币 {asset['symbol']} 的价格，使用默认值"
            )
            return 1.0
        except Exception as e:
            self.logger.error(f"获取代币价格失败: {str(e)}")
            return 0.0

    async def _get_okx_token_price(self, asset: Dict[str, str]) -> float:
        """
        从OKX API获取代币价格

        Args:
            token_id: 代币ID、符号或地址

        Returns:
            代币价格（USD）
        """
        try:
            self.logger.info(f"从OKX获取代币价格: {asset['symbol']}")

            try:
                # 使用OKX的DeFi API获取代币价格
                endpoint = "/token/current-price"

                # 构建请求参数
                payload = {
                    [
                        {
                            "chainIndex": 1,
                            "tokenAddress": asset["address"],
                        }  # 默认使用以太坊链
                    ]
                }

                # 发送请求
                data = await self._okx_request(
                    "POST", endpoint, payload, self.okx_api_wallet_path
                )

                if data and "data" in data:
                    token_info = data["data"].get("tokenList", [])
                    if token_info and len(token_info) > 0:
                        price = float(token_info[0].get("price", 0))
                        if price > 0:
                            self.logger.info(
                                f"OKX DeFi API返回的{asset['symbol']}价格: {price}"
                            )
                            return price

            except Exception as e:
                self.logger.error(f"使用OKX DeFi API获取{asset['symbol']}价格失败: {e}")

            # 如果所有方法都失败，返回0
            return 0.0

        except Exception as e:
            self.logger.error(f"从OKX获取代币价格失败: {str(e)}")
            return 0.0

    async def get_all_positions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        获取钱包在所有协议中的头寸

        首先尝试使用OKX API获取更全面的DeFi头寸数据，
        如果失败则回退到基础方法获取有限的协议数据。

        Args:
            wallet_address: 钱包地址

        Returns:
            头寸列表
        """
        try:
            # 缓存检查
            cache_key = f"wallet_positions_{wallet_address}"
            cached_positions = self.historical_data_cache.get(cache_key, "1d")
            if cached_positions is not None:
                self.logger.info(f"从缓存获取钱包头寸: {wallet_address}")
                return cached_positions

            self.logger.info(f"开始获取地址 {wallet_address} 的所有DeFi头寸")

            # 首先尝试使用OKX API获取更全面的头寸数据
            try:
                self.logger.info(f"尝试使用OKX API获取头寸数据")
                okx_positions = await self._get_okx_positions(wallet_address)

                if okx_positions and len(okx_positions) > 0:
                    self.logger.info(
                        f"成功从OKX API获取到 {len(okx_positions)} 个协议的头寸数据"
                    )
                    # 直接返回OKX API获取的头寸数据
                    return okx_positions
                else:
                    self.logger.warning("OKX API未返回有效头寸数据，将使用基础方法")
            except Exception as e:
                self.logger.error(f"使用OKX API获取头寸失败: {str(e)}，将使用基础方法")

            # 如果OKX API获取失败，回退到基础方法
            self.logger.info("使用基础方法获取有限的协议头寸数据")
            # 合并结果
            all_positions = []

            return all_positions
        except Exception as e:
            self.logger.error(f"获取所有头寸失败: {str(e)}")
            return []

    def _get_invest_type_name(self, invest_type: int) -> str:
        """获取投资类型的名称

        Args:
            invest_type: 投资类型ID

        Returns:
            str: 投资类型名称
        """
        invest_type_map = {
            1: "存币",
            2: "流动性池",
            3: "挖矿",
            4: "机枪池",
            5: "质押",
            6: "借贷",
        }
        return invest_type_map.get(invest_type, "未知类型")

    def _generate_okx_signature(
        self, method: str, request_path: str, params: Optional[Dict] = None
    ) -> Dict[str, str]:
        """生成OKX API请求所需的签名和时间戳

        Args:
            method: HTTP方法 ('GET' 或 'POST')
            request_path: 请求路径
            params: 请求参数

        Returns:
            包含签名和时间戳的字典
        """
        # 获取ISO 8601格式时间戳
        timestamp = datetime.utcnow().isoformat()[:-3] + "Z"

        # 生成预签名字符串
        query_string = ""
        if method == "GET" and params:
            query_string = "?" + urllib3.parse.urlencode(params)
        elif method == "POST" and params:
            query_string = json.dumps(params)

        pre_hash = timestamp + method + request_path + query_string

        # 使用HMAC-SHA256生成签名
        secret_key = self.okx_api_config["secret_key"].encode("utf-8")
        signature = base64.b64encode(
            hmac.new(secret_key, pre_hash.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")

        return {
            "OK-ACCESS-KEY": self.okx_api_config["api_key"],
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.okx_api_config["passphrase"],
            "OK-ACCESS-PROJECT": self.okx_api_config["project"],
        }

    async def _okx_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        full_path_header: str = "",
    ) -> Dict:
        """发送带有认证的OKX API请求

        Args:
            method: HTTP方法 ('GET' 或 'POST')
            path: API路径
            params: 请求参数

        Returns:
            API响应数据
        """
        # 间隔1-2秒
        time.sleep(random.randint(1, 2))
        if full_path_header == "":
            full_path = self.okx_api_defi_path + path
        else:
            full_path = full_path_header + path
        headers = self._generate_okx_signature(method, full_path, params)

        if method == "POST":
            headers["Content-Type"] = "application/json"
            url = self.okx_api_base_url + full_path
            response = requests.post(url, json=params, headers=headers, proxies=proxies)
        else:  # GET
            url = self.okx_api_base_url + full_path
            if params:
                url += "?" + urllib3.parse.urlencode(params)
            response = requests.get(url, headers=headers, proxies=proxies)

        if response.status_code != 200:
            self.logger.error(
                f"OKX API请求失败: {response.status_code}, {response.text}"
            )
            raise Exception(f"OKX API请求失败: {response.status_code}")

        data = response.json()
        if data.get("code") != 0:
            self.logger.error(f"OKX API返回错误: {data}")
            raise Exception(f"OKX API返回错误: {data.get('msg', 'Unknown error')}")

        return data

    async def _get_protocol_risk_summary(self, protocol: str) -> Dict[str, Any]:
        """获取协议的风险摘要信息，集成AI预测功能

        Args:
            protocol: 协议名称

        Returns:
            Dict: 包含风险等级和评分的字典
        """
        try:
            # 尝试获取缓存的风险分析结果
            cache_key = f"protocol_risk_{protocol.lower()}"
            cache_interval = "1d"  # 使用1天缓存
            cached_risk = self.historical_data_cache.get(cache_key, cache_interval)

            if cached_risk is not None:
                return cached_risk

            # 获取协议数据
            protocol_data = await self.get_protocol(protocol)

            # 获取协议历史TVL数据
            historical_tvl = await self.get_protocol_historical_tvl(protocol)

            # 获取协议审计状态
            audit_status = await self.get_protocol_audit_status(protocol)

            # 准备用于AI分析的数据
            ai_protocol_data = {
                "protocol_metadata": protocol_data,
                "historical_tvl": historical_tvl,
                "audit_status": audit_status,
                "basic_analysis": {
                    "name": protocol_data.get("name", protocol),
                    "category": protocol_data.get("category", "未知"),
                    "chains": protocol_data.get("chains", []),
                    "tvl": protocol_data.get("tvl", 0),
                    "audit_count": audit_status.get("audit_count", 0),
                    "is_open_source": audit_status.get("is_open_source", False),
                },
                "chain_distribution": protocol_data.get("chainTvls", {}),
            }

            # 尝试使用AI预测器进行高级风险分析
            try:
                from app.services.ai_predictor import AiPredictor

                ai_predictor = AiPredictor()

                self.logger.info(f"使用AI预测器分析协议 {protocol} 的风险")
                ai_risk_analysis = ai_predictor.analyze_defi_protocol_risk(
                    ai_protocol_data
                )

                if ai_risk_analysis and "risk_score" in ai_risk_analysis:
                    # 提取AI分析的关键风险信息
                    risk_summary = {
                        "risk_level": ai_risk_analysis.get("risk_level", "未知"),
                        "risk_score": ai_risk_analysis.get("risk_score", 0),
                        "audit_status": audit_status.get("audited", False),
                        "tvl_trend": ai_risk_analysis.get("tvl_trend", {}),
                        "recommendations": ai_risk_analysis.get("recommendations", [])[
                            :3
                        ],  # 取前3条建议
                        "ai_confidence": ai_risk_analysis.get("confidence", 0.8),
                        "analysis_timestamp": ai_risk_analysis.get(
                            "analysis_timestamp", datetime.now().isoformat()
                        ),
                    }

                    # 缓存结果
                    self.historical_data_cache.set(
                        cache_key, risk_summary, cache_interval
                    )
                    self.logger.info(f"成功使用AI预测器分析协议 {protocol} 的风险")
                    return risk_summary

            except Exception as e:
                self.logger.error(
                    f"使用AI预测器分析协议 {protocol} 风险失败: {str(e)}，将使用基础方法"
                )

            # 如果AI分析失败，回退到基础风险分析
            self.logger.info(f"使用基础方法分析协议 {protocol} 的风险")
            risk_analysis = await self.analyze_protocol_risk(protocol)

            # 提取关键风险信息
            risk_summary = {
                "risk_level": risk_analysis.get("risk_level", "未知"),
                "risk_score": risk_analysis.get("risk_score", 0),
                "audit_status": audit_status.get("audited", False),
                "recommendations": risk_analysis.get("analysis", {})
                .get("recommendation", "")
                .split("，")[:3],
            }

            # 缓存结果
            self.historical_data_cache.set(cache_key, risk_summary, cache_interval)

            return risk_summary
        except Exception as e:
            self.logger.error(f"获取协议 {protocol} 风险摘要失败: {str(e)}")
            return {"risk_level": "未知", "risk_score": 0, "audit_status": False}

    async def _get_okx_positions(self, address: str) -> List[Dict[str, Any]]:
        """使用OKX API获取用户在各DeFi协议中的存款头寸

        Args:
            address: 用户的钱包地址

        Returns:
            List[Dict]: 用户的DeFi头寸列表
        """
        try:
            self.logger.info(f"使用OKX API获取地址 {address} 的DeFi头寸")
            positionAll = []

            # 1. 获取用户资产列表
            payload = {
                "walletAddressList": [
                    {"walletAddress": address, "chainId": 1}  # 默认使用以太坊主网
                ]
            }

            try:
                data = await self._okx_request(
                    "POST", "/user/asset/platform/list", payload
                )
            except Exception as e:
                self.logger.error(f"获取用户资产列表失败: {e}")
                return []

            wallet_platform_list = data["data"].get("walletIdPlatformList", [])
            if not wallet_platform_list:
                self.logger.info(f"地址 {address} 在OKX API中没有找到任何DeFi头寸")
                return []

            # 2. 处理每个平台的资产
            for wallet_platform in wallet_platform_list:
                platform_list = wallet_platform.get("platformList", [])

                # 按平台分组的资产数据结构
                platform_assets = {}  # 按平台分组的资产

                for platform in platform_list:
                    platform_name = platform.get("platformName")
                    analysis_platform_id = platform.get("analysisPlatformId")

                    # 初始化平台资产数据
                    if platform_name not in platform_assets:
                        platform_assets[platform_name] = {
                            "protocol": platform_name,
                            "total_assets": 0.0,  # 总资产价值
                            "total_debts": 0.0,  # 总负债价值
                            "leverage": 0.0,  # 杠杆率
                            "positions": [],  # 该平台的所有头寸
                        }

                    # 获取平台详细信息
                    try:
                        platform_detail_payload = {
                            "analysisPlatformId": analysis_platform_id,
                            "accountIdInfoList": [
                                {
                                    "walletAddressList": [
                                        {
                                            "chainId": 1,
                                            "walletAddress": address,
                                        }
                                    ]
                                }
                            ],
                        }

                        platform_detail_data = await self._okx_request(
                            "POST",
                            "/user/asset/platform/detail",
                            platform_detail_payload,
                        )

                        if "data" in platform_detail_data:
                            wallet_details = platform_detail_data["data"].get(
                                "walletIdPlatformDetailList", []
                            )

                            for wallet_detail in wallet_details:
                                network_holds = wallet_detail.get(
                                    "networkHoldVoList", []
                                )

                                for network_hold in network_holds:
                                    network = network_hold.get("network")
                                    chain_id = network_hold.get("chainId")
                                    # 总资产
                                    total_assets = network_hold.get("totalAssert", 0)
                                    # 总负债
                                    total_debts = 0
                                    # 投资品
                                    invest_tokens = network_hold.get(
                                        "investTokenBalanceVoList", []
                                    )

                                    for invest_token in invest_tokens:
                                        invest_type = invest_token.get("investType", 1)
                                        investment_name = invest_token.get(
                                            "investmentName", ""
                                        )
                                        total_value = float(
                                            invest_token.get("totalValue", "0")
                                        )
                                        # 创建头寸对象
                                        position = PlatformAsset(
                                            protocol=platform_name,
                                            asset=investment_name,
                                            tokenList=[],
                                            amount=total_value,
                                            invest_type=invest_type,
                                            apy=None,
                                        )
                                        if invest_type == 2:
                                            # 流动性池
                                            positionList = invest_token.get(
                                                "positionList", []
                                            )
                                            for position in positionList:
                                                assets = position.get("assets", [])
                                                for asset in assets:
                                                    tokenSymbol = asset.get(
                                                        "tokenSymbol", ""
                                                    )
                                                    tokenLogo = asset.get(
                                                        "tokenLogo", ""
                                                    )
                                                    coinAmount = asset.get(
                                                        "coinAmount", ""
                                                    )
                                                    currencyAmount = asset.get(
                                                        "currencyAmount", ""
                                                    )
                                                    tokenPrecision = asset.get(
                                                        "tokenPrecision", ""
                                                    )
                                                    tokenAddress = asset.get(
                                                        "tokenAddress", ""
                                                    )
                                                    network = asset.get("network", "")
                                                    position.tokenList.append(
                                                        {
                                                            "tokenSymbol": tokenSymbol,
                                                            "tokenLogo": tokenLogo,
                                                            "coinAmount": coinAmount,
                                                            "currencyAmount": currencyAmount,
                                                            "tokenPrecision": tokenPrecision,
                                                            "tokenAddress": tokenAddress,
                                                            "network": network,
                                                        }
                                                    )
                                        else:
                                            assets = invest_token.get(
                                                "assetsTokenList", []
                                            )
                                            for asset in assets:
                                                tokenSymbol = asset.get(
                                                    "tokenSymbol", ""
                                                )
                                                tokenLogo = asset.get("tokenLogo", "")
                                                coinAmount = asset.get("coinAmount", "")
                                                currencyAmount = asset.get(
                                                    "currencyAmount", ""
                                                )
                                                tokenPrecision = asset.get(
                                                    "tokenPrecision", ""
                                                )
                                                tokenAddress = asset.get(
                                                    "tokenAddress", ""
                                                )
                                                network = asset.get("network", "")
                                                position.tokenList.append(
                                                    {
                                                        "tokenSymbol": tokenSymbol,
                                                        "tokenLogo": tokenLogo,
                                                        "coinAmount": coinAmount,
                                                        "currencyAmount": currencyAmount,
                                                        "tokenPrecision": tokenPrecision,
                                                        "tokenAddress": tokenAddress,
                                                        "network": network,
                                                    }
                                                )
                                            rewardDefitokeninfo = invest_token.get(
                                                "rewardDefiTokenInfo", []
                                            )[0]
                                            baseDefiTokenInfos = (
                                                rewardDefitokeninfo.get(
                                                    "baseDefiTokenInfos", []
                                                )
                                            )
                                            for reward in baseDefiTokenInfos:
                                                tokenSymbol = reward.get(
                                                    "tokenSymbol", ""
                                                )
                                                tokenLogo = reward.get("tokenLogo", "")
                                                coinAmount = reward.get(
                                                    "coinAmount", ""
                                                )
                                                currencyAmount = reward.get(
                                                    "currencyAmount", ""
                                                )
                                                tokenPrecision = reward.get(
                                                    "tokenPrecision", ""
                                                )
                                                tokenAddress = reward.get(
                                                    "tokenAddress", ""
                                                )
                                                network = reward.get("network", "")
                                                position.tokenList.append(
                                                    {
                                                        "tokenSymbol": tokenSymbol,
                                                        "tokenType": "reward",
                                                        "tokenLogo": tokenLogo,
                                                        "coinAmount": coinAmount,
                                                        "currencyAmount": currencyAmount,
                                                        "tokenPrecision": tokenPrecision,
                                                        "tokenAddress": tokenAddress,
                                                        "network": network,
                                                    }
                                                )

                                        # 更新平台资产统计
                                        if invest_type == 6:  # 借贷
                                            platform_assets[platform_name][
                                                "total_debts"
                                            ] += total_value
                                        else:  # 其他类型都计入总资产
                                            platform_assets[platform_name][
                                                "total_assets"
                                            ] += total_value

                                        # 添加到平台头寸列表
                                        platform_assets[platform_name][
                                            "positions"
                                        ].append(position)
                            # 计算每个平台的杠杆率
                            total_assets = platform_assets[platform_name][
                                "total_assets"
                            ]
                            total_debts = platform_assets[platform_name]["total_debts"]
                            leverage = (
                                total_assets / (total_assets - total_debts)
                                if total_debts < total_assets and total_assets > 0
                                else 0
                            )
                            platform_assets[platform_name]["leverage"] = leverage
                            # 尝试从DefiLlama获取额外信息并更新头寸
                            try:
                                # 更新OKX头寸的APY和其他信息
                                for position in platform_assets[platform_name][
                                    "positions"
                                ]:
                                    defi_llama_pools = await self.get_defi_llama_pools(
                                        position.protocol, position.asset
                                    )
                                    if defi_llama_pools:
                                        position.apy = defi_llama_pools

                                self.logger.info(f"已使用DefiLlama数据更新OKX头寸信息")
                            except Exception as e:
                                self.logger.error(
                                    f"使用DefiLlama数据更新OKX头寸时出错: {e}"
                                )
                    except Exception as e:
                        self.logger.error(f"获取平台 {platform_name} 详情时出错: {e}")

                # 将平台资产数据添加到总列表
                for platform_name, platform_data in platform_assets.items():
                    positionAll.append(platform_data)

            self.logger.info(f"成功获取到 {len(positionAll)} 个平台的头寸数据")
            return positionAll

        except Exception as e:
            self.logger.error(f"获取OKX头寸时出错: {e}")
            return []

    async def get_defi_llama_pools(self, protocol: str, symbol: str) -> float:
        """使用DefiLlama API获取DeFi协议池的最新数据

        Args:
            protocol: 协议名称
            symbol: 资产名称

        Returns:
            float: DeFi池的APY
        """
        try:
            logger.info(f"使用DefiLlama API获取{protocol}协议的{symbol}池数据")
            rApy = 0

            # 使用缓存获取数据，避免频繁请求API
            cache_key = "defi_llama_pools"
            cache_interval = "1h"  # 使用1小时缓存

            # 检查缓存中是否有数据
            cached_pools = self.historical_data_cache.get(cache_key, cache_interval)

            if cached_pools is not None:
                logger.info("从缓存获取DefiLlama池数据")
                pools = cached_pools
            else:
                logger.info("从DefiLlama API获取池数据")
                # 创建DefiLlama客户端并获取池数据
                pools = self.defi_llama_client.get_pools()

                # 将数据存入缓存
                self.historical_data_cache.set(cache_key, pools, cache_interval)
                logger.info(f"已将{len(pools)}个池数据存入缓存")

            # 处理池数据
            for pool in pools.get("data", []):
                if (
                    pool.get("chain") == "Ethereum"
                    and protocol.lower() == pool.get("protocol", "").lower()
                ):
                    pool_symbol = pool.get("symbol", "")
                    # 添加检查，确保apy不为None
                    apy = pool.get("apy")
                    if apy is not None and symbol.lower() in pool_symbol.lower():
                        rApy = apy
                        break

            logger.info(f"获取到{protocol}协议{symbol}资产的APY: {rApy}")
            return rApy
        except Exception as e:
            logger.error(f"获取DefiLlama池数据时出错: {e}")
            return 0.0

    async def _get_24h_data(
        self,
        asset: str,
    ) -> Optional[Dict]:
        """
        获取24小时行情数据 (已弃用)

        注意：该方法已被弃用，应直接使用_get_coingecko_24h_data方法获取数据。
        保留此方法只是为了向后兼容。

        Args:
            asset: 资产名称或代币符号

        Returns:
            Optional[Dict]: 包含24小时行情数据的字典，如果获取失败则返回None
        """
        self.logger.warning(
            f"_get_24h_data方法已弃用，正在重定向到_get_coingecko_24h_data方法获取{asset}的数据"
        )

        # 直接调用CoinGecko方法
        return await self._get_coingecko_24h_data(asset)

    def _normalize_asset_symbol(self, asset: str) -> str:
        """
        将资产名称标准化为Binance交易对符号

        Args:
            asset: 资产名称或代币符号

        Returns:
            str: 标准化后的交易对符号
        """
        # 移除空格并转为大写
        asset = asset.strip().upper()

        # 常见稳定币和主流代币的映射
        common_assets = {
            "ETH": "ETHUSDT",
            "ETHEREUM": "ETHUSDT",
            "BTC": "BTCUSDT",
            "BITCOIN": "BTCUSDT",
            "USDC": "USDCUSDT",
            "USDT": "USDTBUSD",  # USDT本身通常不与USDT交易
            "DAI": "DAIUSDT",
            "BNB": "BNBUSDT",
            "SOL": "SOLUSDT",
            "MATIC": "MATICUSDT",
            "POLYGON": "MATICUSDT",
            "AVAX": "AVAXUSDT",
            "AVALANCHE": "AVAXUSDT",
            "DOT": "DOTUSDT",
            "POLKADOT": "DOTUSDT",
            "ADA": "ADAUSDT",
            "CARDANO": "ADAUSDT",
            "LINK": "LINKUSDT",
            "CHAINLINK": "LINKUSDT",
            "UNI": "UNIUSDT",
            "UNISWAP": "UNIUSDT",
            "AAVE": "AAVEUSDT",
            "SUSHI": "SUSHIUSDT",
            "SUSHISWAP": "SUSHIUSDT",
            "COMP": "COMPUSDT",
            "COMPOUND": "COMPUSDT",
            "MKR": "MKRUSDT",
            "MAKER": "MKRUSDT",
            "CRV": "CRVUSDT",
            "CURVE": "CRVUSDT",
            "SNX": "SNXUSDT",
            "SYNTHETIX": "SNXUSDT",
            "YFI": "YFIUSDT",
            "YEARN": "YFIUSDT",
            "1INCH": "1INCHUSDT",
        }

        # 检查是否是常见资产
        if asset in common_assets:
            return common_assets[asset]

        # 处理封装代币
        wrapped_tokens = {
            "WETH": "ETHUSDT",
            "WBTC": "BTCUSDT",
            "WBNB": "BNBUSDT",
            "WMATIC": "MATICUSDT",
            "WAVAX": "AVAXUSDT",
        }

        if asset in wrapped_tokens:
            self.logger.info(f"将封装代币 {asset} 映射到 {wrapped_tokens[asset]}")
            return wrapped_tokens[asset]

        # 处理LP代币和复合代币
        if "/" in asset or "-" in asset or "LP" in asset:
            self.logger.info(f"检测到LP代币或复合代币: {asset}")
            # 尝试提取基础代币
            parts = asset.replace("-", "/").split("/")
            if len(parts) >= 2:
                # 尝试获取第一个代币的价格
                base_token = parts[0].strip()
                self.logger.info(f"尝试使用基础代币 {base_token} 的价格")
                if base_token in common_assets:
                    return common_assets[base_token]
                # 如果第一个代币不是常见代币，尝试第二个
                if len(parts) > 1 and parts[1].strip() in common_assets:
                    return common_assets[parts[1].strip()]

        # 处理合成代币和衍生品
        synthetic_tokens = {
            "SETH": "ETHUSDT",  # 合成ETH
            "SBTC": "BTCUSDT",  # 合成BTC
            "CETH": "ETHUSDT",  # Compound ETH
            "CBTC": "BTCUSDT",  # Compound BTC
            "STETH": "ETHUSDT",  # Staked ETH
            "RETH": "ETHUSDT",  # Rocket Pool ETH
            "FRXETH": "ETHUSDT",  # Frax ETH
        }

        if asset in synthetic_tokens:
            self.logger.info(f"将合成代币 {asset} 映射到 {synthetic_tokens[asset]}")
            return synthetic_tokens[asset]

        # 如果是以ETH结尾，可能是ETH交易对
        if asset.endswith("ETH") and asset != "ETH":
            base_token = asset[:-3]
            self.logger.info(f"检测到ETH交易对: {asset}，尝试转换为USDT交易对")
            return f"{base_token}USDT"

        # 如果是以BTC结尾，可能是BTC交易对
        if asset.endswith("BTC") and asset != "BTC":
            base_token = asset[:-3]
            self.logger.info(f"检测到BTC交易对: {asset}，尝试转换为USDT交易对")
            return f"{base_token}USDT"

        # 默认添加USDT后缀
        self.logger.info(f"未识别的代币 {asset}，默认添加USDT后缀")
        return f"{asset}USDT"

    async def get_asset_historical_data(self, asset: str) -> Optional[pd.DataFrame]:
        """
        获取资产的历史数据

        Args:
            asset: 资产名称

        Returns:
            历史数据
        """
        # 在get_asset_historical_data方法中添加
        try:
            # 尝试从CoinGecko获取数据
            coingecko_data = await self.get_coingecko_historical_data(asset)
            if coingecko_data is not None and not coingecko_data.empty:
                self.logger.info(f"使用CoinGecko获取{asset}的历史数据")
                return coingecko_data
        except Exception as e:
            self.logger.warning(
                f"从CoinGecko获取{asset}的历史数据失败: {e}，尝试使用Binance数据"
            )
        # try:
        #     # 检查缓存
        #     cache_key = f"historical_data_{asset}"
        #     cache_interval = "1h"
        #     cached_data = self.historical_data_cache.get(cache_key, cache_interval)

        #     if cached_data is not None:
        #         self.logger.info(f"从缓存获取{asset}的历史数据")
        #         return cached_data

        #     asset = self._normalize_asset_symbol(asset)

        #     """从Binance API获取历史数据"""
        #     url = "https://api.binance.com/api/v3/klines"
        #     # 计算时间范围（过去30天）
        #     end_time = int(datetime.now().timestamp() * 1000)
        #     start_time = end_time - (30 * 24 * 60 * 60 * 1000)  # 30天的毫秒数

        #     # 设置请求参数
        #     params = {
        #         "symbol": asset,
        #         "interval": "1d",  # 1天的K线
        #         "startTime": start_time,
        #         "endTime": end_time,
        #         "limit": 30,  # 最多30个数据点
        #     }

        #     try:
        #         response = requests.get(url, params=params, proxies=proxies)
        #         if response.status_code == 200:
        #             data = response.json()

        #             if not data:
        #                 logger.warning(f"Binance返回的{asset}数据为空")
        #                 return None

        #             # 创建DataFrame
        #             # Binance K线数据格式:
        #             # [
        #             #   [
        #             #     开盘时间,
        #             #     开盘价,
        #             #     最高价,
        #             #     最低价,
        #             #     收盘价,
        #             #     成交量,
        #             #     收盘时间,
        #             #     成交额,
        #             #     成交笔数,
        #             #     主动买入成交量,
        #             #     主动买入成交额,
        #             #     忽略
        #             #   ]
        #             # ]
        #             df = pd.DataFrame(
        #                 {
        #                     "timestamp": [
        #                         datetime.fromtimestamp(k[0] / 1000) for k in data
        #                     ],
        #                     "price": [float(k[4]) for k in data],  # 使用收盘价
        #                     "volume": [float(k[5]) for k in data],
        #                     "market_cap": [None] * len(data),  # Binance不提供市值数据
        #                 }
        #             )
        #             df["source"] = "binance"
        #             # 存入缓存
        #             self.historical_data_cache.set(cache_key, df, cache_interval)
        #             return df
        #         else:
        #             logger.error(f"Binance API返回错误: {response.status}")
        #             # 返回默认数据
        #             df = pd.DataFrame(
        #                 {
        #                     "timestamp": [],
        #                     "price": [],
        #                     "volume": [],
        #                     "market_cap": [],
        #                     "source": [],
        #                 }
        #             )
        #             return df

        #     except Exception as e:
        #         logger.error(f"获取{asset}历史数据失败: {str(e)}")
        #         return None

        #     return data
        # except Exception as e:
        #     self.logger.error(f"获取资产历史数据失败: {str(e)}")
        #     return {}

    # 获取 get_protocol 作缓存
    async def get_protocol(self, protocol: str) -> float:
        """
        获取协议的详细信息

        Args:
            protocol: 协议名称

        Returns:
            协议的详细信息
        """
        try:
            # 检查缓存
            cache_key = f"protocol_{protocol}"
            cache_interval = "1h"
            cached_protocol = self.historical_data_cache.get(cache_key, cache_interval)

            if cached_protocol is not None:
                self.logger.info(f"从缓存获取{protocol}的详细信息")
                return cached_protocol

            if protocol == "Pendle V2":
                protocol = "Pendle"
            if protocol == "Aethir":
                protocol = "aethir"
            protocol = self.defi_llama_client.get_protocol(protocol)
            self.historical_data_cache.set(cache_key, protocol, cache_interval)
            return protocol
        except Exception as e:
            self.logger.error(f"获取协议的详细信息失败: {str(e)}")
            return 0.0

    async def get_protocol_tvl(self, protocol: str) -> float:
        """
        获取协议的TVL

        Args:
            protocol: 协议名称

        Returns:
            TVL（USD）
        """
        try:
            # 检查缓存
            cache_key = f"protocol_tvl_{protocol}"
            cache_interval = "1h"
            cached_tvl = self.historical_data_cache.get(cache_key, cache_interval)

            if cached_tvl is not None:
                self.logger.info(f"从缓存获取{protocol}的TVL数据")
                return cached_tvl

            if protocol == "Pendle V2":
                protocol = "Pendle"

            if protocol == "Aethir":
                protocol = "aethir"

            # 这里应该调用DeFiLlama或类似的API
            tvl = self.defi_llama_client.get_protocol_current_tvl(protocol)

            # 存入缓存
            self.historical_data_cache.set(cache_key, tvl, cache_interval)

            return tvl
        except Exception as e:
            self.logger.error(f"获取协议TVL失败: {str(e)}")
            return 0.0

    async def get_protocol_historical_tvl(self, protocol: str) -> List[Dict[str, Any]]:
        """
        获取协议的历史TVL数据

        Args:
            protocol: 协议名称

        Returns:
            历史TVL数据列表
        """
        try:
            # 检查缓存
            cache_key = f"historical_tvl_{protocol}"
            cache_interval = "1d"
            cached_data = self.historical_data_cache.get(cache_key, cache_interval)

            if cached_data is not None:
                self.logger.info(f"从缓存获取{protocol}的历史TVL数据")
                return cached_data

            # 获取协议数据
            protocol_data = await self.get_protocol(protocol)

            # 提取历史TVL数据
            historical_tvl = protocol_data.get("tvl", [])

            # 格式化数据为统一格式
            formatted_data = []
            for item in historical_tvl:
                formatted_data.append(
                    {
                        "date": datetime.fromtimestamp(item.get("date", 0)),
                        "tvl": item.get("totalLiquidityUSD", 0),
                    }
                )

            # 存入缓存
            self.historical_data_cache.set(cache_key, formatted_data, cache_interval)

            return formatted_data
        except Exception as e:
            self.logger.error(f"获取协议历史TVL失败: {str(e)}")
            return []

    async def get_protocol_audit_status(self, protocol: str) -> Dict[str, Any]:
        """
        获取协议的审计状态

        使用DefiLlama API获取协议的审计信息，包括审计次数、审计报告链接、
        是否开源等，并计算审计评分。

        Args:
            protocol: 协议名称或slug

        Returns:
            Dict: 包含审计状态信息的字典
        """
        try:
            # 检查缓存
            cache_key = f"protocol_audit_{protocol.lower()}"
            cache_interval = "1d"  # 使用1天缓存
            cached_data = self.historical_data_cache.get(cache_key, cache_interval)

            if cached_data is not None:
                self.logger.info(f"从缓存获取{protocol}的审计状态")
                return cached_data

            # 从DefiLlama API获取协议数据
            self.logger.info(f"从DefiLlama API获取{protocol}的审计状态")
            protocol_data = await self.get_protocol(protocol)

            if not protocol_data:
                self.logger.warning(f"DefiLlama API未返回{protocol}的数据")
                return {
                    "audited": False,
                    "audit_firms": [],
                    "last_audit_date": "",
                    "audit_score": 0,
                    "audit_count": 0,
                    "audit_links": [],
                    "is_open_source": False,
                    "github_repos": [],
                }

            # 提取审计相关信息
            protocol_name = protocol_data.get("name", protocol)
            audit_count_str = protocol_data.get("audits", "0")
            # 确保审计次数是整数
            try:
                audit_count = int(audit_count_str)
            except (ValueError, TypeError):
                audit_count = 0

            audit_links = protocol_data.get("audit_links", [])
            is_open_source = protocol_data.get("openSource", False)
            github_repos = protocol_data.get("github", [])
            listed_at = protocol_data.get("listedAt", 0)

            # 尝试推断最后审计日期
            last_audit_date = ""
            if listed_at:
                try:
                    # 使用上市日期作为参考
                    listed_date = datetime.fromtimestamp(listed_at)
                    # 假设审计在上市前1-3个月完成
                    estimated_audit_date = listed_date - timedelta(
                        days=random.randint(30, 90)
                    )
                    last_audit_date = estimated_audit_date.strftime("%Y-%m-%d")
                except Exception as e:
                    self.logger.warning(f"无法推断{protocol}的审计日期: {e}")

            # 计算审计评分
            # 基础分数：每次审计20分，最多60分
            base_score = min(60, audit_count * 20)

            # 开源加分：开源项目加20分
            open_source_score = 20 if is_open_source else 0

            # GitHub活跃度加分：有GitHub仓库加10分
            github_score = 10 if github_repos else 0

            # 审计链接加分：每个审计链接加5分，最多10分
            audit_links_score = min(10, len(audit_links) * 5)

            # 总分
            audit_score = (
                base_score + open_source_score + github_score + audit_links_score
            )

            # 推断审计机构
            audit_firms = []
            common_audit_firms = [
                "CertiK",
                "OpenZeppelin",
                "PeckShield",
                "Trail of Bits",
                "Quantstamp",
                "ChainSecurity",
                "ConsenSys Diligence",
                "Hacken",
                "SlowMist",
                "Omniscia",
                "ABDK",
            ]

            # 从审计链接中尝试推断审计机构
            for link in audit_links:
                for firm in common_audit_firms:
                    if firm.lower() in link.lower():
                        if firm not in audit_firms:
                            audit_firms.append(firm)

            # 如果无法推断，则使用默认值
            if not audit_firms and audit_count > 0:
                audit_firms = ["未知审计机构"]

            # 构建结果
            result = {
                "protocol": protocol_name,
                "audited": audit_count > 0,
                "audit_count": audit_count,
                "audit_firms": audit_firms,
                "last_audit_date": last_audit_date,
                "audit_score": audit_score,
                "audit_links": audit_links,
                "is_open_source": is_open_source,
                "github_repos": github_repos,
            }

            # 存入缓存
            self.historical_data_cache.set(cache_key, result, cache_interval)

            self.logger.info(
                f"成功获取{protocol}的审计状态: 审计次数={audit_count}, 评分={audit_score}"
            )
            return result

        except Exception as e:
            self.logger.error(f"获取协议审计状态失败: {str(e)}")
            return {
                "audited": False,
                "audit_firms": [],
                "last_audit_date": "",
                "audit_score": 0,
                "audit_count": 0,
                "audit_links": [],
                "is_open_source": False,
                "github_repos": [],
            }

    async def analyze_protocol_risk(self, protocol: str) -> RiskAnalysisResult:
        """
        分析协议的风险指标

        Args:
            protocol: 协议名称

        Returns:
            RiskAnalysisResult: 协议的风险分析结果
        """
        try:
            # 获取完整的协议数据
            protocol_data = await self.get_protocol(protocol)

            # 提取基本信息
            protocol_name = protocol_data.get("name", protocol)
            protocol_category = protocol_data.get("category", "未知")
            protocol_chains = protocol_data.get("chains", [])

            # 获取当前TVL
            tvl = protocol_data.get("tvl", [])[0].get("totalLiquidityUSD", 0)
            # 获取历史TVL数据
            historical_tvl = protocol_data.get("tvl", [])
            formatted_data = []
            for item in historical_tvl:
                formatted_data.append(
                    {
                        "date": datetime.fromtimestamp(item.get("date", 0)),
                        "tvl": item.get("totalLiquidityUSD", 0),
                    }
                )
            historical_tvl = formatted_data

            # 提取审计信息
            audit_count = int(protocol_data.get("audits", 0))
            audit_links = protocol_data.get("audit_links", [])
            is_open_source = protocol_data.get("openSource", False)

            # 计算TVL稳定性
            tvl_stability = 0
            if historical_tvl and len(historical_tvl) > 7:  # 至少需要一周的数据
                recent_tvl = [item.get("tvl", 0) for item in historical_tvl[-30:]]
                if len(recent_tvl) > 0 and sum(recent_tvl) > 0:
                    tvl_std = np.std(recent_tvl)
                    tvl_mean = np.mean(recent_tvl)
                    tvl_stability = 1 - min(1, tvl_std / tvl_mean)

            # 构建审计状态
            audit_status = {
                "audited": audit_count > 0,
                "audit_count": audit_count,
                "audit_links": audit_links,
                "open_source": is_open_source,
                "audit_score": min(
                    100, audit_count * 20 + (50 if is_open_source else 0)
                ),  # 每次审计20分，开源50分，最高100分
            }

            # 根据各项指标计算综合风险评分
            risk_score = 0
            max_score = 0

            # TVL因素 (TVL越高，风险越低)
            if tvl > 0:
                tvl_score = min(5, np.log10(tvl) - 5)  # 假设TVL在1亿以上为低风险
                risk_score += tvl_score
                max_score += 5

            # TVL稳定性因素
            if tvl_stability > 0:
                stability_score = tvl_stability * 3
                risk_score += stability_score
                max_score += 3

            # 审计因素
            if audit_status.get("audited", False):
                audit_score = audit_status.get("audit_score", 0) / 20  # 满分5分
                risk_score += audit_score
                max_score += 5

            # 多链部署因素 (部署在多条链上可能增加风险面)
            chain_count = len(protocol_chains)
            if chain_count > 0:
                # 1-2条链较为安全，过多可能增加风险
                chain_factor = 2 if chain_count <= 2 else (1 if chain_count <= 5 else 0)
                risk_score += chain_factor
                max_score += 2

            # 开源因素
            if is_open_source:
                risk_score += 2
                max_score += 2

            # 规范化风险分数 (0-100，越高表示风险越低)
            normalized_risk_score = 0
            if max_score > 0:
                normalized_risk_score = (risk_score / max_score) * 100

            # 风险等级
            risk_level = "高"
            if normalized_risk_score >= 80:
                risk_level = "极低"
            elif normalized_risk_score >= 60:
                risk_level = "低"
            elif normalized_risk_score >= 40:
                risk_level = "中"
            elif normalized_risk_score >= 20:
                risk_level = "高"

            return RiskAnalysisResult(
                asset_id=protocol_name,
                risk_score=normalized_risk_score,
                risk_level=risk_level,
                metrics=RiskMetrics(
                    tvl_stability=tvl_stability * 100,
                    audit_score=audit_status.get("audit_score", 0),
                    market_cap=tvl,
                ),
                analysis=RiskAnalysis(
                    tvl_factor=f"TVL为{tvl:,.2f}美元，"
                    + (
                        "较高"
                        if tvl > 100000000
                        else "中等" if tvl > 10000000 else "较低"
                    ),
                    stability_factor=f"TVL稳定性为{tvl_stability*100:.2f}%，"
                    + (
                        "很稳定"
                        if tvl_stability > 0.8
                        else "较稳定" if tvl_stability > 0.5 else "波动较大"
                    ),
                    audit_factor=f"{'已通过' + str(audit_count) + '次专业审计' if audit_status.get('audited', False) else '未经专业审计或缺乏审计信息'}，{'且代码开源' if is_open_source else '代码未开源'}",
                    chain_factor=f"部署在{chain_count}条链上，"
                    + ("风险分散" if chain_count <= 2 else "增加了一定的风险面"),
                ),
                recommendations=[
                    f"综合评估，{protocol_name}协议的风险等级为{risk_level}，"
                    + (
                        "建议可以适量配置"
                        if normalized_risk_score >= 60
                        else (
                            "建议谨慎参与"
                            if normalized_risk_score >= 40
                            else "建议避免参与或严格控制仓位"
                        )
                    ),
                ],
                raw_data={"protocol_data": protocol_data},
            )
        except Exception as e:
            self.logger.error(f"分析协议风险失败: {str(e)}")
            return RiskAnalysisResult(
                asset_id=protocol,
                risk_score=0,
                risk_level="未知",
                metrics=RiskMetrics(),
                analysis=RiskAnalysis(),
                error=f"分析协议风险时出错: {str(e)}",
            )

    async def _calculate_lp_token_price(
        self, token_address: str, token_symbol: str = None
    ) -> float:
        """
        计算LP代币价格

        Args:
            token_address: LP代币合约地址
            token_symbol: LP代币符号，格式如 "TOKEN1/TOKEN2"

        Returns:
            LP代币估算价格
        """
        try:
            self.logger.info(f"计算LP代币价格: {token_symbol or token_address}")

            # 如果提供了符号，尝试从符号解析
            if token_symbol:
                # 解析LP代币符号
                parts = token_symbol.replace("-", "/").split("/")
                if len(parts) >= 2:
                    token1, token2 = parts[0].strip(), parts[1].strip()

                    # 获取两个代币的价格
                    price1 = await self.get_token_price(token1)
                    price2 = await self.get_token_price(token2)

                    # 简单估算：假设LP代币价值是两个代币价格的加权平均
                    # 实际情况下，应该考虑池中的代币比例和总流动性
                    estimated_price = (price1 + price2) / 2

                    self.logger.info(
                        f"LP代币 {token_symbol} 估算价格: {estimated_price}"
                    )
                    return estimated_price

            # 如果没有符号或符号解析失败，尝试从链上获取信息
            # 这里需要实现与特定DEX交互的逻辑，如Uniswap、SushiSwap等
            # 由于需要与特定合约交互，这部分代码较为复杂

            # 示例：尝试识别常见DEX的LP代币
            if token_address.startswith("0x"):
                # 检查是否是已知的LP代币合约
                known_lp_tokens = {
                    # Uniswap V2 LP代币
                    "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc": {
                        "name": "USDC/ETH",
                        "token0": "USDC",
                        "token1": "ETH",
                    },
                    # 添加更多已知的LP代币
                }

                if token_address.lower() in known_lp_tokens:
                    lp_info = known_lp_tokens[token_address.lower()]
                    price0 = await self.get_token_price(lp_info["token0"])
                    price1 = await self.get_token_price(lp_info["token1"])

                    # 简单估算
                    estimated_price = (price0 + price1) / 2
                    self.logger.info(
                        f"已知LP代币 {lp_info['name']} 估算价格: {estimated_price}"
                    )
                    return estimated_price

            # 如果无法计算，返回默认值
            self.logger.warning(
                f"无法计算LP代币 {token_symbol or token_address} 的价格，使用默认值"
            )
            return 1.0

        except Exception as e:
            self.logger.error(f"计算LP代币价格失败: {str(e)}")
            return 1.0

    async def get_wallet_alerts(
        self, wallet_address: str, positions: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取钱包相关的警报，使用CoinGecko数据增强风险分析

        注意：该方法已完全适配CoinGecko数据源，直接使用_get_coingecko_24h_data方法获取市场数据，
        不再使用原有的_get_24h_data方法。
        """
        try:
            self.logger.info(f"获取钱包 {wallet_address} 的警报")

            # 如果没有提供头寸，则获取钱包头寸
            if positions is None:
                positions = await self.get_all_positions(wallet_address)

            if not positions:
                self.logger.info(f"钱包 {wallet_address} 没有头寸，无法生成警报")
                return []

            # 提取头寸中的资产和协议
            assets = {}
            protocols = set()
            for position in positions:
                asset = position.get("asset", "unknown")
                protocol = position.get("protocol", "unknown")
                usd_value = float(position.get("usd_value", 0))
                leverage = float(position.get("leverage", 1.0))
                apy = float(position.get("apy", 0))

                if asset in assets:
                    assets[asset] += usd_value
                else:
                    assets[asset] = usd_value

                protocols.add(protocol)

            # 初始化警报列表
            alerts = []

            # 1. 检查资产价格波动
            for asset in assets:
                try:
                    # 获取24小时数据 - 直接使用CoinGecko数据
                    data_24h = await self._get_coingecko_24h_data(asset)
                    if data_24h:
                        # 计算价格波动率
                        price_change = data_24h.get("price_change_percent", 0)
                        current_price = data_24h.get("price", 0)
                        previous_price = current_price / (1 + price_change / 100)

                        # 根据波动率确定警报级别
                        severity = "info"
                        if abs(price_change) > 10:
                            severity = "critical"
                        elif abs(price_change) > 5:
                            severity = "warning"

                        # 生成价格波动警报
                        if abs(price_change) > 3:  # 只有波动超过3%才生成警报
                            direction = "上涨" if price_change > 0 else "下跌"
                            alerts.append(
                                {
                                    "id": f"price-{asset}-{int(datetime.now().timestamp())}",
                                    "type": "price_volatility",
                                    "severity": severity,
                                    "protocol": "",
                                    "asset": asset,
                                    "message": f"{asset}价格24小时{direction} {abs(price_change):.1f}%，当前价格 ${current_price:.2f}",
                                    "timestamp": datetime.now().isoformat(),
                                    "details": {
                                        "current_price": current_price,
                                        "previous_price": previous_price,
                                        "price_change_24h": price_change,
                                        "volatility": abs(price_change),
                                        "data_source": "CoinGecko",
                                    },
                                }
                            )
                except Exception as e:
                    self.logger.error(f"获取{asset}价格数据失败: {str(e)}")

            # 2. 检查杠杆风险
            for position in positions:
                if position.get("leverage", 1.0) > 2.0:
                    asset = position.get("asset", "unknown")
                    protocol = position.get("protocol", "unknown")
                    leverage = float(position.get("leverage", 1.0))

                    # 根据杠杆率确定风险级别
                    severity = "info"
                    if leverage > 5:
                        severity = "critical"
                    elif leverage > 3:
                        severity = "warning"

                    # 估算清算价格（简化计算）
                    current_price = 0
                    try:
                        # 直接使用CoinGecko数据
                        data_24h = await self._get_coingecko_24h_data(
                            asset.split("-")[0]
                        )
                        if data_24h:
                            current_price = data_24h.get("price", 0)
                    except Exception as e:
                        self.logger.error(
                            f"获取{asset}价格数据失败用于清算价格计算: {str(e)}"
                        )
                        pass

                    # 假设清算阈值为杠杆率的80%
                    liquidation_threshold = 0.8
                    liquidation_price = (
                        current_price * (1 - liquidation_threshold / leverage)
                        if current_price > 0
                        else 0
                    )

                    alerts.append(
                        {
                            "id": f"leverage-{protocol}-{asset}-{int(datetime.now().timestamp())}",
                            "type": "leverage_risk",
                            "severity": severity,
                            "protocol": protocol,
                            "asset": asset,
                            "message": f"{protocol}上的{asset}头寸使用了{leverage:.1f}倍杠杆，存在清算风险",
                            "timestamp": datetime.now().isoformat(),
                            "details": {
                                "leverage": leverage,
                                "safe_leverage": 2.0,
                                "current_price": current_price,
                                "liquidation_price": liquidation_price,
                                "risk_ratio": (
                                    (current_price - liquidation_price) / current_price
                                    if current_price > 0
                                    else 0
                                ),
                                "recommendation": "建议降低杠杆或增加抵押以降低清算风险",
                            },
                        }
                    )

            # 3. 检查协议风险
            for protocol in protocols:
                try:
                    # 获取协议风险摘要
                    risk_summary = await self._get_protocol_risk_summary(protocol)
                    risk_level = risk_summary.get("risk_level", "medium")
                    risk_score = risk_summary.get("risk_score", 50)

                    # 根据风险等级确定警报级别
                    severity = "info"
                    if risk_level == "high":
                        severity = "critical"
                    elif risk_level == "medium":
                        severity = "warning"

                    # 只有中高风险才生成警报
                    if risk_level in ["medium", "high"]:
                        alerts.append(
                            {
                                "id": f"protocol-{protocol}-{int(datetime.now().timestamp())}",
                                "type": "protocol_risk",
                                "severity": severity,
                                "protocol": protocol,
                                "asset": "",
                                "message": f"{protocol}协议风险等级为{risk_level}，风险评分{risk_score}",
                                "timestamp": datetime.now().isoformat(),
                                "details": {
                                    "risk_score": risk_score,
                                    "risk_level": risk_level,
                                    "recommendation": risk_summary.get(
                                        "recommendation", "建议关注协议安全更新"
                                    ),
                                    "analysis": risk_summary.get("analysis", ""),
                                },
                            }
                        )
                except Exception as e:
                    self.logger.error(f"获取{protocol}协议风险数据失败: {str(e)}")

            # 4. 检查APY异常
            for position in positions:
                apy = float(position.get("apy", 0))
                if apy > 20:  # 高APY可能意味着高风险
                    asset = position.get("asset", "unknown")
                    protocol = position.get("protocol", "unknown")

                    # 根据APY确定风险级别
                    severity = "info"
                    if apy > 50:
                        severity = "critical"
                    elif apy > 30:
                        severity = "warning"

                    alerts.append(
                        {
                            "id": f"apy-{protocol}-{asset}-{int(datetime.now().timestamp())}",
                            "type": "high_apy",
                            "severity": severity,
                            "protocol": protocol,
                            "asset": asset,
                            "message": f"{protocol}上的{asset}头寸APY异常高({apy:.1f}%)，可能存在风险",
                            "timestamp": datetime.now().isoformat(),
                            "details": {
                                "current_apy": apy,
                                "average_apy": 5.0,  # 假设的行业平均APY
                                "recommendation": "高收益通常伴随高风险，建议谨慎评估",
                                "analysis": "异常高的APY可能意味着项目风险较高或处于早期阶段",
                            },
                        }
                    )

            # 添加新的风险检查

            # 5. 检查市值风险
            for asset in assets:
                try:
                    asset_risk = await self.analyze_asset_risk(asset)
                    if asset_risk.get("risk_level") in ["高风险", "中高风险"]:
                        alerts.append(
                            {
                                "id": f"market_cap-{asset}-{int(datetime.now().timestamp())}",
                                "type": "market_cap_risk",
                                "severity": "warning",
                                "protocol": "",
                                "asset": asset,
                                "message": f"{asset}市值风险较高: {asset_risk['analysis']['market_cap_analysis']}",
                                "timestamp": datetime.now().isoformat(),
                                "details": asset_risk,
                            }
                        )
                except Exception as e:
                    self.logger.error(f"分析{asset}市值风险失败: {str(e)}")

            # 6. 检查流动性风险
            for asset in assets:
                try:
                    data_24h = await self._get_coingecko_24h_data(asset)
                    if data_24h:
                        volume_to_mcap = data_24h.get("volume", 0) / data_24h.get(
                            "market_cap", 1
                        )
                        if volume_to_mcap < 0.01:  # 日交易量不到市值的1%
                            alerts.append(
                                {
                                    "id": f"liquidity-{asset}-{int(datetime.now().timestamp())}",
                                    "type": "liquidity_risk",
                                    "severity": "warning",
                                    "protocol": "",
                                    "asset": asset,
                                    "message": f"{asset}流动性风险较高，日交易量/市值比率{volume_to_mcap:.2%}",
                                    "timestamp": datetime.now().isoformat(),
                                    "details": {
                                        "volume_to_mcap": volume_to_mcap,
                                        "recommendation": "建议关注流动性风险，可能需要调整仓位",
                                    },
                                }
                            )
                except Exception as e:
                    self.logger.error(f"分析{asset}流动性风险失败: {str(e)}")

            # 如果没有生成任何警报，添加一个默认的"无警报"消息
            if not alerts:
                alerts.append(
                    {
                        "id": f"info-{int(datetime.now().timestamp())}",
                        "type": "info",
                        "severity": "info",
                        "protocol": "",
                        "asset": "",
                        "message": "当前没有检测到任何风险警报",
                        "timestamp": datetime.now().isoformat(),
                        "details": {
                            "recommendation": "继续保持良好的风险管理",
                        },
                    }
                )

            # 按照风险级别排序（critical->warning->info）
            severity_order = {"critical": 0, "warning": 1, "info": 2}
            alerts.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 3))

            self.logger.info(f"为钱包 {wallet_address} 生成了 {len(alerts)} 个警报")
            return alerts

        except Exception as e:
            self.logger.error(f"获取钱包警报失败: {str(e)}")
            return [{"error": f"获取警报时出错: {str(e)}"}]

    async def get_coingecko_historical_data(
        self, asset: str, days: int = 30
    ) -> Optional[pd.DataFrame]:
        """
        从CoinGecko API获取资产的历史数据

        Args:
            asset: 资产ID或符号
            days: 获取多少天的数据

        Returns:
            DataFrame: 包含历史数据的DataFrame
        """
        try:
            # 检查缓存
            cache_key = f"coingecko_historical_data_{asset}"
            cache_interval = "1h"
            cached_data = self.historical_data_cache.get(cache_key, cache_interval)

            if cached_data is not None:
                self.logger.info(f"从缓存获取{asset}的CoinGecko历史数据")
                return cached_data

            # 将通用符号转换为CoinGecko的ID
            coingecko_id = self._convert_to_coingecko_id(asset)
            if not coingecko_id:
                self.logger.warning(f"无法将{asset}转换为CoinGecko ID")
                return None

            # 构建API URL
            url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart"
            params = {"vs_currency": "usd", "days": days, "interval": "daily"}
            headers = {
                "accept": "application/json",
                "x-cg-demo-api-key": "CG-2TiEpWzWzfnpD5hnRzk4ufDg",
            }

            # 发送请求
            response = requests.get(
                url, params=params, headers=headers, proxies=proxies
            )

            if response.status_code == 200:
                data = response.json()

                # 提取数据
                prices = data.get("prices", [])
                market_caps = data.get("market_caps", [])
                volumes = data.get("total_volumes", [])

                # 创建时间戳列表
                timestamps = [datetime.fromtimestamp(p[0] / 1000) for p in prices]

                # 创建DataFrame
                df = pd.DataFrame(
                    {
                        "timestamp": timestamps,
                        "price": [p[1] for p in prices],
                        "volume": [v[1] for v in volumes],
                        "market_cap": [m[1] for m in market_caps],
                    }
                )

                df["source"] = "coingecko"

                # 存入缓存
                self.historical_data_cache.set(cache_key, df, cache_interval)

                return df
            else:
                self.logger.error(f"CoinGecko API返回错误: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"从CoinGecko获取{asset}历史数据失败: {str(e)}")
            return None

    def _convert_to_coingecko_id(self, asset: str) -> str:
        """将通用资产符号转换为CoinGecko ID，使用完整的代币列表"""
        # 检查缓存中是否有完整代币列表
        coins_list = self.historical_data_cache.get("coingecko_coins_list", "1d")

        if coins_list is None:
            # 如果缓存中没有，则获取完整列表
            try:
                url = "https://api.coingecko.com/api/v3/coins/list"
                response = requests.get(url, proxies=proxies)

                if response.status_code == 200:
                    coins_list = response.json()
                    # 缓存一天，避免频繁请求
                    self.historical_data_cache.set(
                        "coingecko_coins_list", coins_list, "1d"
                    )
                    self.logger.info(
                        f"成功获取CoinGecko完整代币列表，共{len(coins_list)}个代币"
                    )
                else:
                    self.logger.error(
                        f"获取CoinGecko代币列表失败: {response.status_code}"
                    )
                    coins_list = []
            except Exception as e:
                self.logger.error(f"获取CoinGecko代币列表失败: {str(e)}")
                coins_list = []

        # 标准化输入
        asset_normalized = asset.strip().lower()

        # 首先检查完全匹配的id
        for coin in coins_list:
            if coin.get("id") == asset_normalized:
                return coin.get("id")

        # 然后检查symbol的完全匹配
        exact_matches = [
            coin
            for coin in coins_list
            if coin.get("symbol").lower() == asset_normalized
        ]
        if exact_matches:
            # 如果有多个匹配，优先选择市值较高的主流代币
            if len(exact_matches) > 1:
                # 常见主流代币优先级
                priority_ids = [
                    "bitcoin",
                    "ethereum",
                    "tether",
                    "usd-coin",
                    "binancecoin",
                    "ripple",
                    "cardano",
                    "solana",
                    "dogecoin",
                    "polkadot",
                ]
                for priority_id in priority_ids:
                    for coin in exact_matches:
                        if coin.get("id") == priority_id:
                            return priority_id

                # 如果没有匹配到优先级列表，返回第一个匹配
                return exact_matches[0].get("id")
            else:
                return exact_matches[0].get("id")

        # 如果没有完全匹配，使用硬编码的映射作为后备
        fallback_mapping = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "usdt": "tether",
            "usdc": "usd-coin",
            "bnb": "binancecoin",
            "xrp": "ripple",
            "ada": "cardano",
            "sol": "solana",
            "doge": "dogecoin",
            "dot": "polkadot",
        }

        if asset_normalized in fallback_mapping:
            return fallback_mapping[asset_normalized]

        # 作为最后的尝试，查找部分匹配
        partial_matches = [
            coin
            for coin in coins_list
            if asset_normalized in coin.get("symbol").lower()
        ]
        if partial_matches:
            return partial_matches[0].get("id")

        # 如果所有尝试都失败，返回原始输入（可能导致API错误）
        self.logger.warning(f"无法将{asset}映射到CoinGecko ID，使用原始输入")
        return asset_normalized

    async def _get_coingecko_24h_data(self, asset: str) -> Optional[Dict]:
        """
        从CoinGecko API获取24小时行情数据

        Args:
            asset: 资产ID或符号

        Returns:
            Dict: 包含24小时行情数据的字典
        """
        try:
            # 检查缓存
            cache_key = f"coingecko_24h_data_{asset}"
            cache_interval = "5m"  # 5分钟缓存
            cached_data = self.historical_data_cache.get(cache_key, cache_interval)

            if cached_data is not None:
                self.logger.info(f"从缓存获取{asset}的CoinGecko 24小时数据")
                return cached_data

            # 将通用符号转换为CoinGecko的ID
            coingecko_id = self._convert_to_coingecko_id(asset)
            if not coingecko_id:
                self.logger.warning(f"无法将{asset}转换为CoinGecko ID")
                return None

            # 获取当前币种信息
            url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
            }

            headers = {
                "accept": "application/json",
                "x-cg-demo-api-key": "CG-2TiEpWzWzfnpD5hnRzk4ufDg",
            }

            response = requests.get(
                url, params=params, headers=headers, proxies=proxies
            )

            if response.status_code == 200:
                data = response.json()

                # 提取市场数据
                market_data = data.get("market_data", {})

                # 格式化数据
                formatted_data = {
                    "symbol": data.get("symbol", "").upper(),
                    "price": market_data.get("current_price", {}).get("usd", 0),
                    "price_change": market_data.get("price_change_24h", 0),
                    "price_change_percent": market_data.get(
                        "price_change_percentage_24h", 0
                    ),
                    "high_price": market_data.get("high_24h", {}).get("usd", 0),
                    "low_price": market_data.get("low_24h", {}).get("usd", 0),
                    "volume": market_data.get("total_volume", {}).get("usd", 0),
                    "market_cap": market_data.get("market_cap", {}).get("usd", 0),
                    "volatility": abs(
                        market_data.get("price_change_percentage_24h", 0)
                    ),
                    "last_updated": data.get("last_updated", ""),
                }

                # 将结果存入缓存
                self.historical_data_cache.set(
                    cache_key, formatted_data, cache_interval
                )

                return formatted_data
            else:
                self.logger.error(f"CoinGecko API返回错误: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"从CoinGecko获取{asset}的24小时数据失败: {str(e)}")
            return None

    async def analyze_asset_risk(self, asset: str) -> RiskAnalysisResult:
        """
        分析资产的风险指标，使用CoinGecko数据

        Args:
            asset: 资产符号或ID

        Returns:
            RiskAnalysisResult: 资产风险分析结果
        """
        try:
            # 获取24小时数据
            data_24h = await self._get_coingecko_24h_data(asset)
            if not data_24h:
                return RiskAnalysisResult(
                    asset_id=asset,
                    risk_score=0,
                    risk_level="未知",
                    metrics=RiskMetrics(),
                    analysis=RiskAnalysis(),
                    error=f"无法获取{asset}的市场数据",
                )

            # 获取历史数据
            historical_data = await self.get_coingecko_historical_data(asset)
            if historical_data is None or historical_data.empty:
                return RiskAnalysisResult(
                    asset_id=asset,
                    risk_score=0,
                    risk_level="未知",
                    metrics=RiskMetrics(),
                    analysis=RiskAnalysis(),
                    error=f"无法获取{asset}的历史数据",
                )

            # 1. 价格波动性分析
            price_volatility = historical_data["price"].pct_change().std() * 100

            # 2. 市值分析
            market_cap = data_24h.get("market_cap", 0)
            market_cap_rank = data_24h.get("market_cap_rank", 0)

            # 3. 流动性分析
            volume = data_24h.get("volume", 0)
            volume_to_mcap_ratio = volume / market_cap if market_cap > 0 else 0

            # 4. 价格趋势分析
            current_price = historical_data["price"].iloc[-1]
            price_ma7 = historical_data["price"].rolling(window=7).mean().iloc[-1]
            price_ma30 = historical_data["price"].rolling(window=30).mean().iloc[-1]

            # 5. 计算风险评分
            risk_score = 0
            max_score = 100

            # 市值风险 (30分)
            if market_cap > 10000000000:  # > 100亿
                risk_score += 30
            elif market_cap > 1000000000:  # > 10亿
                risk_score += 20
            elif market_cap > 100000000:  # > 1亿
                risk_score += 10

            # 流动性风险 (20分)
            if volume_to_mcap_ratio > 0.1:  # 日交易量超过市值的10%
                risk_score += 20
            elif volume_to_mcap_ratio > 0.05:  # 日交易量超过市值的5%
                risk_score += 10

            # 波动性风险 (20分)
            if price_volatility < 5:  # 波动率小于5%
                risk_score += 20
            elif price_volatility < 10:  # 波动率小于10%
                risk_score += 10

            # 趋势风险 (30分)
            if current_price > price_ma7 > price_ma30:  # 上升趋势
                risk_score += 30
            elif current_price > price_ma7:  # 短期上升
                risk_score += 20
            elif current_price > price_ma30:  # 长期上升
                risk_score += 10

            # 确定风险等级
            risk_level = "高风险"
            if risk_score >= 80:
                risk_level = "低风险"
            elif risk_score >= 60:
                risk_level = "中低风险"
            elif risk_score >= 40:
                risk_level = "中等风险"
            elif risk_score >= 20:
                risk_level = "中高风险"

            return RiskAnalysisResult(
                asset_id=asset,
                risk_score=risk_score,
                risk_level=risk_level,
                metrics=RiskMetrics(
                    price_volatility=price_volatility,
                    market_cap=market_cap,
                    market_cap_rank=market_cap_rank,
                    volume_to_mcap_ratio=volume_to_mcap_ratio,
                ),
                analysis=RiskAnalysis(
                    market_cap_analysis=f"市值{market_cap:,.0f}美元，排名第{market_cap_rank}位",
                    liquidity_analysis=f"日交易量/市值比率{volume_to_mcap_ratio:.2%}",
                    volatility_analysis=f"价格波动率{price_volatility:.2f}%",
                    trend_analysis=(
                        "上升趋势" if current_price > price_ma7 else "下降趋势"
                    ),
                ),
                recommendations=self._generate_risk_recommendations(
                    risk_score,
                    {
                        "price_volatility": price_volatility,
                        "market_cap": market_cap,
                        "market_cap_rank": market_cap_rank,
                        "volume_to_mcap_ratio": volume_to_mcap_ratio,
                        "price_trend": {
                            "current": current_price,
                            "ma7": price_ma7,
                            "ma30": price_ma30,
                        },
                    },
                ),
            )
        except Exception as e:
            self.logger.error(f"分析资产{asset}风险时出错: {str(e)}")
            return RiskAnalysisResult(
                asset_id=asset,
                risk_score=0,
                risk_level="未知",
                metrics=RiskMetrics(),
                analysis=RiskAnalysis(),
                error=f"风险分析失败: {str(e)}",
            )

    def _generate_risk_recommendations(
        self, risk_score: int, metrics: Dict[str, Any]
    ) -> List[str]:
        """
        根据风险评分和指标生成建议
        """
        recommendations = []

        # 基于市值
        if metrics.get("market_cap", 0) < 100000000:  # < 1亿
            recommendations.append("市值较小，建议控制仓位")

        # 基于流动性
        if metrics.get("volume_to_mcap_ratio", 0) < 0.01:
            recommendations.append("流动性较低，建议关注交易风险")

        # 基于波动性
        if metrics.get("price_volatility", 0) > 10:
            recommendations.append("价格波动较大，建议设置止损")

        # 基于趋势
        if metrics.get("price_trend", {}).get("current", 0) < metrics.get(
            "price_trend", {}
        ).get("ma30", 0):
            recommendations.append("处于下降趋势，建议谨慎操作")

        return recommendations

    async def get_defi_safety_rating(
        self, protocol_name: str, chain_id: str = None
    ) -> Dict[str, Any]:
        """获取DeFi Safety评级数据，支持版本和链筛选"""
        try:
            url = f"https://www.defisafety.com/api/pqrs?status=Active&title={protocol_name}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        if not result.get("data") or len(result["data"]) == 0:
                            return {
                                "pqr_score": 0,
                                "risk_assessment": "Not Found",
                                "source": "DeFi Safety",
                            }

                        # 找到最匹配的协议版本
                        protocol_data = None

                        # 如果提供了链ID，优先匹配该链上最新版本
                        if chain_id:
                            for item in result["data"]:
                                for chain_info in item.get("chain", []):
                                    if chain_info.get("chainID") == chain_id:
                                        if (
                                            not protocol_data
                                            or item["date"] > protocol_data["date"]
                                        ):
                                            protocol_data = item

                        # 如果没找到匹配链的协议或未提供链ID，选择最新版本
                        if not protocol_data:
                            protocol_data = max(
                                result["data"], key=lambda x: x.get("date", "")
                            )

                        return {
                            "pqr_score": protocol_data.get("finalScore", 0),
                            "protocol_version": protocol_data.get("title", "")
                            .replace(protocol_name, "")
                            .strip(),
                            "risk_assessment": (
                                "Low"
                                if protocol_data.get("finalScore", 0) >= 80
                                else (
                                    "Medium"
                                    if protocol_data.get("finalScore", 0) >= 60
                                    else "High"
                                )
                            ),
                            "last_updated": protocol_data.get("date"),
                            "supported_chains": [
                                chain["name"]
                                for chain in protocol_data.get("chain", [])
                            ],
                            "categories": protocol_data.get("categories", []),
                            "source": "DeFi Safety",
                            "url": protocol_data.get("url", ""),
                        }

                    return {
                        "pqr_score": 0,
                        "risk_assessment": "API Error",
                        "source": "DeFi Safety",
                    }
        except Exception as e:
            logger.error(f"获取DeFi Safety数据失败: {str(e)}")
            return {"pqr_score": 0, "risk_assessment": "Error", "source": "DeFi Safety"}

    async def analyze_protocol_security(
        self, protocol_name: str, chain_id: str = None
    ) -> RiskFactor:
        """分析协议安全风险，集成DeFi Safety数据"""
        try:
            # 获取DeFi Safety评级
            defi_safety_data = await self.get_defi_safety_rating(
                protocol_name, chain_id
            )

            # 基础风险评分 - DeFi Safety评分越高风险越低
            if defi_safety_data and defi_safety_data["pqr_score"] > 0:
                # 将DeFi Safety满分100转换为风险评分(100为无风险)
                base_risk_score = 100 - defi_safety_data["pqr_score"]

                # 数据新鲜度调整(数据越新可信度越高)
                from datetime import datetime

                data_age = (
                    datetime.now()
                    - datetime.strptime(defi_safety_data["last_updated"], "%Y-%m-%d")
                ).days
                freshness_factor = min(
                    1.0, max(0.7, 1 - (data_age / 365))
                )  # 数据超过1年老化到70%权重

                # 评分可信度调整
                confidence = 0.9 if defi_safety_data["pqr_score"] > 0 else 0.5

                # 构建风险描述
                description = f"{protocol_name} 安全评分: {defi_safety_data['pqr_score']}/100 ({defi_safety_data['risk_assessment']})"

                # 如果有版本信息，添加到描述
                if defi_safety_data.get("protocol_version"):
                    description += f", 版本: {defi_safety_data['protocol_version']}"

                description += f", 最后更新: {defi_safety_data['last_updated']}"

                # 添加数据来源参考
                description += f" (来源: DeFi Safety)"

                # 生成风险因子
                return self.create_risk_factor(
                    risk_type="SMART_CONTRACT",
                    factor_name="智能合约安全性",
                    score=base_risk_score,
                    confidence=confidence * freshness_factor,
                    weight=0.4,
                    description=description,
                    trend="稳定",
                    data_points=[
                        {
                            "protocol": protocol_name,
                            "safety_score": defi_safety_data["pqr_score"],
                            "risk_score": base_risk_score,
                            "last_updated": defi_safety_data["last_updated"],
                            "source": "DeFi Safety",
                        }
                    ],
                    metadata=defi_safety_data,
                )
        except Exception as e:
            logger.error(f"分析协议安全风险时出错: {str(e)}")
            # 使用后备方法...
