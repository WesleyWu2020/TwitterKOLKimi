# Twitter API 接入指南

## 1. 申请开发者账号
- 访问 https://developer.twitter.com/
- 申请 Basic 或 Pro 套餐
- Basic: $100/月, 10000 条/月

## 2. 创建 App 获取密钥
- Consumer Key (API Key)
- Consumer Secret
- Bearer Token

## 3. 配置到项目
```yaml
# config/config.yaml
twitter:
  bearer_token: "your_bearer_token"
  api_key: "your_api_key"
  api_secret: "your_api_secret"
```
