# src/grok_fetcher.py
"""Grok data fetcher module via OpenRouter API."""
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)

# BTC/ETH 相关关键词
BTC_KEYWORDS = [
    "BTC", "Bitcoin", "比特币", "ETH", "Ethereum", "以太坊",
    "crypto", "cryptocurrency", "区块链", "blockchain",
    "HODL", "bull", "bear", "altcoin", "DeFi"
]


@dataclass
class TweetData:
    """推文数据结构"""
    tweet_id: str
    username: str
    display_name: str
    content: str
    posted_at: datetime
    likes: int = 0
    retweets: int = 0
    has_btc_keyword: bool = False


class GrokFetcher:
    """通过 OpenRouter API 调用 Grok 模型获取 Twitter KOL 推文"""

    def __init__(self, config: Any):
        """
        初始化 GrokFetcher

        Args:
            config: 配置对象，需要包含 api_key, base_url, model, max_tokens, temperature
        """
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "HTTP-Referer": "https://github.com/WesleyWu2020/TwitterKOLKimi",
                "X-Title": "Crypto KOL Sentiment Monitor"
            },
            timeout=60.0
        )
        logger.info(f"GrokFetcher initialized with model: {getattr(config, 'model', 'grok-2-1212')}")

    def _build_prompt(self, username: str, count: int = 10) -> str:
        """
        构建获取推文的 prompt - 使用 X Search 工具获取真实数据

        Args:
            username: Twitter 用户名
            count: 获取推文数量

        Returns:
            构建好的 prompt 字符串
        """
        from datetime import datetime, timedelta
        
        # 计算24小时前的时间
        since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        prompt = f"""Use the x_search tool to search for recent tweets from @{username} about cryptocurrency, Bitcoin, Ethereum, or blockchain.

Search query: "from:{username} (BTC OR Bitcoin OR ETH OR Ethereum OR crypto) since:{since_date}"

Requirements:
1. Use x_search tool to get REAL and RECENT tweets (last 7 days)
2. Return the data in valid JSON format
3. The JSON should have a "tweets" array containing tweet objects
4. Each tweet object must include these fields:
   - tweet_id: The tweet ID (string)
   - username: The Twitter handle without @ (string)
   - display_name: The display name (string)
   - content: The full tweet text (string)
   - posted_at: ISO 8601 formatted timestamp (string, must be from 2025 or 2026)
   - likes: Number of likes (integer)
   - retweets: Number of retweets (integer)

Important notes:
- CRITICAL: Use x_search tool to fetch REAL data from X platform, do NOT generate fake data
- Only include tweets from {since_date} onwards (very recent, within last 7 days)
- Focus on tweets related to cryptocurrency, Bitcoin, Ethereum, or blockchain
- Ensure the JSON is properly formatted and parseable
- Use UTC timezone for timestamps

Return ONLY the JSON response without any additional text or markdown formatting."""
        return prompt

    def _parse_grok_response(self, response_text: str, username: str) -> List[TweetData]:
        """
        解析 Grok 返回的 JSON 响应

        Args:
            response_text: API 返回的文本内容
            username: 查询的用户名

        Returns:
            TweetData 对象列表
        """
        tweets = []
        
        try:
            # 处理 markdown 格式的 JSON (```json ... ```)
            cleaned_text = response_text.strip()
            logger.debug(f"Raw response text (first 1000 chars): {response_text[:1000]}")
            
            if cleaned_text.startswith("```"):
                # 提取代码块内容
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned_text, re.DOTALL)
                if match:
                    cleaned_text = match.group(1).strip()
                    logger.debug("Extracted JSON from markdown code block")
            
            # 解析 JSON
            logger.debug(f"Attempting to parse JSON: {cleaned_text[:200]}...")
            data = json.loads(cleaned_text)
            
            if not isinstance(data, dict):
                logger.warning(f"Response is not a dictionary: {type(data)}")
                return tweets
            
            tweets_data = data.get("tweets", [])
            if not isinstance(tweets_data, list):
                logger.warning(f"'tweets' field is not a list: {type(tweets_data)}")
                return tweets
            
            for tweet_data in tweets_data:
                try:
                    tweet = self._parse_single_tweet(tweet_data, username)
                    if tweet:
                        tweets.append(tweet)
                except Exception as e:
                    logger.warning(f"Failed to parse tweet: {e}")
                    continue
                    
            logger.info(f"Successfully parsed {len(tweets)} tweets for @{username}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
        
        return tweets

    def _parse_single_tweet(self, tweet_data: Dict[str, Any], username: str) -> Optional[TweetData]:
        """
        解析单个推文数据，并验证时间戳合理性

        Args:
            tweet_data: 单个推文的字典数据
            username: 查询的用户名

        Returns:
            TweetData 对象或 None
        """
        try:
            # 解析时间戳
            posted_at_str = tweet_data.get("posted_at", "")
            try:
                # 尝试 ISO 8601 格式
                posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                # 默认使用当前时间
                posted_at = datetime.now(timezone.utc)
            
            # ⚠️ 验证时间戳合理性
            now = datetime.now(timezone.utc)
            one_day_ago = now - timedelta(days=1)
            
            if posted_at > now:
                # 未来时间，可能是假的
                logger.warning(f"Tweet timestamp is in the future: {posted_at}, using current time")
                posted_at = now
            elif posted_at < one_day_ago:
                # 超过1天的推文，可能不是最新的
                logger.warning(f"Tweet is older than 24h: {posted_at}, marking as stale data")
            
            content = tweet_data.get("content", "")
            
            # 检测是否包含 BTC/ETH 关键词
            has_btc_keyword = any(
                keyword.lower() in content.lower() 
                for keyword in BTC_KEYWORDS
            )
            
            return TweetData(
                tweet_id=str(tweet_data.get("tweet_id", "")),
                username=tweet_data.get("username", username),
                display_name=tweet_data.get("display_name", username),
                content=content,
                posted_at=posted_at,
                likes=int(tweet_data.get("likes", 0)),
                retweets=int(tweet_data.get("retweets", 0)),
                has_btc_keyword=has_btc_keyword
            )
        except Exception as e:
            logger.warning(f"Error parsing single tweet: {e}")
            return None

    async def fetch_tweets_from_kol(
        self, 
        username: str, 
        max_tweets: int = 10
    ) -> List[TweetData]:
        """
        异步获取单个 KOL 的推文

        Args:
            username: Twitter 用户名（不带 @）
            max_tweets: 最大获取推文数量

        Returns:
            TweetData 对象列表
        """
        logger.info(f"Fetching tweets for @{username}, max_tweets={max_tweets}")
        
        try:
            prompt = self._build_prompt(username, max_tweets)
            
            payload = {
                "model": getattr(self.config, "model", "grok-2-1212"),
                "messages": [
                    {
                        "role": "system",
                        "content": "You have access to X (Twitter) via x_search. Always use x_search to find real, recent tweets. Today's date is 2026-03-26."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": getattr(self.config, "max_tokens", 4000),
                "temperature": getattr(self.config, "temperature", 0.3)
            }
            
            logger.info(f"Calling Grok API for @{username}, model: {payload['model']}")
            response = await self.client.post("/chat/completions", json=payload)
            
            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            
            # 提取响应内容
            if "choices" not in data or not data["choices"]:
                logger.error("No choices in API response")
                return []
            
            content = data["choices"][0].get("message", {}).get("content", "")
            if not content:
                logger.error("Empty content in API response")
                return []
            
            # 调试：记录原始响应
            logger.debug(f"Grok raw response for @{username}: {content[:500]}...")
            
            tweets = self._parse_grok_response(content, username)
            logger.info(f"Fetched {len(tweets)} tweets for @{username}")
            return tweets
            
        except httpx.TimeoutException:
            logger.error(f"Request timeout for @{username}")
            return []
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching tweets for @{username}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching tweets for @{username}: {e}")
            return []

    async def fetch_all_kols_tweets(
        self, 
        kols: List[str], 
        max_tweets: int = 10
    ) -> Dict[str, List[TweetData]]:
        """
        批量获取多个 KOL 的推文

        Args:
            kols: Twitter 用户名列表
            max_tweets: 每个 KOL 最大获取推文数量

        Returns:
            字典，键为用户名，值为 TweetData 列表
        """
        if not kols:
            logger.warning("Empty KOL list provided")
            return {}
        
        logger.info(f"Fetching tweets for {len(kols)} KOLs")
        
        results = {}
        for username in kols:
            try:
                tweets = await self.fetch_tweets_from_kol(username, max_tweets)
                results[username] = tweets
            except Exception as e:
                logger.error(f"Failed to fetch tweets for @{username}: {e}")
                results[username] = []
        
        total_tweets = sum(len(tweets) for tweets in results.values())
        logger.info(f"Fetched total {total_tweets} tweets from {len(kols)} KOLs")
        
        return results
