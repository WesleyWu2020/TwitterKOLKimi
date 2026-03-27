# src/feishu_notifier.py
"""飞书通知模块."""
import json
import base64
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger
import requests


class FeishuNotifier:
    """飞书通知器类"""
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        """
        初始化飞书通知器
        
        Args:
            webhook_url: 飞书Webhook URL
            secret: 签名密钥（可选）
        """
        self.webhook_url = webhook_url
        self.secret = secret
        logger.info("FeishuNotifier initialized")
    
    def _generate_sign(self, timestamp: int) -> Optional[str]:
        """
        生成飞书签名
        
        Args:
            timestamp: 时间戳
            
        Returns:
            签名字符串或None
        """
        if not self.secret:
            return None
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign
    
    def _send_message(self, content: Dict[str, Any]) -> bool:
        """
        发送消息到飞书
        
        Args:
            content: 消息内容
            
        Returns:
            是否发送成功
        """
        try:
            timestamp = int(datetime.now().timestamp())
            
            payload = {
                "timestamp": timestamp,
                "msg_type": "interactive",
                "card": content
            }
            
            sign = self._generate_sign(timestamp)
            if sign:
                payload["sign"] = sign
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                logger.info("Message sent to Feishu successfully")
                return True
            else:
                logger.error(f"Feishu API error: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to Feishu: {e}")
            return False
    
    def send_market_sentiment(self, sentiment_data: Dict[str, Any], tweet_urls: List[Dict[str, str]] = None) -> bool:
        """
        发送市场情绪通知
        
        Args:
            sentiment_data: 市场情绪数据
            tweet_urls: 可选，推文链接列表
            
        Returns:
            是否发送成功
        """
        card = self._format_sentiment_card(sentiment_data, tweet_urls)
        return self._send_message(card)
    
    def send_debate_result(self, debate_result: Dict[str, Any]) -> bool:
        """
        发送辩论结果通知
        
        Args:
            debate_result: 辩论结果数据
            
        Returns:
            是否发送成功
        """
        card = self._format_debate_card(debate_result)
        return self._send_message(card)
    
    def _format_sentiment_card(self, data: Dict[str, Any], tweet_urls: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        格式化市场情绪卡片（带数据源警告和推文链接）
        
        Args:
            data: 市场情绪数据
            tweet_urls: 推文链接列表
            
        Returns:
            飞书卡片格式
        """
        index = data.get("market_sentiment_index", 0.5)
        confidence = data.get("confidence", 0)
        distribution = data.get("distribution", {})
        active_kols = data.get("active_kols", 0)
        sample_count = data.get("sample_count", 0)
        
        # 根据指数确定颜色和情绪描述
        if index > 0.7:
            color = "red"
            mood = "🟢 极度看涨"
        elif index > 0.6:
            color = "orange"
            mood = "🟡 看涨"
        elif index < 0.3:
            color = "green"
            mood = "🔴 极度看跌"
        elif index < 0.4:
            color = "blue"
            mood = "🔵 看跌"
        else:
            color = "grey"
            mood = "⚪ 中性"
        
        # 构建基础元素
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**当前情绪:** {mood}\n**情绪指数:** {index:.3f}\n**置信度:** {confidence:.1%}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**情绪分布**\n🟢 看涨: {distribution.get('bullish', 0)} | ⚪ 中性: {distribution.get('neutral', 0)} | 🔴 看跌: {distribution.get('bearish', 0)}"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**样本统计**\n活跃KOL: {active_kols} | 分析推文: {sample_count} 条"
                }
            }
        ]
        
        # 添加可折叠的推文链接列表
        if tweet_urls:
            links_text = f"**📎 参考推文 ({len(tweet_urls)}条)**\n\n"
            for i, item in enumerate(tweet_urls[:10], 1):  # 最多显示10条
                username = item.get('username', 'unknown')
                preview = item.get('content_preview', '')
                url = item.get('url', '')
                links_text += f"{i}. [@{username}]({url})\n   {preview}\n\n"
            
            if len(tweet_urls) > 10:
                links_text += f"*...还有 {len(tweet_urls) - 10} 条推文*"
            
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": links_text
                },
                "collapsible": True,
                "header": {
                    "tag": "plain_text",
                    "content": f"📎 查看参考推文 ({len(tweet_urls)}条)"
                }
            })
        
        # 添加底部信息
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"✅ 数据来源: Grok X Search (实时) | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })
        
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 市场情绪报告"
                },
                "template": color
            },
            "elements": elements
        }
        
        return card
    
    def _format_debate_card(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化辩论结果卡片（包含详细过程）
        
        Args:
            result: 辩论结果数据
            
        Returns:
            飞书卡片格式
        """
        stance = result.get("proponent_stance", "neutral")
        confidence = result.get("proponent_confidence", 0)
        adjusted_confidence = result.get("proponent_adjusted_confidence", confidence)
        high_risks = result.get("opponent_high_risk_count", 0)
        medium_risks = result.get("opponent_medium_risk_count", 0)
        recommendation = result.get("final_recommendation", {})
        
        # 获取详细过程
        key_points = result.get("proponent_key_points", [])
        challenges = result.get("opponent_challenges", [])
        admitted = result.get("proponent_admitted_points", [])
        refuted = result.get("proponent_refuted_points", [])
        
        # 根据立场确定颜色
        if stance == "bullish":
            color = "red"
            stance_text = "📈 看涨"
        elif stance == "bearish":
            color = "green"
            stance_text = "📉 看跌"
        else:
            color = "grey"
            stance_text = "➡️ 中性"
        
        action = recommendation.get("action", "hold")
        risk_level = recommendation.get("risk_level", "medium")
        
        # 行动翻译
        action_map = {
            "buy": "买入",
            "sell": "卖出",
            "hold": "持有",
            "观望": "观望",
            "cautious_bullish": "谨慎看涨",
            "cautious_bearish": "谨慎看跌"
        }
        action_text = action_map.get(action, action)
        
        # 风险等级翻译和颜色
        risk_map = {
            "high": "🔴 高风险",
            "medium": "🟡 中风险",
            "low": "🟢 低风险"
        }
        risk_text = risk_map.get(risk_level, risk_level)
        
        # 置信度变化趋势
        confidence_change = adjusted_confidence - confidence
        if confidence_change > 0:
            trend = f"↗️ +{confidence_change:.1%}"
        elif confidence_change < 0:
            trend = f"↘️ {confidence_change:.1%}"
        else:
            trend = "➡️ 持平"
        
        # 构建详细过程文本
        # Round 1: 正方论点
        round1_text = "**🎙️ 正方观点**\n"
        if key_points:
            for i, point in enumerate(key_points[:3], 1):
                round1_text += f"{i}. {point}\n"
        else:
            round1_text += "（无详细论点）\n"
        
        # Round 2: 反方挑战
        round2_text = "**⚔️ 反方质疑**\n"
        if challenges:
            for i, challenge in enumerate(challenges[:3], 1):
                round2_text += f"{i}. {challenge}\n"
        else:
            round2_text += "（无详细质疑）\n"
        
        # Round 3: 正方回应
        round3_text = "**🛡️ 正方回应**\n"
        if admitted:
            round3_text += "✅ 承认:\n"
            for point in admitted[:2]:
                round3_text += f"  • {point}\n"
        if refuted:
            round3_text += "❌ 反驳:\n"
            for point in refuted[:2]:
                round3_text += f"  • {point}\n"
        if not admitted and not refuted:
            round3_text += "（无详细回应）\n"
        
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🤖 AI 辩论过程"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**立场:** {stance_text} | **置信度:** {confidence:.0%} → {adjusted_confidence:.0%} ({trend})"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": round1_text
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": round2_text
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": round3_text
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**⚠️ 风险评估**\n🔴 高风险: {high_risks} 个 | 🟡 中风险: {medium_risks} 个"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**🎯 最终建议**\n行动: {action_text} | 风险等级: {risk_text}"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
        
        return card
    
    def _format_sentiment_message(self, data: Dict[str, Any]) -> str:
        """
        格式化市场情绪消息（文本格式，用于调试）
        
        Args:
            data: 市场情绪数据
            
        Returns:
            格式化消息文本
        """
        index = data.get("market_sentiment_index", 0.5)
        confidence = data.get("confidence", 0)
        distribution = data.get("distribution", {})
        
        return f"""
市场情绪报告
============
情绪指数: {index:.3f}
置信度: {confidence:.1%}
情绪分布: 看涨({distribution.get('bullish', 0)}) 中性({distribution.get('neutral', 0)}) 看跌({distribution.get('bearish', 0)})
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def _format_debate_message(self, result: Dict[str, Any]) -> str:
        """
        格式化辩论结果消息（文本格式，用于调试）
        
        Args:
            result: 辩论结果数据
            
        Returns:
            格式化消息文本
        """
        stance = result.get("proponent_stance", "neutral")
        confidence = result.get("proponent_confidence", 0)
        adjusted = result.get("proponent_adjusted_confidence", confidence)
        recommendation = result.get("final_recommendation", {})
        
        return f"""
AI 辩论结果
===========
立场: {stance}
初始置信度: {confidence:.1%}
调整后置信度: {adjusted:.1%}
建议行动: {recommendation.get('action', 'hold')}
风险等级: {recommendation.get('risk_level', 'medium')}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
