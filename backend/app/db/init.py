"""数据库初始化：建表 + FTS5 全文检索虚表与同步触发器 + 管理员种子数据。幂等，可重复执行。"""
from loguru import logger
from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models import User

# FTS5 外部内容表：content_tokens 为 jieba 空格分词结果，实现中文 BM25 关键词检索
FTS5_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content_tokens,
    content='chunks',
    content_rowid='id',
    tokenize='unicode61'
)
"""

# 同步触发器：chunks 表增删改时自动维护 FTS5 索引
FTS5_TRIGGERS = (
    """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_ai AFTER INSERT ON chunks BEGIN
        INSERT INTO chunks_fts(rowid, content_tokens) VALUES (new.id, new.content_tokens);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_ad AFTER DELETE ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, content_tokens)
        VALUES ('delete', old.id, old.content_tokens);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_au AFTER UPDATE OF content_tokens ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, content_tokens)
        VALUES ('delete', old.id, old.content_tokens);
        INSERT INTO chunks_fts(rowid, content_tokens) VALUES (new.id, new.content_tokens);
    END
    """,
)


async def init_db() -> None:
    """建表 + FTS5 虚表/触发器 + 播种管理员（admin / 123456）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for ddl in (FTS5_DDL, *FTS5_TRIGGERS):
            await conn.execute(text(ddl))
    await seed_admin()
    logger.info("数据库初始化完成（建表 + FTS5 全文检索 + 管理员种子）")


async def seed_admin() -> None:
    """首次启动创建初始管理员账号 admin / 123456。"""
    async with AsyncSessionLocal() as session:
        exists = (
            await session.execute(select(User).where(User.username == "admin"))
        ).scalar_one_or_none()
        if exists is None:
            session.add(User(username="admin", password_hash=hash_password("123456"), role="admin"))
            await session.commit()
            logger.info("已创建初始管理员账号 admin")
