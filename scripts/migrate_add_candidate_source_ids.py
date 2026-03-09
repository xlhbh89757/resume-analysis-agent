"""为 candidates 和批处理治理表补充多来源标识字段。"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import engine  # noqa: E402


def _has_table(table_name: str) -> bool:
    return inspect(engine).has_table(table_name)


def _get_columns(table_name: str) -> set[str]:
    inspector = inspect(engine)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _get_indexes(table_name: str) -> set[str]:
    inspector = inspect(engine)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None:
    if not _has_table(table_name):
        return
    if column_name in _get_columns(table_name):
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))


def _create_index_if_missing(table_name: str, index_name: str, ddl: str) -> None:
    if not _has_table(table_name):
        return
    if index_name in _get_indexes(table_name):
        return
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if not _has_table(table_name):
        return
    if index_name not in _get_indexes(table_name):
        return
    with engine.begin() as conn:
        conn.execute(text(f"DROP INDEX {index_name} ON {table_name}"))


def _rename_employee_id_to_source_id_if_needed() -> None:
    if not _has_table("resume_struct_tasks") or not _has_table("resume_struct_deadletters"):
        return

    task_columns = _get_columns("resume_struct_tasks")
    dead_columns = _get_columns("resume_struct_deadletters")

    with engine.begin() as conn:
        if "employee_id" in task_columns and "source_id" not in task_columns:
            conn.execute(
                text(
                    "ALTER TABLE resume_struct_tasks "
                    "CHANGE COLUMN employee_id source_id VARCHAR(100) NOT NULL COMMENT '来源业务ID'"
                )
            )
        if "employee_id" in dead_columns and "source_id" not in dead_columns:
            conn.execute(
                text(
                    "ALTER TABLE resume_struct_deadletters "
                    "CHANGE COLUMN employee_id source_id VARCHAR(100) NOT NULL COMMENT '来源业务ID'"
                )
            )


def _backfill_source_type_defaults() -> None:
    if not _has_table("resume_struct_tasks") or not _has_table("resume_struct_deadletters"):
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE resume_struct_tasks "
                "SET source_type = 'employee' "
                "WHERE source_type IS NULL OR source_type = ''"
            )
        )
        conn.execute(
            text(
                "UPDATE resume_struct_deadletters "
                "SET source_type = 'employee' "
                "WHERE source_type IS NULL OR source_type = ''"
            )
        )


def _backfill_legacy_idempotency_keys() -> None:
    if not _has_table("resume_struct_tasks"):
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE resume_struct_tasks "
                "SET idempotency_key = CONCAT('employee:', source_id, ':', resume_created_time) "
                "WHERE source_type = 'employee' "
                "AND idempotency_key = CONCAT(source_id, ':', resume_created_time)"
            )
        )


def main() -> None:
    _add_column_if_missing(
        "candidates",
        "employee_id",
        "employee_id VARCHAR(100) NULL COMMENT '在职员工工号'",
    )
    _add_column_if_missing(
        "candidates",
        "entrant_id",
        "entrant_id VARCHAR(100) NULL COMMENT '待入职人员标识'",
    )
    _add_column_if_missing(
        "candidates",
        "submit_candidate_id",
        "submit_candidate_id VARCHAR(100) NULL COMMENT '报备候选人标识'",
    )
    _create_index_if_missing(
        "candidates",
        "idx_candidates_employee_id",
        "CREATE INDEX idx_candidates_employee_id ON candidates(employee_id)",
    )
    _create_index_if_missing(
        "candidates",
        "idx_candidates_entrant_id",
        "CREATE INDEX idx_candidates_entrant_id ON candidates(entrant_id)",
    )
    _create_index_if_missing(
        "candidates",
        "idx_candidates_submit_candidate_id",
        "CREATE INDEX idx_candidates_submit_candidate_id ON candidates(submit_candidate_id)",
    )
    _create_index_if_missing(
        "candidates",
        "ix_candidates_name",
        "CREATE INDEX ix_candidates_name ON candidates(name)",
    )

    _drop_index_if_exists("candidates", "ix_candidates_email")

    _rename_employee_id_to_source_id_if_needed()
    _add_column_if_missing(
        "resume_struct_tasks",
        "source_type",
        "source_type VARCHAR(50) NOT NULL DEFAULT 'employee' COMMENT '来源类型'",
    )
    _add_column_if_missing(
        "resume_struct_deadletters",
        "source_type",
        "source_type VARCHAR(50) NOT NULL DEFAULT 'employee' COMMENT '来源类型'",
    )
    _backfill_source_type_defaults()
    _backfill_legacy_idempotency_keys()

    print("Candidate source identifiers migration completed.")


if __name__ == "__main__":
    main()
