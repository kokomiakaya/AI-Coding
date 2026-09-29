"""pytest 公共配置：离线模式（MOCK_MODE）+ 独立临时数据库，无需真实 API Key 即可跑。

说明：环境变量必须在导入 app 之前设置（pydantic-settings 环境变量优先于 .env）。
"""
import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="ragkb_test_")
os.environ["MOCK_MODE"] = "1"
os.environ["RATE_LIMIT_DISABLED"] = "1"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/test.db"
os.environ["CHROMA_PERSIST_DIR"] = f"{_TMP}/chroma"
os.environ["UPLOAD_DIR"] = f"{_TMP}/uploads"
os.environ["LOG_DIR"] = f"{_TMP}/logs"
os.environ["DASHSCOPE_API_KEY"] = "test-key"
os.environ["DEEPSEEK_API_KEY"] = "test-key"  # 默认 chat_model 为 deepseek-chat，openai 客户端构造即校验 key

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def client():
    """带 lifespan 的应用测试客户端（建库 + 种子 + 摄取 worker 启动）。"""
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture(scope="session")
async def admin_headers(client):
    r = await client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest_asyncio.fixture(scope="session")
async def user_headers(client):
    await client.post(
        "/api/auth/register", json={"username": "testuser", "password": "test123456"}
    )
    r = await client.post(
        "/api/auth/login", json={"username": "testuser", "password": "test123456"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def create_kb_with_doc(client, admin_headers, name: str, content: str, filename="说明.txt") -> int:
    """测试辅助：建库 + 上传一份文本 + 等待摄取完成，返回 kb_id。"""
    import asyncio

    r = await client.post("/api/kb", json={"name": name}, headers=admin_headers)
    assert r.status_code == 201, r.text
    kb_id = r.json()["id"]
    files = {"files": (filename, content.encode("utf-8"))}
    r = await client.post(f"/api/kb/{kb_id}/documents", files=files, headers=admin_headers)
    assert r.status_code == 200, r.text
    doc_id = r.json()["items"][0]["id"]
    for _ in range(80):  # 等待后台 worker 摄取完成（mock 嵌入，很快）
        d = (await client.get(f"/api/documents/{doc_id}", headers=admin_headers)).json()
        if d["status"] in ("ready", "failed"):
            break
        await asyncio.sleep(0.25)
    assert d["status"] == "ready", f"摄取失败：{d.get('error_message')}"
    return kb_id
