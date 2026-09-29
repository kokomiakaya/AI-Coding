"""会话管理接口测试：CRUD / 归属隔离 / Markdown 导出。"""
from .conftest import create_kb_with_doc


async def test_session_crud_and_export(client, admin_headers, user_headers):
    # 新建空会话
    r = await client.post("/api/sessions", json={"title": "我的会话"}, headers=user_headers)
    assert r.status_code == 201
    session_id = r.json()["id"]

    # 重命名
    r = await client.patch(f"/api/sessions/{session_id}", json={"title": "改名后"}, headers=user_headers)
    assert r.json()["title"] == "改名后"

    # 绑定知识库
    kb_id = await create_kb_with_doc(client, admin_headers, "会话绑定库", "内容")
    r = await client.patch(f"/api/sessions/{session_id}", json={"kb_id": kb_id}, headers=user_headers)
    assert r.json()["kb_id"] == kb_id

    # 列表搜索
    r = await client.get("/api/sessions", params={"q": "改名"}, headers=user_headers)
    assert any(s["id"] == session_id for s in r.json()["items"])

    # 导出 Markdown
    r = await client.get(f"/api/sessions/{session_id}/export", headers=user_headers)
    assert r.status_code == 200
    assert "改名后" in r.text
    assert r.headers["content-type"].startswith("text/markdown")

    # 删除
    r = await client.delete(f"/api/sessions/{session_id}", headers=user_headers)
    assert r.status_code == 200
    r = await client.get(f"/api/sessions/{session_id}/messages", headers=user_headers)
    assert r.status_code == 404


async def test_session_owner_isolation(client, admin_headers, user_headers):
    """用户不能访问他人的会话（404 而非 403，防探测）。"""
    r = await client.post("/api/sessions", json={}, headers=admin_headers)
    admin_session = r.json()["id"]

    r = await client.get(f"/api/sessions/{admin_session}/messages", headers=user_headers)
    assert r.status_code == 404
    r = await client.patch(f"/api/sessions/{admin_session}", json={"title": "hack"}, headers=user_headers)
    assert r.status_code == 404
    r = await client.delete(f"/api/sessions/{admin_session}", headers=user_headers)
    assert r.status_code == 404
