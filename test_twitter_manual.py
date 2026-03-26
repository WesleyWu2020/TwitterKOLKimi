#!/usr/bin/env python3
"""
手动测试 Twitter 登录和抓取

使用方式:
    python test_twitter_manual.py

这个脚本会:
1. 打开浏览器窗口 (headless=False)
2. 尝试登录 Twitter
3. 如果成功，抓取 cz_binance 的 3 条推文
4. 显示结果

如果登录失败，会显示详细的错误信息和截图。
"""
import sys
from loguru import logger

# 配置日志显示 DEBUG 级别
logger.remove()
logger.add(sys.stderr, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>")

from src.config import load_config
from src.twitter_scraper import TwitterScraper

def main():
    print("=" * 70)
    print("Twitter 登录和抓取测试")
    print("=" * 70)
    
    # 加载配置
    config = load_config("config/config.yaml")
    
    print(f"\n配置信息:")
    print(f"  Twitter 用户名: {config.twitter.username}")
    print(f"  目标 KOL: @cz_binance")
    print(f"  抓取数量: 3 条推文")
    print(f"\n注意: 会打开浏览器窗口，请观察登录过程")
    print("=" * 70)
    
    # 创建 scraper（非无头模式，方便观察）
    scraper = TwitterScraper(config.twitter, headless=False)
    
    try:
        # 抓取推文
        print("\n开始抓取...")
        tweets = scraper.fetch_tweets_from_kol("cz_binance", max_tweets=3)
        
        print("\n" + "=" * 70)
        print(f"结果: 成功抓取 {len(tweets)} 条推文")
        print("=" * 70)
        
        for i, tweet in enumerate(tweets, 1):
            print(f"\n[{i}] @{tweet.username} ({tweet.posted_at.strftime('%Y-%m-%d %H:%M')})")
            print(f"    内容: {tweet.content[:100]}...")
            print(f"    👍 {tweet.likes} | 🔁 {tweet.retweets} | BTC关键词: {tweet.has_btc_keyword}")
        
        if tweets:
            print("\n✅ 测试成功！登录和抓取功能正常。")
        else:
            print("\n⚠️ 没有抓取到推文。可能原因:")
            print("   - 登录失败（请检查用户名密码）")
            print("   - 需要验证码（请查看 data/login_challenge.png）")
            print("   - cz_binance 没有新推文")
            
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        input("\n按 Enter 键退出...")

if __name__ == "__main__":
    main()
