# tests/test_twitter_scraper.py
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from src.twitter_scraper import TwitterScraper


class TestTwitterScraper:
    @pytest.fixture
    def scraper(self):
        config = MagicMock()
        config.username = "test_user"
        config.password = "test_pass"
        config.min_followers = 100000
        config.keywords = ["BTC", "Bitcoin"]
        config.tweets_per_kol = 10
        return TwitterScraper(config)

    def test_init(self, scraper):
        """测试初始化"""
        assert scraper.config.username == "test_user"
        assert "BTC" in scraper.config.keywords

    def test_check_btc_keyword(self, scraper):
        """测试BTC关键词检测"""
        assert scraper._check_btc_keyword("Bitcoin is great") is True
        assert scraper._check_btc_keyword("ETH is rising") is False

    def test_fetch_tweets_empty(self, scraper):
        """测试推文获取（简化实现返回空列表）"""
        tweets = scraper.fetch_tweets_from_kol("test_user")
        assert len(tweets) == 0  # 简化实现返回空列表
