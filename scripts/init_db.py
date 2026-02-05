"""数据库初始化脚本"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import init_db, engine
from src.core.config import settings


def main():
    """初始化数据库表"""
    print(f"Initializing database: {settings.database_url}")
    
    try:
        init_db()
        print("Database initialized successfully!")
        print("\nCreated tables:")
        print("  - candidates")
        print("  - work_experiences")
        print("  - skills")
        print("  - job_descriptions")
        print("  - match_results")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
