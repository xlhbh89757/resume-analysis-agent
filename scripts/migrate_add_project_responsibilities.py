"""Add responsibilities column to project_experiences if missing."""

import sys
from pathlib import Path

from sqlalchemy import text

# Add project root to import path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import engine  # noqa: E402


def main() -> None:
    db_name = engine.url.database
    if not db_name:
        print("Failed: database name not found in DATABASE_URL")
        sys.exit(1)

    check_sql = text(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = :schema
          AND TABLE_NAME = 'project_experiences'
          AND COLUMN_NAME = 'responsibilities'
        """
    )

    with engine.begin() as conn:
        exists = conn.execute(check_sql, {"schema": db_name}).scalar() or 0
        if exists:
            print("Column already exists: project_experiences.responsibilities")
            return

        conn.execute(
            text("ALTER TABLE project_experiences ADD COLUMN responsibilities TEXT NULL")
        )
        print("Column added: project_experiences.responsibilities")


if __name__ == "__main__":
    main()

