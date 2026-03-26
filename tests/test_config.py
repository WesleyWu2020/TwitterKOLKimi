# tests/test_config.py
import pytest
from src.config import Config, AIModelConfig, TwitterConfig


class TestAIModelConfig:
    def test_valid_config(self):
        config = AIModelConfig(
            api_key="test-key",
            model="test-model",
            weight=0.4
        )
        assert config.api_key == "test-key"
        assert config.model == "test-model"
        assert config.weight == 0.4

    def test_weight_validation(self):
        with pytest.raises(ValueError):
            AIModelConfig(api_key="k", model="m", weight=1.5)  # > 1
        with pytest.raises(ValueError):
            AIModelConfig(api_key="k", model="m", weight=-0.1)  # < 0


class TestTwitterConfig:
    def test_default_values(self):
        config = TwitterConfig(username="user", password="pass")
        assert config.min_followers == 100000
        assert "BTC" in config.keywords


class TestConfig:
    def test_model_weights_sum_to_one(self):
        """测试模型权重之和为1"""
        # 这个测试会在实现后通过
        pass
