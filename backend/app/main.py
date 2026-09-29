"""FastAPI 应用入口：服务装配、中间件、路由注册。

启动流程：日志 → 建库（含 FTS5 与 admin 种子）→ 构建服务（LLM/嵌入/重排/向量库）
→ 摄取 worker（含崩溃恢复）。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import admin, auth, chat, documents, health, kb, sessions, users
from app.core.logging import setup_logging
from app.db.init import init_db
from app.middleware.timing import TimingMiddleware
from app.services.container import build_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("========== 服务启动中 ==========")
    await init_db()
    services = build_services()
    app.state.services = services
    await services.start()
    logger.info("========== 服务启动完成，请访问 http://127.0.0.1:8000 ==========")
    yield
    await services.stop()
    logger.info("========== 服务已关闭 ==========")


app = FastAPI(
    title="电商知识库问答系统",
    description="基于 LangChain 的 RAG 企业级知识库问答系统（毕业设计）",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS：Vite 开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimingMiddleware)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(kb.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(admin.router)
