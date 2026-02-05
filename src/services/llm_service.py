"""LLM 分析服务 - 简历信息提取和 JD 匹配"""
import json
import logging
from typing import Dict, Any, Optional, List

from src.llm.manager import LLMProviderManager
from src.utils.prompts import (
    RESUME_EXTRACTION_PROMPT,
    JD_EXTRACTION_PROMPT,
    JD_MATCH_PROMPT,
    RISK_ANALYSIS_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMAnalysisService:
    """LLM 分析服务
    
    负责调用 LLM 进行简历信息提取、JD 匹配等分析任务。
    """
    
    def __init__(self, provider_name: Optional[str] = None):
        """
        Args:
            provider_name: 指定使用的 LLM Provider，不指定则使用默认
        """
        self.provider_name = provider_name
    
    async def extract_jd_info(self, jd_text: str) -> Dict[str, Any]:
        """从 JD 文本中提取结构化信息"""
        prompt = JD_EXTRACTION_PROMPT.format(jd_text=jd_text)
        
        try:
            result = await LLMProviderManager.generate_json_with_fallback(
                prompt,
                primary_provider=self.provider_name,
            )
            return result
        except Exception as e:
            logger.error(f"Failed to extract JD info: {e}")
            return {}

    async def extract_resume_info(self, resume_text: str) -> Dict[str, Any]:
        """从简历中提取结构化信息
        
        Args:
            resume_text: 简历原始文本
            
        Returns:
            结构化的简历信息字典
        """
        prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
        
        try:
            result = await LLMProviderManager.generate_json_with_fallback(
                prompt,
                primary_provider=self.provider_name,
            )
            
            # 验证并补充必要字段
            result = self._validate_extraction_result(result)
            
            logger.info(f"Extracted resume info: name={result.get('name')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract resume info: {e}")
            # 返回降级结果
            return self._fallback_extraction(resume_text)
    
    async def analyze_jd_match(
        self,
        candidate_info: Dict[str, Any],
        job_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """分析候选人与 JD 的匹配度
        
        Args:
            candidate_info: 候选人结构化信息
            job_info: JD 信息
            
        Returns:
            匹配分析结果
        """
        prompt = JD_MATCH_PROMPT.format(
            candidate_info=json.dumps(candidate_info, ensure_ascii=False, indent=2),
            job_info=json.dumps(job_info, ensure_ascii=False, indent=2),
        )
        
        try:
            result = await LLMProviderManager.generate_json_with_fallback(
                prompt,
                primary_provider=self.provider_name,
            )
            
            # 确保评分在合理范围内
            result = self._normalize_scores(result)
            
            logger.info(f"JD match analysis completed, overall_score={result.get('overall_score')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze JD match: {e}")
            return self._fallback_match_result()
    
    async def analyze_risks(
        self,
        candidate_info: Dict[str, Any],
        work_experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """分析候选人潜在风险
        
        Args:
            candidate_info: 候选人信息
            work_experiences: 工作经历列表
            
        Returns:
            风险标识列表
        """
        prompt = RISK_ANALYSIS_PROMPT.format(
            candidate_info=json.dumps(candidate_info, ensure_ascii=False, indent=2),
            work_experiences=json.dumps(work_experiences, ensure_ascii=False, indent=2),
        )
        
        try:
            result = await LLMProviderManager.generate_json_with_fallback(
                prompt,
                primary_provider=self.provider_name,
            )
            
            return result.get("risk_flags", [])
            
        except Exception as e:
            logger.error(f"Failed to analyze risks: {e}")
            return []
    
    def _validate_extraction_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证提取结果并补充缺失字段"""
        default_fields = {
            "name": None,
            "email": None,
            "phone": None,
            "education_level": None,
            "years_of_experience": None,
            "current_position": None,
            "work_experiences": [],
            "skills": [],
        }
        
        for key, default_value in default_fields.items():
            if key not in result:
                result[key] = default_value
        
        return result
    
    def _normalize_scores(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """规范化评分"""
        score_fields = [
            "overall_score",
            "skill_match_score",
            "experience_match_score",
            "education_match_score",
        ]
        
        for field in score_fields:
            if field in result:
                score = result[field]
                if isinstance(score, (int, float)):
                    result[field] = max(0, min(100, score))
        
        return result
    
    def _fallback_extraction(self, resume_text: str) -> Dict[str, Any]:
        """降级提取：使用简单规则提取"""
        import re
        
        result = {
            "name": None,
            "email": None,
            "phone": None,
            "education_level": None,
            "years_of_experience": None,
            "current_position": None,
            "work_experiences": [],
            "skills": [],
        }
        
        # 提取邮箱
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
        if email_match:
            result["email"] = email_match.group()
        
        # 提取手机号
        phone_match = re.search(r'1[3-9]\d{9}', resume_text)
        if phone_match:
            result["phone"] = phone_match.group()
        
        return result
    
    def _fallback_match_result(self) -> Dict[str, Any]:
        """降级匹配结果"""
        return {
            "overall_score": 0,
            "skill_match_score": 0,
            "experience_match_score": 0,
            "education_match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "risk_flags": [],
            "summary": "无法完成分析",
            "recommendation": "请手动审核",
            "interview_questions": [],
        }
