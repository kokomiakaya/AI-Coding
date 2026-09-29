# 基于 LangChain 的企业级 RAG 知识库问答系统（电商商品知识问答）

毕业设计项目：面向电商平台商品知识库的检索增强生成（RAG）问答系统。
用户通过浏览器进行知识库问答（回答引用知识库片段）；管理员负责知识库维护。

## 功能特性

### 用户端
- 注册 / 登录 / 修改密码（JWT + bcrypt）
- 多用户多会话：每个用户独立会话列表，支持新建/重命名/删除/搜索/导出 Markdown
- 会话持久化：不同时间登录都能找回历史对话（分页加载历史消息）
- 知识库问答：SSE 流式输出，回答中 [n] 引用角标可点击定位到来源卡片
- 来源卡片：显示文档名、页码/行号、相关性分数、摘要与完整分块原文
- 多轮对话：结合历史自动改写查询（指代消解）
- 答案反馈：点赞/点踩（进入管理端满意度统计）
- 防幻觉：检索分数低于阈值时不调用大模型，直接返回兜底话术

### 管理端（仅 admin / 123456）
- 知识库管理：多知识库 CRUD、分块/检索参数按库可配、启用停用
- 文档管理：多文件上传（PDF/DOCX/TXT/MD/XLSX/CSV）、后台异步解析入库、
  状态实时刷新、失败重试（re-embed 幂等重建）、分块预览、删除
- 检索调试：只跑检索不生成，对比混合检索与重排两阶段结果（答辩演示神器）
- 用户管理：搜索、禁用/启用（即时踢出）、角色调整
- 统计看板：KPI 卡片、问答量/Token 消耗趋势、反馈满意度、知识库分布（ECharts）
- 系统配置：提示词模板、检索参数、模型名热更新（免发版调优）

### 企业级优化（论文素材）
| 优化项 | 实现 |
|---|---|
| 混合检索 | Chroma HNSW 向量检索 + SQLite FTS5 中文 BM25（jieba 分词），RRF 融合 |
| 重排精排 | 两阶段检索（粗排→精排）：本地混合分数重排 / qwen3-rerank 可切换，失败自动降级 |
| 流式输出 | SSE 逐 token 输出，记录分阶段耗时（改写/检索/重排/生成） |
| 异步摄取 | asyncio 队列 + worker 协程 + 批量嵌入 + 并发信号量 + 崩溃恢复 |
| 缓存抽象 | TTLCache 进程内缓存（配置/嵌入），预留 Redis 接口 |
| 限流 | 内存滑动窗口（登录 5 次/分/IP、问答 20 次/分/用户），预留分布式限流 |
| 防幻觉 | 重排阈值过滤 + 空结果兜底 + 引用编号校验（越界剔除） |
| 安全 | bcrypt + JWT + RBAC + 禁用即时生效 + 文件类型/大小校验 + DOMPurify XSS 消毒 |
| 可观测 | loguru 结构化日志 + 请求计时中间件 + token 用量统计 |
| 存储可插拔 | 向量库/缓存/限流三抽象层，生产可切换 PG+pgvector/Redis/Milvus |
| 前端优化 | 路由懒加载、构建分包（vendor 拆分）、消息分页 |

## 技术栈

- **后端**：Python 3.14 + FastAPI + LangChain + SQLAlchemy(async) + aiosqlite
- **大模型**：DeepSeek（OpenAI 兼容模式接入，供应商可切换：改 `.env` 即可切回通义千问）
  - 对话 `deepseek-chat` · 嵌入 `BAAI/bge-small-zh-v1.5`（本地 ONNX，512 维，免费离线）
  - 重排：本地混合分数（向量相似度 + BM25 加成）· 可切换 `qwen3-rerank`（需百炼额度）
- **数据库**：SQLite（WAL + FTS5 中文全文检索）
- **向量库**：Chroma（本地持久化，HNSW 索引；可回退 FAISS）
- **前端**：Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts
- **无 Docker、无 Redis、无外部服务**，pip + npm 安装即可跑

## 快速开始

### 0. 前置条件
- Python 3.10+（本项目在 3.14 验证）、Node.js 18+
- DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com/) 申请）
- 嵌入与重排为本地模型，无需额外 Key；首次启动自动下载 BGE 嵌入模型
  （国内网络可先设 `HF_ENDPOINT=https://hf-mirror.com` 再启动）

### 1. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`（其余保持默认）。
切换供应商：`CHAT_MODEL=qwen-plus` 并配 `DASHSCOPE_API_KEY`；嵌入/重排可设
`EMBEDDING_PROVIDER=dashscope` / `RERANK_PROVIDER=dashscope` 切回百炼（维度变化后
需运行 `scripts/rebuild_vectors.py` 重建向量）。

```bash
scripts\run_backend.bat           # 或：.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

启动时自动建库（含 FTS5 全文检索与管理员账号 **admin / 123456**）。
验证：浏览器打开 http://127.0.0.1:8000/api/health 应返回全部 ok。

### 2. 前端

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

### 3. 演示数据（可选）

```bash
backend\.venv\Scripts\python scripts\generate_sample_docs.py   # 生成 3 份商品演示文档
```

用 admin 登录 → 管理后台 → 知识库管理 → 新建知识库 → 上传 `scripts/sample_docs/` 下的文件。

## 项目结构

```
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # REST 接口（auth/users/kb/documents/chat/sessions/admin/health）
│   │   ├── core/            # 配置/安全/缓存/限流/日志
│   │   ├── db/              # 引擎/建库初始化（含 FTS5 与触发器）
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 校验
│   │   ├── services/
│   │   │   ├── rag/         # RAG 链路：改写/混合检索/重排/生成/引用校验/总编排
│   │   │   └── ingestion/   # 异步摄取：解析/切分/嵌入/worker
│   │   ├── vectorstore/     # 向量库抽象（Chroma / FAISS 回退）
│   │   └── middleware/      # 计时中间件
│   └── tests/               # pytest 测试（30 个用例，离线模式无需 API Key）
├── frontend/                # Vue3 SPA
│   └── src/
│       ├── views/           # 聊天页 + 管理后台 5 个页面
│       ├── components/      # 会话侧栏/消息/引用卡片/反馈等
│       └── api/             # Axios 封装 + SSE 流解析
├── scripts/                 # 启动脚本/建库脚本/演示数据生成/E2E 自测
└── docs/                    # 架构文档与论文素材
```

## 测试

```bash
cd backend
.venv\Scripts\python -m pytest tests/ -v        # 30 个用例（离线模式，无需 API Key）
.venv\Scripts\python ..\scripts\e2e_test.py     # 端到端真实 API 自测（需后端已启动）
```

## 接口文档

启动后访问 http://127.0.0.1:8000/docs （FastAPI 自动生成的 Swagger 文档）。

## 安全说明

- API Key 只存本地 `backend/.env`，已被 `.gitignore` 排除，请勿提交或截图外泄
- 演示账号 admin/123456 仅用于本机演示，生产需修改密码并强制密钥轮换
- 离线演示模式：`.env` 中 `MOCK_MODE=1` 时 LLM/嵌入/重排返回确定性假数据，无网络也能演示

## 论文写作建议

- 检索质量：混合检索 vs 单路检索 Recall@k 对照（`search-test` 接口取数）
- 多轮效果：`rewrite_enabled` 开关消融实验
- 性能：`messages.meta` 记录了改写/检索/重排/生成分阶段耗时与 token 用量
- 架构演进：向量库/缓存/限流抽象层的可插拔设计（SQLite+Chroma → PG+Redis 演进路径）
