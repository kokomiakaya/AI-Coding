"""引用解析与校验单元测试。"""
from app.services.rag.citations import build_sources, extract_citation_numbers
from app.services.rag.hybrid import RetrievedChunk


def _chunk(i: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=i, document_id=1, document_name="商品说明.pdf", content=f"内容{i}", score=0.8
    )


def test_extract_numbers():
    assert extract_citation_numbers("见 [1] 和 [2][3] 与【4】") == {1, 2, 3, 4}
    assert extract_citation_numbers("没有引用的回答") == set()
    assert extract_citation_numbers("价格 99[元]") == set()


def test_build_sources_marks_cited():
    chunks = [_chunk(1), _chunk(2)]
    sources, no_citation = build_sources(chunks, "答案是 42 [2]")
    assert [s["index"] for s in sources] == [1, 2]
    assert sources[0]["cited"] is False
    assert sources[1]["cited"] is True
    assert no_citation is False


def test_out_of_range_rejected():
    """越界/伪造编号不应出现在 sources 的 cited 标记中（引用校验）。"""
    chunks = [_chunk(1)]
    sources, no_citation = build_sources(chunks, "见 [1] 与伪造的 [9]")
    assert sources[0]["cited"] is True
    assert no_citation is False


def test_no_citation_flag():
    chunks = [_chunk(1)]
    _, no_citation = build_sources(chunks, "没有引用任何片段的回答")
    assert no_citation is True


def test_sources_structure_complete():
    chunks = [RetrievedChunk(chunk_id=7, document_id=3, document_name="a.pdf", content="x" * 300, page=2, score=0.55)]
    sources, _ = build_sources(chunks, "见 [1]")
    s = sources[0]
    assert s["excerpt"] == "x" * 200  # excerpt 截断 200 字
    assert s["content"] == "x" * 300  # 完整内容保留（前端展开用）
    assert s["page"] == 2
    assert s["relevance_score"] == 0.55
