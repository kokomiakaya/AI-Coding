"""统计服务：管理看板的聚合数据（KPI/趋势/反馈/KB 分布）。

数据量级对毕设场景足够，直接对 messages/documents 聚合；
论文可注明"未来可加物化视图/日表"。
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, KnowledgeBase, Message, ChatSession, User


async def overview(db: AsyncSession) -> dict:
    user_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    session_count = (await db.execute(select(func.count(ChatSession.id)))).scalar_one()
    message_count = (await db.execute(select(func.count(Message.id)))).scalar_one()
    kb_count = (await db.execute(select(func.count(KnowledgeBase.id)))).scalar_one()
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar_one()
    chunk_count = (await db.execute(select(func.count(Chunk.id)))).scalar_one()
    total_tokens = (
        await db.execute(
            select(func.coalesce(func.sum(Message.prompt_tokens + Message.completion_tokens), 0))
        )
    ).scalar_one()
    return {
        "user_count": user_count,
        "session_count": session_count,
        "message_count": message_count,
        "kb_count": kb_count,
        "document_count": doc_count,
        "chunk_count": chunk_count,
        "total_tokens": total_tokens,
    }


async def trend(db: AsyncSession, days: int = 30) -> list[dict]:
    """按天聚合：问答消息数与 token 消耗（ECharts 双轴折线数据）。"""
    days = min(max(days, 1), 90)
    since = (datetime.now(timezone.utc) - timedelta(days=days - 1)).isoformat(timespec="seconds")
    rows = (
        await db.execute(
            select(
                func.substr(Message.created_at, 1, 10).label("day"),
                func.count(Message.id),
                func.coalesce(func.sum(Message.prompt_tokens + Message.completion_tokens), 0),
            )
            .where(Message.created_at >= since)
            .group_by("day")
            .order_by("day")
        )
    ).all()
    return [{"date": day, "messages": n, "tokens": int(t)} for day, n, t in rows]


async def kb_stats(db: AsyncSession) -> list[dict]:
    """每 KB：文档数、分块数、被问答的助手消息数。"""
    kb_rows = (await db.execute(select(KnowledgeBase))).scalars().all()
    msg_rows = (
        await db.execute(
            text(
                """
                SELECT COALESCE(s.kb_id, 0) AS kb_id, COUNT(m.id) AS cnt
                FROM messages m JOIN sessions s ON s.id = m.session_id
                WHERE m.role = 'assistant'
                GROUP BY COALESCE(s.kb_id, 0)
                """
            )
        )
    ).all()
    msg_map = {int(kb_id): cnt for kb_id, cnt in msg_rows}
    result = []
    for kb in kb_rows:
        doc_count = (
            await db.execute(select(func.count(Document.id)).where(Document.kb_id == kb.id))
        ).scalar_one()
        chunk_count = (
            await db.execute(select(func.count(Chunk.id)).where(Chunk.kb_id == kb.id))
        ).scalar_one()
        result.append(
            {
                "kb_id": kb.id,
                "name": kb.name,
                "document_count": doc_count,
                "chunk_count": chunk_count,
                "answer_count": msg_map.get(kb.id, 0),
            }
        )
    result.append(
        {"kb_id": 0, "name": "全部知识库", "answer_count": msg_map.get(0, 0)}
    )
    return result


async def feedback_stats(db: AsyncSession) -> dict:
    """赞踩计数、满意度率、按天趋势。"""
    rows = (
        await db.execute(
            select(Message.feedback, func.count(Message.id))
            .where(Message.feedback.is_not(None))
            .group_by(Message.feedback)
        )
    ).all()
    likes = next((n for f, n in rows if f == 1), 0)
    dislikes = next((n for f, n in rows if f == -1), 0)
    total = likes + dislikes
    trend_rows = (
        await db.execute(
            select(
                func.substr(Message.created_at, 1, 10).label("day"),
                func.sum(func.iif(Message.feedback == 1, 1, 0)),
                func.sum(func.iif(Message.feedback == -1, 1, 0)),
            )
            .where(Message.feedback.is_not(None))
            .group_by("day")
            .order_by("day")
        )
    ).all()
    return {
        "likes": likes,
        "dislikes": dislikes,
        "total": total,
        "satisfaction_rate": round(likes / total, 4) if total else None,
        "trend": [{"date": day, "likes": l, "dislikes": d} for day, l, d in trend_rows],
    }
