#!/usr/bin/env python3
import json
import requests

API_KEY = "xai-your-api-key-here"

payload = {
    "model": "grok-3",
    "messages": [
        {
            "role": "system",
            "content": "You have access to X platform via x_search tool. Always use x_search to find real, recent tweets."
        },
        {
            "role": "user",
            "content": 'Search X for recent posts from @cz_binance about Bitcoin or crypto. Return results as JSON with fields: tweet_id, username, content, posted_at, likes, retweets.'
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
                        "query": {
                            "type": "string",
                            "description": "X search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ],
    "tool_choice": "auto",
    "max_tokens": 4000
}

response = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json=payload
)

print(f"Status: {response.status_code}")
data = response.json()
print(f"\nFull response:\n{json.dumps(data, indent=2)[:3000]}")
