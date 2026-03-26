# tests/test_debate_engine.py
import pytest
from unittest.mock import patch, MagicMock
from src.debate_engine import DebateEngine


class TestDebateEngineInit:
    def test_init(self):
        """测试初始化"""
        config = MagicMock()
        config.models = {
            "zhipu": MagicMock(api_key="key1", model="model1", base_url="http://test"),
            "minimax": MagicMock(api_key="key2", model="model2", base_url="http://test"),
        }
        engine = DebateEngine(config)
        assert engine.config == config


class TestDebatePrompts:
    def test_proponent_prompt(self):
        """测试正方Prompt构建"""
        config = MagicMock()
        config.models = {}
        engine = DebateEngine(config)
        
        prompt = engine._build_proponent_prompt_1("bullish", 0.8, [{"reasoning": "test"}])
        assert "正方" in prompt or "bullish" in prompt.lower()

    def test_opponent_prompt(self):
        """测试反方Prompt构建"""
        config = MagicMock()
        config.models = {}
        engine = DebateEngine(config)
        
        prompt = engine._build_opponent_prompt("Bullish stance", ["point1"])
        assert "反方" in prompt or "挑战" in prompt


class TestDebateExecution:
    @pytest.fixture
    def engine(self):
        config = MagicMock()
        config.models = {
            "zhipu": MagicMock(api_key="key1", model="model1", base_url="http://test"),
            "minimax": MagicMock(api_key="key2", model="model2", base_url="http://test"),
        }
        return DebateEngine(config)

    @patch("src.debate_engine.DebateEngine._call_model")
    def test_debate_execution(self, mock_call, engine):
        """测试辩论执行流程"""
        # _call_model 返回的是原始字符串，不是解析后的字典
        mock_call.side_effect = [
            # Round 1: Proponent - 返回模型原始输出字符串
            """
            立场: bullish
            置信度: 0.8
            关键论点:
            1. BTC突破关键阻力
            2. 机构资金流入
            """,
            # Round 2: Opponent
            """
            挑战点:
            1. 市场过度乐观
            2. 监管风险
            风险因子评估:
            高风险因子数: 1
            中风险因子数: 0
            """,
            # Round 3: Response
            """
            承认的有效点:
            1. 监管风险确实存在
            反驳的点:
            1. 机构流入真实
            调整后立场: bullish
            调整后置信度: 0.75
            最终建议:
            行动: cautious_bullish
            风险等级: medium
            理由: 谨慎乐观
            """
        ]
        
        result = engine.debate(
            sentiment_label="bullish",
            market_index=0.75,
            supporting_evidence=[{"reasoning": "BTC突破"}]
        )
        
        assert "final_recommendation" in result
        assert result["proponent_stance"] == "bullish"
        assert result["opponent_high_risk_count"] == 1


class TestParseFunctions:
    def test_parse_proponent_output(self):
        """测试解析正方输出"""
        config = MagicMock()
        config.models = {}
        engine = DebateEngine(config)
        
        output = """
        立场: bullish
        置信度: 0.8
        关键论点: ["BTC突破阻力", "机构入场"]
        """
        result = engine._parse_proponent_output(output)
        assert result["stance"] == "bullish"
        assert result["confidence"] == 0.8

    def test_parse_opponent_output(self):
        """测试解析反方输出"""
        config = MagicMock()
        config.models = {}
        engine = DebateEngine(config)
        
        output = """
        挑战点:
        1. 市场过度乐观
        2. 监管风险
        风险因子评估:
        高风险因子数: 2
        中风险因子数: 1
        """
        result = engine._parse_opponent_output(output)
        assert len(result["challenges"]) == 2
        assert result["high_risk_count"] == 2
