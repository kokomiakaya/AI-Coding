"""混合检索基础单元测试：RRF 融合与中文分词。"""
from app.services.rag.hybrid import RRF_K, rrf_fuse, tokenize
from app.vectorstore.base import VectorHit


def test_rrf_fuse_both_lists():
    """两路都命中的 chunk 分数最高。"""
    hits = [VectorHit(chunk_id=1, similarity=0.9), VectorHit(chunk_id=2, similarity=0.5)]
    rows = [{"id": 2}, {"id": 3}]
    scores = rrf_fuse(hits, rows)
    assert scores[2] > scores[1]
    assert scores[2] > scores[3]
    # 单路首名 = 1/(K+1)
    assert abs(scores[1] - 1.0 / (RRF_K + 1)) < 1e-9


def test_rrf_fuse_empty():
    assert rrf_fuse([], []) == {}


def test_tokenize_chinese():
    tokens = tokenize("星耀X1电池容量是多少")
    assert len(tokens) >= 3
    assert all(tokens)
    assert tokens == [t.lower() for t in tokens]
