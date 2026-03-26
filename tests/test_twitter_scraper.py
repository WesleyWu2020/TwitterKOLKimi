# tests/test_twitter_scraper.py
"""Twitter 爬虫测试"""
import pytest
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.twitter_scraper import TwitterScraper, TweetData


class TestTweetData:
    """测试 TweetData 数据类"""
    
    def test_tweet_data_creation(self):
        """测试创建 TweetData 对象"""
        tweet = TweetData(
            tweet_id="123456789",
            username="test_user",
            display_name="Test User",
            content="Bitcoin to the moon!",
            posted_at=datetime.now(timezone.utc),
            likes=100,
            retweets=50,
            has_btc_keyword=True
        )
        
        assert tweet.tweet_id == "123456789"
        assert tweet.username == "test_user"
        assert tweet.has_btc_keyword is True


class TestTwitterScraperInit:
    """测试 TwitterScraper 初始化"""
    
    @pytest.fixture
    def mock_config(self):
        """创建 Mock 配置"""
        config = Mock()
        config.username = "test_user"
        config.password = "test_pass"
        config.min_followers = 100000
        config.keywords = ["BTC", "Bitcoin", "比特币"]
        config.tweets_per_kol = 10
        return config
    
    def test_init_with_defaults(self, mock_config):
        """测试默认初始化"""
        scraper = TwitterScraper(mock_config)
        
        assert scraper.config == mock_config
        assert scraper.headless is True
        assert scraper.is_logged_in is False
    
    def test_init_with_custom_params(self, mock_config):
        """测试自定义参数初始化"""
        scraper = TwitterScraper(
            mock_config,
            headless=False,
            cookie_file="/tmp/test_cookies.json"
        )
        
        assert scraper.headless is False
        assert scraper.cookie_file == Path("/tmp/test_cookies.json")


class TestCheckBtcKeyword:
    """测试 BTC 关键词检查"""
    
    @pytest.fixture
    def scraper(self):
        config = Mock()
        config.keywords = ["BTC", "Bitcoin", "以太坊"]
        return TwitterScraper(config)
    
    def test_contains_btc(self, scraper):
        """测试包含 BTC 关键词"""
        assert scraper._check_btc_keyword("Bitcoin is going up!") is True
        assert scraper._check_btc_keyword("BTC to the moon") is True
        assert scraper._check_btc_keyword("看好以太坊") is True
    
    def test_not_contains_btc(self, scraper):
        """测试不包含 BTC 关键词"""
        assert scraper._check_btc_keyword("Hello world") is False
        assert scraper._check_btc_keyword("Stock market today") is False
    
    def test_empty_text(self, scraper):
        """测试空文本"""
        assert scraper._check_btc_keyword("") is False
        assert scraper._check_btc_keyword(None) is False


class TestRateLimit:
    """测试限流功能"""
    
    @pytest.fixture
    def scraper(self, tmp_path):
        config = Mock()
        config.username = "test"
        scraper = TwitterScraper(config)
        scraper.rate_limit_file = tmp_path / "rate_limit.json"
        return scraper
    
    def test_check_rate_limit_no_file(self, scraper):
        """测试没有限流文件时返回 True"""
        assert scraper._check_rate_limit() is True
    
    def test_check_rate_limit_within_limit(self, scraper):
        """测试在限制内"""
        # 创建限流文件，计数为 2
        with open(scraper.rate_limit_file, "w") as f:
            json.dump({
                "last_reset": datetime.now(timezone.utc).isoformat(),
                "count": 2
            }, f)
        
        assert scraper._check_rate_limit() is True
    
    def test_check_rate_limit_exceeded(self, scraper):
        """测试超过限制"""
        # 创建限流文件，计数超过限制
        with open(scraper.rate_limit_file, "w") as f:
            json.dump({
                "last_reset": datetime.now(timezone.utc).isoformat(),
                "count": 10
            }, f)
        
        assert scraper._check_rate_limit() is False
    
    def test_rate_limit_reset_after_hour(self, scraper):
        """测试1小时后重置"""
        from datetime import timedelta
        # 创建限流文件，时间超过1小时
        with open(scraper.rate_limit_file, "w") as f:
            json.dump({
                "last_reset": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                "count": 10
            }, f)
        
        assert scraper._check_rate_limit() is True


class TestRandomization:
    """测试随机化功能"""
    
    @pytest.fixture
    def scraper(self):
        config = Mock()
        return TwitterScraper(config)
    
    def test_random_delay_range(self, scraper):
        """测试随机延迟在范围内"""
        delay = scraper._get_random_delay(3.0, 10.0)
        assert 3.0 <= delay <= 10.0
    
    def test_random_viewport(self, scraper):
        """测试随机视窗"""
        viewport = scraper._get_random_viewport()
        assert "width" in viewport
        assert "height" in viewport
        assert viewport in scraper.VIEWPORT_SIZES
    
    def test_random_user_agent(self, scraper):
        """测试随机 User-Agent"""
        ua = scraper._get_random_user_agent()
        assert ua in scraper.USER_AGENTS
        assert "Mozilla" in ua


class TestCookiePersistence:
    """测试 Cookie 持久化"""
    
    @pytest.fixture
    def scraper(self, tmp_path):
        config = Mock()
        scraper = TwitterScraper(config)
        scraper.cookie_file = tmp_path / "cookies.json"
        return scraper
    
    def test_save_cookies_no_context(self, scraper):
        """测试没有 context 时保存不报错"""
        scraper.context = None
        scraper._save_cookies()  # 应该不抛出异常
    
    def test_load_cookies_no_file(self, scraper):
        """测试没有文件时返回空列表"""
        cookies = scraper._load_cookies()
        assert cookies == []
    
    def test_load_cookies_with_file(self, scraper):
        """测试加载 cookie 文件"""
        test_cookies = [{"name": "test", "value": "123"}]
        with open(scraper.cookie_file, "w") as f:
            json.dump(test_cookies, f)
        
        cookies = scraper._load_cookies()
        assert cookies == test_cookies


class TestParseTweetData:
    """测试推文解析"""
    
    @pytest.fixture
    def scraper(self):
        config = Mock()
        config.keywords = ["BTC"]
        return TwitterScraper(config)
    
    def test_parse_valid_tweet(self, scraper):
        """测试解析有效推文数据"""
        raw_data = {
            "id": "123456789",
            "username": "test_user",
            "name": "Test User",
            "text": "Bitcoin is great! #BTC",
            "public_metrics": {
                "like_count": 100,
                "retweet_count": 50
            }
        }
        
        tweet = scraper.parse_tweet_data(raw_data)
        
        assert tweet is not None
        assert tweet.tweet_id == "123456789"
        assert tweet.content == "Bitcoin is great! #BTC"
        assert tweet.has_btc_keyword is True
        assert tweet.likes == 100
    
    def test_parse_invalid_data(self, scraper):
        """测试解析无效数据"""
        tweet = scraper.parse_tweet_data({})
        assert tweet is None
    
    def test_parse_missing_optional_fields(self, scraper):
        """测试解析缺少可选字段的数据"""
        raw_data = {
            "id": "123",
            "username": "user",
            "name": "User",
            "text": "Hello"
        }
        
        tweet = scraper.parse_tweet_data(raw_data)
        
        assert tweet is not None
        assert tweet.likes == 0
        assert tweet.retweets == 0


class TestFetchWithRateLimit:
    """测试带限流的抓取"""
    
    @pytest.fixture
    def scraper(self, tmp_path):
        config = Mock()
        config.username = "test"
        config.min_followers = 1000
        config.keywords = ["BTC"]
        scraper = TwitterScraper(config)
        scraper.rate_limit_file = tmp_path / "rate_limit.json"
        return scraper
    
    def test_fetch_with_rate_limit_exceeded(self, scraper):
        """测试超过限流时返回空列表"""
        # 设置超过限流
        with open(scraper.rate_limit_file, "w") as f:
            json.dump({
                "last_reset": datetime.now(timezone.utc).isoformat(),
                "count": 100
            }, f)
        
        result = scraper.fetch_tweets_from_kol("test_user")
        assert result == []


class TestFetchAllKols:
    """测试批量抓取 KOL"""
    
    @pytest.fixture
    def scraper(self, tmp_path):
        config = Mock()
        config.username = "test"
        config.min_followers = 100000
        config.keywords = ["BTC"]
        scraper = TwitterScraper(config)
        scraper.rate_limit_file = tmp_path / "rate_limit.json"
        # Mock fetch_tweets_from_kol 避免实际调用 Playwright
        scraper.fetch_tweets_from_kol = Mock(return_value=[])
        return scraper
    
    def test_fetch_all_kols_empty_list(self, scraper):
        """测试空列表"""
        result = scraper.fetch_all_kols_tweets([])
        assert result == []
    
    def test_fetch_all_kols_skip_low_followers(self, scraper):
        """测试跳过低粉丝数 KOL"""
        kols = [
            {"username": "big_kol", "followers_count": 200000},
            {"username": "small_kol", "followers_count": 1000},  # 低于阈值
        ]
        
        scraper.fetch_all_kols_tweets(kols)
        
        # 只抓取了一个（跳过了 small_kol）
        assert scraper.fetch_tweets_from_kol.call_count == 1
        scraper.fetch_tweets_from_kol.assert_called_with("big_kol", 10)
