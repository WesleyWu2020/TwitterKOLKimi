# tests/test_market_calculator.py
import pytest
from unittest.mock import MagicMock
from src.market_calculator import MarketCalculator


class TestMarketCalculatorInit:
    def test_init(self):
        """测试初始化"""
        calc = MarketCalculator()
        assert calc is not None


class TestCalculateKOLInfluenceWeight:
    def test_influence_weight(self):
        """测试KOL影响力权重计算"""
        calc = MarketCalculator()
        
        # 粉丝数越多，权重越高
        weight1 = calc.calculate_kol_influence_weight(100000, 0.5)
        weight2 = calc.calculate_kol_influence_weight(1000000, 0.6)
        
        assert weight2 > weight1
        assert weight1 > 0


class TestCalculateMarketSentiment:
    def test_empty_sentiments(self):
        """测试空情绪数据"""
        calc = MarketCalculator()
        result = calc.calculate_market_sentiment([])
        
        assert result["market_index"] == 0.5
        assert result["confidence"] == 0.0

    def test_with_sentiments(self):
        """测试有情绪数据的情况"""
        calc = MarketCalculator()
        
        sentiments = [
            {"score": 0.8, "weight": 1.0},
            {"score": 0.6, "weight": 1.5},
            {"score": 0.9, "weight": 1.0},
        ]
        
        result = calc.calculate_market_sentiment(sentiments)
        
        assert 0 <= result["market_index"] <= 1
        assert result["confidence"] > 0
        assert "distribution" in result


class TestSentimentDistribution:
    def test_distribution_calculation(self):
        """测试情绪分布统计"""
        calc = MarketCalculator()
        
        labels = ["bullish", "bullish", "neutral", "bearish", "bullish"]
        dist = calc.calculate_sentiment_distribution(labels)
        
        assert dist["bullish"] == 3
        assert dist["neutral"] == 1
        assert dist["bearish"] == 1
        assert dist["total"] == 5
