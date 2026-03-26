# src/sentiment_analyzer.py
"""情绪分析模块."""
import re
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
import requests


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    model_name: str
    sentiment_score: float  # 0-1, 0.5为中性
    confidence: float       # 0-1
    reasoning: str
    raw_response: Optional[str] = None


class SentimentAnalyzer:
    """情绪分析器类"""
    
    # 情绪分析Prompt模板
    SENTIMENT_PROMPT = """你是一个专业的加密货币市场情绪分析专家。

请分析以下推文的情绪倾向，重点关注对比特币(BTC)的看法。

推文内容：
{tweet_content}

请按以下格式返回分析结果：
情绪分数: [0.0-1.0之间的数值，0.5为中性，>0.5为看涨，<0.5为看跌]
置信度: [0.0-1.0之间的数值]
推理: [简要分析推理过程]

注意：
1. 情绪分数0.5表示中性，接近1.0表示极度看涨，接近0.0表示极度看跌
2. 置信度反映你对这个判断的确信程度
3. 如果推文不含BTC相关内容，情绪分数应为0.5，置信度降低
"""
    
    def __init__(self, config):
        """
        初始化情绪分析器
        
        Args:
            config: Config对象，包含模型配置
        """
        self.config = config
        self.model_configs = config.models
        self.executor = ThreadPoolExecutor(max_workers=3)
        logger.info("SentimentAnalyzer initialized with models: {}".format(
            list(self.model_configs.keys())
        ))
    
    def _build_prompt(self, tweet_content: str) -> str:
        """构建分析Prompt"""
        return self.SENTIMENT_PROMPT.format(tweet_content=tweet_content)
    
    def _call_model_api(
        self, 
        model_name: str, 
        model_config, 
        prompt: str
    ) -> Optional[AnalysisResult]:
        """
        调用单个模型API
        
        Args:
            model_name: 模型名称
            model_config: 模型配置
            prompt: 提示词
            
        Returns:
            AnalysisResult或None
        """
        try:
            headers = {
                "Authorization": f"Bearer {model_config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_config.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的加密货币市场情绪分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            base_url = model_config.base_url or self._get_default_base_url(model_name)
            
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            
            # 解析响应
            result = self._parse_response(raw_content, model_name)
            if result:
                result.raw_response = raw_content
                return result
            
            logger.warning(f"Failed to parse response from {model_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error calling {model_name} API: {e}")
            return None
    
    def _get_default_base_url(self, model_name: str) -> str:
        """获取默认API基础URL"""
        urls = {
            "kimi": "https://api.moonshot.cn/v1",
            "minimax": "https://api.minimax.chat/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4"
        }
        return urls.get(model_name, "")
    
    def _parse_response(self, response: str, model_name: str) -> Optional[AnalysisResult]:
        """
        解析模型响应
        
        Args:
            response: 原始响应文本
            model_name: 模型名称
            
        Returns:
            AnalysisResult或None
        """
        try:
            # 尝试提取情绪分数
            score_match = re.search(r'情绪分数[:：]\s*([0-9.]+)', response)
            confidence_match = re.search(r'置信度[:：]\s*([0-9.]+)', response)
            reasoning_match = re.search(r'推理[:：]\s*(.+?)(?:\n|$)', response, re.DOTALL)
            
            if score_match and confidence_match:
                score = float(score_match.group(1))
                confidence = float(confidence_match.group(1))
                reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"
                
                # 限制在有效范围内
                score = max(0.0, min(1.0, score))
                confidence = max(0.0, min(1.0, confidence))
                
                return AnalysisResult(
                    model_name=model_name,
                    sentiment_score=score,
                    confidence=confidence,
                    reasoning=reasoning
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
    
    def analyze_tweet(self, tweet_content: str) -> Dict[str, Any]:
        """
        分析推文情绪（并行调用多个模型）
        
        Args:
            tweet_content: 推文内容
            
        Returns:
            包含综合分数、标签和各模型结果的字典
        """
        prompt = self._build_prompt(tweet_content)
        
        # 并行调用所有模型
        results = []
        with ThreadPoolExecutor(max_workers=len(self.model_configs)) as executor:
            futures = {
                executor.submit(
                    self._call_model_api, 
                    name, 
                    config, 
                    prompt
                ): name 
                for name, config in self.model_configs.items()
            }
            
            for future in futures:
                try:
                    result = future.result(timeout=35)
                    if result:
                        results.append(result)
                        logger.info(f"Got result from {result.model_name}: score={result.sentiment_score:.3f}")
                except Exception as e:
                    logger.error(f"Model {futures[future]} failed: {e}")
        
        if not results:
            logger.warning("No valid results from any model")
            return {
                "composite_score": 0.5,
                "sentiment_label": "neutral",
                "btc_signal": False,
                "model_results": [],
                "model_consensus": 0.0
            }
        
        # 计算综合分数
        composite_score = self.calculate_composite_score(results)
        
        # 确定情绪标签
        sentiment_label = self._get_sentiment_label(composite_score)
        
        # 判断是否包含BTC信号
        btc_signal = composite_score != 0.5
        
        # 计算模型一致性
        model_consensus = self._calculate_consensus(results)
        
        logger.info(f"Analysis complete: score={composite_score:.3f}, label={sentiment_label}")
        
        return {
            "composite_score": composite_score,
            "sentiment_label": sentiment_label,
            "btc_signal": btc_signal,
            "model_results": [
                {
                    "model": r.model_name,
                    "score": r.sentiment_score,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning
                }
                for r in results
            ],
            "model_consensus": model_consensus
        }
    
    def calculate_composite_score(self, results: List[AnalysisResult]) -> float:
        """
        计算加权综合分数
        
        Args:
            results: 各模型分析结果列表
            
        Returns:
            加权综合分数
        """
        total_weight = 0
        weighted_sum = 0
        
        for result in results:
            model_config = self.model_configs.get(result.model_name)
            if model_config:
                # 权重 = 配置权重 * 置信度
                weight = model_config.weight * result.confidence
                weighted_sum += result.sentiment_score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        return round(weighted_sum / total_weight, 4)
    
    def _get_sentiment_label(self, score: float) -> str:
        """
        根据分数获取情绪标签
        
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
    
    def _calculate_consensus(self, results: List[AnalysisResult]) -> float:
        """
        计算模型一致性（方差的倒数）
        
        Args:
            results: 各模型分析结果列表
            
        Returns:
            一致性分数 (0-1)
        """
        if len(results) < 2:
            return 1.0
        
        scores = [r.sentiment_score for r in results]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        
        # 将方差转换为一致性分数（方差越小，一致性越高）
        consensus = max(0, 1 - variance * 4)  # 放大方差影响
        return round(consensus, 4)
