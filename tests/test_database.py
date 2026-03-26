# tests/test_database.py
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, KOL, Tweet, ModelAnalysis, Sentiment, MarketSentimentHistory
from src.database import Database


@pytest.fixture
def db_instance():
    """创建内存数据库实例用于测试"""
    instance = Database("sqlite:///:memory:")
    instance.init_tables()
    yield instance
    instance.close()


class TestDatabaseInit:
    def test_init_tables(self, db_instance):
        """测试初始化表"""
        # 验证所有表都已创建
        from sqlalchemy import inspect
        inspector = inspect(db_instance.engine)
        tables = inspector.get_table_names()
        assert "kols" in tables
        assert "tweets" in tables
        assert "model_analyses" in tables
        assert "sentiments" in tables
        assert "market_sentiment_history" in tables
        assert "debate_records" in tables


class TestGetOrCreateKOL:
    def test_create_new_kol(self, db_instance):
        """测试创建新KOL"""
        kol = db_instance.get_or_create_kol("test_user", "Test User", 150000)
        assert kol.username == "test_user"
        assert kol.display_name == "Test User"
        assert kol.followers_count == 150000
        
    def test_get_existing_kol(self, db_instance):
        """测试获取已存在的KOL"""
        kol1 = db_instance.get_or_create_kol("test_user", "Test User", 150000)
        kol2 = db_instance.get_or_create_kol("test_user", "Updated Name", 200000)
        assert kol1.id == kol2.id
        assert kol2.followers_count == 200000


class TestSaveTweet:
    def test_save_new_tweet(self, db_instance):
        """测试保存新推文"""
        kol = db_instance.get_or_create_kol("test_user", "Test User", 150000)
        tweet = db_instance.save_tweet(
            tweet_id="123456789",
            username="test_user",
            content="Bitcoin is rising!",
            posted_at=datetime.now(timezone.utc),
            has_btc_keyword=True
        )
        assert tweet.tweet_id == "123456789"
        assert tweet.kol_id == kol.id
        assert tweet.has_btc_keyword is True


class TestSaveModelAnalysis:
    def test_save_analysis(self, db_instance):
        """测试保存模型分析"""
        db_instance.get_or_create_kol("test_user", "Test User", 150000)
        tweet = db_instance.save_tweet(
            tweet_id="123456789",
            username="test_user",
            content="Test content"
        )
        analysis = db_instance.save_model_analysis(
            tweet_id=tweet.id,
            model_name="kimi",
            sentiment_score=0.8,
            confidence=0.9,
            reasoning="Bullish signal"
        )
        assert analysis.model_name == "kimi"
        assert analysis.sentiment_score == 0.8


class TestSaveSentiment:
    def test_save_sentiment(self, db_instance):
        """测试保存综合情绪"""
        db_instance.get_or_create_kol("test_user", "Test User", 150000)
        tweet = db_instance.save_tweet(
            tweet_id="123456789",
            username="test_user",
            content="Test content"
        )
        sentiment = db_instance.save_sentiment(
            tweet_id=tweet.id,
            composite_score=0.75,
            sentiment_label="bullish",
            btc_signal=True
        )
        assert sentiment.composite_score == 0.75
        assert sentiment.sentiment_label == "bullish"


class TestGetRecentTweetsForAnalysis:
    def test_get_unanalyzed_tweets(self, db_instance):
        """测试获取未分析推文"""
        db_instance.get_or_create_kol("test_user", "Test User", 150000)
        tweet = db_instance.save_tweet(
            tweet_id="123456789",
            username="test_user",
            content="Test content"
        )
        tweets = db_instance.get_recent_tweets_for_analysis(limit=10)
        assert len(tweets) == 1
        assert tweets[0].tweet_id == "123456789"


class TestCalculateMarketSentiment:
    def test_calculate_market_sentiment(self, db_instance):
        """测试计算市场情绪"""
        # 创建KOL和推文
        kol = db_instance.get_or_create_kol("test_user", "Test User", 150000)
        tweet = db_instance.save_tweet(
            tweet_id="123",
            username="test_user",
            content="Bullish on BTC"
        )
        db_instance.save_sentiment(
            tweet_id=tweet.id,
            composite_score=0.8,
            sentiment_label="bullish",
            btc_signal=True
        )
        
        result = db_instance.calculate_market_sentiment()
        assert result["market_sentiment_index"] > 0
        assert result["active_kols"] >= 0
