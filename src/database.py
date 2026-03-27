# src/database.py
"""数据库操作模块."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, Session
from src.models import Base, KOL, Tweet, ModelAnalysis, Sentiment, MarketSentimentHistory, DebateRecord


class Database:
    """数据库操作类"""
    
    def __init__(self, database_url: str = "sqlite:///data/sentiment.db"):
        """
        初始化数据库连接
        
        Args:
            database_url: 数据库连接URL
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info(f"Database initialized: {database_url}")
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def init_tables(self):
        """初始化所有表"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables initialized")
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()
        logger.info("Database connection closed")
    
    def get_or_create_kol(
        self, 
        username: str, 
        display_name: Optional[str] = None,
        followers_count: int = 0
    ) -> KOL:
        """
        获取或创建KOL记录
        
        Args:
            username: KOL用户名
            display_name: 显示名称
            followers_count: 粉丝数
            
        Returns:
            KOL对象
        """
        session = self.get_session()
        try:
            kol = session.query(KOL).filter(KOL.username == username).first()
            
            if kol:
                # 更新现有记录
                if display_name:
                    kol.display_name = display_name
                if followers_count:
                    kol.followers_count = followers_count
                kol.updated_at = datetime.now(timezone.utc)
                logger.debug(f"Updated KOL: {username}")
            else:
                # 创建新记录
                kol = KOL(
                    username=username,
                    display_name=display_name or username,
                    followers_count=followers_count
                )
                session.add(kol)
                logger.info(f"Created new KOL: {username}")
            
            session.commit()
            # 刷新并分离对象
            session.refresh(kol)
            return kol
        finally:
            session.close()
    
    def save_tweet(
        self,
        tweet_id: str,
        username: str,
        content: str,
        posted_at: Optional[datetime] = None,
        has_btc_keyword: bool = False,
        url: str = ""
    ) -> Tweet:
        """
        保存推文
        
        Args:
            tweet_id: 推文ID
            username: KOL用户名
            content: 推文内容
            posted_at: 发布时间
            has_btc_keyword: 是否包含BTC关键词
            url: 推文链接
            
        Returns:
            Tweet对象
        """
        session = self.get_session()
        try:
            # 检查是否已存在
            existing = session.query(Tweet).filter(Tweet.tweet_id == tweet_id).first()
            if existing:
                logger.debug(f"Tweet already exists: {tweet_id}")
                return existing
            
            # 获取KOL
            kol = session.query(KOL).filter(KOL.username == username).first()
            if not kol:
                kol = KOL(username=username, display_name=username)
                session.add(kol)
                session.flush()
            
            # 创建新推文
            tweet = Tweet(
                tweet_id=tweet_id,
                kol_id=kol.id,
                content=content,
                posted_at=posted_at or datetime.now(timezone.utc),
                has_btc_keyword=has_btc_keyword,
                url=url
            )
            session.add(tweet)
            session.commit()
            session.refresh(tweet)
            logger.info(f"Saved tweet: {tweet_id}")
            return tweet
        finally:
            session.close()
    
    def save_model_analysis(
        self,
        tweet_id: int,
        model_name: str,
        sentiment_score: float,
        confidence: float,
        reasoning: Optional[str] = None,
        raw_response: Optional[str] = None
    ) -> ModelAnalysis:
        """
        保存模型分析结果
        
        Args:
            tweet_id: 推文数据库ID
            model_name: 模型名称
            sentiment_score: 情绪分数
            confidence: 置信度
            reasoning: 推理过程
            raw_response: 原始响应
            
        Returns:
            ModelAnalysis对象
        """
        session = self.get_session()
        try:
            # 检查是否已存在
            existing = session.query(ModelAnalysis).filter(
                ModelAnalysis.tweet_id == tweet_id,
                ModelAnalysis.model_name == model_name
            ).first()
            
            if existing:
                # 更新现有记录
                existing.sentiment_score = sentiment_score
                existing.confidence = confidence
                existing.reasoning = reasoning
                existing.raw_response = raw_response
                session.commit()
                logger.debug(f"Updated analysis for tweet {tweet_id} by {model_name}")
                return existing
            
            # 创建新记录
            analysis = ModelAnalysis(
                tweet_id=tweet_id,
                model_name=model_name,
                sentiment_score=sentiment_score,
                confidence=confidence,
                reasoning=reasoning,
                raw_response=raw_response
            )
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
            logger.info(f"Saved analysis by {model_name} for tweet {tweet_id}")
            return analysis
        finally:
            session.close()
    
    def save_sentiment(
        self,
        tweet_id: int,
        composite_score: float,
        sentiment_label: str,
        btc_signal: bool = False,
        model_consensus: Optional[float] = None
    ) -> Sentiment:
        """
        保存综合情绪分析结果
        
        Args:
            tweet_id: 推文数据库ID
            composite_score: 综合分数
            sentiment_label: 情绪标签
            btc_signal: 是否包含BTC信号
            model_consensus: 模型一致性
            
        Returns:
            Sentiment对象
        """
        session = self.get_session()
        try:
            # 检查是否已存在
            existing = session.query(Sentiment).filter(
                Sentiment.tweet_id == tweet_id
            ).first()
            
            if existing:
                existing.composite_score = composite_score
                existing.sentiment_label = sentiment_label
                existing.btc_signal = btc_signal
                existing.model_consensus = model_consensus
                session.commit()
                logger.debug(f"Updated sentiment for tweet {tweet_id}")
                return existing
            
            sentiment = Sentiment(
                tweet_id=tweet_id,
                composite_score=composite_score,
                sentiment_label=sentiment_label,
                btc_signal=btc_signal,
                model_consensus=model_consensus
            )
            session.add(sentiment)
            session.commit()
            session.refresh(sentiment)
            logger.info(f"Saved sentiment for tweet {tweet_id}: {sentiment_label}")
            return sentiment
        finally:
            session.close()
    
    def get_recent_tweets_for_analysis(
        self, 
        limit: int = 100,
        hours: int = 24
    ) -> List[Tweet]:
        """
        获取需要分析的最近推文
        
        Args:
            limit: 返回数量限制
            hours: 时间范围（小时）
            
        Returns:
            Tweet对象列表
        """
        session = self.get_session()
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # 获取没有情绪分析结果的推文
            tweets = session.query(Tweet).outerjoin(
                Sentiment, Tweet.id == Sentiment.tweet_id
            ).filter(
                Tweet.fetched_at >= since,
                Sentiment.id.is_(None)
            ).limit(limit).all()
            
            # 分离对象以便在会话外使用
            result = []
            for tweet in tweets:
                session.expunge(tweet)
                result.append(tweet)
            
            logger.info(f"Found {len(result)} tweets pending analysis")
            return result
        finally:
            session.close()
    
    def calculate_market_sentiment(
        self,
        hours: int = 1
    ) -> Dict[str, Any]:
        """
        计算市场情绪指数
        
        Args:
            hours: 统计时间范围（小时）
            
        Returns:
            市场情绪统计结果字典
        """
        session = self.get_session()
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # 获取指定时间范围内的情绪数据
            results = session.query(
                Sentiment,
                KOL
            ).join(
                Tweet, Sentiment.tweet_id == Tweet.id
            ).join(
                KOL, Tweet.kol_id == KOL.id
            ).filter(
                Sentiment.created_at >= since
            ).all()
            
            if not results:
                return {
                    "market_sentiment_index": 0.5,
                    "confidence": 0.0,
                    "participation_rate": 0.0,
                    "active_kols": 0,
                    "total_kols": 0,
                    "distribution": {"bullish": 0, "neutral": 0, "bearish": 0},
                    "sample_count": 0
                }
            
            # 计算加权情绪指数
            total_weight = 0
            weighted_sum = 0
            distribution = {"bullish": 0, "neutral": 0, "bearish": 0}
            active_kol_ids = set()
            
            for sentiment, kol in results:
                weight = kol.influence_score or 1.0
                weighted_sum += sentiment.composite_score * weight
                total_weight += weight
                active_kol_ids.add(kol.id)
                
                # 统计分布
                if sentiment.sentiment_label in distribution:
                    distribution[sentiment.sentiment_label] += 1
            
            market_index = weighted_sum / total_weight if total_weight > 0 else 0.5
            
            # 计算置信度（基于样本数量）
            confidence = min(1.0, len(results) / 50)  # 50条推文达到最高置信度
            
            # 获取总KOL数
            total_kols = session.query(KOL).filter(KOL.is_active == True).count()
            participation_rate = len(active_kol_ids) / total_kols if total_kols > 0 else 0
            
            return {
                "market_sentiment_index": round(market_index, 4),
                "confidence": round(confidence, 4),
                "participation_rate": round(participation_rate, 4),
                "active_kols": len(active_kol_ids),
                "total_kols": total_kols,
                "distribution": distribution,
                "sample_count": len(results)
            }
        finally:
            session.close()
    
    def save_market_sentiment(self, data: Dict[str, Any]) -> MarketSentimentHistory:
        """
        保存市场情绪历史记录
        
        Args:
            data: 市场情绪数据
            
        Returns:
            MarketSentimentHistory对象
        """
        session = self.get_session()
        try:
            record = MarketSentimentHistory(
                market_sentiment_index=data["market_sentiment_index"],
                confidence=data["confidence"],
                participation_rate=data["participation_rate"],
                active_kols=data["active_kols"],
                total_kols=data["total_kols"],
                distribution=data["distribution"]
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(f"Saved market sentiment: {data['market_sentiment_index']}")
            return record
        finally:
            session.close()
    
    def get_latest_market_sentiment(self, hours: int = 24) -> Optional[Dict[str, Any]]:
        """
        获取最新的市场情绪记录
        
        Args:
            hours: 查询时间范围
            
        Returns:
            最新市场情绪数据或None
        """
        session = self.get_session()
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            record = session.query(MarketSentimentHistory).filter(
                MarketSentimentHistory.timestamp >= since
            ).order_by(desc(MarketSentimentHistory.timestamp)).first()
            
            if record:
                return {
                    "market_sentiment_index": record.market_sentiment_index,
                    "timestamp": record.timestamp,
                    "confidence": record.confidence,
                    "distribution": record.distribution
                }
            return None
        finally:
            session.close()


    def get_recent_tweet_urls(self, hours: int = 1, limit: int = 20) -> List[Dict[str, str]]:
        """
        获取最近推文的 URL 列表
        
        Args:
            hours: 时间范围（小时）
            limit: 最大返回数量
            
        Returns:
            推文链接列表，每个元素包含 username, content_preview, url
        """
        session = self.get_session()
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            tweets = session.query(Tweet, KOL).join(
                KOL, Tweet.kol_id == KOL.id
            ).filter(
                Tweet.fetched_at >= since,
                Tweet.url != ""
            ).order_by(
                desc(Tweet.fetched_at)
            ).limit(limit).all()
            
            result = []
            for tweet, kol in tweets:
                result.append({
                    "username": kol.username,
                    "content_preview": tweet.content[:80] + "..." if len(tweet.content) > 80 else tweet.content,
                    "url": tweet.url,
                    "posted_at": tweet.posted_at
                })
            
            return result
        finally:
            session.close()
