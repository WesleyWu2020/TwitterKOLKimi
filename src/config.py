# src/config.py
"""Pydantic configuration models."""
import yaml
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


__all__ = [
    "AIModelConfig",
    "TwitterConfig",
    "DebateTriggerConfig",
    "Config",
    "load_config",
]

WEIGHT_TOLERANCE = 0.01


class AIModelConfig(BaseModel):
    """单个AI模型的配置"""
    api_key: str
    model: str
    weight: float = Field(..., ge=0.0, le=1.0)
    base_url: Optional[str] = None


class TwitterConfig(BaseModel):
    """Twitter相关配置"""
    username: str
    password: str
    min_followers: int = 100000
    keywords: List[str] = Field(default_factory=lambda: [
        "BTC", "Bitcoin", "比特币", "ETH", "以太坊", "crypto"
    ])
    tweets_per_kol: int = 10


class DebateTriggerConfig(BaseModel):
    """辩论触发配置"""
    sentiment_change_threshold: float = 0.3
    extreme_sentiment_threshold: float = 0.7


class Config(BaseModel):
    """主配置类"""
    twitter: TwitterConfig
    models: Dict[str, AIModelConfig]
    feishu_webhook: str
    feishu_secret: Optional[str] = None
    database_path: str = "data/sentiment.db"
    debug: bool = False
    debate_trigger: DebateTriggerConfig = Field(default_factory=DebateTriggerConfig)
    
    @field_validator("models")
    @classmethod
    def validate_model_weights(cls, v: Dict[str, AIModelConfig]) -> Dict[str, AIModelConfig]:
        """验证模型权重之和为1"""
        if not v:
            raise ValueError("Models dictionary cannot be empty")
        total_weight = sum(model.weight for model in v.values())
        if abs(total_weight - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(f"Model weights must sum to 1.0, got {total_weight}")
        return v


def load_config(config_path: str = "config/config.yaml") -> Config:
    """从YAML文件加载配置"""
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(**data)
