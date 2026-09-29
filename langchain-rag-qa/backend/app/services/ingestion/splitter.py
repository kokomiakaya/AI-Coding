"""分块与中文分词：中文分隔符递归切分 + jieba 搜索模式分词（FTS5 索引源数据）。"""
import jieba
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 中文感知分隔符：从大到小递归切分，句子边界优先
CHINESE_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]


def make_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        separators=CHINESE_SEPARATORS,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        keep_separator=False,
    )


def split_pages(pages: list[dict], chunk_size: int, chunk_overlap: int) -> list[dict]:
    """逐页切分（保留页码/行号定位信息），返回 [{content, meta}]。"""
    splitter = make_splitter(chunk_size, chunk_overlap)
    result = []
    for page in pages:
        text = page["text"].strip()
        if not text:
            continue
        for piece in splitter.split_text(text):
            result.append({"content": piece, "meta": page["meta"]})
    return result


def tokenize_for_fts(text: str) -> str:
    """jieba 搜索模式分词，空格连接（FTS5 unicode61 按空格切词，实现中文 BM25）。"""
    return " ".join(t.strip() for t in jieba.cut_for_search(text) if t.strip())
