"""系统配置服务：DB 覆盖 + 默认值 + TTL 缓存（管理页修改后缓存失效即时生效）。"""
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.config import get_settings
from app.models import SystemConfig
from app.services.rag import prompts

# 配置项白名单：key -> (默认值, 描述)。管理页展示与校验都基于此表。
CONFIG_SPECS: dict[str, tuple[Any, str]] = {
    "prompt.system": (prompts.DEFAULT_SYSTEM_PROMPT, "问答生成系统提示词模板"),
    "prompt.rewrite": (prompts.DEFAULT_REWRITE_PROMPT, "查询改写提示词模板"),
    "prompt.no_context": (prompts.DEFAULT_NO_CONTEXT_PROMPT, "检索无结果时的分流提示词（闲聊回答/商品问题兜底）"),
    "chat.fallback_answer": (prompts.DEFAULT_FALLBACK_ANSWER, "检索无结果时的兜底回答话术"),
    "chat.history_max_turns": (6, "多轮对话携带的历史轮数"),
    "retrieval.top_k": (5, "最终送入大模型的片段数（全局默认，知识库可覆盖）"),
    "retrieval.candidates": (20, "RRF 融合后送入重排的候选数"),
    "retrieval.score_threshold": (0.5, "重排相关性分数阈值（低于阈值走闲聊分流/兜底，防幻觉）"),
    "model.chat": (get_settings().chat_model, "对话模型名"),
    "model.embedding": (get_settings().embedding_model, "嵌入模型名"),
    "model.rerank": (get_settings().rerank_model, "重排模型名"),
    "upload.max_size_mb": (get_settings().upload_max_size_mb, "上传文件大小上限（MB）"),
}

_CACHE_PREFIX = "cfg:"


async def get_config(db: AsyncSession, key: str) -> Any:
    """读取配置（缓存优先）：DB 覆盖值，否则默认值。"""
    cached = cache.get(_CACHE_PREFIX + key)
    if cached is not None:
        return cached
    spec = CONFIG_SPECS.get(key)
    if spec is None:
        raise KeyError(f"未知配置项：{key}")
    default, _ = spec
    row = await db.get(SystemConfig, key)
    value = row.value if row else default
    cache.set(_CACHE_PREFIX + key, value)
    return value


async def get_all_configs(db: AsyncSession) -> list[dict]:
    """全部配置项（默认值 + 当前生效值 + 描述），供管理页展示。"""
    rows = (await db.execute(select(SystemConfig))).scalars().all()
    overrides = {r.key: r.value for r in rows}
    return [
        {"key": key, "default": default, "value": overrides.get(key, default), "description": desc}
        for key, (default, desc) in CONFIG_SPECS.items()
    ]


async def set_configs(db: AsyncSession, updates: dict[str, Any], admin_id: int) -> None:
    """批量更新配置（白名单校验），缓存失效即时生效（配置中心思想）。"""
    for key, value in updates.items():
        if key not in CONFIG_SPECS:
            raise KeyError(f"未知配置项：{key}")
        row = await db.get(SystemConfig, key)
        if row is None:
            db.add(
                SystemConfig(
                    key=key, value=value, updated_by=admin_id, description=CONFIG_SPECS[key][1]
                )
            )
        else:
            row.value = value
            row.updated_by = admin_id
    await db.commit()
    cache.invalidate_prefix(_CACHE_PREFIX)
    logger.info(f"系统配置已热更新：{list(updates.keys())}")
