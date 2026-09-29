"""生成器：流式生成 + 提示词拼装 + 离线演示模式。

供应商可切换（OpenAI 兼容协议）：模型名以 deepseek 开头自动走 DeepSeek 密钥与地址，
否则走 DashScope（见 config.chat_api_key/chat_base_url）。
SSE 逐 token 输出（感知延迟优化）；usage 通过回调传出（避免并发共享状态）。
"""
import asyncio
import re

from langchain_openai import ChatOpenAI
from loguru import logger

from app.core.config import get_settings


class Generator:
    def __init__(self) -> None:
        s = get_settings()
        self.mock = s.mock_mode
        self.model_name = s.chat_model
        if not s.chat_api_key:
            # 优雅降级：未配置 Key 时服务仍可启动（摄取/检索/管理可用），问答接口明确报错
            logger.warning("未配置对话模型 API Key（.env 中 DEEPSEEK_API_KEY 为空），问答功能暂不可用")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model=s.chat_model,
                api_key=s.chat_api_key,
                base_url=s.chat_base_url,
                temperature=0.3,
                streaming=True,
                request_timeout=60,
                max_retries=2,
            )

    def build_messages(
        self, system_prompt: str, context: str, history: list[dict], question: str
    ) -> list[dict]:
        """构造消息：系统提示 + 历史对话 + 带编号参考资料的问题。"""
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})
        user_content = (
            question if not context else f"参考资料：\n{context}\n\n用户问题：{question}"
        )
        messages.append({"role": "user", "content": user_content})
        return messages

    async def stream(
        self, messages: list[dict], usage_out: dict | None = None
    ):
        """逐 token 产出文本；结束后把 usage 统计写入 usage_out（如有）。"""
        if self.mock:
            async for token in self._mock_stream(messages, usage_out):
                yield token
            return
        if self.llm is None:
            raise RuntimeError("未配置对话模型 API Key（.env 中 DEEPSEEK_API_KEY 为空），请配置后重启服务")
        async for chunk in self.llm.astream(messages):
            text = chunk.content if isinstance(chunk.content, str) else ""
            if text:
                yield text
            if getattr(chunk, "usage_metadata", None) and usage_out is not None:
                usage_out["prompt_tokens"] = chunk.usage_metadata.get("input_tokens", 0)
                usage_out["completion_tokens"] = chunk.usage_metadata.get("output_tokens", 0)

    async def _mock_stream(self, messages: list[dict], usage_out: dict | None) -> None:
        """离线演示模式：基于参考资料生成带引用的确定性回答；无参考资料时给出闲聊式回答。"""
        last = messages[-1]["content"]
        nums = re.findall(r"^\[(\d+)\]", last, flags=re.M)
        if not nums:
            # 检索无结果的分流路径（如"你是什么模型"）
            answer = (
                f"（离线演示模式）我是基于 {self.model_name} 大模型与 LangChain RAG 技术构建的"
                "电商知识库客服助手。关于商品的具体问题，我会优先从知识库中检索答案并标注引用来源。"
            )
        else:
            cites = "".join(f"[{n}]" for n in nums[:3])
            context_part = re.sub(r"用户问题：.*$", "", last, flags=re.S)
            answer = (
                f"（离线演示模式）根据知识库参考资料，为您整理如下{cites}：\n\n"
                f"{context_part.strip()[:300]}"
            )
        if usage_out is not None:
            usage_out["prompt_tokens"] = len(last)
            usage_out["completion_tokens"] = len(answer)
        for i in range(0, len(answer), 12):
            yield answer[i : i + 12]
            await asyncio.sleep(0.01)  # 模拟流式节奏
