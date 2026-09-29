"""独立建库脚本：建表 + FTS5 + 管理员种子（与后端启动时自动执行一致，可手动运行）。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.init import init_db  # noqa: E402


async def main() -> None:
    await init_db()
    print("数据库初始化完成：ragkb.db 已就绪（admin / 123456）")


if __name__ == "__main__":
    asyncio.run(main())
