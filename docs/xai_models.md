# xAI API 模型列表

## 常见模型名

| 模型名 | 说明 | 是否支持 x_search |
|--------|------|-------------------|
| `grok-2-1212` | Grok 2 稳定版 | ✅ 支持 |
| `grok-2` | Grok 2 简写 | 可能支持 |
| `grok-3` | Grok 3 最新版 | ✅ 支持 |
| `grok-3-latest` | Grok 3 最新 | ✅ 支持 |
| `grok-beta` | Beta 版本 | 可能不支持 |

## 如何获取可用模型

登录 xAI Console 查看：
https://console.x.ai/

在 Playground 中可以看到你有权限访问的模型。

## 常见问题

### "Incorrect API key provided"
- API Key 不完整或已过期
- 需要重新生成

### "Model not found"
- 你的账户没有该模型的访问权限
- 尝试其他模型名
- 检查订阅状态

## 测试命令

```bash
# 测试 API Key 是否有效
curl https://api.x.ai/v1/chat/completions \
  -H "Authorization: Bearer xai-YOUR-KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-2-1212",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```
