# src/debate_engine.py
"""AI辩论引擎模块."""
import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger
import requests


@dataclass
class DebateResult:
    """辩论结果数据类"""
    proponent_stance: str
    proponent_confidence: float
    proponent_key_points: List[str]
    proponent_raw_output: str
    
    opponent_challenges: List[str]
    opponent_high_risk_count: int
    opponent_medium_risk_count: int
    opponent_raw_output: str
    
    proponent_admitted_points: List[str]
    proponent_refuted_points: List[str]
    proponent_adjusted_stance: str
    proponent_adjusted_confidence: float
    proponent_response_raw: str
    
    final_recommendation: Dict[str, Any]


class DebateEngine:
    """辩论引擎类"""
    
    # 正方第一轮Prompt
    PROPONENT_PROMPT_1 = """你是加密货币市场情绪分析的正方代表。你的任务是支持当前的市场情绪判断。

当前市场情绪: {sentiment_label}
市场情绪指数: {market_index:.3f}

支持证据:
{supporting_evidence}

请作为正方，阐述支持当前市场情绪的论点。请按以下格式返回：

立场: [bullish/bearish/neutral]
置信度: [0.0-1.0]
关键论点:
1. [论点1]
2. [论点2]
3. [论点3]

要求：
1. 立场必须与当前市场情绪一致
2. 提供具体的数据或逻辑支撑
3. 至少列出2-3个关键论点
"""

    # 反方挑战Prompt
    OPPONENT_PROMPT = """你是加密货币市场情绪分析的反方代表。你的任务是挑战正方的观点，发现潜在风险。

正方立场:
{proponent_stance}

正方关键论点:
{key_points}

请作为反方，对正方观点进行批判性分析。请按以下格式返回：

挑战点:
1. [挑战1]
2. [挑战2]
3. [挑战3]

风险因子评估:
高风险因子数: [数量]
中风险因子数: [数量]

要求：
1. 每个挑战点需针对正方的具体论点
2. 识别可能被忽视的风险因素
3. 客观分析，不要情绪化
"""

    # 正方回应Prompt
    PROPONENT_RESPONSE_PROMPT = """你继续作为正方代表，回应反方的挑战。

原始立场: {proponent_stance}
原始置信度: {proponent_confidence}

反方挑战:
{opponent_challenges}

请对反方的每个挑战点进行回应。请按以下格式返回：

承认的有效点:
1. [点1]
2. [点2]

反驳的点:
1. [点1]
2. [点2]

调整后立场: [bullish/bearish/neutral]
调整后置信度: [0.0-1.0]
置信度调整说明: [简要说明]

最终建议:
行动: [buy/sell/hold/观望]
风险等级: [high/medium/low]
理由: [简要说明]
"""

    def __init__(self, config):
        """
        初始化辩论引擎
        
        Args:
            config: Config对象
        """
        self.config = config
        logger.info("DebateEngine initialized")
    
    def debate(
        self,
        sentiment_label: str,
        market_index: float,
        supporting_evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行三轮辩论
        
        Args:
            sentiment_label: 情绪标签
            market_index: 市场情绪指数
            supporting_evidence: 支持证据列表
            
        Returns:
            辩论结果字典
        """
        logger.info(f"Starting debate for {sentiment_label} sentiment (index: {market_index:.3f})")
        
        # Round 1: 正方阐述观点
        round1_result = self._proponent_round_1(
            sentiment_label, 
            market_index, 
            supporting_evidence
        )
        
        # Round 2: 反方挑战
        round2_result = self._opponent_challenge(
            round1_result["stance"],
            round1_result["key_points"]
        )
        
        # Round 3: 正方回应
        round3_result = self._proponent_response(
            round1_result["stance"],
            round1_result["confidence"],
            round2_result["challenges"]
        )
        
        # 构建最终结果
        result = {
            "proponent_stance": round1_result["stance"],
            "proponent_confidence": round1_result["confidence"],
            "proponent_key_points": round1_result["key_points"],
            "proponent_raw_output": round1_result["raw_output"],
            
            "opponent_challenges": round2_result["challenges"],
            "opponent_high_risk_count": round2_result["high_risk_count"],
            "opponent_medium_risk_count": round2_result["medium_risk_count"],
            "opponent_raw_output": round2_result["raw_output"],
            
            "proponent_admitted_points": round3_result["admitted_points"],
            "proponent_refuted_points": round3_result["refuted_points"],
            "proponent_adjusted_stance": round3_result["adjusted_stance"],
            "proponent_adjusted_confidence": round3_result["adjusted_confidence"],
            "proponent_response_raw": round3_result["raw_output"],
            
            "final_recommendation": round3_result["recommendation"]
        }
        
        logger.info(f"Debate completed. Final recommendation: {result['final_recommendation']}")
        return result
    
    def _proponent_round_1(
        self,
        sentiment_label: str,
        market_index: float,
        supporting_evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """第一轮：正方阐述观点"""
        prompt = self._build_proponent_prompt_1(
            sentiment_label, 
            market_index, 
            supporting_evidence
        )
        
        # 调用智谱API
        model_config = self.config.models.get("zhipu")
        if not model_config:
            raise ValueError("Zhipu model configuration not found")
        
        raw_output = self._call_model(model_config, prompt)
        parsed = self._parse_proponent_output(raw_output)
        parsed["raw_output"] = raw_output
        
        logger.info(f"Round 1 (Proponent) completed: stance={parsed.get('stance')}")
        return parsed
    
    def _opponent_challenge(
        self,
        proponent_stance: str,
        key_points: List[str]
    ) -> Dict[str, Any]:
        """第二轮：反方挑战"""
        prompt = self._build_opponent_prompt(proponent_stance, key_points)
        
        # 调用MiniMax API
        model_config = self.config.models.get("minimax")
        if not model_config:
            raise ValueError("MiniMax model configuration not found")
        
        raw_output = self._call_model(model_config, prompt)
        parsed = self._parse_opponent_output(raw_output)
        parsed["raw_output"] = raw_output
        
        logger.info(f"Round 2 (Opponent) completed: {parsed.get('high_risk_count')} high risks")
        return parsed
    
    def _proponent_response(
        self,
        proponent_stance: str,
        proponent_confidence: float,
        opponent_challenges: List[str]
    ) -> Dict[str, Any]:
        """第三轮：正方回应"""
        prompt = self._build_proponent_response_prompt(
            proponent_stance,
            proponent_confidence,
            opponent_challenges
        )
        
        # 调用智谱API
        model_config = self.config.models.get("zhipu")
        if not model_config:
            raise ValueError("Zhipu model configuration not found")
        
        raw_output = self._call_model(model_config, prompt)
        parsed = self._parse_proponent_response_output(raw_output)
        parsed["raw_output"] = raw_output
        
        logger.info(f"Round 3 (Response) completed: adjusted_confidence={parsed.get('adjusted_confidence')}")
        return parsed
    
    def _call_model(self, model_config, prompt: str) -> str:
        """调用模型API"""
        try:
            headers = {
                "Authorization": f"Bearer {model_config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_config.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的加密货币市场分析师。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 1000
            }
            
            base_url = model_config.base_url or self._get_default_base_url(model_config)
            
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error calling model API: {e}")
            raise
    
    def _get_default_base_url(self, model_config):
        """获取默认API基础URL"""
        # 简单判断模型名称中包含的关键字
        model = model_config.model.lower()
        if "glm" in model or "zhipu" in model:
            return "https://open.bigmodel.cn/api/paas/v4"
        elif "minimax" in model:
            return "https://api.minimax.chat/v1"
        else:
            return "https://api.openai.com/v1"
    
    def _build_proponent_prompt_1(
        self,
        sentiment_label: str,
        market_index: float,
        supporting_evidence: List[Dict[str, Any]]
    ) -> str:
        """构建正方第一轮Prompt"""
        evidence_text = "\n".join([
            f"- {e.get('reasoning', 'No reasoning')} (分数: {e.get('score', 'N/A')})"
            for e in supporting_evidence[:5]  # 最多取5条
        ])
        
        return self.PROPONENT_PROMPT_1.format(
            sentiment_label=sentiment_label,
            market_index=market_index,
            supporting_evidence=evidence_text if evidence_text else "暂无具体证据"
        )
    
    def _build_opponent_prompt(
        self,
        proponent_stance: str,
        key_points: List[str]
    ) -> str:
        """构建反方Prompt"""
        points_text = "\n".join([f"{i+1}. {p}" for i, p in enumerate(key_points)])
        
        return self.OPPONENT_PROMPT.format(
            proponent_stance=proponent_stance,
            key_points=points_text
        )
    
    def _build_proponent_response_prompt(
        self,
        proponent_stance: str,
        proponent_confidence: float,
        opponent_challenges: List[str]
    ) -> str:
        """构建正方回应Prompt"""
        challenges_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(opponent_challenges)])
        
        return self.PROPONENT_RESPONSE_PROMPT.format(
            proponent_stance=proponent_stance,
            proponent_confidence=proponent_confidence,
            opponent_challenges=challenges_text
        )
    
    def _parse_proponent_output(self, output: str) -> Dict[str, Any]:
        """解析正方输出"""
        result = {"stance": "neutral", "confidence": 0.5, "key_points": [], "raw_output": output}
        
        try:
            stance_match = re.search(r'立场[:：]\s*(\w+)', output, re.IGNORECASE)
            confidence_match = re.search(r'置信度[:：]\s*([0-9.]+)', output)
            
            if stance_match:
                result["stance"] = stance_match.group(1).lower()
            if confidence_match:
                result["confidence"] = float(confidence_match.group(1))
            
            # 提取关键论点
            key_points = []
            for line in output.split('\n'):
                if re.match(r'^\d+\.', line.strip()):
                    point = re.sub(r'^\d+\.\s*', '', line.strip())
                    key_points.append(point)
            result["key_points"] = key_points[:5]  # 最多5个论点
            
        except Exception as e:
            logger.error(f"Error parsing proponent output: {e}")
        
        return result
    
    def _parse_opponent_output(self, output: str) -> Dict[str, Any]:
        """解析反方输出"""
        result = {
            "challenges": [],
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "raw_output": output
        }
        
        try:
            high_risk_match = re.search(r'高风险因子[:数]*[:：]\s*(\d+)', output)
            medium_risk_match = re.search(r'中风险因子[:数]*[:：]\s*(\d+)', output)
            
            if high_risk_match:
                result["high_risk_count"] = int(high_risk_match.group(1))
            if medium_risk_match:
                result["medium_risk_count"] = int(medium_risk_match.group(1))
            
            # 提取挑战点
            challenges = []
            in_challenge_section = False
            for line in output.split('\n'):
                line = line.strip()
                # 检测挑战点区域
                if '挑战' in line and ':' in line:
                    in_challenge_section = True
                    continue
                # 匹配编号列表项
                if in_challenge_section and re.match(r'^\d+\.', line):
                    challenge = re.sub(r'^\d+\.\s*', '', line)
                    if challenge and len(challenge) > 3:
                        challenges.append(challenge)
                # 遇到空行或其他区域结束
                elif in_challenge_section and line and not re.match(r'^\d+\.', line):
                    if '风险' in line or '评估' in line:
                        break
            
            result["challenges"] = challenges[:5]
            
        except Exception as e:
            logger.error(f"Error parsing opponent output: {e}")
        
        return result
    
    def _parse_proponent_response_output(self, output: str) -> Dict[str, Any]:
        """解析正方回应输出"""
        result = {
            "admitted_points": [],
            "refuted_points": [],
            "adjusted_stance": "neutral",
            "adjusted_confidence": 0.5,
            "recommendation": {"action": "hold", "risk_level": "medium"},
            "raw_output": output
        }
        
        try:
            stance_match = re.search(r'调整后立场[:：]\s*(\w+)', output, re.IGNORECASE)
            confidence_match = re.search(r'调整后置信度[:：]\s*([0-9.]+)', output)
            action_match = re.search(r'行动[:：]\s*(\w+)', output, re.IGNORECASE)
            risk_match = re.search(r'风险等级[:：]\s*(\w+)', output, re.IGNORECASE)
            
            if stance_match:
                result["adjusted_stance"] = stance_match.group(1).lower()
            if confidence_match:
                result["adjusted_confidence"] = float(confidence_match.group(1))
            if action_match:
                result["recommendation"]["action"] = action_match.group(1).lower()
            if risk_match:
                result["recommendation"]["risk_level"] = risk_match.group(1).lower()
            
            # 提取承认和反驳的点
            admitted = []
            refuted = []
            current_section = None
            
            for line in output.split('\n'):
                if '承认' in line:
                    current_section = 'admitted'
                elif '反驳' in line:
                    current_section = 'refuted'
                elif re.match(r'^\d+\.', line.strip()) and current_section:
                    point = re.sub(r'^\d+\.\s*', '', line.strip())
                    if current_section == 'admitted':
                        admitted.append(point)
                    else:
                        refuted.append(point)
            
            result["admitted_points"] = admitted
            result["refuted_points"] = refuted
            
        except Exception as e:
            logger.error(f"Error parsing proponent response: {e}")
        
        return result
