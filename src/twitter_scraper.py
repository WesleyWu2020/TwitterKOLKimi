# src/twitter_scraper.py
"""Twitter 爬虫模块 (简化接口)."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from loguru import logger


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


class TwitterScraper:
    """Twitter 爬虫类"""
    
    def __init__(self, config):
        """
        初始化爬虫
        
        Args:
            config: TwitterConfig 配置对象
        """
        self.config = config
        self.session = None
        logger.info(f"TwitterScraper initialized for user: {config.username}")
    
    def _check_btc_keyword(self, text: str) -> bool:
        """
        检查文本是否包含BTC相关关键词
        
        Args:
            text: 推文内容
            
        Returns:
            是否包含BTC关键词
        """
        text_upper = text.upper()
        keywords_upper = [k.upper() for k in self.config.keywords]
        return any(kw in text_upper for kw in keywords_upper)
    
    def fetch_tweets_from_kol(self, username: str) -> List[TweetData]:
        """
        从指定KOL获取推文
        
        Args:
            username: KOL用户名
            
        Returns:
            推文数据列表
            
        Note:
            这是一个简化接口，实际实现需要使用 Twitter API 或网页抓取
        """
        logger.info(f"Fetching tweets for KOL: {username}")
        # 简化实现：返回空列表
        # 实际项目中这里会调用 Twitter API
        return []
    
    def fetch_all_kols_tweets(self, kols: List[Dict[str, Any]]) -> List[TweetData]:
        """
        批量获取多个KOL的推文
        
        Args:
            kols: KOL列表，每项包含username, followers_count等
            
        Returns:
            所有推文数据列表
        """
        all_tweets = []
        
        for kol in kols:
            if kol.get("followers_count", 0) >= self.config.min_followers:
                try:
                    tweets = self.fetch_tweets_from_kol(kol["username"])
                    all_tweets.extend(tweets)
                    logger.info(f"Fetched {len(tweets)} tweets from {kol['username']}")
                except Exception as e:
                    logger.error(f"Failed to fetch tweets from {kol['username']}: {e}")
            else:
                logger.debug(f"Skipping {kol['username']}: insufficient followers")
        
        return all_tweets
    
    def parse_tweet_data(self, raw_data: Dict[str, Any]) -> Optional[TweetData]:
        """
        解析原始推文数据
        
        Args:
            raw_data: 原始API返回数据
            
        Returns:
            解析后的TweetData对象
        """
        try:
            content = raw_data.get("text", "")
            return TweetData(
                tweet_id=str(raw_data.get("id", "")),
                username=raw_data.get("username", ""),
                display_name=raw_data.get("name", ""),
                content=content,
                posted_at=datetime.now(timezone.utc),  # 简化处理
                likes=raw_data.get("public_metrics", {}).get("like_count", 0),
                retweets=raw_data.get("public_metrics", {}).get("retweet_count", 0),
                has_btc_keyword=self._check_btc_keyword(content)
            )
        except Exception as e:
            logger.error(f"Failed to parse tweet data: {e}")
            return None
