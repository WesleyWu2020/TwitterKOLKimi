# 币圈 KOL 情绪监控系统 - 启动指南

## 快速开始

### 1. 安装依赖

```bash
cd /Users/dmiwu/work/PythonProject/Polymarket_BTCETH_Kimi
pip install -r requirements.txt
```

### 2. 配置 API 密钥

```bash
# 复制配置模板
cp config/config.yaml.example config/config.yaml

# 编辑配置文件，填入你的 API 密钥
nano config/config.yaml  # 或使用其他编辑器
```

需要填写的字段：
- `models.kimi.api_key` - Kimi API 密钥
- `models.minimax.api_key` - MiniMax API 密钥  
- `models.zhipu.api_key` - 智谱 API 密钥
- `feishu_webhook` - 飞书机器人 Webhook 地址

### 3. 运行测试

```bash
python -m pytest tests/ -v
```

### 4. 启动系统

**测试模式（单次运行）:**
```bash
python main.py --once
```

**生产模式（定时调度）:**
```bash
python main.py
```

---

## API 密钥申请指南

### Kimi (Moonshot AI)
1. 访问 https://platform.moonshot.cn
2. 注册账号并登录
3. 进入"API 密钥管理"
4. 创建新密钥并复制

### MiniMax
1. 访问 https://minimax.chat
2. 注册开发者账号
3. 创建应用获取 API 密钥

### 智谱 AI (GLM)
1. 访问 https://open.bigmodel.cn
2. 注册账号
3. 在"API 密钥"页面创建密钥

### 飞书机器人
1. 打开飞书群聊
2. 点击右上角 "..." → "设置"
3. 选择 "群机器人" → "添加机器人"
4. 选择 "自定义机器人"
5. 复制 Webhook 地址

---

## 系统工作流程

```
每小时执行:
  1. 抓取 KOL 推文
  2. AI 情绪分析 (3个模型)
  3. 计算市场情绪指数
  4. [如果情绪变化大] AI 辩论生成投资建议
  5. 发送飞书通知
```

---

## 常见问题

### Q: Twitter 爬虫无法登录？
A: Twitter/X 的反爬机制严格，建议：
- 使用代理池
- 降低抓取频率
- 考虑使用 Twitter API (付费)

### Q: API 费用高吗？
A: 三个模型都有免费额度，一般情况下：
- Kimi: 赠送 15 元额度
- MiniMax: 有免费试用
- 智谱: 赠送 100 万 tokens

### Q: 可以只用一个模型吗？
A: 可以，在配置中设置两个模型的 weight 为 0 即可。

### Q: 如何停止系统？
A: 按 `Ctrl+C` 即可停止定时调度。

---

## 推送至 GitHub（可选）

```bash
# 1. 在 GitHub 创建新仓库（不要初始化 README）

# 2. 添加远程仓库（替换为你的用户名和仓库名）
git remote add origin https://github.com/YOUR_USERNAME/crypto-kol-sentiment.git

# 3. 推送代码
git push -u origin main
```

---

## 项目结构

```
crypto-kol-sentiment/
├── config/config.yaml       # 配置文件（需自行创建）
├── src/                     # 源代码
│   ├── config.py           # 配置管理
│   ├── models.py           # 数据库模型
│   ├── database.py         # 数据库操作
│   ├── sentiment_analyzer.py  # AI 情绪分析
│   ├── market_calculator.py   # 市场情绪计算
│   ├── debate_engine.py    # AI 辩论引擎
│   ├── feishu_notifier.py  # 飞书通知
│   ├── scheduler.py        # 主调度器
│   ├── twitter_scraper.py  # Twitter 爬虫
│   └── main.py             # 入口文件
├── tests/                   # 测试文件
├── data/                    # 数据库目录
└── README.md               # 项目说明
```

---

## 风险提示

⚠️ **投资有风险，入市需谨慎**

- 本系统仅供参考，不构成投资建议
- AI 分析结果可能存在偏差
- 加密货币交易风险极高，请自行判断
- 请严格遵守当地法律法规
