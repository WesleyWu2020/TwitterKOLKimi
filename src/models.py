# src/models.py
"""SQLAlchemy ORM models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey, UniqueConstraint, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class KOL(Base):
    """KOL (Key Opinion Leader) 表"""
    __tablename__ = "kols"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100))
    followers_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    accuracy_rate = Column(Float, default=0.5)
    influence_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tweets = relationship("Tweet", back_populates="kol", lazy="dynamic")


class Tweet(Base):
    """推文表"""
    __tablename__ = "tweets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tweet_id = Column(String(50), unique=True, nullable=False)
    kol_id = Column(Integer, ForeignKey("kols.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    posted_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    has_btc_keyword = Column(Boolean, default=False)
    
    kol = relationship("KOL", back_populates="tweets")
    sentiment = relationship("Sentiment", back_populates="tweet", uselist=False)
    model_analyses = relationship("ModelAnalysis", back_populates="tweet", lazy="dynamic")


class ModelAnalysis(Base):
    """模型分析表"""
    __tablename__ = "model_analyses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), nullable=False)
    model_name = Column(String(20), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text)
    raw_response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tweet = relationship("Tweet", back_populates="model_analyses")
    
    __table_args__ = (
        UniqueConstraint("tweet_id", "model_name", name="uq_tweet_model"),
    )


class Sentiment(Base):
    """综合情绪表"""
    __tablename__ = "sentiments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), unique=True, nullable=False)
    composite_score = Column(Float, nullable=False)
    sentiment_label = Column(String(20), nullable=False)
    btc_signal = Column(Boolean, default=False)
    model_consensus = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tweet = relationship("Tweet", back_populates="sentiment")


class MarketSentimentHistory(Base):
    """市场情绪历史表"""
    __tablename__ = "market_sentiment_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    market_sentiment_index = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    participation_rate = Column(Float, nullable=False)
    active_kols = Column(Integer, nullable=False)
    total_kols = Column(Integer, nullable=False)
    distribution = Column(JSON, nullable=False)
    top_signals = Column(JSON)
    change_1h = Column(Float)
    change_24h = Column(Float)
    
    debates = relationship("DebateRecord", back_populates="market_sentiment")


class DebateRecord(Base):
    """辩论记录表"""
    __tablename__ = "debate_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    market_sentiment_id = Column(Integer, ForeignKey("market_sentiment_history.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    proponent_stance = Column(String(20))
    proponent_confidence = Column(Float)
    proponent_key_points = Column(JSON)
    proponent_raw_output = Column(Text)
    
    opponent_challenges = Column(JSON)
    opponent_high_risk_count = Column(Integer, default=0)
    opponent_medium_risk_count = Column(Integer, default=0)
    opponent_raw_output = Column(Text)
    
    proponent_admitted_points = Column(JSON)
    proponent_refuted_points = Column(JSON)
    proponent_adjusted_stance = Column(String(20))
    proponent_adjusted_confidence = Column(Float)
    proponent_response_raw = Column(Text)
    
    final_recommendation = Column(JSON)
    
    market_sentiment = relationship("MarketSentimentHistory", back_populates="debates")
