"""LLM 分析服务。"""

import json
import logging
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.llm.manager import LLMProviderManager
from src.services.budget_guard import BudgetExceededError, BudgetGuard
from src.utils.prompts import (
    JD_EXTRACTION_PROMPT,
    JD_MATCH_PROMPT,
    RESUME_EXTRACTION_PROMPT,
    RISK_ANALYSIS_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMAnalysisService:
    """负责调用 LLM 执行简历提取和匹配分析。"""

    def __init__(
        self,
        provider_name: Optional[str] = None,
        budget_guard: Optional[BudgetGuard] = None,
    ):
        self.provider_name = provider_name
        self.budget_guard = budget_guard or BudgetGuard()

    async def extract_jd_info(self, jd_text: str) -> Dict[str, Any]:
        prompt = JD_EXTRACTION_PROMPT.format(jd_text=jd_text)

        try:
            self.budget_guard.assert_can_consume(self._estimate_cost(prompt))
            result = await LLMProviderManager.generate_json_with_fallback(
                prompt,
                primary_provider=self.provider_name,
                max_tokens=4096,
            )
            self.budget_guard.record_usage(self._estimate_cost(prompt, result))
            return result
        except BudgetExceededError:
            raise
        except Exception as e:
            logger.error(f"Failed to extract JD info: {e}")
            return {}

    async def extract_resume_info(self, resume_text: str) -> Dict[str, Any]:
        prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)

        try:
            estimated_cost = self._estimate_cost(prompt)
            self.budget_guard.assert_can_consume(estimated_cost)
            result = await LLMProviderManager.generate_json_with_fallback(
                prompt,
                primary_provider=self.provider_name,
            )
            actual_cost = self._estimate_cost(prompt, result)
            self.budget_guard.record_usage(actual_cost)

            result = self._validate_extraction_result(result)
            result["_llm_meta"] = {
                "provider": self.provider_name or settings.llm_provider,
                "estimated_cost": actual_cost,
                "budget_blocked": False,
            }
            logger.info(f"Extracted resume info: name={result.get('name')}")
            return result
        except BudgetExceededError as e:
            logger.warning(f"Resume extraction blocked by budget guard: {e.message}")
            result = self._fallback_extraction(resume_text)
            result["_llm_meta"] = {
                "provider": self.provider_name or settings.llm_provider,
                "error_code": e.error_code,
                "budget_blocked": True,
            }
            return result
        except Exception as e:
            logger.error(f"Failed to extract resume info: {e}")
            result = self._fallback_extraction(resume_text)
            result["_llm_meta"] = {
                "provider": self.provider_name or settings.llm_provider,
                "budget_blocked": False,
            }
            return result

    async def analyze_jd_match(
        self,
        candidate_info: Dict[str, Any],
        job_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = JD_MATCH_PROMPT.format(
            candidate_info=json.dumps(candidate_info, ensure_ascii=False, indent=2),
            job_info=json.dumps(job_info, ensure_ascii=False, indent=2),
        )

        try:
            self.budget_guard.assert_can_consume(self._estimate_cost(prompt))
            result = await LLMProviderManager.generate_json_with_fallback(
                prompt,
                primary_provider=self.provider_name,
            )
            self.budget_guard.record_usage(self._estimate_cost(prompt, result))
            result = self._normalize_scores(result)
            logger.info(
                f"JD match analysis completed, overall_score={result.get('overall_score')}"
            )
            return result
        except BudgetExceededError:
            raise
        except Exception as e:
            logger.error(f"Failed to analyze JD match: {e}")
            return self._fallback_match_result()

    async def analyze_risks(
        self,
        candidate_info: Dict[str, Any],
        work_experiences: List[Dict[str, Any]],
    ) -> List[str]:
        prompt = RISK_ANALYSIS_PROMPT.format(
            candidate_info=json.dumps(candidate_info, ensure_ascii=False, indent=2),
            work_experiences=json.dumps(work_experiences, ensure_ascii=False, indent=2),
        )

        try:
            self.budget_guard.assert_can_consume(self._estimate_cost(prompt))
            result = await LLMProviderManager.generate_json_with_fallback(
                prompt,
                primary_provider=self.provider_name,
            )
            self.budget_guard.record_usage(self._estimate_cost(prompt, result))
            return result.get("risk_flags", [])
        except BudgetExceededError:
            raise
        except Exception as e:
            logger.error(f"Failed to analyze risks: {e}")
            return []

    def _estimate_cost(self, prompt: str, result: Optional[Dict[str, Any]] = None) -> float:
        """按字符长度粗略估算一次 LLM 调用成本。"""
        prompt_tokens = max(len(prompt) // 4, 1)
        response_tokens = max(len(json.dumps(result, ensure_ascii=False)) // 4, 1) if result else 256
        total_tokens = prompt_tokens + response_tokens
        return round(total_tokens / 1_000_000 * 2.0, 6)

    def _validate_extraction_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        default_fields = {
            "name": None,
            "email": None,
            "phone": None,
            "education_level": None,
            "years_of_experience": None,
            "current_position": None,
            "summary": None,
            "work_experiences": [],
            "project_experiences": [],
            "skills": [],
        }

        for key, default_value in default_fields.items():
            if key not in result:
                result[key] = default_value

        return result

    def _normalize_scores(self, result: Dict[str, Any]) -> Dict[str, Any]:
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
        import re

        result = {
            "name": None,
            "email": None,
            "phone": None,
            "education_level": None,
            "years_of_experience": None,
            "current_position": None,
            "summary": None,
            "work_experiences": [],
            "project_experiences": [],
            "skills": [],
        }

        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", resume_text)
        if email_match:
            result["email"] = email_match.group()

        phone_match = re.search(r"1[3-9]\d{9}", resume_text)
        if phone_match:
            result["phone"] = phone_match.group()

        return result

    def _fallback_match_result(self) -> Dict[str, Any]:
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