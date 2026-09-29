"""问答接口：SSE 流式问答 + 非流式调试版 + 答案反馈。

流式协议事件：meta → delta* → sources → usage → done（或 error）。
EventSource 只支持 GET，故前端用 fetch 流式解析 POST。
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.models import Message, User
from app.schemas.chat import ChatIn, FeedbackIn
from app.services.rag.pipeline import run_chat_events, sse_encode

router = APIRouter(prefix="/api", tags=["问答"])

CHAT_RATE = (20, 60)  # 20 次 / 分钟 / 用户


def _check_chat_rate(user: User) -> None:
    if get_settings().rate_limit_disabled:
        return
    if not rate_limiter.check(f"chat:{user.id}", *CHAT_RATE):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "提问过于频繁，请稍后再试")


@router.post("/chat/stream", summary="流式问答（SSE）")
async def chat_stream(
    body: ChatIn,
    request: Request,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    _check_chat_rate(user)
    services = request.app.state.services
    return StreamingResponse(
        (sse_encode(event, data) async for event, data in run_chat_events(db, user, body, services)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat", summary="非流式问答（调试/测试用）")
async def chat(
    body: ChatIn,
    request: Request,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    _check_chat_rate(user)
    services = request.app.state.services
    result: dict = {"answer": "", "sources": [], "session_id": None, "message_id": None}
    async for event, data in run_chat_events(db, user, body, services):
        if event == "meta":
            result["session_id"] = data["session_id"]
            result["message_id"] = data["message_id"]
        elif event == "delta":
            result["answer"] += data["content"]
        elif event == "sources":
            result["sources"] = data["sources"]
        elif event == "usage":
            result["usage"] = data
        elif event == "error":
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, data.get("detail", "回答生成失败"))
    return result


@router.post("/messages/{message_id}/feedback", summary="答案反馈（赞/踩）")
async def feedback(
    message_id: int,
    body: FeedbackIn,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    message = await db.get(Message, message_id)
    if message is None or message.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "消息不存在")
    if message.role != "assistant":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "只能对回答进行反馈")
    message.feedback = body.rate
    message.feedback_comment = body.comment
    await db.commit()
    return {"message": "反馈已记录"}
