"""知识库接口：列表（全员）/ 增删改（仅管理员）/ 检索调试（仅管理员）。"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models import KnowledgeBase, User
from app.schemas.kb import KBCreate, KBOut, KBUpdate, SearchTestIn
from app.services import kb_service
from app.services.rag.hybrid import hybrid_search

router = APIRouter(prefix="/api/kb", tags=["知识库"])


@router.get("", summary="知识库列表（聊天选库用；管理员可见全部）")
async def list_kbs(user: User = Depends(get_current_user), db=Depends(get_db)):
    query = select(KnowledgeBase).order_by(KnowledgeBase.id)
    if user.role != "admin":
        query = query.where(KnowledgeBase.is_active.is_(True))
    rows = (await db.execute(query)).scalars().all()
    counts = await kb_service.kb_counts(db, [kb.id for kb in rows])
    return [
        KBOut.model_validate(kb).model_copy(
            update={
                "document_count": counts.get(kb.id, {}).get("document_count", 0),
                "chunk_count": counts.get(kb.id, {}).get("chunk_count", 0),
            }
        )
        for kb in rows
    ]


@router.post("", summary="新建知识库（仅管理员）", status_code=status.HTTP_201_CREATED)
async def create_kb(
    body: KBCreate,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    kb = KnowledgeBase(**body.model_dump(), created_by=admin.id)
    db.add(kb)
    await db.commit()
    return KBOut.model_validate(kb)


@router.get("/{kb_id}", summary="知识库详情")
async def get_kb(kb_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None or (not kb.is_active and user.role != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
    counts = await kb_service.kb_counts(db, [kb.id])
    return KBOut.model_validate(kb).model_copy(update=counts.get(kb.id, {}))


@router.patch("/{kb_id}", summary="修改知识库（仅管理员，参数只影响新文档）")
async def update_kb(
    kb_id: int,
    body: KBUpdate,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(kb, field, value)
    await db.commit()
    return KBOut.model_validate(kb)


@router.delete("/{kb_id}", summary="删除知识库（仅管理员，级联清理）")
async def delete_kb(
    kb_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
    await kb_service.delete_kb(db, request.app.state.services.vector_store, kb)
    return {"message": "知识库已删除"}


@router.post("/{kb_id}/search-test", summary="检索调试（仅管理员，答辩演示神器）")
async def search_test(
    kb_id: int,
    body: SearchTestIn,
    request: Request,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """只跑检索不生成：返回混合检索与重排两个阶段的结果和分数，便于调试与演示。"""
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
    services = request.app.state.services
    fused = await hybrid_search(
        db,
        services.vector_store,
        services.embedder,
        body.question,
        [kb_id],
        candidates=kb.top_k * 4,
    )
    reranked = await services.reranker.rerank(
        body.question, fused, top_n=min(len(fused), kb.top_k * 2)
    )
    # 把重排分数写回候选（与问答管线 _apply_rerank 一致），供调试页展示
    for i, score in reranked or []:
        if i < len(fused):
            fused[i].score = score

    def _dump(chunks):
        out = []
        for c in chunks:
            out.append(
                {
                    "chunk_id": c.chunk_id,
                    "document_name": c.document_name,
                    "page": c.page,
                    "sheet": c.sheet,
                    "row": c.row,
                    "excerpt": c.content[:120],
                    "rrf_score": c.rrf_score,
                    "vector_similarity": c.vector_similarity,
                    "bm25_rank": c.bm25_rank,
                    "relevance_score": c.score if c.score else None,
                }
            )
        return out

    rerank_map = dict(reranked) if reranked else None

    return {
        "question": body.question,
        "retrieved_count": len(fused),
        "hybrid": _dump(fused),
        "reranked": _dump(
            [fused[i] for i, _ in sorted(reranked, key=lambda x: -x[1])]
            if rerank_map is not None
            else []
        ),
        "rerank_skipped": rerank_map is None,
    }
