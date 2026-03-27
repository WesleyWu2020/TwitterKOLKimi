#!/usr/bin/env python3
import json
import requests

API_KEY = "xai-your-api-key-here"

# 强制工具调用
payload = {
    "model": "grok-3",
    "messages": [
        {
            "role": "system", 
            "content": "You must use x_search tool to find real tweets from X platform. Do not rely on training data."
        },
        {
            "role": "user",
            "content": "Search X for @cz_binance tweets about Bitcoin from March 2025. Return JSON with tweet_id, content, posted_at."
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "x_search",
                "description": "Search X platform for real-time tweets",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        }
    ],
    "tool_choice": {"type": "function", "function": {"name": "x_search"}},  # 强制使用 x_search
    "max_tokens": 4000
}

response = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json=payload
)

data = response.json()
print(f"Status: {response.status_code}")
print(f"Sources used: {data.get('usage', {}).get('num_sources_used', 0)}")
print(f"Content: {data.get('choices', [{}])[0].get('message', {}).get('content', '')[:500]}")
print(f"\nTool calls: {data.get('choices', [{}])[0].get('message', {}).get('tool_calls', [])}")
