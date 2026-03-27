#!/usr/bin/env python3
"""测试直接调用 xAI API 使用 Grok X Search"""
import os
import json
import requests

# xAI API 配置
XAI_API_KEY = "xai-..."  # 需要 xAI API Key，不是 OpenRouter

def test_xai_api():
    """测试 xAI API"""
    url = "https://api.x.ai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-2-1212",  # 或 grok-beta
        "messages": [
            {
                "role": "system",
                "content": "You have access to X platform via x_search tool. Use it to find real tweets."
            },
            {
                "role": "user",
                "content": 'Search X for recent tweets from @cz_binance about Bitcoin. Return as JSON.'
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "x_search",
                    "description": "Search X platform",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        }
                    }
                }
            }
        ],
        "tool_choice": "auto"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:2000]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if XAI_API_KEY.startswith("xai-"):
        test_xai_api()
    else:
        print("请设置 xAI API Key (以 xai- 开头)")
