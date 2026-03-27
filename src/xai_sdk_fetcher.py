# src/xai_sdk_fetcher.py
"""使用 xAI 官方 SDK 获取真实 Twitter 数据."""
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# 尝试导入 xai-sdk，如果未安装则给出提示
try:
    from xai_sdk import Client
    from xai_sdk.chat import user
    from xai_sdk.tools import x_search
    XAI_SDK_AVAILABLE = True
except ImportError:
    XAI_SDK_AVAILABLE = False
    logging.warning("xai-sdk not installed. Run: pip install xai-sdk")

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
    url: str = ""  # 推文链接


class XAISDKFetcher:
    """通过 xAI SDK 调用 Grok X Search 获取真实推文"""

    def __init__(self, api_key: str, model: str = "grok-4.20-reasoning"):
        """
        初始化 xAI SDK Fetcher
        
        Args:
            api_key: xAI API Key
            model: 模型名称（推荐 grok-4.20-reasoning）
        """
        if not XAI_SDK_AVAILABLE:
            raise ImportError("xai-sdk not installed. Run: pip install xai-sdk")
        
        self.api_key = api_key
        self.model = model
        self.client = Client(api_key=api_key)
        logger.info(f"XAISDKFetcher initialized with model: {model}")

    def fetch_tweets_from_kol(
        self,
        username: str,
        max_tweets: int = 10,
        since_date: Optional[str] = None
    ) -> List[TweetData]:
        """
        获取单个 KOL 的推文
        
        Args:
            username: Twitter 用户名
            max_tweets: 最大获取数量
            since_date: 可选，格式 "2026-03-20"
            
        Returns:
            TweetData 列表
        """
        logger.info(f"Fetching tweets from xAI SDK for @{username}")
        
        try:
            # 启用 x_search 工具，限制只搜索该账号
            tools = [x_search(allowed_x_handles=[username])]
            
            # 构建 Prompt
            date_filter = f" since:{since_date}" if since_date else ""
            prompt = f"""
请搜索 X 平台用户 @{username} 的最新推文，关于加密货币、Bitcoin、Ethereum 或区块链。

搜索参数：
- Query: "from:{username} (BTC OR Bitcoin OR ETH OR Ethereum OR crypto OR blockchain){date_filter}"
- Max results: {max_tweets}
- Mode: Latest

要求：
1. 使用 x_search 工具获取真实推文
2. 返回完整原始文本（不要总结）
3. 输出严格 JSON 格式：
{{
  "tweets": [
    {{
      "tweet_id": "string",
      "username": "{username}",
      "display_name": "string",
      "content": "完整推文内容",
      "posted_at": "ISO 8601 timestamp",
      "likes": integer,
      "retweets": integer,
      "url": "https://x.com/username/status/tweet_id"
    }}
  ]
}}
4. 按时间倒序排序
5. 只包含 {since_date or "最近"} 的推文
"""
            
            # 创建聊天会话
            chat = self.client.chat.create(
                model=self.model,
                tools=tools,
                max_turns=5,
                temperature=0.0,
            )
            
            chat.append(user(prompt))
            
            # 执行并获取结果
            logger.info(f"Calling xAI SDK for @{username}...")
            response = chat.sample()
            
            content = response.content
            if not content:
                logger.warning(f"Empty response from xAI for @{username}")
                return []
            
            # 解析 JSON
            tweets = self._parse_response(content, username)
            logger.info(f"Fetched {len(tweets)} tweets for @{username} via xAI SDK")
            return tweets
            
        except Exception as e:
            logger.error(f"Error fetching tweets for @{username}: {e}")
            return []

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
                    
                    # 构建推文 URL
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

    def fetch_all_kols_tweets(
        self,
        kols: List[Dict[str, Any]],
        max_tweets: int = 10
    ) -> Dict[str, List[TweetData]]:
        """批量获取多个 KOL 的推文"""
        results = {}
        
        # 计算日期（最近7天）
        since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        for kol in kols:
            username = kol.get("username", "") if isinstance(kol, dict) else kol
            if not username:
                continue
            
            try:
                tweets = self.fetch_tweets_from_kol(username, max_tweets, since_date)
                results[username] = tweets
            except Exception as e:
                logger.error(f"Failed to fetch tweets for @{username}: {e}")
                results[username] = []
        
        return results
