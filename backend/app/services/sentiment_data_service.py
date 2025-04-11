"""
情绪数据服务 - 负责从各种来源采集加密货币相关的情绪数据
"""

import logging
import asyncio
import aiohttp
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from dataclasses import dataclass, field
from cachetools import TTLCache
from twitter.account import Account
from pytrends.request import TrendReq
from twitter.search import Search
from pathlib import Path

logger = logging.getLogger("defi_risk.sentiment_data_service")


@dataclass
class SentimentSource:
    """情绪数据源定义"""

    name: str  # 数据源名称
    type: str  # 数据源类型: social, news, github, search
    weight: float  # 在最终情绪计算中的权重
    enabled: bool = True  # 是否启用该数据源
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class RawSentimentData:
    """原始情绪数据"""

    source: str  # 数据来源
    asset: str  # 相关资产
    timestamp: datetime  # 数据时间戳
    content: str  # 原始内容
    author: Optional[str] = None  # 作者/来源
    url: Optional[str] = None  # 原始内容URL
    engagement: Optional[Dict[str, int]] = None  # 互动数据 (点赞、评论等)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


class SentimentDataService:
    """情绪数据服务"""

    def __init__(self):
        """初始化情绪数据服务"""
        self.logger = logger
        self.sources = self._initialize_sources()
        self.cache = TTLCache(maxsize=1000, ttl=3600 * 3)  # 3小时缓存

        # 初始化各API客户端
        self.twitter_client = self._init_twitter_client()
        self.news_client = None  # 将在需要时初始化

        self.logger.info("情绪数据服务初始化完成")

    def _initialize_sources(self) -> Dict[str, SentimentSource]:
        """初始化数据源配置"""
        sources = {
            "twitter": SentimentSource(
                name="Twitter/X",
                type="social",
                weight=0.3,
                enabled=settings.ENABLE_TWITTER_API,
                metadata={"api_version": "v2"},
            ),
            "crypto_news": SentimentSource(
                name="Crypto News",
                type="news",
                weight=0.25,
                enabled=settings.ENABLE_NEWS_API,
                metadata={"sources": ["coindesk", "cointelegraph"]},
            ),
            "google_trends": SentimentSource(
                name="Google Trends",
                type="search",
                weight=0.15,
                enabled=settings.ENABLE_GOOGLE_TRENDS_API,
            ),
        }
        return sources

    def _init_twitter_client(self):
        """初始化Twitter API客户端"""
        if not settings.ENABLE_TWITTER_API:
            return None

        try:
            # 使用 twitter-api-client 和 cookies 进行认证
            if settings.TWITTER_COOKIE_CT0 and settings.TWITTER_COOKIE_AUTH_TOKEN:
                account = Account(
                    cookies={
                        "ct0": settings.TWITTER_COOKIE_CT0,
                        "auth_token": settings.TWITTER_COOKIE_AUTH_TOKEN,
                    }
                )
                search = Search(session=account.session)
                self.logger.info("Twitter API客户端初始化成功 (使用cookies认证)")
                return search
            else:
                self.logger.warning("未配置Twitter API cookies，Twitter数据源将被禁用")
                self.sources["twitter"].enabled = False
                return None
        except Exception as e:
            self.logger.error(f"初始化Twitter API客户端失败: {str(e)}")
            self.sources["twitter"].enabled = False
            return None

    async def get_asset_sentiment_data(
        self, asset: str, days: int = 7, sources: List[str] = None
    ) -> Dict[str, List[RawSentimentData]]:
        """
        获取特定资产的情绪数据

        Args:
            asset: 资产符号 (例如 "BTC", "ETH")
            days: 获取多少天的数据
            sources: 指定要获取的数据源，如果为None则获取所有启用的数据源

        Returns:
            Dict[str, List[RawSentimentData]]: 按数据源分组的情绪数据
        """
        self.logger.info(f"获取{asset}的情绪数据，时间范围: {days}天")

        # 检查缓存
        cache_key = f"sentiment_{asset}_{days}"
        if cache_key in self.cache:
            self.logger.info(f"使用缓存数据: {cache_key}")
            return self.cache[cache_key]

        # 确定要查询的数据源
        if sources is None:
            sources = [s for s, source in self.sources.items() if source.enabled]
        else:
            # 只保留已启用的数据源
            sources = [
                s for s in sources if s in self.sources and self.sources[s].enabled
            ]

        # 并行获取各数据源的数据
        tasks = []
        for source in sources:
            if source == "twitter":
                tasks.append(self._get_twitter_data(asset, days))
            elif source == "crypto_news":
                tasks.append(self._get_news_data(asset, days))
            elif source == "google_trends":
                tasks.append(self._get_google_trends_data(asset, days))

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        sentiment_data = {}
        for i, source in enumerate(sources):
            if isinstance(results[i], Exception):
                self.logger.error(f"获取{source}数据出错: {str(results[i])}")
                sentiment_data[source] = []
            else:
                sentiment_data[source] = results[i]

        # 缓存结果
        self.cache[cache_key] = sentiment_data

        return sentiment_data

    async def _get_twitter_data(self, asset: str, days: int) -> List[RawSentimentData]:
        """获取Twitter数据"""
        if not self.sources["twitter"].enabled or not self.twitter_client:
            return []

        try:
            # 构建搜索查询
            search_query = f"#{asset} OR ${asset} -filter:retweets lang:en"

            # 定义并创建临时输出路径 (如果需要持久化，应移到配置)
            out_path = Path("data/twitter_temp_search")
            out_path.mkdir(parents=True, exist_ok=True)

            # 使用 twitter-api-client 搜索推文 (调用 process 而不是 run)
            # 使用配置限制或默认值，例如 10
            tweet_limit = getattr(settings, "TWITTER_SEARCH_LIMIT", 10)
            all_results = await self.twitter_client.process(
                queries=[{"category": "Latest", "query": search_query}],
                limit=tweet_limit,
                out=out_path,
            )
            # process 返回列表的列表，每个内部列表对应一个查询结果
            search_results = all_results[0] if all_results else []

            # 添加日志记录搜索结果的类型和结构
            self.logger.info(f"Twitter搜索结果类型: {type(search_results)}")
            if search_results is None:
                self.logger.warning("Twitter搜索结果为None")
                return []

            # 检查结果是否为字符串
            if isinstance(search_results, str):
                self.logger.warning(
                    f"Twitter搜索结果为字符串: {search_results[:10]}..."
                )
                return []

            # 处理搜索结果集合
            tweets = []
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            # 确保search_results是可迭代的
            if not hasattr(search_results, "__iter__"):
                self.logger.warning(
                    f"Twitter搜索结果不是可迭代的集合: {type(search_results)}"
                )
                if isinstance(search_results, dict):
                    # 尝试从字典中提取可能的tweet列表
                    for key in ["data", "results", "tweets", "statuses", "content"]:
                        if key in search_results and isinstance(
                            search_results[key], (list, tuple)
                        ):
                            self.logger.info(f"从字典的'{key}'键中提取Twitter搜索结果")
                            search_results = search_results[key]
                            break
                    else:
                        self.logger.warning(
                            f"无法从字典中提取Twitter搜索结果，键: {list(search_results.keys())}"
                        )
                        return []
                else:
                    return []

            # 迭代处理每条推文
            for i, entry in enumerate(search_results):
                try:
                    # 记录前几条推文结构以便调试
                    if i < 2:
                        self.logger.info(f"推文条目类型: {type(entry)}")
                        if isinstance(entry, dict):
                            self.logger.info(f"推文条目顶级键: {list(entry.keys())}")

                    # 处理新的 Twitter JSON 结构
                    tweet_data = None

                    # 尝试提取推文数据
                    if isinstance(entry, dict):
                        # 新API结构通常有entryId, sortIndex, content等字段
                        if "content" in entry and isinstance(entry["content"], dict):
                            content = entry["content"]

                            # 继续深入查找itemContent和tweet_results
                            if "itemContent" in content and isinstance(
                                content["itemContent"], dict
                            ):
                                item_content = content["itemContent"]

                                if "tweet_results" in item_content and isinstance(
                                    item_content["tweet_results"], dict
                                ):
                                    result = item_content["tweet_results"].get(
                                        "result", {}
                                    )

                                    # 提取legacy数据，包含大部分推文信息
                                    if "legacy" in result and isinstance(
                                        result["legacy"], dict
                                    ):
                                        tweet_data = result["legacy"]

                                        # 处理用户数据
                                        if "core" in result and isinstance(
                                            result["core"], dict
                                        ):
                                            user_results = result["core"].get(
                                                "user_results", {}
                                            )
                                            if (
                                                "result" in user_results
                                                and "legacy" in user_results["result"]
                                            ):
                                                user_data = user_results["result"][
                                                    "legacy"
                                                ]
                                            else:
                                                user_data = {}
                                        else:
                                            user_data = {}
                        # 兼容旧格式，直接包含tweet数据的情况
                        elif "legacy" in entry:
                            tweet_data = entry.get("legacy", {})
                            # 处理旧格式的用户数据
                            if "core" in entry and "user_results" in entry["core"]:
                                user_data = (
                                    entry["core"]["user_results"]
                                    .get("result", {})
                                    .get("legacy", {})
                                )
                            else:
                                user_data = {}

                    # 如果找不到推文数据，继续下一条
                    if not tweet_data:
                        continue

                    # 提取推文创建时间
                    created_at = None
                    if "created_at" in tweet_data:
                        try:
                            created_at_str = tweet_data["created_at"]
                            # 尝试不同的日期格式
                            date_formats = [
                                "%Y-%m-%dT%H:%M:%S.%fZ",  # 标准ISO格式
                                "%a %b %d %H:%M:%S %z %Y",  # Twitter API常用格式
                            ]

                            for date_format in date_formats:
                                try:
                                    created_at = datetime.strptime(
                                        created_at_str, date_format
                                    )
                                    break
                                except ValueError:
                                    continue

                            if created_at is None:
                                self.logger.warning(
                                    f"无法解析推文创建时间: {created_at_str}"
                                )
                                created_at = datetime.now(
                                    timezone.utc
                                )  # 使用当前时间作为后备
                        except Exception as e:
                            self.logger.warning(f"处理推文创建时间时出错: {str(e)}")
                            created_at = datetime.now(
                                timezone.utc
                            )  # 使用当前时间作为后备
                    else:
                        created_at = datetime.now(timezone.utc)  # 使用当前时间作为后备

                    # Ensure created_at is offset-aware (UTC) for comparison
                    if (
                        created_at.tzinfo is None
                        or created_at.tzinfo.utcoffset(created_at) is None
                    ):
                        # If naive, assume it's UTC and make it aware
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    else:
                        # If aware but not UTC, convert it to UTC
                        created_at = created_at.astimezone(timezone.utc)

                    # 检查推文是否在指定的时间范围内
                    if created_at < start_time:
                        continue

                    # 提取推文ID
                    tweet_id = tweet_data.get("id_str", tweet_data.get("rest_id", ""))

                    # 提取用户名
                    user_name = user_data.get("screen_name", "")
                    user_id = user_data.get("id_str", user_data.get("rest_id", ""))

                    # 提取文本内容
                    text = tweet_data.get("full_text", tweet_data.get("text", ""))
                    if not text:
                        # 尝试从entities中提取
                        entities = tweet_data.get("entities", {})
                        if (
                            "description" in entities
                            and "urls" in entities["description"]
                        ):
                            text = entities["description"].get("text", "")

                    # 提取交互数据
                    likes = tweet_data.get("favorite_count", 0)
                    retweets = tweet_data.get("retweet_count", 0)
                    replies = tweet_data.get("reply_count", 0)
                    quotes = tweet_data.get("quote_count", 0)

                    # 创建情感数据对象
                    tweets.append(
                        RawSentimentData(
                            source="twitter",
                            asset=asset,
                            timestamp=created_at,
                            content=text,
                            author=user_name,
                            url=(
                                f"https://twitter.com/{user_name}/status/{tweet_id}"
                                if user_name and tweet_id
                                else None
                            ),
                            engagement={
                                "likes": likes,
                                "retweets": retweets,
                                "replies": replies,
                                "quotes": quotes,
                            },
                            metadata={
                                "user_id": user_id,
                                "tweet_id": tweet_id,
                            },
                        )
                    )
                except Exception as tweet_error:
                    # 捕获并记录处理单条推文时的错误，但继续处理其他推文
                    self.logger.warning(f"处理单条推文时出错: {str(tweet_error)}")
                    continue

            self.logger.info(f"从Twitter获取了{len(tweets)}条关于{asset}的推文")
            return tweets

        except Exception as e:
            self.logger.error(f"获取Twitter数据出错: {str(e)}")
            return []

    async def _get_news_data(self, asset: str, days: int) -> List[RawSentimentData]:
        """获取加密货币新闻数据"""
        if not self.sources["crypto_news"].enabled:
            return []

        try:
            # 使用第三方新闻API (例如: Crypto Compare News API)
            async with aiohttp.ClientSession() as session:
                url = f"https://min-api.cryptocompare.com/data/v2/news/?lang=EN&categories={asset.lower()}?limit=10"
                if settings.CRYPTOCOMPARE_API_KEY:
                    url += f"&api_key={settings.CRYPTOCOMPARE_API_KEY}"

                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"获取新闻API失败: {response.status}")
                        return []

                    data = await response.json()
                    if "Data" not in data:
                        return []

                    news_items = []
                    end_time = datetime.now(timezone.utc)
                    start_time = end_time - timedelta(days=days)

                    # 只返回前10条数据
                    data["Data"] = data["Data"][:10]
                    for item in data["Data"]:
                        # 检查时间是否在范围内
                        news_time = datetime.fromtimestamp(item["published_on"])
                        if news_time < start_time:
                            continue

                        news_items.append(
                            RawSentimentData(
                                source="crypto_news",
                                asset=asset,
                                timestamp=news_time,
                                content=f"{item['title']}\n{item.get('body', '')}",
                                author=item.get("source", ""),
                                url=item.get("url", ""),
                                metadata={
                                    "categories": item.get("categories", ""),
                                    "tags": item.get("tags", ""),
                                },
                            )
                        )

                    self.logger.info(
                        f"从加密货币新闻源获取了{len(news_items)}条关于{asset}的新闻"
                    )
                    return news_items

        except Exception as e:
            self.logger.error(f"获取新闻数据出错: {str(e)}")
            return []

    async def _get_google_trends_data(
        self, asset: str, days: int
    ) -> List[RawSentimentData]:
        """获取Google趋势数据"""
        if not self.sources["google_trends"].enabled:
            return []

        try:
            # 基于指定的天数确定时间范围
            # Google Trends 支持的时间范围：'now 1-H', 'now 4-H', 'now 1-d', 'now 7-d', 'today 1-m', 'today 3-m', 'today 12-m', 'today 5-y'
            if days <= 1:
                timeframe = "now 1-d"
            elif days <= 7:
                timeframe = "now 7-d"
            elif days <= 30:
                timeframe = "today 1-m"
            elif days <= 90:
                timeframe = "today 3-m"
            else:
                timeframe = "today 12-m"

            # 创建搜索词列表，包括币种名称和符号
            search_terms = []
            if asset.lower() in [
                "btc",
                "eth",
                "usdt",
                "bnb",
                "sol",
                "xrp",
                "ada",
                "doge",
                "avax",
                "dot",
            ]:
                # 常见加密货币简称映射到全名
                crypto_map = {
                    "btc": "bitcoin",
                    "eth": "ethereum",
                    "usdt": "tether",
                    "bnb": "binance coin",
                    "sol": "solana",
                    "xrp": "ripple",
                    "ada": "cardano",
                    "doge": "dogecoin",
                    "avax": "avalanche",
                    "dot": "polkadot",
                }
                # 如果是常见加密货币，添加全名
                if asset.lower() in crypto_map:
                    search_terms.append(crypto_map[asset.lower()])

            # 添加币种符号，例如 BTC 或 $BTC
            search_terms.append(asset)
            search_terms.append(f"${asset}")

            # 异步执行 Google Trends API 调用
            # 由于 pytrends 是同步库，我们使用 run_in_executor 使其异步执行
            loop = asyncio.get_event_loop()
            trends_data = await loop.run_in_executor(
                None, self._fetch_google_trends, search_terms, timeframe
            )

            if trends_data.empty:
                self.logger.info(f"未找到关于{asset}的Google趋势数据")
                return []

            # 将趋势数据转换为RawSentimentData对象
            results = []
            for index, row in trends_data.iterrows():
                # 计算搜索量的平均值作为趋势值
                trend_value = 0
                count = 0
                for term in search_terms:
                    if term in row:
                        trend_value += row[term]
                        count += 1

                if count > 0:
                    avg_trend = trend_value / count
                    # 将0-100的趋势值归一化到-1到1的情绪分数范围
                    # 我们使用简单的线性转换: score = (trend - 50) / 50
                    # 这样，趋势值50对应情绪分数0，趋势值100对应情绪分数1，趋势值0对应情绪分数-1
                    sentiment_score = (avg_trend - 50) / 50
                    # 限制在 -1 到 1 的范围内
                    sentiment_score = max(-1, min(1, sentiment_score))

                    # 创建RawSentimentData对象
                    results.append(
                        RawSentimentData(
                            source="google_trends",
                            asset=asset,
                            timestamp=index,  # 日期索引作为时间戳
                            content=f"Google Trends data for {asset}: {avg_trend}",
                            author="Google Trends",
                            url=f"https://trends.google.com/trends/explore?date={timeframe}&q={','.join(search_terms)}",
                            engagement={"score": int(avg_trend)},
                            metadata={
                                "trend_value": float(avg_trend),
                                "sentiment_score": float(sentiment_score),
                                "search_terms": search_terms,
                            },
                        )
                    )

            self.logger.info(f"从Google趋势获取了{len(results)}条关于{asset}的数据")
            return results

        except Exception as e:
            self.logger.error(f"获取Google趋势数据出错: {str(e)}")
            return []

    def _fetch_google_trends(
        self, search_terms: List[str], timeframe: str
    ) -> pd.DataFrame:
        """
        获取Google趋势数据

        Args:
            search_terms: 搜索词列表
            timeframe: 时间范围

        Returns:
            包含趋势数据的DataFrame
        """
        try:
            # 初始化pytrends
            pytrends = TrendReq(hl="en-US", tz=360)

            # 构建请求
            # 由于Google Trends一次最多只能请求5个关键词，所以我们限制为前5个
            search_terms = search_terms[:5]
            pytrends.build_payload(
                search_terms, cat=0, timeframe=timeframe, geo="", gprop=""
            )

            # 获取兴趣随时间的变化
            interest_over_time_df = pytrends.interest_over_time()

            # 删除isPartial列，它表示数据是否部分完成
            if "isPartial" in interest_over_time_df.columns:
                interest_over_time_df = interest_over_time_df.drop("isPartial", axis=1)

            # 只返回前10条数据
            return interest_over_time_df.head(10)

        except Exception as e:
            self.logger.error(f"获取Google趋势数据失败: {str(e)}")
            return pd.DataFrame()  # 返回空DataFrame

    async def get_batch_sentiment_data(
        self, assets: List[str], days: int = 7
    ) -> Dict[str, Dict[str, List[RawSentimentData]]]:
        """
        批量获取多个资产的情绪数据

        Args:
            assets: 资产符号列表
            days: 获取多少天的数据

        Returns:
            Dict[str, Dict[str, List[RawSentimentData]]]: 按资产和数据源分组的情绪数据
        """
        results = {}
        for asset in assets:
            results[asset] = await self.get_asset_sentiment_data(asset, days)
        return results

    async def close(self):
        """关闭服务并释放资源"""
        self.logger.info("关闭情绪数据服务")
        # 释放资源的逻辑
