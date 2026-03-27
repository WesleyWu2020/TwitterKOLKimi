# xAI SDK 安装与使用指南

## 安装

```bash
pip install xai-sdk
```

如果安装慢，可以尝试：
```bash
pip install xai-sdk -i https://pypi.org/simple
```

## 配置

编辑 `config/config.yaml`：

```yaml
data_source: "xai_sdk"  # ← 使用 xAI SDK

xai:
  api_key: "xai-your-api-key-here"
  model: "grok-4.20-reasoning"  # 推荐此模型，工具调用能力更强
```

## 验证安装

```bash
python test_xai_sdk.py
```

## 与 REST API 的区别

| 特性 | xAI SDK | xAI REST API |
|------|---------|--------------|
| 工具调用 | ✅ 自动处理 | ⚠️ 需手动处理 |
| 代码复杂度 | 简单 | 较复杂 |
| 实时数据 | ✅ 支持 X Search | ⚠️ 可能不支持 |
| 推荐度 | ⭐⭐⭐ 推荐 | ⭐⭐ 备选 |

## 测试

```bash
python -m src.main --once
```

日志应显示：
```
✅ Using xAI SDK with Grok X Search (REAL-TIME Twitter data)
```
