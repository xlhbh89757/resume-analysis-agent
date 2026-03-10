"""本地调试 OBS 预签名 URL。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import settings
from src.obs.OBSSigner import OBSSigner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据 filekey 生成 OBS 临时访问链接")
    parser.add_argument(
        "--filekey",
        default="/employee/2023-08-09/4ee3d06f-2789-4612-9506-b5591593e260.pdf",
        help="对象 filekey，例如 /employee/2025/01/demo.pdf",
    )
    parser.add_argument("--expire-seconds", type=int, default=settings.obs_url_expire_seconds)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    signer = OBSSigner(
        access_key=settings.obs_access_key or "",
        secret_key=settings.obs_secret_key or "",
        bucket=settings.obs_bucket or "",
        host=settings.obs_host or "",
    )
    print(
        signer.generate_presigned_url(
            object_key=args.filekey,
            expire_seconds=args.expire_seconds,
        )
    )


if __name__ == "__main__":
    main()
