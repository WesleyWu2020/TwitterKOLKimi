#!/usr/bin/env python3
import json
import requests

API_KEY = "xai-your-api-key-here"

# 第一次调用：让 Grok 调用 x_search
payload1 = {
    "model": "grok-3",
    "messages": [
        {
            "role": "system",
            "content": "You have access to X platform via x_search tool. Always use x_search to find real, recent tweets. After searching, return the results as JSON."
        },
        {
            "role": "user",
            "content": 'Search X for recent posts from @cz_binance about Bitcoin or crypto since 2025-01-01. Return the tweet data as JSON array with fields: tweet_id, username, content, posted_at, likes, retweets.'
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "x_search",
                "description": "Search for posts on X (Twitter) platform",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        }
    ],
    "tool_choice": "auto",
    "max_tokens": 4000
}

response1 = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json=payload1
)

data1 = response1.json()
print("Step 1 - Grok wants to call tool:")
print(json.dumps(data1, indent=2)[:2000])

# 获取 tool_call
message = data1["choices"][0]["message"]
tool_calls = message.get("tool_calls", [])

if tool_calls:
    # 第二次调用：把 tool 结果传回去
    # 但 x_search 是内部工具，xAI 应该已经执行了
    # 让我们尝试另一种方式 - 直接要求 Grok 生成 JSON
    
    print("\n\nStep 2 - Asking Grok to provide search results as JSON...")
    
    payload2 = {
        "model": "grok-3",
        "messages": [
            {
                "role": "system",
                "content": "You have access to X platform. Use x_search to find real tweets from @cz_binance about Bitcoin/crypto posted in 2025-2026. Return ONLY valid JSON array of tweets."
            },
            {
                "role": "user",
                "content": 'Find @cz_binance recent tweets about Bitcoin or crypto. Return as JSON: [{"tweet_id": "...", "username": "cz_binance", "content": "...", "posted_at": "2025-...", "likes": 0, "retweets": 0}]'
            }
        ],
        "max_tokens": 4000
    }
    
    response2 = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=payload2
    )
    
    data2 = response2.json()
    print(f"\nContent: {data2['choices'][0]['message']['content'][:2000]}")
