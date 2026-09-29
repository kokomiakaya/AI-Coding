"""知识库接口与权限矩阵测试。"""


async def test_kb_permission_matrix(client, admin_headers, user_headers):
    # 普通用户建库 → 403
    r = await client.post("/api/kb", json={"name": "非法建库"}, headers=user_headers)
    assert r.status_code == 403

    # 管理员建库 → 201
    r = await client.post(
        "/api/kb",
        json={"name": "权限测试库", "description": "测试", "top_k": 6},
        headers=admin_headers,
    )
    assert r.status_code == 201
    kb_id = r.json()["id"]
    assert r.json()["top_k"] == 6

    # 普通用户可见（聊天选库用）
    r = await client.get("/api/kb", headers=user_headers)
    assert any(k["id"] == kb_id for k in r.json())

    # 普通用户改库 → 403
    r = await client.patch(f"/api/kb/{kb_id}", json={"top_k": 8}, headers=user_headers)
    assert r.status_code == 403

    # 管理员更新与删除
    r = await client.patch(f"/api/kb/{kb_id}", json={"top_k": 8}, headers=admin_headers)
    assert r.status_code == 200
    r = await client.delete(f"/api/kb/{kb_id}", headers=admin_headers)
    assert r.status_code == 200

    # 删除后详情 404
    r = await client.get(f"/api/kb/{kb_id}", headers=user_headers)
    assert r.status_code == 404


async def test_kb_count_fields(client, admin_headers):
    from .conftest import create_kb_with_doc

    kb_id = await create_kb_with_doc(client, admin_headers, "计数测试库", "商品A 价格 100 元")
    r = await client.get(f"/api/kb/{kb_id}", headers=admin_headers)
    data = r.json()
    assert data["document_count"] == 1
    assert data["chunk_count"] >= 1
