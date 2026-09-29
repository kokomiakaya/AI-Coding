# 系统架构设计文档（论文素材）

## 1. 总体架构

```
┌──────────────────────── 浏览器 SPA（Vue3 + TS + Element Plus）──────────────────────┐
│  登录/注册 │ 聊天页（会话侧栏 + SSE 流式回答 + 引用卡片） │ 管理后台（5 个页面）        │
└───────────────────────────────────┬──────────────────────────────────────────────────┘
                                    │ HTTP / SSE（Vite 开发代理，Nginx 生产反代需关闭缓冲）
┌───────────────────────────────────▼──────────────────────────────────────────────────┐
│  FastAPI 后端（uvicorn 单进程）                                                       │
│  ├─ 中间件链：CORS → 请求计时(request_id/耗时) → JWT 鉴权 → 限流（滑动窗口）           │
│  ├─ API 层：auth / users / kb / documents / chat / sessions / admin / health          │
│  ├─ 服务层：RAG 管线（编排）· 摄取管道（异步）· 配置/统计/导出                          │
│  ├─ 抽象层：VectorStore（Chroma/FAISS）· CacheBackend（TTLCache）· RateLimiter（内存） │
│  └─ 数据层：SQLAlchemy async + aiosqlite（WAL）+ chromadb PersistentClient             │
└───────┬──────────────────────────────────────────┬───────────────────────────────────┘
        │ SQLite（WAL）                              │ httpx（连接复用）
┌───────▼───────────────────────┐   ┌───────────────▼───────────────────────────────────┐
│ SQLite：users / kb / documents │   │ DeepSeek（OpenAI 兼容模式）                          │
│   chunks(+FTS5 中文 BM25) /    │   │  deepseek-chat（对话+查询改写，流式）                │
│   sessions / messages / configs│   │ 本地嵌入：BGE-small-zh（fastembed/ONNX，512 维）    │
│ Chroma：每 KB 一个 collection  │   │ 本地重排：向量相似度+BM25 加成混合分数              │
│   （HNSW 索引，cosine 距离）    │   │ （DashScope 欠费降级，充值后可切回 Qwen 全套）       │
└───────────────────────────────┘
```

三条数据流主线：

1. **摄取流**：上传 → 校验落盘 → documents 行(pending) → asyncio 队列 → worker 协程
   解析（5 类 loader）→ 中文分隔符切分 → jieba 分词 → 批量嵌入 → 写 chunks（FTS5 触发器
   同步）→ 写 Chroma 向量 → ready；前端 2s 轮询状态。
2. **问答流**：问题 → 查询改写（历史压缩）→ 双路检索（向量 top-50 + BM25 top-30）
   → RRF 融合 top-20 → 重排精排（qwen3-rerank 或本地混合分数）→ 阈值过滤 → 提示词生成
   （[n] 引用约束）→ SSE 流式输出 → 引用校验落库（sources + 分阶段耗时）。
3. **统计流**：messages 聚合（按天/按 KB/反馈），token 来自上游 usage 实时落库。

## 2. 核心设计决策

| 决策点 | 方案 | 理由 |
|---|---|---|
| 模型接入 | OpenAI 兼容模式 + langchain-openai | 供应商可插拔（DeepSeek/Qwen 切换只改 .env，按模型名前缀自动选密钥与地址）；嵌入支持本地 BGE（fastembed/ONNX）与云端两套实现，重排支持本地混合分数与专用重排模型两套实现 |
| 混合检索 | Chroma HNSW(cosine) + SQLite FTS5 中文 BM25 | 语义与关键词互补；FTS5 外部内容表 + jieba 预分词（unicode61 空格切词），无需 ES/自建倒排 |
| 融合方式 | RRF（k=60） | 两路分数尺度不可比时无需归一化调参 |
| 两阶段检索 | 融合 top-20 → 重排 top-k → 阈值过滤 | 粗排保召回、精排保精度；阈值过滤实现防幻觉兜底 |
| 向量真源 | SQLite chunks 表为唯一真源，Chroma 可幂等重建 | 崩溃一致性：先写 SQLite 后写向量，恢复时按状态机重建 |
| 异步摄取 | asyncio.Queue + 2 worker + Semaphore(4) + 批量嵌入 | 无消息队列的轻量方案；上传秒回；崩溃恢复扫描中间状态 |
| 流式交互 | POST + SSE（fetch 流解析） | EventSource 仅支持 GET；X-Accel-Buffering: no 防代理缓冲 |
| 引用机制 | 提示词约束 [n] 编号 → 正则解析 → 越界剔除 → cited 标记 | 引用覆盖率可统计（meta.no_citation），防伪造编号 |

## 3. 数据库设计

7 张表 + 1 个 FTS5 虚表（见 README/模型定义），关键点：

- 时间戳统一 UTC ISO8601 文本（同格式可直接字符串排序）
- `chunks.content_tokens`：jieba 搜索模式分词结果，FTS5 external content 模式
  + 3 个同步触发器（INSERT/DELETE/UPDATE）自动维护索引
- `messages.sources`：JSON 引用数组（index/chunk_id/文档名/页行定位/相关度/cited）
- `messages.meta`：JSON 分阶段耗时与降级标记（改写/检索/重排/LLM 毫秒、fallback、
  no_citation、rewritten_query）——性能章节数据直接取这里
- WAL + busy_timeout=5000 + foreign_keys=ON（连接级 PRAGMA）

## 4. RAG 链路细节

```
question + history(6 轮，单条截断 2000 字)
 ① 查询改写：deepseek-chat（温度 0.1），输出独立检索查询；超时/失败降级原问题
 ② 向量路：BGE-small-zh(512，本地 ONNX) → Chroma cosine top-50（每 KB collection，合并）
    BM25 路：jieba(cut_for_search，过滤单字 token) → FTS5 MATCH("词1" OR "词2"…) → bm25() top-30
 ③ RRF：score = Σ 1/(60+rank)（rank 1 起）
 ④ 重排：本地混合分数 = 0.65×向量相似度 + 0.35×BM25 排名加成（top_n=2×top_k）；
    RERANK_PROVIDER=dashscope 时改用 qwen3-rerank，失败自动降级本地
 ⑤ 过滤：relevance ≥ KB.score_threshold → 取 KB.top_k（默认 5）
 ⑥ 兜底：空结果走闲聊分流提示词（闲聊直接答、商品问题不编造）
 ⑦ 生成：system 模板 + [n] 编号上下文 + 历史 + 问题 → deepseek-chat stream（温度 0.3）
 ⑧ 校验：[n]/【n】正则解析 → 越界剔除并告警 → sources（cited 标记）→ 落库
```

SSE 事件协议：`meta → delta* → sources → usage → done`（异常时 `error`）。
前端渲染：markdown-it + 角标替换 + DOMPurify 消毒；角标点击 → 来源卡片滚动高亮。

## 5. 可演进架构（预留扩展）

- **向量库**：`BaseVectorStore` 接口（upsert/delete/search/health），当前 Chroma，
  生产切换 PG+pgvector 或 Milvus 仅需新实现一个类
- **缓存**：`CacheBackend` 接口（TTLCache 实现），Redis 实现约 30 行
- **限流**：`RateLimiter` 接口（内存滑动窗口），Redis 分布式限流同理
- **消息队列**：摄取 worker 与 API 通过 asyncio.Queue 解耦，可替换 arq/Celery+Redis
- **部署**：Nginx 反代需 `proxy_buffering off`（SSE）；前端 `vite build` 产物可托管任意静态服务

## 6. 性能优化清单（论文实验设计）

| 优化项 | 实验指标 | 数据来源 |
|---|---|---|
| 混合检索 vs 单路 | Recall@k、命中率 | `search-test` 接口 + 构造评测集 |
| 重排前后对比 | 相关性分数分布、top1 命中 | search-test 两阶段结果 |
| 查询改写开关 | 多轮指代问题命中率 | rewrite_enabled 消融 |
| 流式输出 | 首 token 延迟(TTFT)、总耗时 | messages.meta.llm_ms 前后对比 |
| 批量嵌入 | 摄取总耗时 | 批大小 1 vs 16 对照 |
| 缓存 | 命中率、重复查询耗时 | 嵌入缓存/配置缓存开关 |
| 阈值兜底 | 幻觉率（人工标注） | fallback 触发率 + 抽查 |
| 引用覆盖率 | 回答中引用编号占比 | meta.no_citation 统计 |

## 7. 已知局限（论文"局限与展望"章节素材）

- SQLite 单机写入吞吐有限：论文论证"适用中小规模，生产可切换 PG"
- 表格型 PDF/扫描件需 OCR（超出范围）
- 单进程内存限流/缓存在多实例部署下失效（已抽象接口，接 Redis 即可）
- 统计直接聚合业务表，数据量增大后可加物化视图/日表
