"""死信任务重试脚本。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.database import SessionLocal
from src.models.resume_batch import ResumeStructDeadletter, ResumeStructTask
from src.tasks.analysis import extract_resume_task


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按来源ID重试死信任务")
    parser.add_argument("--source-id", action="append", dest="source_ids", default=[], help="指定需要重试的来源ID，可重复传入")
    parser.add_argument("--employee-id", action="append", dest="employee_ids", default=[], help="兼容旧参数，等价于 source-id")
    return parser.parse_args(argv)


def _enqueue_extract(source_type: str, source_id: str, resume_created_time: str) -> None:
    if hasattr(extract_resume_task, "delay"):
        extract_resume_task.delay(
            source_type=source_type,
            source_id=source_id,
            resume_created_time=resume_created_time,
        )
        return
    extract_resume_task.run(
        source_type=source_type,
        source_id=source_id,
        resume_created_time=resume_created_time,
    )


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    target_source_ids = list(dict.fromkeys([*args.source_ids, *args.employee_ids]))

    db = SessionLocal()
    try:
        query = (
            db.query(ResumeStructDeadletter, ResumeStructTask)
            .join(ResumeStructTask, ResumeStructDeadletter.task_id == ResumeStructTask.id)
        )
        if target_source_ids:
            query = query.filter(ResumeStructDeadletter.source_id.in_(target_source_ids))

        rows = query.all()
        requeued_count = 0
        for _, task in rows:
            task.status = "queued"
            task.attempt_count = (task.attempt_count or 0) + 1
            task.error_code = None
            task.error_message = None
            task.started_at = None
            task.finished_at = None
            _enqueue_extract(
                source_type=task.source_type,
                source_id=task.source_id,
                resume_created_time=task.resume_created_time,
            )
            requeued_count += 1

        db.commit()
        return {
            "requeued_count": requeued_count,
            "source_ids": target_source_ids,
            "requeued_at": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


if __name__ == "__main__":
    print(main())
