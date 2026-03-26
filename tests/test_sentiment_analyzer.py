# tests/test_sentiment_analyzer.py
import pytest
from unittest.mock import patch, MagicMock
from src.sentiment_analyzer import SentimentAnalyzer, AnalysisResult


class TestAnalysisResult:
    def test_result_creation(self):
        """测试结果对象创建"""
        result = AnalysisResult(
            model_name="kimi",
            sentiment_score=0.8,
            confidence=0.9,
            reasoning="Bullish signal"
        )
        assert result.model_name == "kimi"
        assert result.sentiment_score == 0.8
        assert result.confidence == 0.9


class TestSentimentAnalyzerInit:
    def test_init(self):
        """测试初始化"""
        config = MagicMock()
        config.models = {
            "kimi": MagicMock(api_key="key1", model="model1", weight=0.4, base_url="http://test"),
            "minimax": MagicMock(api_key="key2", model="model2", weight=0.3, base_url="http://test"),
            "zhipu": MagicMock(api_key="key3", model="model3", weight=0.3, base_url="http://test"),
        }
        analyzer = SentimentAnalyzer(config)
        assert len(analyzer.model_configs) == 3
        assert "kimi" in analyzer.model_configs


class TestParseResponse:
    def test_parse_valid_response(self):
        """测试解析有效响应"""
        config = MagicMock()
        config.models = {}
        analyzer = SentimentAnalyzer(config)
        
        response = """
        情绪分数: 0.75
        置信度: 0.85
        推理: BTC价格突破关键阻力位
        """
        result = analyzer._parse_response(response, "kimi")
        assert result is not None
        assert result.sentiment_score == 0.75
        assert result.confidence == 0.85
        assert result.model_name == "kimi"

    def test_parse_invalid_response(self):
        """测试解析无效响应"""
        config = MagicMock()
        config.models = {}
        analyzer = SentimentAnalyzer(config)
        
        result = analyzer._parse_response("invalid response", "kimi")
        assert result is None


class TestCalculateCompositeScore:
    def test_weighted_calculation(self):
        """测试加权计算"""
        config = MagicMock()
        config.models = {
            "kimi": MagicMock(weight=0.5),
            "minimax": MagicMock(weight=0.5),
        }
        analyzer = SentimentAnalyzer(config)
        
        results = [
            AnalysisResult("kimi", 0.8, 0.9, "test"),
            AnalysisResult("minimax", 0.6, 0.8, "test")
        ]
        
        score = analyzer.calculate_composite_score(results)
        # (0.8*0.5 + 0.6*0.5) = 0.7
        assert abs(score - 0.7) < 0.01


class TestAnalyzeTweet:
    @pytest.fixture
    def analyzer(self):
        config = MagicMock()
        config.models = {
            "kimi": MagicMock(api_key="key1", model="model1", weight=0.4, base_url="http://test"),
            "minimax": MagicMock(api_key="key2", model="model2", weight=0.3, base_url="http://test"),
            "zhipu": MagicMock(api_key="key3", model="model3", weight=0.3, base_url="http://test"),
        }
        return SentimentAnalyzer(config)

    @patch("src.sentiment_analyzer.SentimentAnalyzer._call_model_api")
    def test_analyze_with_mock(self, mock_call, analyzer):
        """测试分析功能（Mock API调用）"""
        mock_call.return_value = AnalysisResult(
            model_name="kimi",
            sentiment_score=0.8,
            confidence=0.9,
            reasoning="Bullish"
        )
        
        result = analyzer.analyze_tweet("Bitcoin is going up!")
        assert "composite_score" in result
        assert "sentiment_label" in result
        assert "model_results" in result
