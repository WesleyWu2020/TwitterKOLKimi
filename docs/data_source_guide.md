# 数据源配置指南

## 概述

本项目支持三种数据源获取 Twitter/X 数据：

| 数据源 | 类型 | 成本 | 实时性 | 推荐场景 |
|--------|------|------|--------|----------|
| **xAI API** | 真实数据 | $5/月订阅 | ⭐⭐⭐ 实时 | ✅ 生产环境 |
| **Twitter API v2** | 真实数据 | $100/月 | ⭐⭐⭐ 实时 | 企业级应用 |
| **OpenRouter (Grok)** | 模拟数据 | 按量付费 | ⭐ 可能过时 | 测试/开发 |

---

## 方案 1：xAI API (推荐 ⭐)

使用 Grok X Search 工具获取真实、实时的 X 数据。

### 优点
- 真实数据：直接访问 X 平台
- 实时性强：获取最新推文
- 成本低：$5/月订阅
- 智能搜索：支持语义搜索、过滤

### 配置步骤

1. **获取 xAI API Key**
   - 访问 https://x.ai/api
   - 注册账号
   - 订阅 API 服务（$5/月）
   - 创建 API Key（格式：`xai-...`）

2. **修改配置**
   ```yaml
   # config/config.yaml
   data_source: "xai"
   
   xai:
     api_key: "xai-your-api-key-here"  # 以 xai- 开头
     model: "grok-2-1212"              # 或 "grok-beta"
   ```

3. **运行测试**
   ```bash
   python -m src.main --once
   ```

---

## 方案 2：Twitter API v2

使用官方 Twitter API 获取数据。

### 优点
- 官方数据源
- 稳定可靠
- 完整的数据字段

### 缺点
- 成本高：$100/月起
- 需要开发者审核

### 配置步骤

1. **申请开发者账号**
   - 访问 https://developer.twitter.com/
   - 申请 Basic 或 Pro 套餐

2. **获取 Bearer Token**
   - 创建 App
   - 生成 Bearer Token

3. **修改配置**
   ```yaml
   # config/config.yaml
   data_source: "twitter_api"
   
   twitter_api:
     bearer_token: "AAAAAAAAAAAAAAAAAAAAA..."
   ```

---

## 方案 3：OpenRouter (Grok)

通过 OpenRouter 使用 Grok，但数据可能是模拟的。

### 注意 ⚠️
- **数据可能不是实时的**：Grok 可能基于训练数据生成响应
- **时间戳可能不准确**：可能返回过时的信息
- **仅适合测试**：不建议用于实盘交易决策

### 配置
```yaml
# config/config.yaml
data_source: "grok"

openrouter:
  api_key: "sk-or-v1-..."
  model: "x-ai/grok-4-fast"  # 或 x-ai/grok-beta
```

---

## 数据源对比

### 测试数据真实性
```bash
# 查看数据库中的推文时间戳
sqlite3 data/sentiment.db "SELECT username, content, posted_at FROM tweets ORDER BY posted_at DESC LIMIT 5;"
```

### 预期结果
- **xAI/Twitter API**: 时间戳应该是最近几小时/几天的
- **OpenRouter Grok**: 时间戳可能是随机的，或者内容包含过时的信息

---

## 切换数据源

编辑 `config/config.yaml`：

```yaml
# 使用 xAI API (推荐)
data_source: "xai"

# 或使用 Twitter API
data_source: "twitter_api"

# 或使用 OpenRouter (测试用)
data_source: "grok"
```

---

## 常见问题

### Q: Grok 返回的数据是真的吗？
A: 取决于数据源：
- **xAI API**: ✅ 真实数据
- **OpenRouter**: ❌ 可能是模拟数据

### Q: 为什么飞书显示"数据来源: AI模拟生成"？
A: 这表示你正在使用 OpenRouter，建议切换到 xAI API。

### Q: xAI API 和 OpenRouter 有什么区别？
A: 
- xAI API: 直接访问 Grok，支持 X Search 工具，获取真实数据
- OpenRouter: 第三方代理，可能不支持工具调用，返回模拟数据
