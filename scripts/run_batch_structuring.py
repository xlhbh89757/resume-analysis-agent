"""离线简历结构化批处理投递脚本。"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.database import SessionLocal
from src.models.resume_batch import ResumeStructBatch, ResumeStructTask
from src.services.resume_source_client import ResumeSourceClient
from src.tasks.analysis import dispatch_batch_task


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按来源范围批量投递简历结构化任务")
    parser.add_argument("--start-employee", required=True, help="起始来源ID")
    parser.add_argument("--end-employee", required=True, help="结束来源ID")
    parser.add_argument("--source-type", required=True, choices=["employee", "submit_candidate"], help="来源类型")
    parser.add_argument("--batch-size", type=int, default=100, help="每批投递数量")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写库不投递")
    return parser.parse_args(argv)


async def _fetch_pending_items(client: ResumeSourceClient, source_type: str, limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        response = await client.list_pending_resumes(source_type=source_type, cursor=cursor, limit=limit)
        items.extend(response.get("items", []))
        cursor = response.get("next_cursor")
        if not cursor:
            return items


def _select_items(items: list[dict[str, Any]], start_source_id: str, end_source_id: str, batch_size: int) -> list[dict[str, Any]]:
    selected = [
        {
            "source_type": item["source_type"],
            "source_id": item["source_id"],
            "filekey": item.get("filekey"),
            "resume_created_time": item["resume_created_time"],
        }
        for item in items
        if start_source_id <= item["source_id"] <= end_source_id
    ]
    return selected[:batch_size]


def _enqueue_dispatch(batch_id: str, items: list[dict[str, Any]]) -> None:
    if hasattr(dispatch_batch_task, "delay"):
        dispatch_batch_task.delay(batch_id, items)
        return
    dispatch_batch_task.run(batch_id=batch_id, items=items)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    source_client = ResumeSourceClient()
    pending_items = asyncio.run(_fetch_pending_items(source_client, args.source_type, args.batch_size))
    selected_items = _select_items(
        pending_items,
        start_source_id=args.start_employee,
        end_source_id=args.end_employee,
        batch_size=args.batch_size,
    )

    result = {"dry_run": args.dry_run, "enqueued_count": len(selected_items), "items": selected_items}
    if args.dry_run or not selected_items:
        return result

    db = SessionLocal()
    try:
        batch = ResumeStructBatch(
            batch_id=f"batch-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            total_count=len(selected_items),
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(batch)
        db.flush()

        queued_items: list[dict[str, Any]] = []
        for item in selected_items:
            idempotency_key = f"{item['source_type']}:{item['source_id']}:{item['resume_created_time']}"
            existing = db.query(ResumeStructTask).filter(ResumeStructTask.idempotency_key == idempotency_key).first()
            if existing:
                continue

            db.add(
                ResumeStructTask(
                    batch_id=batch.id,
                    source_type=item["source_type"],
                    source_id=item["source_id"],
                    resume_created_time=item["resume_created_time"],
                    idempotency_key=idempotency_key,
                    status="queued",
                )
            )
            queued_items.append(item)

        batch.total_count = len(queued_items)
        db.commit()

        if queued_items:
            _enqueue_dispatch(batch.batch_id, queued_items)

        result["enqueued_count"] = len(queued_items)
        result["batch_id"] = batch.batch_id
        return result
    finally:
        db.close()


if __name__ == "__main__":
    print(main())
