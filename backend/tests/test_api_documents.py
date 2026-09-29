"""文档管理接口测试：上传校验 / 异步摄取状态机 / 分块 / 检索调试 / 删除。"""
import asyncio


async def test_upload_ingest_chunks_search(client, admin_headers):
    from .conftest import create_kb_with_doc

    kb_id = await create_kb_with_doc(
        client, admin_headers, "摄取测试库", "星耀X1 电池容量 4500mAh，支持 66W 快充，IP68 防水。"
    )

    # 文档列表
    r = await client.get(f"/api/kb/{kb_id}/documents", headers=admin_headers)
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "ready"
    doc_id = data["items"][0]["id"]

    # 分块预览
    r = await client.get(f"/api/documents/{doc_id}/chunks", headers=admin_headers)
    assert r.json()["total"] >= 1

    # 检索调试（mock 模式：哈希嵌入 + 词重叠打分）
    r = await client.post(
        f"/api/kb/{kb_id}/search-test", json={"question": "电池容量"}, headers=admin_headers
    )
    data = r.json()
    assert data["retrieved_count"] >= 1
    assert "4500" in data["hybrid"][0]["excerpt"]

    # 删除文档
    r = await client.delete(f"/api/documents/{doc_id}", headers=admin_headers)
    assert r.status_code == 200
    r = await client.get(f"/api/documents/{doc_id}", headers=admin_headers)
    assert r.status_code == 404


async def test_create_text_document(client, admin_headers):
    """直接录入文本 → 落盘 .txt → 走与上传相同的摄取管道。"""
    r = await client.post("/api/kb", json={"name": "文本录入测试库"}, headers=admin_headers)
    kb_id = r.json()["id"]

    r = await client.post(
        f"/api/kb/{kb_id}/documents/text",
        json={"filename": "新品卖点", "content": "云听P2 降噪深度 45dB，总续航 36 小时。"},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    for _ in range(80):
        d = (await client.get(f"/api/documents/{doc_id}", headers=admin_headers)).json()
        if d["status"] in ("ready", "failed"):
            break
        await asyncio.sleep(0.25)
    assert d["status"] == "ready" and d["chunk_count"] >= 1

    # 检索调试能命中录入的文本
    r = await client.post(
        f"/api/kb/{kb_id}/search-test", json={"question": "降噪深度"}, headers=admin_headers
    )
    assert r.json()["retrieved_count"] >= 1

    # 空内容 → 400
    r = await client.post(
        f"/api/kb/{kb_id}/documents/text", json={"filename": "x", "content": "   "}, headers=admin_headers
    )
    assert r.status_code == 400


async def test_upload_reject_bad_type(client, admin_headers):
    r = await client.post("/api/kb", json={"name": "校验测试库"}, headers=admin_headers)
    kb_id = r.json()["id"]
    files = {"files": ("病毒.exe", b"MZ...")}
    r = await client.post(f"/api/kb/{kb_id}/documents", files=files, headers=admin_headers)
    assert r.status_code == 400


async def test_upload_reject_oversize(client, admin_headers):
    r = await client.post("/api/kb", json={"name": "大小测试库"}, headers=admin_headers)
    kb_id = r.json()["id"]
    big = b"a" * (51 * 1024 * 1024)  # 超过 50MB
    files = {"files": ("大文件.txt", big)}
    r = await client.post(f"/api/kb/{kb_id}/documents", files=files, headers=admin_headers)
    assert r.status_code == 400


async def test_reembed_flow(client, admin_headers):
    from .conftest import create_kb_with_doc

    kb_id = await create_kb_with_doc(client, admin_headers, "重建测试库", "内容一")
    r = await client.get(f"/api/kb/{kb_id}/documents", headers=admin_headers)
    doc_id = r.json()["items"][0]["id"]

    # 已完成状态 → re-embed → 回到 pending → 再变 ready（幂等重建）
    r = await client.post(f"/api/documents/{doc_id}/re-embed", headers=admin_headers)
    assert r.status_code == 200
    for _ in range(80):
        d = (await client.get(f"/api/documents/{doc_id}", headers=admin_headers)).json()
        if d["status"] == "ready":
            break
        await asyncio.sleep(0.25)
    assert d["status"] == "ready"
