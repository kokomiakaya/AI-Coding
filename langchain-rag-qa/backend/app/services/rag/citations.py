"""引用解析与校验：提取回答中的 [n]/【n】编号，校验范围并构造 sources 结构。

越界/伪造编号直接剔除（防幻觉机制的一部分，论文"引用覆盖率"统计素材）。
"""
import re

from loguru import logger

from app.services.rag.hybrid import RetrievedChunk

CITE_PATTERN = re.compile(r"\[(\d{1,2})\]|【(\d{1,2})】")


def extract_citation_numbers(text: str) -> set[int]:
    """提取回答中出现的全部引用编号。"""
    nums: set[int] = set()
    for m in CITE_PATTERN.finditer(text):
        nums.add(int(m.group(1) or m.group(2)))
    return nums


def build_sources(
    chunks: list[RetrievedChunk], answer: str, start_index: int = 1
) -> tuple[list[dict], bool]:
    """构造 sources 数组并标记 cited。

    返回 (sources, no_citation)：
    - sources 包含全部检索片段，cited 标记该片段编号是否真实出现在回答中；
    - no_citation=True 表示回答未引用任何片段（引用覆盖率统计用）。
    """
    cited = extract_citation_numbers(answer)
    valid = {n for n in cited if start_index <= n < start_index + len(chunks)}
    invalid = cited - valid
    if invalid:
        logger.warning(f"回答中出现越界引用编号 {sorted(invalid)}，已剔除")

    sources = []
    for i, chunk in enumerate(chunks, start=start_index):
        sources.append(
            {
                "index": i,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "excerpt": chunk.content[:200],
                "content": chunk.content[:500],  # 完整分块文本（前端"查看原文"展开用）
                "page": chunk.page,
                "sheet": chunk.sheet,
                "row": chunk.row,
                "relevance_score": round(chunk.score, 4),
                "cited": i in valid,
            }
        )
    no_citation = not any(s["cited"] for s in sources)
    return sources, no_citation
