"""数据模型模块"""
from src.models.candidate import Candidate, WorkExperience, Skill
from src.models.job import JobDescription
from src.models.match import MatchResult

__all__ = [
    "Candidate",
    "WorkExperience",
    "Skill",
    "JobDescription",
    "MatchResult",
]
