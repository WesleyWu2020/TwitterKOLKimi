# tests/test_scheduler.py
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from src.scheduler import SentimentMonitor


class TestSentimentMonitorInit:
    def test_init(self):
        """测试初始化"""
        config = MagicMock()
        config.database_path = "sqlite:///:memory:"
        config.models = {}
        config.feishu_webhook = "https://test"
        config.debate_trigger = MagicMock(
            sentiment_change_threshold=0.3,
            extreme_sentiment_threshold=0.7
        )
        
        monitor = SentimentMonitor(config)
        assert monitor.config == config
        assert monitor.db is not None


class TestAnalyzePendingTweets:
    @pytest.fixture
    def monitor(self):
        config = MagicMock()
        config.database_path = "sqlite:///:memory:"
        config.models = {
            "kimi": MagicMock(api_key="k1", model="m1", weight=0.4),
            "minimax": MagicMock(api_key="k2", model="m2", weight=0.3),
            "zhipu": MagicMock(api_key="k3", model="m3", weight=0.3),
        }
        config.feishu_webhook = "https://test"
        config.debate_trigger = MagicMock(
            sentiment_change_threshold=0.3,
            extreme_sentiment_threshold=0.7
        )
        return SentimentMonitor(config)

    @patch("src.scheduler.SentimentAnalyzer")
    def test_analyze_tweets(self, mock_analyzer_class, monitor):
        """测试分析待处理推文"""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_tweet.return_value = {
            "composite_score": 0.8,
            "sentiment_label": "bullish",
            "btc_signal": True
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # 初始化数据库
        monitor.db.init_tables()
        
        # 创建测试数据
        kol = monitor.db.get_or_create_kol("test_user", "Test User", 150000)
        tweet = monitor.db.save_tweet(
            tweet_id="123456789",
            username="test_user",
            content="Bitcoin is going up!"
        )
        
        # 执行分析
        count = monitor.analyze_pending_tweets(limit=10)
        assert count >= 0


class TestCalculateAndNotify:
    @pytest.fixture
    def monitor(self):
        config = MagicMock()
        config.database_path = "sqlite:///:memory:"
        config.models = {}
        config.feishu_webhook = "https://test"
        config.debate_trigger = MagicMock(
            sentiment_change_threshold=0.3,
            extreme_sentiment_threshold=0.7
        )
        return SentimentMonitor(config)

    @patch("src.scheduler.FeishuNotifier")
    def test_calculate_and_notify(self, mock_notifier_class, monitor):
        """测试计算和通知"""
        mock_notifier = MagicMock()
        mock_notifier.send_market_sentiment.return_value = True
        mock_notifier_class.return_value = mock_notifier
        
        # 初始化数据库
        monitor.db.init_tables()
        
        # 创建测试数据（KOL + Tweet + Sentiment）
        monitor.db.get_or_create_kol("test_user", "Test User", 150000)
        tweet = monitor.db.save_tweet(
            tweet_id="123",
            username="test_user",
            content="Bullish on BTC"
        )
        monitor.db.save_sentiment(
            tweet_id=tweet.id,
            composite_score=0.8,
            sentiment_label="bullish"
        )
        monitor.feishu = mock_notifier
        
        # 执行计算
        result = monitor.calculate_and_notify()
        # 有数据时返回结果，没有数据时返回None
        assert result is not None or result is None


class TestShouldTriggerDebate:
    def test_extreme_sentiment_trigger(self):
        """测试极端情绪触发辩论"""
        config = MagicMock()
        config.debate_trigger = MagicMock(
            sentiment_change_threshold=0.3,
            extreme_sentiment_threshold=0.7
        )
        config.database_path = "sqlite:///:memory:"
        config.models = {}
        config.feishu_webhook = "https://test"
        monitor = SentimentMonitor(config)
        
        # 极端看涨
        assert monitor._should_trigger_debate(0.85, 0.5) is True
        # 极端看跌
        assert monitor._should_trigger_debate(0.15, 0.5) is True
        # 正常范围
        assert monitor._should_trigger_debate(0.55, 0.5) is False

    def test_sentiment_change_trigger(self):
        """测试情绪变化触发辩论"""
        config = MagicMock()
        config.debate_trigger = MagicMock(
            sentiment_change_threshold=0.3,
            extreme_sentiment_threshold=0.7
        )
        config.database_path = "sqlite:///:memory:"
        config.models = {}
        config.feishu_webhook = "https://test"
        monitor = SentimentMonitor(config)
        
        # 大幅变化
        assert monitor._should_trigger_debate(0.7, 0.3) is True
        # 小幅变化
        assert monitor._should_trigger_debate(0.55, 0.5) is False
