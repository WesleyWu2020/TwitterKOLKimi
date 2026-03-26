import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.config import Config, OpenRouterConfig, TwitterConfig, AIModelConfig
from src.scheduler import SentimentMonitor


@pytest.mark.asyncio
async def test_grok_end_to_end():
    """测试 Grok 完整流程"""
    # Mock GrokFetcher at the source module before creating SentimentMonitor
    with patch("src.grok_fetcher.GrokFetcher") as MockGrok:
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_kols_tweets = AsyncMock(return_value={
            "test_kol": [
                Mock(
                    tweet_id="123",
                    username="test_kol",
                    display_name="Test KOL",
                    content="Bitcoin looking bullish! BTC to the moon!",
                    posted_at=Mock(),
                    likes=100,
                    retweets=50,
                    has_btc_keyword=True
                )
            ]
        })
        MockGrok.return_value = mock_fetcher
        
        # 创建包含 OpenRouter 的配置，并添加 KOLs
        config = Config(
            openrouter=OpenRouterConfig(
                api_key="test-key",
                model="grok-2-1212"
            ),
            twitter=TwitterConfig(
                username="test", 
                password="test",
                kols=[{"username": "test_kol", "followers_count": 100000}]
            ),
            models={
                "kimi": AIModelConfig(api_key="k", model="m", weight=1.0)
            },
            feishu_webhook="https://test"
        )
        
        monitor = SentimentMonitor(config)
        
        # 验证使用了 Grok
        assert monitor.using_grok is True
        
        # 运行一次
        result = await monitor.run_once()
        
        # 验证 Grok 被调用
        mock_fetcher.fetch_all_kols_tweets.assert_called_once()
        
        print(f"Result: {result}")
