# 币圈 KOL 情绪监控与 AI 投资建议系统 - 设计文档

**创建日期:** 2026-03-26  
**版本:** 1.0  
**状态:** 已批准

---

## 1. 项目概述

构建一个自动化的币圈 KOL 情绪监控系统，每小时抓取 Twitter 上粉丝数超过 10 万的币圈 KOL 帖子，使用多模型 AI 进行情绪分析，并通过正反方大模型辩论生成投资建议，最终通过飞书机器人推送。

### 1.1 核心功能

- **Twitter 数据抓取**: 自动发现和追踪符合条件的币圈 KOL
- **多模型情绪分析**: Kimi(40%) + MiniMax(30%) + 智谱(30%) 加权投票
- **市场情绪指数**: 聚合所有 KOL 情绪的量化指标
- **AI 辩论系统**: 正方(智谱) vs 反方(MiniMax) 的投资观点辩论
- **飞书通知**: 实时推送市场情绪和最终投资建议

### 1.2 技术栈

- **语言**: Python 3.11+
- **数据库**: SQLite (初期)
- **爬虫**: Playwright
- **AI API**: Kimi API, MiniMax API, 智谱 API
- **调度**: APScheduler
- **配置**: Pydantic Settings

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        调度层                                │
│                   (APScheduler)                              │
│              每小时触发任务调度                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
    ▼                  ▼                  ▼
┌──────────┐    ┌──────────┐      ┌──────────────┐
│ KOL发现   │    │ 推文抓取  │      │ 情绪指数计算  │
│ 爬虫     │    │ 爬虫     │      │ 定时任务     │
└────┬─────┘    └────┬─────┘      └──────┬───────┘
     │               │                   │
     └───────────────┼───────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │   SQLite DB    │
            │  - kols        │
            │  - tweets      │
            │  - sentiments  │
            │  - debates     │
            │  - market_idx  │
            └────────┬───────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
     ▼               ▼               ▼
┌─────────┐   ┌─────────────┐  ┌──────────┐
│情绪分析  │   │  辩论引擎    │  │飞书通知  │
│(3模型)   │   │ 正方↔反方   │  │机器人   │
└─────────┘   └─────────────┘  └──────────┘
```

---

## 3. 数据模型

### 3.1 KOL 表
```sql
CREATE TABLE kols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,          -- Twitter 用户名
    display_name TEXT,                       -- 显示名称
    followers_count INTEGER,                 -- 粉丝数
    is_active BOOLEAN DEFAULT 1,             -- 是否活跃监控
    accuracy_rate REAL DEFAULT 0.5,          -- 历史预测准确率
    influence_score REAL DEFAULT 1.0,        -- 影响力分数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 推文表
```sql
CREATE TABLE tweets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT UNIQUE NOT NULL,           -- Twitter 推文 ID
    kol_id INTEGER NOT NULL,
    content TEXT NOT NULL,                   -- 推文内容
    posted_at TIMESTAMP,                     -- 推文发布时间
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    has_btc_keyword BOOLEAN DEFAULT 0,       -- 是否包含BTC关键词
    FOREIGN KEY (kol_id) REFERENCES kols(id)
);
```

### 3.3 模型分析表
```sql
CREATE TABLE model_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,                -- kimi/minimax/zhipu
    sentiment_score REAL NOT NULL,           -- -1.0 ~ +1.0
    confidence REAL NOT NULL,                -- 0.0 ~ 1.0
    reasoning TEXT,                          -- 分析理由
    raw_response TEXT,                       -- 原始API返回
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tweet_id) REFERENCES tweets(id),
    UNIQUE(tweet_id, model_name)
);
```

### 3.4 综合情绪表
```sql
CREATE TABLE sentiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id INTEGER UNIQUE NOT NULL,
    composite_score REAL NOT NULL,           -- 加权综合分数
    sentiment_label TEXT NOT NULL,           -- 极度看空/看空/中性/看多/极度看多
    btc_signal BOOLEAN DEFAULT 0,            -- 是否包含BTC交易信号
    model_consensus REAL,                    -- 模型一致性(标准差)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tweet_id) REFERENCES tweets(id)
);
```

### 3.5 市场情绪历史表
```sql
CREATE TABLE market_sentiment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    market_sentiment_index REAL NOT NULL,    -- 市场情绪指数 -1.0 ~ +1.0
    confidence REAL NOT NULL,                -- 整体置信度
    participation_rate REAL NOT NULL,        -- 参与率
    active_kols INTEGER NOT NULL,            -- 活跃KOL数
    total_kols INTEGER NOT NULL,             -- 总监控KOL数
    distribution TEXT NOT NULL,              -- JSON: 情绪分布
    top_signals TEXT,                        -- JSON: Top信号
    change_1h REAL,                          -- 1小时变化
    change_24h REAL                          -- 24小时变化
);
```

### 3.6 辩论记录表
```sql
CREATE TABLE debate_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_sentiment_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 正方第一轮
    proponent_stance TEXT,                   -- 看多/看空/中性
    proponent_confidence REAL,               -- 置信度
    proponent_key_points TEXT,               -- JSON: 核心理由
    proponent_raw_output TEXT,               -- 原始输出
    
    -- 反方
    opponent_challenges TEXT,                -- JSON: 质疑清单
    opponent_high_risk_count INTEGER,        -- 严重质疑数
    opponent_medium_risk_count INTEGER,      -- 中等质疑数
    opponent_raw_output TEXT,                -- 原始输出
    
    -- 正方回应
    proponent_admitted_points TEXT,          -- JSON: 承认的质疑
    proponent_refuted_points TEXT,           -- JSON: 反驳的质疑
    proponent_adjusted_stance TEXT,          -- 调整后立场
    proponent_adjusted_confidence REAL,      -- 调整后置信度
    proponent_response_raw TEXT,             -- 回应原始输出
    
    -- 最终建议
    final_recommendation TEXT,               -- JSON: 最终投资建议
    
    FOREIGN KEY (market_sentiment_id) REFERENCES market_sentiment_history(id)
);
```

---

## 4. 核心模块设计

### 4.1 配置模块 (config.py)

使用 Pydantic Settings 管理配置：

```python
class TwitterConfig(BaseModel):
    username: str
    password: str
    min_followers: int = 100000
    keywords: List[str] = ["BTC", "Bitcoin", "比特币", "ETH", "以太坊"]
    tweets_per_kol: int = 10

class AIModelConfig(BaseModel):
    api_key: str
    model: str
    weight: float
    base_url: Optional[str] = None

class Config(BaseSettings):
    twitter: TwitterConfig
    models: Dict[str, AIModelConfig]  # kimi, minimax, zhipu
    feishu_webhook: str
    feishu_secret: Optional[str] = None
    database_path: str = "data/sentiment.db"
    debate_trigger_threshold: float = 0.3
```

### 4.2 数据库模块 (database.py)

使用 SQLAlchemy ORM：

```python
class Database:
    def __init__(self, db_path: str)
    def init_tables(self) -> None
    def get_or_create_kol(self, username: str, **kwargs) -> KOL
    def save_tweet(self, kol_id: int, tweet_data: dict) -> Tweet
    def save_model_analysis(self, tweet_id: int, model: str, result: dict)
    def calculate_market_sentiment(self) -> MarketSentimentResult
    def get_recent_tweets_for_analysis(self, hours: int = 1) -> List[Tweet]
```

### 4.3 Twitter 爬虫模块 (twitter_scraper.py)

```python
class TwitterScraper:
    def __init__(self, config: TwitterConfig)
    async def login(self) -> bool
    async def discover_kols(self, keywords: List[str]) -> List[dict]
    async def fetch_kol_tweets(self, username: str, count: int) -> List[dict]
    async def close(self)
```

### 4.4 AI 情绪分析模块 (sentiment_analyzer.py)

```python
class SentimentAnalyzer:
    def __init__(self, models_config: Dict[str, AIModelConfig])
    
    async def analyze_with_kimi(self, tweet: Tweet) -> AnalysisResult
    async def analyze_with_minimax(self, tweet: Tweet) -> AnalysisResult
    async def analyze_with_zhipu(self, tweet: Tweet) -> AnalysisResult
    
    async def analyze_tweet(self, tweet: Tweet) -> CompositeResult:
        """并行调用三个模型，计算加权综合分数"""
        
    def calculate_composite_score(self, results: List[AnalysisResult]) -> float:
        """加权平均，处理分歧"""
```

### 4.5 市场情绪计算模块 (market_calculator.py)

```python
class MarketCalculator:
    def __init__(self, db: Database)
    
    def calculate_market_sentiment(self) -> MarketSentimentResult:
        """
        计算市场情绪指数
        公式: Σ(情绪分数 × 影响力权重) / Σ(影响力权重)
        """
        
    def calculate_kol_influence_weight(self, kol: KOL) -> float:
        """
        影响力权重 = 粉丝数权重40% + 历史准确率40% + 互动率20%
        """
        
    def get_sentiment_distribution(self, sentiments: List[Sentiment]) -> dict
```

### 4.6 AI 辩论引擎模块 (debate_engine.py)

```python
class DebateEngine:
    def __init__(self, zhipu_config: AIModelConfig, minimax_config: AIModelConfig)
    
    async def debate(self, market_data: MarketSentimentResult) -> DebateResult:
        """
        辩论流程:
        1. 正方(智谱)给出投资建议
        2. 反方(MiniMax)提出质疑
        3. 正方(智谱)回应质疑并完善建议
        """
        
    async def _proponent_round_1(self, market_data: dict) -> ProponentOutput
    async def _opponent_challenge(self, market_data: dict, proponent_output: ProponentOutput) -> OpponentOutput
    async def _proponent_response(self, market_data: dict, round1: ProponentOutput, opponent: OpponentOutput) -> FinalOutput
```

### 4.7 飞书通知模块 (feishu_notifier.py)

```python
class FeishuNotifier:
    def __init__(self, webhook: str, secret: Optional[str] = None)
    
    async def send_market_sentiment(self, result: MarketSentimentResult)
    async def send_debate_result(self, debate: DebateResult, sentiment: MarketSentimentResult)
    def _format_sentiment_message(self, result: MarketSentimentResult) -> dict
    def _format_debate_message(self, debate: DebateResult) -> dict
```

### 4.8 主调度器 (scheduler.py)

```python
class SentimentMonitor:
    def __init__(self, config: Config)
    
    async def run_fetch_job(self):
        """每小时执行: 抓取推文 -> 情绪分析 -> 存储"""
        
    async def run_market_analysis_job(self):
        """每小时执行: 计算市场情绪 -> AI辩论 -> 飞书通知"""
        
    def start_scheduler(self):
        """启动定时调度"""
        
    async def run_once(self):
        """单次运行（测试用）"""
```

---

## 5. 情绪分析 Prompt 设计

### 5.1 系统 Prompt 模板

```
你是一位专业的加密货币市场情绪分析师。

【任务】
分析以下推文的情绪倾向，给出量化评分。

【评分标准】
-1.0 = 极度看空 (强烈看跌，建议做空)
-0.6 = 看空 (看跌，可能下跌)
-0.2 = 中性偏空 (轻微看跌)
 0.0 = 完全中性
+0.2 = 中性偏多 (轻微看涨)
+0.6 = 看多 (看涨，可能上涨)
+1.0 = 极度看多 (强烈看涨，建议做多)

【输出格式】
{
  "sentiment_score": float,      // -1.0 到 +1.0
  "confidence": float,           // 0.0 到 1.0，你对判断的确信程度
  "btc_signal": boolean,         // 是否明确提及BTC交易建议
  "reasoning": string            // 简要分析理由(50字以内)
}

【推文内容】
{tweet_content}
```

---

## 6. 辩论 Prompt 设计

### 6.1 正方第一轮 (智谱)
```
你是一位专业的加密货币投资分析师，立场看多BTC。

【输入数据】
市场情绪指数: {sentiment_index}
情绪分布: {distribution}
Top看多信号: {bullish_signals}
Top看空信号: {bearish_signals}

【任务】
基于KOL情绪数据，给出看多投资建议：
1. 投资立场（强烈看多/看多/中性偏多）
2. 核心理由（3-5条，基于数据）
3. 具体操作建议（方向/杠杆/止损/目标/周期）
4. 置信度（0-100%）
```

### 6.2 反方质疑 (MiniMax)
```
你是一位严谨的风险分析师，专门发现投资机会中的风险。

【正方投资建议】
{proponent_output}

【任务】
逐条质疑正方观点：
1. 数据盲区（KOL情绪是滞后指标等）
2. 逻辑漏洞（price in、幸存者偏差等）
3. 反向指标（链上数据、宏观经济等）
4. 黑天鹅风险
每条标注严重程度（高/中/低）
```

### 6.3 正方回应 (智谱)
```
回应反方质疑，完善投资建议。

【原始建议】{proponent_round1}
【反方质疑】{opponent_challenges}

【任务】
1. 承认合理的质疑
2. 反驳无理的质疑
3. 基于合理质疑调整建议（仓位/止损/目标）
4. 给出最终投资建议（带风险提示）
```

---

## 7. 项目结构

```
crypto-kol-sentiment/
├── config/
│   └── config.yaml              # 配置文件
├── src/
│   ├── __init__.py
│   ├── config.py                # Pydantic配置模型
│   ├── database.py              # 数据库操作
│   ├── models.py                # SQLAlchemy模型
│   ├── twitter_scraper.py       # Twitter爬虫
│   ├── sentiment_analyzer.py    # 情绪分析器
│   ├── market_calculator.py     # 市场情绪计算
│   ├── debate_engine.py         # AI辩论引擎
│   ├── feishu_notifier.py       # 飞书通知
│   └── scheduler.py             # 主调度器
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_sentiment_analyzer.py
│   ├── test_market_calculator.py
│   ├── test_debate_engine.py
│   └── test_feishu_notifier.py
├── data/
│   └── .gitkeep                 # SQLite数据库目录
├── docs/
│   └── superpowers/
│       ├── specs/               # 设计文档
│       └── plans/               # 实施计划
├── requirements.txt
├── main.py                      # 入口文件
└── README.md
```

---

## 8. 测试策略

### 8.1 单元测试
- 数据库 CRUD 操作
- 情绪分数计算（加权平均、分歧处理）
- 市场情绪指数计算
- 飞书消息格式化

### 8.2 集成测试
- 完整情绪分析流程
- 辩论引擎全流程
- 数据库 + 业务逻辑集成

### 8.3 手动验证
- 爬虫实际抓取
- AI API 调用和响应解析
- 飞书通知实际发送

---

## 9. 部署与运行

### 9.1 安装依赖
```bash
pip install -r requirements.txt
playwright install
```

### 9.2 配置
复制 `config/config.yaml.example` 为 `config/config.yaml`，填入 API 密钥。

### 9.3 初始化数据库
```bash
python -c "from src.database import Database; db = Database('data/sentiment.db'); db.init_tables()"
```

### 9.4 运行
```bash
# 开发模式（单次运行）
python main.py --once

# 生产模式（定时调度）
python main.py
```

---

## 10. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| Twitter 反爬 | Playwright + 随机延迟 + 代理池 |
| AI API 成本 | 缓存机制 + 按量控制 + 分层触发 |
| 情绪分析不准确 | 多模型投票 + 历史准确率追踪 |
| 数据丢失 | SQLite 定期备份 |
| 投资建议亏损 | 明确风险提示 + 不承诺收益 |

---

**设计确认:** ✅ 已批准  
**下一步:** 编写实施计划
