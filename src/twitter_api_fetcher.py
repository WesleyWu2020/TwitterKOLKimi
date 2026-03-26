# src/twitter_api_fetcher.py
"""使用 Twitter API v2 获取真实推文数据."""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

BTC_KEYWORDS = [
    "BTC", "Bitcoin", "比特币", "ETH", "Ethereum", "以太坊",
    "crypto", "cryptocurrency", "区块链", "blockchain"
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
    is_real_data: bool = True  # 标记是否为真实数据


class TwitterAPIFetcher:
    """通过 Twitter API v2 获取真实推文数据"""

    def __init__(self, bearer_token: str):
        """
        初始化 Twitter API 获取器
        
        Args:
            bearer_token: Twitter API Bearer Token
        """
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        logger.info("TwitterAPIFetcher initialized")

    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """发送 API 请求"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.error("Twitter API rate limit exceeded")
                return None
            elif response.status_code != 200:
                logger.error(f"Twitter API error: {response.status_code} - {response.text}")
                return None
            
            return response.json()
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def get_user_id(self, username: str) -> Optional[str]:
        """获取用户 ID"""
        # 移除 @ 符号
        username = username.replace("@", "")
        
        data = self._make_request(
            f"/users/by/username/{username}",
            {"user.fields": "public_metrics,created_at"}
        )
        
        if data and "data" in data:
            return data["data"]["id"]
        return None

    def fetch_tweets_from_kol(
        self,
        username: str,
        max_tweets: int = 10,
        exclude_replies: bool = True,
        exclude_retweets: bool = True
    ) -> List[TweetData]:
        """
        获取单个 KOL 的最新推文
        
        Args:
            username: Twitter 用户名
            max_tweets: 最大获取数量
            exclude_replies: 排除回复
            exclude_retweets: 排除转发
            
        Returns:
            TweetData 列表
        """
        logger.info(f"Fetching real tweets for @{username}")
        
        # 获取用户 ID
        user_id = self.get_user_id(username)
        if not user_id:
            logger.error(f"Could not find user: {username}")
            return []
        
        # 构建查询参数
        params = {
            "max_results": min(max_tweets, 100),  # API 限制
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "username,name"
        }
        
        # 排除回复和转发
        exclude = []
        if exclude_replies:
            exclude.append("replies")
        if exclude_retweets:
            params["exclude"] = "retweets"
        
        # 获取推文
        data = self._make_request(f"/users/{user_id}/tweets", params)
        
        if not data or "data" not in data:
            logger.warning(f"No tweets found for @{username}")
            return []
        
        # 解析用户映射
        users_map = {}
        if "includes" in data and "users" in data["includes"]:
            for user in data["includes"]["users"]:
                users_map[user["id"]] = user
        
        tweets = []
        for tweet_data in data["data"]:
            try:
                # 解析时间
                posted_at = datetime.fromisoformat(
                    tweet_data["created_at"].replace("Z", "+00:00")
                )
                
                # 获取用户信息
                author_id = tweet_data.get("author_id", "")
                user_info = users_map.get(author_id, {})
                
                content = tweet_data.get("text", "")
                metrics = tweet_data.get("public_metrics", {})
                
                # 检测关键词
                has_btc_keyword = any(
                    kw.lower() in content.lower()
                    for kw in BTC_KEYWORDS
                )
                
                tweet = TweetData(
                    tweet_id=tweet_data["id"],
                    username=user_info.get("username", username),
                    display_name=user_info.get("name", username),
                    content=content,
                    posted_at=posted_at,
                    likes=metrics.get("like_count", 0),
                    retweets=metrics.get("retweet_count", 0),
                    has_btc_keyword=has_btc_keyword,
                    is_real_data=True
                )
                tweets.append(tweet)
                
            except Exception as e:
                logger.warning(f"Error parsing tweet: {e}")
                continue
        
        logger.info(f"Fetched {len(tweets)} real tweets for @{username}")
        return tweets

    def fetch_all_kols_tweets(
        self,
        kols: List[Dict[str, Any]],
        max_tweets: int = 10
    ) -> Dict[str, List[TweetData]]:
        """
        批量获取多个 KOL 的推文
        
        Args:
            kols: KOL 配置列表
            max_tweets: 每个 KOL 最大数量
            
        Returns:
            按用户名分组的推文字典
        """
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
