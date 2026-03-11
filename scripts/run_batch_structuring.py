from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.database import SessionLocal
from src.models.resume_batch import ResumeStructBatch, ResumeStructTask
from src.services.resume_source_client import ResumeSourceClient
from src.tasks.analysis import dispatch_batch_task
from src.utils.time_utils import local_now


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按来源范围批量投递简历结构化任务")
    parser.add_argument("--start-employee", required=True, help="起始来源ID")
    parser.add_argument("--end-employee", required=True, help="结束来源ID")
    parser.add_argument("--source-type", required=True, choices=["employee", "submit_candidate"], help="来源类型")
    parser.add_argument("--cursor", default=None, help="待结构化清单游标")
    parser.add_argument("--batch-size", type=int, default=100, help="每批投递数量")
    parser.add_argument("--total-limit", type=int, default=None, help="自动连续投递的总目标数量")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写库不投递")
    return parser.parse_args(argv)


async def _fetch_selected_items(
    client: ResumeSourceClient,
    source_type: str,
    start_source_id: str,
    end_source_id: str,
    batch_size: int,
    cursor: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    selected: list[dict[str, Any]] = []
    next_cursor = cursor

    while len(selected) < batch_size:
        response = await client.list_pending_resumes(
            source_type=source_type,
            cursor=next_cursor,
            limit=batch_size,
        )
        items = response.get("items", [])
        next_cursor = response.get("next_cursor")

        for item in items:
            source_id = item["source_id"]
            if start_source_id <= source_id <= end_source_id:
                selected.append(
                    {
                        "source_type": item["source_type"],
                        "source_id": source_id,
                        "filekey": item.get("filekey"),
                        "resume_created_time": item["resume_created_time"],
                    }
                )
                if len(selected) >= batch_size:
                    break

        if not next_cursor:
            break

    return selected[:batch_size], next_cursor


def _enqueue_dispatch(batch_id: str, items: list[dict[str, Any]]) -> None:
    if hasattr(dispatch_batch_task, "delay"):
        dispatch_batch_task.delay(batch_id, items)
        return
    dispatch_batch_task.run(batch_id=batch_id, items=items)


def _filter_new_items(db, selected_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queued_items: list[dict[str, Any]] = []
    for item in selected_items:
        idempotency_key = f"{item['source_type']}:{item['source_id']}:{item['resume_created_time']}"
        existing = db.query(ResumeStructTask).filter(ResumeStructTask.idempotency_key == idempotency_key).first()
        if existing:
            continue
        queued_items.append(item)
    return queued_items


def _create_batch_and_tasks(db, queued_items: list[dict[str, Any]]) -> str | None:
    if not queued_items:
        return None

    now = local_now()
    batch = ResumeStructBatch(
        batch_id=f"batch-{now.strftime('%Y%m%d%H%M%S%f')}",
        total_count=len(queued_items),
        status="running",
        started_at=now,
    )
    db.add(batch)
    db.flush()

    for item in queued_items:
        idempotency_key = f"{item['source_type']}:{item['source_id']}:{item['resume_created_time']}"
        db.add(
            ResumeStructTask(
                batch_id=batch.id,
                source_type=item["source_type"],
                source_id=item["source_id"],
                filekey=item.get("filekey"),
                resume_created_time=item["resume_created_time"],
                idempotency_key=idempotency_key,
                status="queued",
            )
        )

    db.commit()
    return batch.batch_id


def _run_single_batch(
    args: argparse.Namespace,
    source_client: ResumeSourceClient,
    cursor: str | None,
) -> dict[str, Any]:
    selected_items, next_cursor = asyncio.run(
        _fetch_selected_items(
            client=source_client,
            source_type=args.source_type,
            start_source_id=args.start_employee,
            end_source_id=args.end_employee,
            batch_size=args.batch_size,
            cursor=cursor,
        )
    )

    result = {
        "dry_run": args.dry_run,
        "enqueued_count": len(selected_items),
        "items": selected_items,
        "next_cursor": next_cursor,
        "batch_id": None,
    }
    if args.dry_run or not selected_items:
        return result

    db = SessionLocal()
    try:
        queued_items = _filter_new_items(db, selected_items)
        result["enqueued_count"] = len(queued_items)
        result["items"] = queued_items

        if not queued_items:
            return result

        batch_id = _create_batch_and_tasks(db, queued_items)
        if batch_id:
            _enqueue_dispatch(batch_id, queued_items)

        result["batch_id"] = batch_id
        return result
    finally:
        db.close()


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    source_client = ResumeSourceClient()

    if args.total_limit is None:
        return _run_single_batch(args, source_client, args.cursor)

    total_enqueued = 0
    cursor = args.cursor
    batches: list[dict[str, Any]] = []
    requested_batches = 0

    while total_enqueued < args.total_limit:
        requested_batches += 1
        remaining = args.total_limit - total_enqueued
        effective_batch_size = min(args.batch_size, remaining)
        batch_args = argparse.Namespace(**vars(args))
        batch_args.batch_size = effective_batch_size

        batch_result = _run_single_batch(batch_args, source_client, cursor)
        batches.append(batch_result)
        total_enqueued += batch_result["enqueued_count"]
        cursor = batch_result.get("next_cursor")

        if not cursor:
            break

    return {
        "dry_run": args.dry_run,
        "batch_size": args.batch_size,
        "total_limit": args.total_limit,
        "requested_batches": requested_batches,
        "enqueued_count": total_enqueued,
        "batches": batches,
        "next_cursor": cursor,
    }


if __name__ == "__main__":
    print(main())
