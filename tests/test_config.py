# tests/test_config.py
import os
import tempfile
import pytest
from src.config import Config, AIModelConfig, TwitterConfig, DebateTriggerConfig, OpenRouterConfig, load_config


class TestAIModelConfig:
    def test_valid_config(self) -> None:
        config = AIModelConfig(
            api_key="test-key",
            model="test-model",
            weight=0.4
        )
        assert config.api_key == "test-key"
        assert config.model == "test-model"
        assert config.weight == 0.4

    def test_weight_validation(self) -> None:
        with pytest.raises(ValueError):
            AIModelConfig(api_key="k", model="m", weight=1.5)
        with pytest.raises(ValueError):
            AIModelConfig(api_key="k", model="m", weight=-0.1)


class TestTwitterConfig:
    def test_default_values(self) -> None:
        config = TwitterConfig(username="user", password="pass")
        assert config.min_followers == 100000
        assert "BTC" in config.keywords
        assert config.tweets_per_kol == 10


class TestDebateTriggerConfig:
    def test_default_values(self) -> None:
        config = DebateTriggerConfig()
        assert config.sentiment_change_threshold == 0.3
        assert config.extreme_sentiment_threshold == 0.7


class TestOpenRouterConfig:
    def test_default_values(self) -> None:
        config = OpenRouterConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.model == "grok-2-1212"
        assert config.base_url == "https://openrouter.ai/api/v1"
        assert config.max_tokens == 4000
        assert config.temperature == 0.3

    def test_custom_values(self) -> None:
        config = OpenRouterConfig(
            api_key="custom-key",
            model="custom-model",
            base_url="https://custom.api.com",
            max_tokens=8000,
            temperature=0.5
        )
        assert config.api_key == "custom-key"
        assert config.model == "custom-model"
        assert config.base_url == "https://custom.api.com"
        assert config.max_tokens == 8000
        assert config.temperature == 0.5


class TestConfig:
    def test_model_weights_sum_to_one(self) -> None:
        """测试模型权重之和必须为1"""
        config = Config(
            twitter=TwitterConfig(username="u", password="p"),
            models={
                "kimi": AIModelConfig(api_key="k1", model="m1", weight=0.4),
                "minimax": AIModelConfig(api_key="k2", model="m2", weight=0.3),
                "zhipu": AIModelConfig(api_key="k3", model="m3", weight=0.3),
            },
            feishu_webhook="https://test"
        )
        assert "kimi" in config.models
        assert config.models["kimi"].weight == 0.4

    def test_model_weights_must_sum_to_one(self) -> None:
        """测试权重和不等于1时应报错"""
        with pytest.raises(ValueError, match="Model weights must sum to 1.0"):
            Config(
                twitter=TwitterConfig(username="u", password="p"),
                models={
                    "kimi": AIModelConfig(api_key="k1", model="m1", weight=0.5),
                    "minimax": AIModelConfig(api_key="k2", model="m2", weight=0.5),
                    "zhipu": AIModelConfig(api_key="k3", model="m3", weight=0.5),
                },
                feishu_webhook="https://test"
            )

    def test_empty_models_validation(self) -> None:
        """测试空模型字典应报错"""
        with pytest.raises(ValueError, match="Models dictionary cannot be empty"):
            Config(
                twitter=TwitterConfig(username="u", password="p"),
                models={},
                feishu_webhook="https://test"
            )


class TestLoadConfig:
    def test_load_config_from_yaml(self) -> None:
        """测试从YAML文件加载配置"""
        yaml_content = """
twitter:
  username: "test_user"
  password: "test_pass"
models:
  kimi:
    api_key: "test_key"
    model: "test_model"
    weight: 1.0
feishu_webhook: "https://test.webhook"
database_path: "test.db"
debug: true
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            assert config.twitter.username == "test_user"
            assert config.twitter.password == "test_pass"
            assert config.models["kimi"].api_key == "test_key"
            assert config.models["kimi"].weight == 1.0
            assert config.feishu_webhook == "https://test.webhook"
            assert config.database_path == "test.db"
            assert config.debug is True
        finally:
            os.unlink(temp_path)
