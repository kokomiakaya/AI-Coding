"""认证接口测试：注册 / 登录 / 当前用户 / 修改密码 / 鉴权。"""


async def test_register_login_me(client):
    r = await client.post("/api/auth/register", json={"username": "alice", "password": "abc12345"})
    assert r.status_code == 200
    assert r.json()["role"] == "user"

    r = await client.post("/api/auth/login", json={"username": "alice", "password": "abc12345"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


async def test_duplicate_username_rejected(client):
    r = await client.post("/api/auth/register", json={"username": "alice", "password": "xyz12345"})
    assert r.status_code == 400


async def test_wrong_password_rejected(client):
    r = await client.post("/api/auth/login", json={"username": "alice", "password": "wrong-password"})
    assert r.status_code == 400


async def test_change_password_flow(client):
    await client.post("/api/auth/register", json={"username": "bob", "password": "old123456"})
    r = await client.post("/api/auth/login", json={"username": "bob", "password": "old123456"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 旧密码错误 → 400
    r = await client.post(
        "/api/auth/change-password",
        json={"old_password": "bad", "new_password": "new123456"},
        headers=headers,
    )
    assert r.status_code == 400

    # 正确改密
    r = await client.post(
        "/api/auth/change-password",
        json={"old_password": "old123456", "new_password": "new123456"},
        headers=headers,
    )
    assert r.status_code == 200

    # 旧密码登录失败，新密码成功
    assert (await client.post("/api/auth/login", json={"username": "bob", "password": "old123456"})).status_code == 400
    assert (await client.post("/api/auth/login", json={"username": "bob", "password": "new123456"})).status_code == 200


async def test_unauthorized_401(client):
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await client.get("/api/sessions")).status_code == 401


async def test_invalid_token_401(client):
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert r.status_code == 401
