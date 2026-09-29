"""后端端到端自测脚本：登录 → 建库 → 上传 → 摄取 → 检索调试 → 流式问答 → 引用校验。

运行前提：后端已启动在 127.0.0.1:8000。
用法：backend/.venv/Scripts/python.exe scripts/e2e_test.py
"""
import asyncio
import json
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
SAMPLE_DIR = Path(__file__).resolve().parent / "sample_docs"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, timeout=120) as client:
        # 1. 管理员登录
        r = await client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
        assert r.status_code == 200, f"登录失败: {r.text}"
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[1] 管理员登录 OK")

        # 2. 新建知识库
        r = await client.post(
            "/api/kb",
            json={"name": "商品知识库", "description": "演示用电商商品知识库"},
            headers=headers,
        )
        assert r.status_code == 201, f"建库失败: {r.text}"
        kb_id = r.json()["id"]
        print(f"[2] 新建知识库 OK（id={kb_id}）")

        # 3. 上传三个演示文档
        files = []
        for name in ("商品FAQ.md", "商品信息表.xlsx", "商品说明书.pdf"):
            p = SAMPLE_DIR / name
            files.append(("files", (name, p.read_bytes())))
        r = await client.post(f"/api/kb/{kb_id}/documents", files=files, headers=headers)
        assert r.status_code == 200, f"上传失败: {r.text}"
        doc_ids = [d["id"] for d in r.json()["items"]]
        print(f"[3] 上传 3 个文档 OK（ids={doc_ids}）")

        # 4. 轮询摄取状态
        deadline = time.time() + 180
        while time.time() < deadline:
            r = await client.get(f"/api/kb/{kb_id}/documents", headers=headers)
            statuses = [d["status"] for d in r.json()["items"]]
            print(f"    摄取状态: {statuses}")
            if all(s in ("ready", "failed") for s in statuses):
                break
            await asyncio.sleep(3)
        assert all(s == "ready" for s in statuses), f"摄取未全部成功: {statuses}"
        print("[4] 文档摄取全部完成 OK")

        # 5. 检索调试
        r = await client.post(
            f"/api/kb/{kb_id}/search-test",
            json={"question": "星耀X1 电池容量"},
            headers=headers,
        )
        data = r.json()
        top = data["hybrid"][0] if data["hybrid"] else None
        assert top, "检索无结果"
        print(f"[5] 检索调试 OK：命中 {data['retrieved_count']} 条，top1={top['document_name']} "
              f"(rrf={top['rrf_score']}, rerank={top['relevance_score']})")
        assert "4500" in top["excerpt"] or "电池" in top["excerpt"], "top1 内容不相关"

        # 6. 流式问答（SSE）
        events = []
        async with client.stream(
            "POST",
            "/api/chat/stream",
            json={"question": "星耀X1 手机的电池容量是多少？"},
            headers=headers,
        ) as resp:
            assert resp.status_code == 200, f"问答失败: {await resp.aread()}"
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        deltas = [e["content"] for e in events if e.get("content")]
        answer = "".join(deltas)
        sources_event = next(e for e in events if "sources" in e and "content" not in e)
        sources = sources_event["sources"]
        print(f"[6] 流式问答 OK：{len(deltas)} 个 token 块")
        print(f"    回答：{answer[:100]}...")
        cited = [s for s in sources if s.get("cited")]
        cited_desc = ", ".join(
            "{}({})".format(s["document_name"], "第{}页".format(s["page"]) if s.get("page") else "第{}行".format(s.get("row")))
            for s in cited
        )
        print(f"    引用片段 {len(cited)}/{len(sources)} 条，来源: {cited_desc}")
        assert cited, "回答没有引用任何片段"

        # 7. 多轮追问（改写生效验证）
        events2 = []
        session_id = events[0]["session_id"]
        async with client.stream(
            "POST",
            "/api/chat/stream",
            json={"question": "那它的屏幕多大？", "session_id": session_id},
            headers=headers,
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    events2.append(json.loads(line[6:]))
        answer2 = "".join(e["content"] for e in events2 if "content" in e)
        print(f"[7] 多轮追问 OK：{answer2[:80]}...")
        assert "6.7" in answer2 or "屏幕" in answer2, "追问未结合上下文"

        # 8. 防幻觉兜底
        events3 = []
        async with client.stream(
            "POST",
            "/api/chat/stream",
            json={"question": "明天北京的天气怎么样？"},
            headers=headers,
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    events3.append(json.loads(line[6:]))
        answer3 = "".join(e["content"] for e in events3 if "content" in e)
        sources3 = next(e for e in events3 if "sources" in e)["sources"]
        print(f"[8] 防幻觉兜底 OK：{answer3[:50]}（sources={len(sources3)} 条）")
        assert len(sources3) == 0 and "未找到" in answer3

        # 9. 会话历史恢复验证
        r = await client.get(f"/api/sessions/{session_id}/messages", headers=headers)
        msgs = r.json()["items"]
        print(f"[9] 会话历史 OK：共 {r.json()['total']} 条消息，首条: {msgs[0]['content'][:20]}")
        assert r.json()["total"] >= 4

        # 10. 普通用户权限验证
        await client.post("/api/auth/register", json={"username": "zhangsan", "password": "123456"})
        r = await client.post("/api/auth/login", json={"username": "zhangsan", "password": "123456"})
        user_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = await client.post("/api/kb", json={"name": "非法建库"}, headers=user_headers)
        assert r.status_code == 403, f"普通用户建库未被拒绝: {r.status_code}"
        print("[10] 权限控制 OK：普通用户建库被拒（403）")

        print("\n========== 全部端到端测试通过 ==========")


if __name__ == "__main__":
    asyncio.run(main())
