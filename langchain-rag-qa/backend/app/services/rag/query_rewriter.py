"""查询改写：结合会话历史把问题改写为独立检索查询。

多轮对话中用户常使用指代词（"它多少钱"），直接检索效果差；
改写补全指代对象可显著提升检索命中率（论文消融实验素材）。失败自动降级为原问题。
"""
from loguru import logger
from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.services.rag import prompts


class QueryRewriter:
    def __init__(self) -> None:
        s = get_settings()
        self.mock = s.mock_mode
        if not s.chat_api_key:
            # 优雅降级：未配置 Key 时跳过改写（直接降级用原问题）
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model=s.chat_model,
                api_key=s.chat_api_key,
                base_url=s.chat_base_url,
                temperature=0.1,
                request_timeout=15,
                max_retries=1,
            )

    async def rewrite(
        self, question: str, history: list[dict], template: str | None = None
    ) -> str:
        """返回改写后的查询；无历史、未配置 Key、离线模式或任何异常时降级返回原问题。"""
        if self.mock or not history or self.llm is None:
            return question
        template = template or prompts.DEFAULT_REWRITE_PROMPT
        try:
            hist_text = "\n".join(
                f"{'用户' if h['role'] == 'user' else '助手'}：{h['content'][:500]}" for h in history
            )
            resp = await self.llm.ainvoke(
                [
                    {"role": "system", "content": template},
                    {
                        "role": "user",
                        "content": f"对话历史：\n{hist_text}\n\n最新问题：{question}\n改写结果：",
                    },
                ]
            )
            rewritten = (resp.content or "").strip()
            return rewritten if rewritten else question
        except Exception as exc:
            logger.warning(f"查询改写失败，降级使用原问题：{exc}")
            return question
