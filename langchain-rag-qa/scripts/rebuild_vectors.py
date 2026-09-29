"""切换嵌入模型（维度变化）后的重建脚本：把全部文档重置为 pending。

非破坏性：原始文件保留在 storage/uploads，分块与向量由摄取 worker 幂等重建；
向量集合名带维度后缀（kb_{id}_d{dim}），旧维度集合保留在磁盘不受影响。

用法（先停后端）：
    cd backend && .venv/Scripts/python.exe ../scripts/rebuild_vectors.py
重启后端后，摄取 worker 的崩溃恢复机制会自动重新入队并完成嵌入。
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import get_settings

s = get_settings()
con = sqlite3.connect(str(s.sqlite_path))
try:
    n = con.execute(
        "UPDATE documents SET status='pending', error_message=NULL, chunk_count=0"
    ).rowcount
    con.commit()
    print(f"已将 {n} 个文档重置为 pending，重启后端后自动重建分块与向量")
finally:
    con.close()
