# src/market_calculator.py
"""市场情绪计算模块."""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class KOLSentiment:
    """KOL情绪数据"""
    kol_id: int
    username: str
    sentiment_score: float
    confidence: float
    followers_count: int
    accuracy_rate: float
    influence_score: float


class MarketCalculator:
    """市场情绪计算器"""
    
    def __init__(self):
        """初始化市场情绪计算器"""
        logger.info("MarketCalculator initialized")
    
    def calculate_kol_influence_weight(
        self,
        followers_count: int,
        accuracy_rate: float,
        base_weight: float = 1.0
    ) -> float:
        """
        计算KOL影响力权重
        
        Args:
            followers_count: 粉丝数
            accuracy_rate: 历史准确率
            base_weight: 基础权重
            
        Returns:
            影响力权重
        """
        # 粉丝数权重（对数缩放，避免大V过于主导）
        followers_factor = min(3.0, max(0.5, (followers_count / 100000) ** 0.5))
        
        # 准确率权重（历史表现好的KOL权重更高）
        accuracy_factor = 0.5 + accuracy_rate  # 范围0.5-1.5
        
        # 综合权重
        weight = base_weight * followers_factor * accuracy_factor
        
        return round(weight, 4)
    
    def calculate_market_sentiment(
        self,
        sentiments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算综合市场情绪指数
        
        Args:
            sentiments: 情绪数据列表，每项包含score和weight
            
        Returns:
            市场情绪统计结果
        """
        if not sentiments:
            return {
                "market_index": 0.5,
                "confidence": 0.0,
                "weighted_std": 0.0,
                "participation_score": 0.0,
                "distribution": {"bullish": 0, "neutral": 0, "bearish": 0}
            }
        
        # 计算加权平均
        total_weight = sum(s.get("weight", 1.0) for s in sentiments)
        weighted_sum = sum(s["score"] * s.get("weight", 1.0) for s in sentiments)
        
        market_index = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        # 计算加权标准差（衡量分歧程度）
        variance_sum = sum(
            s.get("weight", 1.0) * (s["score"] - market_index) ** 2 
            for s in sentiments
        )
        weighted_std = (variance_sum / total_weight) ** 0.5 if total_weight > 0 else 0
        
        # 置信度：基于样本数量和一致性
        sample_confidence = min(1.0, len(sentiments) / 30)  # 30个样本达到满置信度
        consistency_confidence = max(0, 1 - weighted_std * 2)  # 分歧小则置信度高
        confidence = round((sample_confidence + consistency_confidence) / 2, 4)
        
        # 参与度分数
        participation_score = min(1.0, len(sentiments) / 20)
        
        # 情绪分布
        labels = [self._score_to_label(s["score"]) for s in sentiments]
        distribution = self.calculate_sentiment_distribution(labels)
        
        return {
            "market_index": round(market_index, 4),
            "confidence": confidence,
            "weighted_std": round(weighted_std, 4),
            "participation_score": round(participation_score, 4),
            "distribution": distribution,
            "sample_count": len(sentiments)
        }
    
    def calculate_sentiment_distribution(
        self,
        labels: List[str]
    ) -> Dict[str, Any]:
        """
        计算情绪分布统计
        
        Args:
            labels: 情绪标签列表
            
        Returns:
            分布统计字典
        """
        distribution = {
            "bullish": 0,
            "neutral": 0,
            "bearish": 0,
            "total": len(labels)
        }
        
        for label in labels:
            if label in distribution:
                distribution[label] += 1
        
        # 计算百分比
        total = len(labels)
        if total > 0:
            distribution["bullish_pct"] = round(distribution["bullish"] / total * 100, 2)
            distribution["neutral_pct"] = round(distribution["neutral"] / total * 100, 2)
            distribution["bearish_pct"] = round(distribution["bearish"] / total * 100, 2)
        else:
            distribution["bullish_pct"] = 0
            distribution["neutral_pct"] = 0
            distribution["bearish_pct"] = 0
        
        return distribution
    
    def _score_to_label(self, score: float) -> str:
        """
        分数转标签
        
        Args:
            score: 情绪分数
            
        Returns:
            情绪标签
        """
        if score > 0.6:
            return "bullish"
        elif score < 0.4:
            return "bearish"
        else:
            return "neutral"
    
    def detect_sentiment_change(
        self,
        current_index: float,
        previous_index: float,
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        检测市场情绪变化
        
        Args:
            current_index: 当前情绪指数
            previous_index: 上一期情绪指数
            threshold: 变化阈值
            
        Returns:
            变化检测结果
        """
        change = current_index - previous_index
        change_pct = (change / previous_index * 100) if previous_index != 0 else 0
        
        return {
            "change": round(change, 4),
            "change_pct": round(change_pct, 2),
            "direction": "up" if change > 0 else "down" if change < 0 else "stable",
            "significant": abs(change) >= threshold,
            "current": round(current_index, 4),
            "previous": round(previous_index, 4)
        }
    
    def get_market_summary(
        self,
        sentiment_data: Dict[str, Any],
        change_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成市场情绪摘要
        
        Args:
            sentiment_data: 情绪数据
            change_data: 变化数据
            
        Returns:
            摘要文本
        """
        index = sentiment_data["market_index"]
        confidence = sentiment_data["confidence"]
        dist = sentiment_data["distribution"]
        
        # 情绪描述
        if index > 0.7:
            mood = "极度看涨"
        elif index > 0.6:
            mood = "看涨"
        elif index < 0.3:
            mood = "极度看跌"
        elif index < 0.4:
            mood = "看跌"
        else:
            mood = "中性"
        
        summary = f"市场情绪: {mood} (指数: {index:.3f}, 置信度: {confidence:.1%})\n"
        summary += f"看涨: {dist.get('bullish', 0)} | 中性: {dist.get('neutral', 0)} | 看跌: {dist.get('bearish', 0)}\n"
        
        if change_data and change_data["significant"]:
            direction = "上涨" if change_data["direction"] == "up" else "下跌"
            summary += f"较上期{direction}: {abs(change_data['change']):.3f}"
        
        return summary
