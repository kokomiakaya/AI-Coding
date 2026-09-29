"""会话接口：多会话 CRUD、消息分页、Markdown 导出（历史持久化可找回）。"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import ChatSession, KnowledgeBase, Message, User
from app.schemas.session import MessageOut, SessionCreate, SessionOut, SessionUpdate
from app.services import export_service

router = APIRouter(prefix="/api/sessions", tags=["会话"])


async def _get_owned_session(db, session_id: int, user: User) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    return session


async def _enrich_sessions(db, sessions: list[ChatSession]) -> list[SessionOut]:
    """附加最后一条消息预览与消息数。"""
    if not sessions:
        return []
    ids = [s.id for s in sessions]
    last_rows = (
        await db.execute(
            select(Message.session_id, Message.content, Message.id).where(
                Message.session_id.in_(ids),
                Message.id.in_(
                    select(func.max(Message.id))
                    .where(Message.session_id.in_(ids))
                    .group_by(Message.session_id)
                ),
            )
        )
    ).all()
    last_map = {sid: (content, mid) for sid, content, mid in last_rows}
    count_rows = (
        await db.execute(
            select(Message.session_id, func.count(Message.id))
            .where(Message.session_id.in_(ids))
            .group_by(Message.session_id)
        )
    ).all()
    count_map = {sid: n for sid, n in count_rows}
    out = []
    for s in sessions:
        last_content, _ = last_map.get(s.id, (None, None))
        out.append(
            SessionOut.model_validate(s).model_copy(
                update={
                    "last_message": (last_content or "")[:100] if last_content else None,
                    "message_count": count_map.get(s.id, 0),
                }
            )
        )
    return out


@router.get("", summary="会话列表（分页+标题搜索）")
async def list_sessions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    filters = [ChatSession.user_id == user.id]
    if q:
        filters.append(ChatSession.title.like(f"%{q}%"))
    total = (await db.execute(select(func.count(ChatSession.id)).where(*filters))).scalar_one()
    rows = (
        await db.execute(
            select(ChatSession)
            .where(*filters)
            .order_by(ChatSession.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars().all()
    return {
        "items": [s.model_dump() for s in await _enrich_sessions(db, list(rows))],
        "total": total,
        "page": page,
        "size": size,
    }


@router.post("", summary="新建空会话", status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if body.kb_id is not None:
        kb = await db.get(KnowledgeBase, body.kb_id)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
    session = ChatSession(
        user_id=user.id, kb_id=body.kb_id, title=body.title or "新会话"
    )
    db.add(session)
    await db.commit()
    return SessionOut.model_validate(session)


@router.get("/{session_id}/messages", summary="会话消息（倒序分页，前端加载更多）")
async def list_messages(
    session_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_owned_session(db, session_id, user)
    total = (
        await db.execute(select(func.count(Message.id)).where(Message.session_id == session_id))
    ).scalar_one()
    rows = (
        await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars().all()
    # 前端按时间正序渲染，返回时翻转
    return {
        "items": [MessageOut.model_validate(m).model_dump() for m in reversed(rows)],
        "total": total,
        "page": page,
        "size": size,
    }


@router.patch("/{session_id}", summary="重命名 / 改绑知识库")
async def update_session(
    session_id: int,
    body: SessionUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    session = await _get_owned_session(db, session_id, user)
    if body.title is not None:
        session.title = body.title
    if body.kb_id is not None:
        kb = await db.get(KnowledgeBase, body.kb_id)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
        session.kb_id = body.kb_id
    await db.commit()
    return SessionOut.model_validate(session)


@router.delete("/{session_id}", summary="删除会话（级联删消息）")
async def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    session = await _get_owned_session(db, session_id, user)
    await db.delete(session)
    await db.commit()
    return {"message": "会话已删除"}


@router.get("/{session_id}/export", summary="导出会话为 Markdown")
async def export_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    session = await _get_owned_session(db, session_id, user)
    messages = (
        await db.execute(
            select(Message).where(Message.session_id == session_id).order_by(Message.id)
        )
    ).scalars().all()
    markdown = export_service.build_markdown(session, list(messages))
    filename = f"会话_{session.title}_{session_id}.md"
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
