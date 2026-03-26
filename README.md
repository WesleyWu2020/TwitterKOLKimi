# Polymarket BTC/ETH 情绪监控系统

基于多模型AI的加密货币市场情绪监控与智能分析系统。通过分析Twitter KOL推文，结合Kimi/MiniMax/智谱AI的多维度情绪分析，提供市场情绪指数、AI辩论验证和飞书通知功能。

## 功能特性

- 🐦 **Twitter KOL监控**: 自动追踪指定KOL的推文，识别BTC/ETH相关内容
- 🤖 **多模型情绪分析**: 并行调用Kimi、MiniMax、智谱三个AI模型进行情绪评分
- 📊 **市场情绪指数**: 加权计算综合市场情绪，支持KOL影响力权重
- 🗣️ **AI辩论引擎**: 三轮辩论机制（正方-反方-回应）验证极端情绪
- 📱 **飞书通知**: 实时推送市场情绪报告和辩论结果
- ⏰ **定时调度**: 支持定时任务自动分析

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

#### 方式一：使用 OpenRouter + Grok（推荐）

无需登录 Twitter，直接使用 Grok 模型获取数据。

1. 获取 OpenRouter API Key
   - 访问 https://openrouter.ai/
   - 注册并创建 API Key
   - 确保账户有余额（新用户有免费额度）

2. 配置 OpenRouter
   ```yaml
   # 编辑 config/config.yaml
   openrouter:
     api_key: "sk-or-v1-your-api-key"
     model: "grok-2-1212"
   ```

3. 运行程序
   ```bash
   python -m src.main --once
   ```

#### 方式二：使用 Twitter 登录（备选）

如果 OpenRouter 无法使用，可以回退到 Twitter 登录方式。

创建 `config/config.yaml`:

```yaml
twitter:
  username: "your_twitter_username"
  password: "your_twitter_password"
  min_followers: 100000
  keywords: ["BTC", "Bitcoin", "比特币", "ETH", "以太坊", "crypto"]
  tweets_per_kol: 10

models:
  kimi:
    api_key: "your_kimi_api_key"
    model: "moonshot-v1-8k"
    weight: 0.4
    base_url: "https://api.moonshot.cn/v1"
  minimax:
    api_key: "your_minimax_api_key"
    model: "abab6.5-chat"
    weight: 0.3
    base_url: "https://api.minimax.chat/v1"
  zhipu:
    api_key: "your_zhipu_api_key"
    model: "glm-4"
    weight: 0.3
    base_url: "https://open.bigmodel.cn/api/paas/v4"

feishu_webhook: "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook"
feishu_secret: "your_secret"  # 可选，用于签名验证

database_path: "data/sentiment.db"
debug: false

debate_trigger:
  sentiment_change_threshold: 0.3
  extreme_sentiment_threshold: 0.7
```

### 3. 运行

单次运行:
```bash
python -m src.main --once
```

定时调度（每5分钟）:
```bash
python -m src.main --interval 300
```

调试模式:
```bash
python -m src.main --once --debug
```

## 项目结构

```
.
├── src/
│   ├── __init__.py
│   ├── config.py          # 配置模型（Pydantic）
│   ├── models.py          # 数据库模型（SQLAlchemy）
│   ├── database.py        # 数据库操作
│   ├── twitter_scraper.py # Twitter爬虫
│   ├── sentiment_analyzer.py  # 情绪分析
│   ├── market_calculator.py   # 市场情绪计算
│   ├── debate_engine.py   # AI辩论引擎
│   ├── feishu_notifier.py # 飞书通知
│   ├── scheduler.py       # 主调度器
│   └── main.py           # 入口文件
├── tests/                # 测试文件
├── config/               # 配置文件目录
├── data/                 # 数据库目录
├── logs/                 # 日志目录
├── requirements.txt      # 依赖列表
└── README.md            # 本文档
```

## 核心模块说明

### 1. 情绪分析 (sentiment_analyzer.py)

使用 Prompt 工程引导AI模型输出结构化情绪分析:

```python
{
    "composite_score": 0.75,      # 综合情绪分数 (0-1)
    "sentiment_label": "bullish", # 情绪标签
    "btc_signal": true,           # 是否包含BTC信号
    "model_results": [...],       # 各模型详细结果
    "model_consensus": 0.85       # 模型一致性
}
```

### 2. AI辩论引擎 (debate_engine.py)

三轮辩论流程:
1. **正方阐述**: 智谱AI支持当前市场情绪
2. **反方挑战**: MiniMax AI提出质疑和风险
3. **正方回应**: 智谱AI回应质疑并调整置信度

### 3. 市场情绪计算 (market_calculator.py)

计算公式:
```
市场情绪指数 = Σ(情绪分数 × KOL权重) / Σ(KOL权重)
KOL权重 = 基础权重 × 粉丝因子 × 准确率因子
```

### 4. 飞书通知 (feishu_notifier.py)

支持交互式卡片消息:
- 市场情绪报告卡片
- AI辩论结果卡片
- 签名验证（可选）

## 数据库模型

### KOL 表
- 用户名、粉丝数、准确率、影响力评分

### Tweet 表
- 推文ID、内容、发布时间、BTC关键词标记

### Sentiment 表
- 综合情绪分数、标签、BTC信号

### MarketSentimentHistory 表
- 市场情绪历史、置信度、参与率、情绪分布

### DebateRecord 表
- 辩论过程记录、风险因子、最终建议

## 测试

运行所有测试:
```bash
python -m pytest tests/ -v
```

运行特定模块测试:
```bash
python -m pytest tests/test_sentiment_analyzer.py -v
```

## API 集成说明

### Kimi (Moonshot)
- API文档: https://platform.moonshot.cn/docs
- 模型: moonshot-v1-8k/32k/128k

### MiniMax
- API文档: https://api.minimax.chat/
- 模型: abab6.5-chat

### 智谱AI
- API文档: https://open.bigmodel.cn/dev/api
- 模型: glm-4/glm-4v

## 环境变量

可通过环境变量覆盖配置:

```bash
export KIMI_API_KEY="your_key"
export MINIMAX_API_KEY="your_key"
export ZHIPU_API_KEY="your_key"
export FEISHU_WEBHOOK="your_webhook"
```

## 日志

日志文件位于 `logs/sentiment_monitor.log`，支持:
- 按天轮转
- 保留7天
- 控制台和文件双输出

## 许可证

MIT License
