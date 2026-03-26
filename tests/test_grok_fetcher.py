# tests/test_grok_fetcher.py
"""Tests for Grok fetcher module."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from src.grok_fetcher import TweetData, GrokFetcher


class TestTweetData:
    """测试 TweetData dataclass"""

    def test_tweet_data_creation(self):
        """测试创建 TweetData 对象"""
        tweet = TweetData(
            tweet_id="123456789",
            username="elonmusk",
            display_name="Elon Musk",
            content="Bitcoin to the moon!",
            posted_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            likes=1000,
            retweets=500,
            has_btc_keyword=True
        )
        assert tweet.tweet_id == "123456789"
        assert tweet.username == "elonmusk"
        assert tweet.display_name == "Elon Musk"
        assert tweet.content == "Bitcoin to the moon!"
        assert tweet.likes == 1000
        assert tweet.retweets == 500
        assert tweet.has_btc_keyword is True

    def test_tweet_data_defaults(self):
        """测试 TweetData 默认值"""
        tweet = TweetData(
            tweet_id="123",
            username="test",
            display_name="Test User",
            content="Test content",
            posted_at=datetime.now(timezone.utc)
        )
        assert tweet.likes == 0
        assert tweet.retweets == 0
        assert tweet.has_btc_keyword is False

    def test_tweet_data_to_dict(self):
        """测试 TweetData 转换为字典"""
        tweet = TweetData(
            tweet_id="123",
            username="test",
            display_name="Test User",
            content="Test content",
            posted_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            likes=100
        )
        data = asdict(tweet)
        assert data["tweet_id"] == "123"
        assert data["likes"] == 100


class TestGrokFetcherInit:
    """测试 GrokFetcher 初始化"""

    def test_init_with_config(self):
        """测试使用配置初始化"""
        config = MagicMock()
        config.api_key = "test-api-key"
        config.base_url = "https://api.test.com"
        config.model = "grok-2-1212"
        config.max_tokens = 4000
        config.temperature = 0.3

        fetcher = GrokFetcher(config)
        assert fetcher.config == config
        assert fetcher.client is not None
        assert fetcher.client.base_url == "https://api.test.com"
        assert "Authorization" in fetcher.client.headers
        assert "Bearer test-api-key" in fetcher.client.headers["Authorization"]

    def test_init_headers(self):
        """测试初始化 headers"""
        config = MagicMock()
        config.api_key = "test-key"
        config.base_url = "https://api.test.com"

        fetcher = GrokFetcher(config)
        headers = fetcher.client.headers
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["HTTP-Referer"] == "https://github.com/WesleyWu2020/TwitterKOLKimi"
        assert headers["X-Title"] == "Crypto KOL Sentiment Monitor"


class TestBuildPrompt:
    """测试 prompt 构建"""

    @pytest.fixture
    def fetcher(self):
        config = MagicMock()
        config.api_key = "test-key"
        config.base_url = "https://api.test.com"
        return GrokFetcher(config)

    def test_build_prompt_contains_username(self, fetcher):
        """测试 prompt 包含用户名"""
        prompt = fetcher._build_prompt("elonmusk", 10)
        assert "elonmusk" in prompt

    def test_build_prompt_contains_count(self, fetcher):
        """测试 prompt 包含推文数量"""
        prompt = fetcher._build_prompt("testuser", 5)
        assert "5" in prompt or "five" in prompt.lower()

    def test_build_prompt_contains_json_format(self, fetcher):
        """测试 prompt 要求 JSON 格式"""
        prompt = fetcher._build_prompt("testuser", 10)
        assert "JSON" in prompt

    def test_build_prompt_contains_required_fields(self, fetcher):
        """测试 prompt 包含必要字段要求"""
        prompt = fetcher._build_prompt("testuser", 10)
        assert "tweet_id" in prompt
        assert "content" in prompt
        assert "posted_at" in prompt


class TestParseResponse:
    """测试响应解析"""

    @pytest.fixture
    def fetcher(self):
        config = MagicMock()
        config.api_key = "test-key"
        config.base_url = "https://api.test.com"
        return GrokFetcher(config)

    def test_parse_valid_json_response(self, fetcher):
        """测试解析有效 JSON 响应"""
        response_text = '''
        {
            "tweets": [
                {
                    "tweet_id": "123",
                    "username": "elonmusk",
                    "display_name": "Elon Musk",
                    "content": "Bitcoin is great!",
                    "posted_at": "2024-01-01T12:00:00Z",
                    "likes": 1000,
                    "retweets": 500
                }
            ]
        }
        '''
        tweets = fetcher._parse_grok_response(response_text, "elonmusk")
        assert len(tweets) == 1
        assert tweets[0].tweet_id == "123"
        assert tweets[0].username == "elonmusk"
        assert tweets[0].content == "Bitcoin is great!"
        assert tweets[0].has_btc_keyword is True  # 包含 Bitcoin 关键词

    def test_parse_markdown_json_response(self, fetcher):
        """测试解析 markdown 格式 JSON 响应"""
        response_text = '''```json
        {
            "tweets": [
                {
                    "tweet_id": "456",
                    "username": "test",
                    "display_name": "Test",
                    "content": "ETH news",
                    "posted_at": "2024-01-01T10:00:00Z",
                    "likes": 100,
                    "retweets": 50
                }
            ]
        }
        ```'''
        tweets = fetcher._parse_grok_response(response_text, "test")
        assert len(tweets) == 1
        assert tweets[0].tweet_id == "456"

    def test_parse_empty_tweets(self, fetcher):
        """测试解析空推文列表"""
        response_text = '{"tweets": []}'
        tweets = fetcher._parse_grok_response(response_text, "test")
        assert len(tweets) == 0

    def test_parse_invalid_json(self, fetcher):
        """测试解析无效 JSON"""
        response_text = "not valid json"
        tweets = fetcher._parse_grok_response(response_text, "test")
        assert len(tweets) == 0

    def test_parse_missing_tweets_key(self, fetcher):
        """测试解析缺少 tweets 键的响应"""
        response_text = '{"data": []}'
        tweets = fetcher._parse_grok_response(response_text, "test")
        assert len(tweets) == 0

    def test_parse_btc_keyword_detection(self, fetcher):
        """测试 BTC 关键词检测"""
        response_text = '''
        {
            "tweets": [
                {
                    "tweet_id": "1",
                    "username": "test",
                    "display_name": "Test",
                    "content": "I love Bitcoin!",
                    "posted_at": "2024-01-01T10:00:00Z",
                    "likes": 10,
                    "retweets": 5
                },
                {
                    "tweet_id": "2",
                    "username": "test",
                    "display_name": "Test",
                    "content": "Just a normal day",
                    "posted_at": "2024-01-01T11:00:00Z",
                    "likes": 5,
                    "retweets": 1
                }
            ]
        }
        '''
        tweets = fetcher._parse_grok_response(response_text, "test")
        assert len(tweets) == 2
        assert tweets[0].has_btc_keyword is True
        assert tweets[1].has_btc_keyword is False


class TestFetchTweets:
    """测试异步获取推文"""

    @pytest.fixture
    def fetcher(self):
        config = MagicMock()
        config.api_key = "test-key"
        config.base_url = "https://api.test.com"
        config.model = "grok-2-1212"
        config.max_tokens = 4000
        config.temperature = 0.3
        return GrokFetcher(config)

    @pytest.mark.asyncio
    async def test_fetch_tweets_success(self, fetcher):
        """测试成功获取推文"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '''{"tweets": [{
                        "tweet_id": "123",
                        "username": "test",
                        "display_name": "Test",
                        "content": "BTC is rising!",
                        "posted_at": "2024-01-01T12:00:00Z",
                        "likes": 100,
                        "retweets": 50
                    }]}'''
                }
            }]
        }

        with patch.object(fetcher.client, "post", new_callable=AsyncMock, return_value=mock_response):
            tweets = await fetcher.fetch_tweets_from_kol("testuser", 5)
            assert len(tweets) == 1
            assert tweets[0].tweet_id == "123"

    @pytest.mark.asyncio
    async def test_fetch_tweets_api_error(self, fetcher):
        """测试 API 错误处理"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(fetcher.client, "post", new_callable=AsyncMock, return_value=mock_response):
            tweets = await fetcher.fetch_tweets_from_kol("testuser", 5)
            assert len(tweets) == 0

    @pytest.mark.asyncio
    async def test_fetch_tweets_exception(self, fetcher):
        """测试异常处理"""
        with patch.object(fetcher.client, "post", new_callable=AsyncMock, side_effect=Exception("Network error")):
            tweets = await fetcher.fetch_tweets_from_kol("testuser", 5)
            assert len(tweets) == 0

    @pytest.mark.asyncio
    async def test_fetch_all_kols_tweets(self, fetcher):
        """测试批量获取多个 KOL 推文"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '''{"tweets": [{
                        "tweet_id": "1",
                        "username": "user1",
                        "display_name": "User 1",
                        "content": "BTC up!",
                        "posted_at": "2024-01-01T12:00:00Z",
                        "likes": 100,
                        "retweets": 50
                    }]}'''
                }
            }]
        }

        kols = ["user1", "user2"]
        with patch.object(fetcher.client, "post", new_callable=AsyncMock, return_value=mock_response):
            results = await fetcher.fetch_all_kols_tweets(kols, 5)
            assert len(results) == 2
            assert "user1" in results
            assert "user2" in results
            assert len(results["user1"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_all_kols_empty_list(self, fetcher):
        """测试空 KOL 列表"""
        results = await fetcher.fetch_all_kols_tweets([], 5)
        assert len(results) == 0
