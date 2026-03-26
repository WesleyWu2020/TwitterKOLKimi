# src/scheduler.py
"""主调度器模块."""
import time
import signal
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import Config
from src.database import Database
from src.sentiment_analyzer import SentimentAnalyzer
from src.market_calculator import MarketCalculator
from src.debate_engine import DebateEngine
from src.feishu_notifier import FeishuNotifier


class SentimentMonitor:
    """情绪监控器类"""
    
    def __init__(self, config: Config):
        """
        初始化监控器
        
        Args:
            config: 配置对象
        """
        self.config = config
        # 支持完整的SQLAlchemy URL或简化的数据库路径
        if config.database_path.startswith("sqlite://"):
            db_url = config.database_path
        else:
            db_url = f"sqlite:///{config.database_path}"
        self.db = Database(db_url)
        self.db.init_tables()
        
        self.analyzer = SentimentAnalyzer(config)
        self.calculator = MarketCalculator()
        self.debate_engine = DebateEngine(config)
        self.feishu = FeishuNotifier(
            webhook_url=config.feishu_webhook,
            secret=config.feishu_secret
        )
        
        self.scheduler = BackgroundScheduler()
        self._setup_signal_handlers()
        
        logger.info("SentimentMonitor initialized")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def analyze_pending_tweets(self, limit: int = 100) -> int:
        """
        分析待处理的推文
        
        Args:
            limit: 处理数量限制
            
        Returns:
            处理的推文数量
        """
        tweets = self.db.get_recent_tweets_for_analysis(limit=limit)
        
        if not tweets:
            logger.info("No pending tweets to analyze")
            return 0
        
        logger.info(f"Analyzing {len(tweets)} pending tweets")
        processed = 0
        
        for tweet in tweets:
            try:
                # 分析推文
                analysis = self.analyzer.analyze_tweet(tweet.content)
                
                # 保存模型分析结果
                for model_result in analysis.get("model_results", []):
                    self.db.save_model_analysis(
                        tweet_id=tweet.id,
                        model_name=model_result["model"],
                        sentiment_score=model_result["score"],
                        confidence=model_result["confidence"],
                        reasoning=model_result["reasoning"]
                    )
                
                # 保存综合情绪结果
                self.db.save_sentiment(
                    tweet_id=tweet.id,
                    composite_score=analysis["composite_score"],
                    sentiment_label=analysis["sentiment_label"],
                    btc_signal=analysis["btc_signal"],
                    model_consensus=analysis.get("model_consensus")
                )
                
                processed += 1
                logger.debug(f"Analyzed tweet {tweet.tweet_id}: {analysis['sentiment_label']}")
                
            except Exception as e:
                logger.error(f"Error analyzing tweet {tweet.tweet_id}: {e}")
        
        logger.info(f"Processed {processed}/{len(tweets)} tweets")
        return processed
    
    def calculate_and_notify(self) -> Optional[Dict[str, Any]]:
        """
        计算市场情绪并发送通知
        
        Returns:
            市场情绪数据或None
        """
        # 计算市场情绪
        sentiment_data = self.db.calculate_market_sentiment(hours=1)
        
        if sentiment_data["sample_count"] == 0:
            logger.info("No sentiment data available for calculation")
            return None
        
        # 保存历史记录
        self.db.save_market_sentiment(sentiment_data)
        
        # 发送通知
        try:
            self.feishu.send_market_sentiment(sentiment_data)
            logger.info("Market sentiment notification sent")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
        
        # 检查是否需要触发辩论
        if self._should_trigger_debate(sentiment_data["market_sentiment_index"]):
            logger.info("Triggering debate due to sentiment conditions")
            self._trigger_debate(sentiment_data)
        
        return sentiment_data
    
    def _should_trigger_debate(
        self, 
        current_index: float,
        previous_index: Optional[float] = None
    ) -> bool:
        """
        检查是否需要触发辩论
        
        Args:
            current_index: 当前情绪指数
            previous_index: 之前的情绪指数
            
        Returns:
            是否触发辩论
        """
        trigger_config = self.config.debate_trigger
        
        # 检查极端情绪
        if current_index >= trigger_config.extreme_sentiment_threshold:
            logger.info(f"Extreme bullish sentiment detected: {current_index:.3f}")
            return True
        
        if current_index <= (1 - trigger_config.extreme_sentiment_threshold):
            logger.info(f"Extreme bearish sentiment detected: {current_index:.3f}")
            return True
        
        # 检查情绪大幅变化
        if previous_index is not None:
            change = abs(current_index - previous_index)
            if change >= trigger_config.sentiment_change_threshold:
                logger.info(f"Significant sentiment change detected: {change:.3f}")
                return True
        
        # 获取上一次的市场情绪进行比较
        latest = self.db.get_latest_market_sentiment(hours=2)
        if latest:
            change = abs(current_index - latest["market_sentiment_index"])
            if change >= trigger_config.sentiment_change_threshold:
                logger.info(f"Sentiment change from previous: {change:.3f}")
                return True
        
        return False
    
    def _trigger_debate(self, sentiment_data: Dict[str, Any]):
        """
        触发辩论流程
        
        Args:
            sentiment_data: 市场情绪数据
        """
        try:
            # 获取支持证据（最近的高置信度情绪分析）
            supporting_evidence = self._get_supporting_evidence()
            
            # 执行辩论
            debate_result = self.debate_engine.debate(
                sentiment_label=self._get_dominant_sentiment(sentiment_data),
                market_index=sentiment_data["market_sentiment_index"],
                supporting_evidence=supporting_evidence
            )
            
            # 发送辩论结果通知
            self.feishu.send_debate_result(debate_result)
            logger.info("Debate result notification sent")
            
        except Exception as e:
            logger.error(f"Error during debate: {e}")
    
    def _get_supporting_evidence(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取支持证据
        
        Args:
            limit: 证据数量限制
            
        Returns:
            证据列表
        """
        # 简化实现：返回空列表
        # 实际项目中可以从数据库查询高置信度的分析结果
        return []
    
    def _get_dominant_sentiment(self, sentiment_data: Dict[str, Any]) -> str:
        """
        获取主导情绪
        
        Args:
            sentiment_data: 市场情绪数据
            
        Returns:
            主导情绪标签
        """
        distribution = sentiment_data.get("distribution", {})
        
        bullish = distribution.get("bullish", 0)
        bearish = distribution.get("bearish", 0)
        neutral = distribution.get("neutral", 0)
        
        if bullish > bearish and bullish > neutral:
            return "bullish"
        elif bearish > bullish and bearish > neutral:
            return "bearish"
        else:
            return "neutral"
    
    def run_once(self):
        """运行一次完整的分析流程"""
        logger.info("Running single analysis cycle")
        
        # 分析待处理推文
        tweet_count = self.analyze_pending_tweets()
        
        # 计算和通知
        sentiment = self.calculate_and_notify()
        
        return {
            "tweets_processed": tweet_count,
            "sentiment": sentiment
        }
    
    def start_scheduler(self, analysis_interval: int = 300):
        """
        启动定时调度器
        
        Args:
            analysis_interval: 分析间隔（秒），默认5分钟
        """
        logger.info(f"Starting scheduler with interval: {analysis_interval}s")
        
        # 添加定时任务
        self.scheduler.add_job(
            func=self.run_once,
            trigger=IntervalTrigger(seconds=analysis_interval),
            id="sentiment_analysis",
            name="Sentiment Analysis",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler started")
        
        # 保持程序运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.stop()
    
    def stop(self):
        """停止调度器"""
        logger.info("Stopping scheduler...")
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.db.close()
        logger.info("Scheduler stopped")


def create_default_config() -> Config:
    """创建默认配置"""
    from src.config import TwitterConfig, AIModelConfig, DebateTriggerConfig
    
    return Config(
        twitter=TwitterConfig(username="user", password="pass"),
        models={
            "kimi": AIModelConfig(api_key="your-key", model="moonshot-v1-8k", weight=1.0)
        },
        feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook",
        database_path="data/sentiment.db",
        debate_trigger=DebateTriggerConfig()
    )
