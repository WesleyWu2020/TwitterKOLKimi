#!/usr/bin/env python3
"""测试 Twitter 登录"""
from src.config import load_config
from src.twitter_scraper import TwitterScraper

config = load_config("config/config.yaml")

# 使用 headless=False 可以看到浏览器窗口
scraper = TwitterScraper(config.twitter, headless=False)

# 只抓取一个 KOL 测试
tweets = scraper.fetch_tweets_from_kol("cz_binance", max_tweets=3)

print(f"抓取到 {len(tweets)} 条推文")
for tweet in tweets:
    print(f"- @{tweet.username}: {tweet.content[:50]}...")
