"""RAG 问答主流程编排（系统核心）：

查询改写 → 混合检索(向量+BM25+RRF) → 重排 → 阈值过滤 → 生成 → 引用校验

以 (event, data) 元组流产出，供 SSE 流式端点与非流式端点复用；
分阶段耗时写入 message.meta（论文性能分析数据来源）。
"""
import time
from typing import AsyncIterator

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatSession, KnowledgeBase, Message, User
from app.schemas.chat import ChatIn
from app.services import config_service
from app.services.container import Services
from app.services.rag import citations
from app.services.rag.hybrid import RetrievedChunk, hybrid_search

MAX_HISTORY_CHARS = 2000  # 历史单条截断，控制 token 消耗


def sse_encode(event: str, data: dict) -> str:
    """SSE 事件编码。"""
    import json

    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_context(chunks: list[RetrievedChunk]) -> str:
    """把检索片段拼成带编号的参考资料文本。"""
    lines = []
    for i, ch in enumerate(chunks, start=1):
        loc = []
        if ch.page:
            loc.append(f"第{ch.page}页")
        if ch.sheet:
            loc.append(f"工作表{ch.sheet}")
        if ch.row:
            loc.append(f"第{ch.row}行")
        loc_text = f"，{'、'.join(loc)}" if loc else ""
        lines.append(f"[{i}] (来源: {ch.document_name}{loc_text})\n{ch.content}")
    return "\n\n".join(lines)


def _estimate_tokens(text: str) -> int:
    """无 usage 数据时的保守估算（中文约 1 字 1 token）。"""
    return max(1, len(text))


def _chunk_text(text: str, size: int = 30):
    for i in range(0, len(text), size):
        yield text[i : i + size]


async def _resolve_session(db: AsyncSession, user: User, body: ChatIn) -> ChatSession:
    if body.session_id:
        session = await db.get(ChatSession, body.session_id)
        if session is None or session.user_id != user.id:
            raise PermissionError("会话不存在或无权访问")
        if body.kb_id is not None:
            session.kb_id = body.kb_id
        return session
    session = ChatSession(user_id=user.id, kb_id=body.kb_id, title="新会话")
    db.add(session)
    await db.flush()
    return session


async def _resolve_kbs(
    db: AsyncSession, session: ChatSession, kb_id: int | None
) -> tuple[list[int], dict]:
    """确定检索范围与检索参数：请求参数 > 会话绑定 > 全部启用 KB（用全局默认参数）。"""
    target = kb_id or session.kb_id
    if target:
        kb = await db.get(KnowledgeBase, target)
        if kb is None:
            raise PermissionError("知识库不存在")
        return [kb.id], {
            "top_k": kb.top_k,
            "score_threshold": kb.score_threshold,
            "rewrite_enabled": kb.rewrite_enabled,
        }
    rows = (
        await db.execute(select(KnowledgeBase).where(KnowledgeBase.is_active.is_(True)))
    ).scalars().all()
    return [kb.id for kb in rows], {
        "top_k": await config_service.get_config(db, "retrieval.top_k"),
        "score_threshold": await config_service.get_config(db, "retrieval.score_threshold"),
        "rewrite_enabled": True,
    }


async def _load_history(
    db: AsyncSession, session_id: int, exclude_message_id: int
) -> list[dict]:
    """最近 N 轮历史（供改写与生成），单条截断控制 token。"""
    max_turns = await config_service.get_config(db, "chat.history_max_turns")
    rows = (
        await db.execute(
            select(Message)
            .where(Message.session_id == session_id, Message.id != exclude_message_id)
            .order_by(Message.id.desc())
            .limit(max_turns * 2)
        )
    ).scalars().all()
    rows = list(reversed(rows))
    return [{"role": r.role, "content": r.content[:MAX_HISTORY_CHARS]} for r in rows]


def _apply_rerank(
    fused: list[RetrievedChunk], reranked: list[tuple[int, float]], top_k: int
) -> list[RetrievedChunk]:
    """把重排分数写回候选并截取 top_k。"""
    ordered = [fused[i] for i, _ in sorted(reranked, key=lambda x: -x[1]) if i < len(fused)]
    for i, score in reranked:
        if i < len(fused):
            fused[i].score = score
    return ordered[:top_k]


async def run_chat_events(
    db: AsyncSession, user: User, body: ChatIn, services: Services
) -> AsyncIterator[tuple[str, dict]]:
    """执行完整 RAG 链路，产出 (event, data) 事件流。"""
    started = time.perf_counter()
    meta_info: dict = {}

    # ---------- 会话与知识库解析 ----------
    try:
        session = await _resolve_session(db, user, body)
        kb_ids, kb_params = await _resolve_kbs(db, session, body.kb_id)
    except PermissionError as exc:
        yield "error", {"detail": str(exc)}
        return

    # ---------- 落库用户消息 + assistant 占位 ----------
    user_msg = Message(session_id=session.id, user_id=user.id, role="user", content=body.question)
    assistant_msg = Message(session_id=session.id, user_id=user.id, role="assistant", content="")
    db.add_all([user_msg, assistant_msg])
    if session.title == "新会话":
        session.title = body.question[:30]
    await db.commit()
    yield "meta", {
        "message_id": assistant_msg.id,
        "user_message_id": user_msg.id,
        "session_id": session.id,
        "session_title": session.title,
        "kb_id": body.kb_id or session.kb_id,
    }

    try:
        top_k = kb_params["top_k"]
        threshold = kb_params["score_threshold"]
        meta_info["kb_ids"] = kb_ids

        # ---------- 历史（排除本轮用户消息） ----------
        history = await _load_history(db, session.id, exclude_message_id=user_msg.id)

        # ---------- ① 查询改写 ----------
        t = time.perf_counter()
        query = body.question
        if kb_params["rewrite_enabled"]:
            template = await config_service.get_config(db, "prompt.rewrite")
            query = await services.rewriter.rewrite(body.question, history, template)
        meta_info["rewrite_ms"] = round((time.perf_counter() - t) * 1000)
        meta_info["rewritten_query"] = query if query != body.question else None

        # ---------- ②③ 混合检索（向量 + BM25 + RRF 融合） ----------
        t = time.perf_counter()
        fused = await hybrid_search(
            db,
            services.vector_store,
            services.embedder,
            query,
            kb_ids,
            candidates=await config_service.get_config(db, "retrieval.candidates"),
        )
        meta_info["retrieve_ms"] = round((time.perf_counter() - t) * 1000)
        meta_info["retrieved_count"] = len(fused)

        # ---------- ④ 重排（粗排→精排；失败时 reranker 内部降级为本地混合分数） ----------
        t = time.perf_counter()
        rerank_top = min(len(fused), top_k * 2)
        reranked = await services.reranker.rerank(query, fused, rerank_top)
        meta_info["rerank_ms"] = round((time.perf_counter() - t) * 1000)
        final_chunks = (
            _apply_rerank(fused, reranked, top_k)
            if reranked is not None
            else [fused[i] for i in range(min(top_k, len(fused)))]
        )

        # ---------- ⑤ 阈值过滤（防幻觉兜底机制） ----------
        final_chunks = [c for c in final_chunks if c.score >= threshold]
        meta_info["final_count"] = len(final_chunks)

        # ---------- ⑥ 空结果分流：闲聊类问题让大模型直接回答；商品类问题兜底不编造 ----------
        if not final_chunks:
            meta_info["fallback"] = True
            no_context_prompt = await config_service.get_config(db, "prompt.no_context")
            answer_parts = []
            usage: dict = {}
            t = time.perf_counter()
            async for token in services.generator.stream(
                [
                    {"role": "system", "content": no_context_prompt},
                    {"role": "user", "content": body.question},
                ],
                usage,
            ):
                answer_parts.append(token)
                yield "delta", {"content": token}
            meta_info["llm_ms"] = round((time.perf_counter() - t) * 1000)
            answer = "".join(answer_parts)
            assistant_msg.content = answer
            assistant_msg.sources = []
            assistant_msg.prompt_tokens = usage.get("prompt_tokens", 0) or _estimate_tokens(
                body.question
            )
            assistant_msg.completion_tokens = usage.get("completion_tokens", 0) or _estimate_tokens(
                answer
            )
            assistant_msg.latency_ms = int((time.perf_counter() - started) * 1000)
            assistant_msg.meta = meta_info
            await db.commit()
            yield "sources", {"sources": []}
            yield "usage", {
                "prompt_tokens": assistant_msg.prompt_tokens,
                "completion_tokens": assistant_msg.completion_tokens,
                "latency_ms": assistant_msg.latency_ms,
                "meta": meta_info,
            }
            yield "done", {"message_id": assistant_msg.id}
            return

        # ---------- ⑦ 生成（流式） ----------
        system_prompt = await config_service.get_config(db, "prompt.system")
        context = build_context(final_chunks)
        messages = services.generator.build_messages(system_prompt, context, history, body.question)
        answer_parts: list[str] = []
        usage: dict = {}
        t = time.perf_counter()
        async for token in services.generator.stream(messages, usage):
            answer_parts.append(token)
            yield "delta", {"content": token}
        meta_info["llm_ms"] = round((time.perf_counter() - t) * 1000)
        answer = "".join(answer_parts)

        # ---------- ⑧ 引用校验 + 落库 ----------
        sources, no_citation = citations.build_sources(final_chunks, answer)
        meta_info["no_citation"] = no_citation
        assistant_msg.content = answer
        assistant_msg.sources = sources
        assistant_msg.prompt_tokens = usage.get("prompt_tokens", 0) or _estimate_tokens(
            context + body.question
        )
        assistant_msg.completion_tokens = usage.get("completion_tokens", 0) or _estimate_tokens(answer)
        assistant_msg.latency_ms = int((time.perf_counter() - started) * 1000)
        assistant_msg.meta = meta_info
        await db.commit()

        yield "sources", {"sources": sources}
        yield "usage", {
            "prompt_tokens": assistant_msg.prompt_tokens,
            "completion_tokens": assistant_msg.completion_tokens,
            "latency_ms": assistant_msg.latency_ms,
            "meta": meta_info,
        }
        yield "done", {"message_id": assistant_msg.id}
    except Exception as exc:
        logger.exception("问答生成失败")
        assistant_msg.content = "回答生成失败，请稍后重试。"
        assistant_msg.meta = {**meta_info, "error": str(exc)[:300]}
        await db.commit()
        yield "error", {"detail": f"回答生成失败：{exc}"}
