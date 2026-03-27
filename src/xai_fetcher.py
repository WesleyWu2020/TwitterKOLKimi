# src/xai_fetcher.py
"""使用 xAI REST API 获取真实 Twitter 数据."""
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

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
    url: str = ""


class XAIFetcher:
    """通过 xAI REST API 调用 Grok 获取推文"""

    def __init__(self, api_key: str, model: str = "grok-3"):
        """
        初始化 XAI Fetcher
        
        Args:
            api_key: xAI API Key
            model: 模型名称（grok-3, grok-2-1212 等）
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"XAIFetcher initialized with model: {model}")

    def _build_prompt(self, username: str, max_tweets: int = 10) -> str:
        """构建获取推文的 prompt"""
        since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        return f"""Search X (Twitter) for the most recent posts from @{username} about cryptocurrency, Bitcoin, Ethereum, or blockchain.

Search parameters:
- User: @{username}
- Keywords: BTC, Bitcoin, ETH, Ethereum, crypto, blockchain
- Since: {since_date}
- Max results: {max_tweets}

Requirements:
1. Use x_search tool to get REAL data from X platform
2. Return tweets in valid JSON format
3. Each tweet must include:
   - tweet_id: The tweet ID
   - username: "{username}"
   - display_name: Display name
   - content: Full tweet text
   - posted_at: ISO 8601 timestamp (2025 or 2026)
   - likes: Number of likes
   - retweets: Number of retweets
   - url: Full URL to tweet (https://x.com/{username}/status/TWEET_ID)

Return ONLY valid JSON in this format:
{{
  "tweets": [
    {{
      "tweet_id": "...",
      "username": "{username}",
      "display_name": "...",
      "content": "...",
      "posted_at": "2026-...",
      "likes": 1234,
      "retweets": 567,
      "url": "https://x.com/{username}/status/..."
    }}
  ]
}}"""

    def _call_api(self, prompt: str) -> Optional[str]:
        """调用 xAI REST API"""
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an assistant with access to X (Twitter) platform. Use x_search tool to find real, recent tweets. Today's date is 2026-03-27."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "x_search",
                            "description": "Search X platform for tweets",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"}
                                }
                            }
                        }
                    }
                ],
                "tool_choice": "auto",
                "max_tokens": 4000,
                "temperature": 0.3
            }
            
            logger.info(f"Calling xAI API with model: {self.model}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"xAI API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 检查使用的 sources
            usage = data.get("usage", {})
            sources = usage.get("num_sources_used", 0)
            if sources > 0:
                logger.info(f"✅ xAI used {sources} sources from X platform")
            else:
                logger.warning("⚠️ xAI used 0 sources - data may be from training set")
            
            return content
            
        except Exception as e:
            logger.error(f"Error calling xAI API: {e}")
            return None

    def _parse_response(self, response_text: str, username: str) -> List[TweetData]:
        """解析 API 响应"""
        tweets = []
        
        try:
            # 提取 JSON
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1).strip()
            
            data = json.loads(cleaned)
            tweets_data = data.get("tweets", [])
            
            for tweet_data in tweets_data:
                try:
                    posted_at_str = tweet_data.get("posted_at", "")
                    try:
                        posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
                    except:
                        posted_at = datetime.now(timezone.utc)
                    
                    content = tweet_data.get("content", "")
                    has_btc = any(kw.lower() in content.lower() for kw in BTC_KEYWORDS)
                    
                    # 构建 URL
                    tweet_id = str(tweet_data.get("tweet_id", ""))
                    url = tweet_data.get("url", "")
                    if not url and tweet_id:
                        url = f"https://x.com/{username}/status/{tweet_id}"
                    
                    tweet = TweetData(
                        tweet_id=tweet_id,
                        username=tweet_data.get("username", username),
                        display_name=tweet_data.get("display_name", username),
                        content=content,
                        posted_at=posted_at,
                        likes=int(tweet_data.get("likes", 0)),
                        retweets=int(tweet_data.get("retweets", 0)),
                        has_btc_keyword=has_btc,
                        url=url
                    )
                    tweets.append(tweet)
                except Exception as e:
                    logger.warning(f"Error parsing tweet: {e}")
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
        
        return tweets

    def fetch_tweets_from_kol(self, username: str, max_tweets: int = 10) -> List[TweetData]:
        """获取单个 KOL 的推文"""
        logger.info(f"Fetching tweets from xAI REST API for @{username}")
        
        prompt = self._build_prompt(username, max_tweets)
        response = self._call_api(prompt)
        
        if not response:
            return []
        
        return self._parse_response(response, username)

    def fetch_all_kols_tweets(
        self,
        kols: List[Dict[str, Any]],
        max_tweets: int = 10
    ) -> Dict[str, List[TweetData]]:
        """批量获取多个 KOL 的推文"""
        results = {}
        
        for kol in kols:
            username = kol.get("username", "") if isinstance(kol, dict) else kol
            if not username:
                continue
            
            try:
                tweets = self.fetch_tweets_from_kol(username, max_tweets)
                results[username] = tweets
            except Exception as e:
                logger.error(f"Failed to fetch tweets for @{username}: {e}")
                results[username] = []
        
        return results
