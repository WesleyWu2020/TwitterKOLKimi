# tests/test_feishu_notifier.py
import pytest
from unittest.mock import patch, MagicMock
from src.feishu_notifier import FeishuNotifier


class TestFeishuNotifierInit:
    def test_init(self):
        """测试初始化"""
        notifier = FeishuNotifier(
            webhook_url="https://test.webhook",
            secret="test_secret"
        )
        assert notifier.webhook_url == "https://test.webhook"
        assert notifier.secret == "test_secret"


class TestMessageFormatting:
    def test_format_sentiment_message(self):
        """测试情绪消息格式化"""
        notifier = FeishuNotifier("https://test")
        
        data = {
            "market_sentiment_index": 0.75,
            "confidence": 0.85,
            "distribution": {"bullish": 5, "neutral": 2, "bearish": 1},
            "active_kols": 8
        }
        
        msg = notifier._format_sentiment_message(data)
        assert "市场情绪" in msg
        assert "0.75" in msg or "75" in msg

    def test_format_debate_message(self):
        """测试辩论消息格式化"""
        notifier = FeishuNotifier("https://test")
        
        debate_result = {
            "proponent_stance": "bullish",
            "proponent_confidence": 0.8,
            "opponent_high_risk_count": 1,
            "opponent_challenges": ["风险1"],
            "final_recommendation": {"action": "cautious_bullish"}
        }
        
        msg = notifier._format_debate_message(debate_result)
        assert "辩论" in msg or "bullish" in msg.lower()


class TestSendNotification:
    @patch("src.feishu_notifier.requests.post")
    def test_send_market_sentiment_success(self, mock_post):
        """测试发送市场情绪通知成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0}
        mock_post.return_value = mock_response
        
        notifier = FeishuNotifier("https://test.webhook")
        data = {
            "market_sentiment_index": 0.75,
            "confidence": 0.85,
            "distribution": {"bullish": 5, "neutral": 2, "bearish": 1},
            "active_kols": 8
        }
        
        result = notifier.send_market_sentiment(data)
        assert result is True
        mock_post.assert_called_once()

    @patch("src.feishu_notifier.requests.post")
    def test_send_market_sentiment_failure(self, mock_post):
        """测试发送市场情绪通知失败"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        notifier = FeishuNotifier("https://test.webhook")
        data = {
            "market_sentiment_index": 0.75,
            "confidence": 0.85,
            "distribution": {"bullish": 5, "neutral": 2, "bearish": 1},
            "active_kols": 8
        }
        
        result = notifier.send_market_sentiment(data)
        assert result is False

    @patch("src.feishu_notifier.requests.post")
    def test_send_debate_result(self, mock_post):
        """测试发送辩论结果通知"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0}
        mock_post.return_value = mock_response
        
        notifier = FeishuNotifier("https://test.webhook")
        debate_result = {
            "proponent_stance": "bullish",
            "proponent_confidence": 0.8,
            "opponent_challenges": ["风险1"],
            "final_recommendation": {"action": "cautious_bullish"}
        }
        
        result = notifier.send_debate_result(debate_result)
        assert result is True
