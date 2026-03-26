# tests/test_models.py
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, KOL, Tweet, ModelAnalysis, Sentiment


@pytest.fixture
def db_session():
    """创建内存数据库会话用于测试"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestKOL:
    def test_create_kol(self, db_session):
        kol = KOL(
            username="test_user",
            display_name="Test User",
            followers_count=150000,
            is_active=True
        )
        db_session.add(kol)
        db_session.commit()
        
        result = db_session.query(KOL).first()
        assert result.username == "test_user"
        assert result.accuracy_rate == 0.5


class TestTweet:
    def test_create_tweet(self, db_session):
        kol = KOL(username="test", display_name="Test", followers_count=100000)
        db_session.add(kol)
        db_session.commit()
        
        tweet = Tweet(
            tweet_id="123456789",
            kol_id=kol.id,
            content="Bitcoin to the moon!",
            posted_at=datetime.now(timezone.utc),
            has_btc_keyword=True
        )
        db_session.add(tweet)
        db_session.commit()
        
        result = db_session.query(Tweet).first()
        assert result.tweet_id == "123456789"
        assert result.kol_id == kol.id


class TestModelAnalysis:
    def test_unique_constraint(self, db_session):
        """测试同一推文同一模型只能有一条分析记录"""
        kol = KOL(username="test", display_name="Test", followers_count=100000)
        db_session.add(kol)
        db_session.commit()
        
        tweet = Tweet(
            tweet_id="123",
            kol_id=kol.id,
            content="Test tweet",
            posted_at=datetime.now(timezone.utc)
        )
        db_session.add(tweet)
        db_session.commit()
        
        from sqlalchemy.exc import IntegrityError
        
        # 创建第一条分析
        analysis1 = ModelAnalysis(
            tweet_id=tweet.id,
            model_name="kimi",
            sentiment_score=0.8,
            confidence=0.9
        )
        db_session.add(analysis1)
        db_session.commit()
        
        # 尝试创建重复分析应该失败
        analysis2 = ModelAnalysis(
            tweet_id=tweet.id,
            model_name="kimi",
            sentiment_score=0.5,
            confidence=0.7
        )
        db_session.add(analysis2)
        with pytest.raises(IntegrityError):
            db_session.commit()
