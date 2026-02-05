"""API Schemas 模块"""
from src.api.schemas.resume import (
    WorkExperienceSchema,
    SkillSchema,
    ResumeUploadResponse,
    CandidateResponse,
    CandidateListResponse,
    CandidateSearchRequest,
    CandidateSearchResponse,
    SearchResultItem,
)
from src.api.schemas.match import (
    MatchRequest,
    MatchResponse,
    JobCreateRequest,
    JobResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    BatchStatusResponse,
)

__all__ = [
    # Resume
    "WorkExperienceSchema",
    "SkillSchema",
    "ResumeUploadResponse",
    "CandidateResponse",
    "CandidateListResponse",
    "CandidateSearchRequest",
    "CandidateSearchResponse",
    "SearchResultItem",
    # Match
    "MatchRequest",
    "MatchResponse",
    "JobCreateRequest",
    "JobResponse",
    "BatchAnalyzeRequest",
    "BatchAnalyzeResponse",
    "BatchStatusResponse",
]
