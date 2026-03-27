#!/usr/bin/env python3
"""测试 xAI SDK 是否正常安装和工作"""
import sys

# 检查 SDK 是否安装
try:
    from xai_sdk import Client
    from xai_sdk.chat import user
    from xai_sdk.tools import x_search
    print("✅ xai-sdk 已安装")
except ImportError as e:
    print(f"❌ xai-sdk 未安装: {e}")
    print("请运行: pip install xai-sdk")
    sys.exit(1)

# 测试导入自定义模块
try:
    from src.xai_sdk_fetcher import XAISDKFetcher
    print("✅ XAISDKFetcher 模块导入成功")
except ImportError as e:
    print(f"❌ XAISDKFetcher 导入失败: {e}")
    sys.exit(1)

# 测试初始化
API_KEY = "xai-your-api-key-here"

try:
    fetcher = XAISDKFetcher(API_KEY, model="grok-4.20-reasoning")
    print("✅ XAISDKFetcher 初始化成功")
    print(f"   Model: grok-4.20-reasoning")
    print("\n准备测试抓取推文...")
    
    # 测试抓取 cz_binance 的一条推文
    tweets = fetcher.fetch_tweets_from_kol("cz_binance", max_tweets=1)
    
    if tweets:
        print(f"✅ 成功抓取 {len(tweets)} 条推文")
        for t in tweets:
            print(f"   - @{t.username}: {t.content[:80]}...")
    else:
        print("⚠️ 未抓取到推文（可能账号无新内容或 API 限制）")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
