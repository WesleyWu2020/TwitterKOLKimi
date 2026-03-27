# src/xai_fetcher.py
"""使用 xAI Chat Completions API 获取 Twitter 数据."""
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
    """通过 xAI Chat Completions API 调用 Grok"""

    def __init__(self, api_key: str, model: str = "grok-4.20-reasoning"):
        """
        初始化 XAI Fetcher
        
        Args:
            api_key: xAI API Key
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"XAIFetcher initialized with model: {model}")

    def _call_api(self, username: str, max_tweets: int = 10) -> Optional[str]:
        """调用 xAI Chat Completions API"""
        try:
            since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            url = f"{self.base_url}/chat/completions"
            
            # 强制工具调用的 prompt
            prompt = f"""You MUST use the web_search tool to find real tweets from X platform.

Search for: from:{username} (Bitcoin OR BTC OR crypto OR Ethereum OR ETH) since:{since_date}

Return EXACTLY {max_tweets} tweets in this JSON format:
{{
  "tweets": [
    {{
      "tweet_id": "string",
      "username": "{username}",
      "display_name": "string", 
      "content": "full tweet text",
      "posted_at": "2025-XX-XX or 2026-XX-XX",
      "likes": number,
      "retweets": number,
      "url": "https://x.com/{username}/status/ID"
    }}
  ]
}}

IMPORTANT: Use web_search tool. Do NOT generate fake data."""
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an assistant with web_search tool access. Today's date is 2026-03-27. ALWAYS use web_search to find real data. Never make up information."
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
                            "name": "web_search",
                            "description": "Search the web for real-time information from X platform and other sources"
                        }
                    }
                ],
                "tool_choice": "auto",
                "max_tokens": 4000,
                "temperature": 0.0
            }
            
            logger.info(f"Calling xAI API for @{username}...")
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"xAI API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            
            # 检查工具调用
            message = data.get("choices", [{}])[0].get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            if tool_calls:
                logger.info(f"✅ Triggered {len(tool_calls)} tool call(s)")
                for tc in tool_calls:
                    logger.info(f"   Tool: {tc.get('function', {}).get('name')}")
            else:
                logger.warning("⚠️ No tool calls - data may be from training set")
            
            # 返回内容
            return message.get("content", "")
            
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
        logger.info(f"Fetching tweets for @{username}")
        
        response = self._call_api(username, max_tweets)
        
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
