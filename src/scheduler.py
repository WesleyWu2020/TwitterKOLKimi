# src/scheduler.py
"""主调度器模块."""
import asyncio
import time
import signal
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Union
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
        
        # 初始化数据获取器：优先使用 Grok，回退到 Twitter Scraper
        self.data_fetcher: Optional[Any] = None
        self.using_grok = False
        self._init_data_fetcher(config)
        
        self.scheduler = BackgroundScheduler()
        self._setup_signal_handlers()
        
        logger.info("SentimentMonitor initialized")
    
    def _init_data_fetcher(self, config: Config):
        """初始化数据获取器"""
        # 检查配置中的数据源设置
        data_source = getattr(config, 'data_source', 'grok')
        
        if data_source == "xai_sdk":
            # 使用 xAI SDK (推荐 - Grok X Search 真实数据)
            try:
                from src.xai_sdk_fetcher import XAISDKFetcher
                if hasattr(config, 'xai') and config.xai:
                    api_key = getattr(config.xai, 'api_key', None)
                    model = getattr(config.xai, 'model', 'grok-4.20-reasoning')
                    if api_key and api_key.startswith("xai-"):
                        self.data_fetcher = XAISDKFetcher(api_key, model)
                        self.using_grok = False
                        logger.info("✅ Using xAI SDK with Grok X Search (REAL-TIME Twitter data)")
                        return
                    else:
                        logger.warning("xAI API key not configured correctly")
                else:
                    logger.warning("xAI config not found")
            except ImportError as e:
                logger.warning(f"xai-sdk not installed: {e}")
        
        if data_source == "xai":
            # 使用 xAI REST API (备选)
            from src.xai_fetcher import XAIFetcher
            if hasattr(config, 'xai') and config.xai:
                api_key = getattr(config.xai, 'api_key', None)
                model = getattr(config.xai, 'model', 'grok-3')
                if api_key and api_key.startswith("xai-"):
                    self.data_fetcher = XAIFetcher(api_key, model)
                    self.using_grok = False
                    logger.info("Using xAI REST API (REAL-TIME Twitter data)")
                    return
        
        if data_source == "twitter_api":
            # 使用 Twitter API (真实数据)
            from src.twitter_api_fetcher import TwitterAPIFetcher
            if hasattr(config, 'twitter_api') and config.twitter_api:
                bearer_token = getattr(config.twitter_api, 'bearer_token', None)
                if bearer_token and bearer_token != "your_bearer_token_here":
                    self.data_fetcher = TwitterAPIFetcher(bearer_token)
                    self.using_grok = False
                    logger.info("Using Twitter API v2 for REAL data fetching")
                    return
                else:
                    logger.warning("Twitter API bearer token not configured, falling back to Grok")
            else:
                logger.warning("Twitter API config not found, falling back to Grok")
        
        # 使用 Grok via OpenRouter (模拟数据)
        from src.config import OpenRouterConfig
        if config.openrouter and isinstance(config.openrouter, OpenRouterConfig):
            from src.grok_fetcher import GrokFetcher
            self.data_fetcher = GrokFetcher(config.openrouter)
            self.using_grok = True
            logger.warning("⚠️ Using Grok via OpenRouter (SIMULATED data - not real-time)")
        else:
            from src.twitter_scraper import TwitterScraper
            self.data_fetcher = TwitterScraper(config.twitter, headless=True)
            self.using_grok = False
            logger.info("Using Twitter Scraper for data fetching")
    
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
    
    async def fetch_and_save_tweets(self, kols: List[Dict[str, Any]]) -> int:
        """
        抓取并保存 KOL 推文（支持 Grok 和 Twitter）
        
        Args:
            kols: KOL 列表
            
        Returns:
            保存的推文数量
        """
        if not kols:
            logger.info("No KOLs configured, skipping tweet fetch")
            return 0
        
        logger.info(f"Fetching tweets for {len(kols)} KOLs...")
        
        # 获取每个 KOL 的最大推文数
        max_tweets_per_kol = self.config.twitter.tweets_per_kol if self.config.twitter else 10
        
        # 根据使用的获取器类型调用不同方法
        if self.using_grok:
            # Grok 是异步的，返回 Dict[str, List[TweetData]]
            results = await self.data_fetcher.fetch_all_kols_tweets(
                [kol.get("username", kol) if isinstance(kol, dict) else kol for kol in kols],
                max_tweets=max_tweets_per_kol
            )
            # 合并所有推文
            from src.grok_fetcher import TweetData
            all_tweets: List[TweetData] = []
            for username, tweets in results.items():
                all_tweets.extend(tweets)
        elif hasattr(self.data_fetcher, '__class__') and 'XAI' in self.data_fetcher.__class__.__name__:
            # xAI fetcher 是同步的，返回 Dict[str, List[TweetData]]
            results = self.data_fetcher.fetch_all_kols_tweets(
                kols,
                max_tweets=max_tweets_per_kol
            )
            # 合并所有推文
            all_tweets = []
            for username, tweets in results.items():
                all_tweets.extend(tweets)
        else:
            # Twitter Scraper 是同步的，返回 List[Tweet]
            all_tweets = self.data_fetcher.fetch_all_kols_tweets(
                kols,
                max_tweets_per_kol=max_tweets_per_kol
            )
        
        if not all_tweets:
            logger.warning("No tweets fetched")
            return 0
        
        # 保存到数据库
        saved_count = 0
        for tweet in all_tweets:
            try:
                # 获取或创建 KOL
                kol = self.db.get_or_create_kol(
                    username=tweet.username,
                    display_name=tweet.display_name
                )
                
                # 保存推文
                self.db.save_tweet(
                    tweet_id=tweet.tweet_id,
                    username=tweet.username,
                    content=tweet.content,
                    posted_at=tweet.posted_at,
                    has_btc_keyword=tweet.has_btc_keyword
                )
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving tweet {tweet.tweet_id}: {e}")
                continue
        
        logger.info(f"Saved {saved_count}/{len(all_tweets)} tweets to database")
        return saved_count
    
    async def run_once(self):
        """运行一次完整的分析流程（异步）"""
        logger.info("Running single analysis cycle")
        
        # Step 1: 获取配置的 KOL 列表（简化：从配置文件读取）
        # 实际项目中可以从数据库或配置文件加载
        kols = self._load_kols_from_config()
        
        # Step 2: 抓取推文（异步）
        fetched_count = await self.fetch_and_save_tweets(kols)
        
        # Step 3: 分析待处理推文（保持同步）
        analyzed_count = self.analyze_pending_tweets()
        
        # Step 4: 计算和通知（保持同步）
        sentiment = self.calculate_and_notify()
        
        return {
            "fetched": fetched_count,
            "analyzed": analyzed_count,
            "sentiment": sentiment
        }
    
    def _load_kols_from_config(self) -> List[Dict[str, Any]]:
        """
        从配置加载 KOL 列表
        
        优先从 config.twitter.kols 读取，如果没有则返回空列表
        """
        # 尝试从配置读取 KOL 列表
        kols = getattr(self.config.twitter, 'kols', None)
        
        if kols and isinstance(kols, list):
            logger.info(f"Loaded {len(kols)} KOLs from config")
            return kols
        
        # 如果没有配置 KOL，尝试从数据库加载已有的 KOL
        try:
            from src.models import KOL
            with self.db.session_scope() as session:
                db_kols = session.query(KOL).filter(KOL.is_active == True).all()
                if db_kols:
                    result = [{"username": k.username, "followers_count": k.followers_count} for k in db_kols]
                    logger.info(f"Loaded {len(result)} KOLs from database")
                    return result
        except Exception as e:
            logger.warning(f"Could not load KOLs from database: {e}")
        
        logger.warning("No KOLs configured. Please add KOLs to config.yaml or database.")
        return []
    
    def _run_async_job(self):
        """包装异步 run_once 供调度器调用"""
        try:
            # 创建新的事件循环来运行异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.run_once())
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error in scheduled job: {e}")
            return None
    
    def start_scheduler(self, analysis_interval: int = 300):
        """
        启动定时调度器
        
        Args:
            analysis_interval: 分析间隔（秒），默认5分钟
        """
        logger.info(f"Starting scheduler with interval: {analysis_interval}s")
        
        # 添加定时任务（使用同步包装器调用异步方法）
        self.scheduler.add_job(
            func=self._run_async_job,
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
