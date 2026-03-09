"""离线简历结构化任务链辅助逻辑。"""

from __future__ import annotations

from typing import Any

PIPELINE_TASK_NAMES = {
    "dispatch": "resume.pipeline.dispatch_batch",
    "extract": "resume.pipeline.extract_resume",
    "llm": "resume.pipeline.llm_extract",
    "persist": "resume.pipeline.persist_result",
    "deadletter": "resume.pipeline.deadletter",
}

PIPELINE_QUEUE_ROUTES = {
    PIPELINE_TASK_NAMES["dispatch"]: {"queue": "dispatch_queue"},
    PIPELINE_TASK_NAMES["extract"]: {"queue": "extract_queue"},
    PIPELINE_TASK_NAMES["llm"]: {"queue": "llm_queue"},
    PIPELINE_TASK_NAMES["persist"]: {"queue": "persist_queue"},
    PIPELINE_TASK_NAMES["deadletter"]: {"queue": "dead_letter_queue"},
}


def build_extract_payload(
    employee_id: str,
    resume_created_time: str,
    temp_url: str | None = None,
) -> dict[str, Any]:
    """构造抽取阶段任务载荷。"""
    payload = {
        "employee_id": employee_id,
        "resume_created_time": resume_created_time,
    }
    _ = temp_url
    return payload


def build_extract_service_request(
    extract_payload: dict[str, Any],
    temp_url: str | None = None,
) -> dict[str, Any]:
    """构造共享 URL 服务的抽取请求上下文。"""
    if temp_url:
        return {
            "mode": "url",
            "resume_url": temp_url,
            "employee_id": extract_payload["employee_id"],
            "resume_created_time": extract_payload["resume_created_time"],
        }

    return {
        "mode": "employee",
        "employee_id": extract_payload["employee_id"],
        "resume_created_time": extract_payload["resume_created_time"],
    }


def build_dispatch_payload(batch_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """构造批次分发摘要，供调度层记录本轮投递范围。"""
    return {
        "batch_id": batch_id,
        "total_count": len(items),
        "items": [
            build_extract_payload(
                employee_id=item["employee_id"],
                resume_created_time=item["resume_created_time"],
            )
            for item in items
        ],
    }


def build_llm_payload(extract_payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    """构造 LLM 抽取阶段输入。"""
    return {
        "employee_id": extract_payload["employee_id"],
        "resume_created_time": extract_payload["resume_created_time"],
        "resume_text": text,
    }


def build_persist_payload(
    llm_payload: dict[str, Any],
    structured_resume: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造幂等落库阶段输入。"""
    llm_meta = structured_resume.get("_llm_meta", {}) if structured_resume else {}
    resume_text = llm_payload.get("resume_text", "")
    fallback_tokens_in = max(len(resume_text) // 4, 1) if resume_text else None
    fallback_tokens_out = (
        max(len(str(structured_resume)) // 4, 1) if structured_resume else None
    )
    return {
        "employee_id": llm_payload["employee_id"],
        "resume_created_time": llm_payload["resume_created_time"],
        "resume_text": resume_text,
        "structured_resume": structured_resume or {},
        # 统一把成本元数据带到落库阶段，便于任务治理表记录预算消耗。
        "llm_tokens_in": llm_meta.get("tokens_in", fallback_tokens_in),
        "llm_tokens_out": llm_meta.get("tokens_out", fallback_tokens_out),
        "llm_cost": llm_meta.get("estimated_cost"),
    }


def build_deadletter_payload(
    payload: dict[str, Any],
    error_code: str,
    error_message: str,
) -> dict[str, Any]:
    """构造死信记录，保留失败上下文用于后续重试。"""
    deadletter_payload = dict(payload)
    deadletter_payload["error_code"] = error_code
    deadletter_payload["error_message"] = error_message
    return deadletter_payload
