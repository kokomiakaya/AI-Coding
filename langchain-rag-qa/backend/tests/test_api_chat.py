"""问答链路测试：SSE 事件契约 / 引用 / 防幻觉兜底 / 多轮 / 会话持久化。"""
import json

from .conftest import create_kb_with_doc


async def _stream(client, headers, body):
    """解析 SSE 流，返回 [(event, data)]。"""
    events = []
    async with client.stream("POST", "/api/chat/stream", json=body, headers=headers) as resp:
        assert resp.status_code == 200, await resp.aread()
        event, data_lines = None, []
        async for line in resp.aiter_lines():
            if line.startswith("event: "):
                event = line[7:].strip()
            elif line.startswith("data: "):
                data_lines.append(line[6:])
            elif line == "" and event and data_lines:
                events.append((event, json.loads("\n".join(data_lines))))
                event, data_lines = None, []
    return events


def _by_event(events, name):
    return [d for e, d in events if e == name]


async def test_chat_stream_citations_and_contract(client, admin_headers, user_headers):
    kb_id = await create_kb_with_doc(
        client, admin_headers, "问答测试库", "星耀X1 电池容量 4500mAh，支持 66W 快充。"
    )
    events = await _stream(
        client, user_headers, {"question": "星耀X1 电池容量是多少", "kb_id": kb_id}
    )

    # 事件序列契约：meta → delta* → sources → usage → done，无 error
    names = [e for e, _ in events]
    assert names[0] == "meta"
    assert "delta" in names
    assert "sources" in names
    assert "usage" in names
    assert names[-1] == "done"
    assert "error" not in names

    meta = _by_event(events, "meta")[0]
    assert meta["session_id"] and meta["message_id"]

    answer = "".join(d["content"] for d in _by_event(events, "delta"))
    assert "4500" in answer

    sources = _by_event(events, "sources")[0]["sources"]
    assert len(sources) >= 1
    assert any(s["cited"] for s in sources), "回答应有被引用的片段"


async def test_chat_no_context_chit_chat(client, admin_headers, user_headers):
    """检索无结果的分流：闲聊类问题直接由大模型回答（不带引用、不编造商品信息）。"""
    kb_id = await create_kb_with_doc(client, admin_headers, "兜底测试库", "星耀X1 电池容量 4500mAh。")
    events = await _stream(
        client, user_headers, {"question": "你是什么模型", "kb_id": kb_id}
    )
    answer = "".join(d["content"] for d in _by_event(events, "delta"))
    sources = _by_event(events, "sources")[0]["sources"]
    usage = _by_event(events, "usage")[0]
    assert sources == []  # 无检索引用
    assert answer.strip() != ""  # 大模型直接回答（离线模式返回确定性闲聊话术）
    assert "4500" not in answer  # 不引用也不编造商品信息
    assert usage["meta"].get("fallback") is True
    assert "error" not in [e for e, _ in events]


async def test_chat_product_question_with_weak_match_no_fabrication(client, admin_headers, user_headers):
    """知识库无关的商品问题：检索分数低于阈值 → 兜底路径，不得编造商品信息。"""
    kb_id = await create_kb_with_doc(client, admin_headers, "防编造测试库", "星耀X1 电池容量 4500mAh。")
    # "云听P2 多少钱"与库内容无词重叠 → 检索低于阈值
    events = await _stream(
        client, user_headers, {"question": "云听P2 耳机的价格是多少钱", "kb_id": kb_id}
    )
    answer = "".join(d["content"] for d in _by_event(events, "delta"))
    sources = _by_event(events, "sources")[0]["sources"]
    assert sources == []  # 未通过阈值，无引用
    assert "499" not in answer  # 离线模式兜底回答不得包含具体价格（防编造）


async def test_chat_session_persistence_and_history(client, admin_headers, user_headers):
    kb_id = await create_kb_with_doc(client, admin_headers, "会话测试库", "星耀X1 屏幕 6.7 英寸。")
    events = await _stream(
        client, user_headers, {"question": "星耀X1 屏幕多大", "kb_id": kb_id}
    )
    session_id = _by_event(events, "meta")[0]["session_id"]

    # 多轮追问（离线模式改写降级原问题，但仍能基于会话继续）
    events2 = await _stream(
        client, user_headers, {"question": "它的电池呢", "session_id": session_id}
    )
    assert events2[0][0] == "meta"

    # 会话历史持久化
    r = await client.get(f"/api/sessions/{session_id}/messages", headers=user_headers)
    data = r.json()
    assert data["total"] == 4  # 两问两答
    assert data["items"][0]["role"] == "user"

    # 会话列表含最后消息预览
    r = await client.get("/api/sessions", headers=user_headers)
    assert any(s["id"] == session_id for s in r.json()["items"])


async def test_chat_feedback(client, admin_headers, user_headers):
    kb_id = await create_kb_with_doc(client, admin_headers, "反馈测试库", "云听P2 售价 499 元。")
    events = await _stream(client, user_headers, {"question": "云听P2 多少钱", "kb_id": kb_id})
    msg_id = _by_event(events, "meta")[0]["message_id"]

    r = await client.post(
        f"/api/messages/{msg_id}/feedback", json={"rate": 1, "comment": "很好"}, headers=user_headers
    )
    assert r.status_code == 200

    # 非本人/不存在消息 → 404
    r = await client.post("/api/messages/999999/feedback", json={"rate": 1}, headers=user_headers)
    assert r.status_code == 404
