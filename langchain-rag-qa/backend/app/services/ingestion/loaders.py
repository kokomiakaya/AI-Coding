"""文档解析：按扩展名分发加载器（PDF/DOCX/TXT/MD/XLSX/CSV），返回 [{text, meta}]。

meta 记录来源定位（页码/工作表/行号），支撑回答引用的"第几页/第几行"展示。
"""
import csv
import io
from pathlib import Path


def load_document(file_path: str, file_type: str) -> list[dict]:
    """按文件类型解析，返回 [{text, meta}]。"""
    path = Path(file_path)
    if file_type == "pdf":
        return _load_pdf(path)
    if file_type in ("txt", "md"):
        return _load_text(path)
    if file_type == "docx":
        return _load_docx(path)
    if file_type == "csv":
        return _load_csv(path)
    if file_type == "xlsx":
        return _load_xlsx(path)
    raise ValueError(f"不支持的文件类型：{file_type}")


def _read_text(path: Path) -> str:
    """多编码尝试读取文本文件（中文文档常见 GBK/UTF-8 混用）。"""
    raw = path.read_bytes()
    for encoding in ("utf-8", "gbk", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _plain_meta() -> dict:
    return {"page": None, "sheet": None, "row": None}


def _load_text(path: Path) -> list[dict]:
    text = _read_text(path)
    return [{"text": text, "meta": _plain_meta()}] if text.strip() else []


def _load_pdf(path: Path) -> list[dict]:
    from langchain_community.document_loaders import PyPDFLoader

    docs = PyPDFLoader(str(path)).load()
    result = []
    for d in docs:
        if not d.page_content.strip():
            continue
        # 页码转 1 基（面向用户展示）
        page = (d.metadata.get("page") or 0) + 1
        result.append({"text": d.page_content, "meta": {"page": page, "sheet": None, "row": None}})
    return result


def _load_docx(path: Path) -> list[dict]:
    import docx2txt

    text = docx2txt.process(str(path)) or ""
    return [{"text": text, "meta": _plain_meta()}] if text.strip() else []


def _load_csv(path: Path) -> list[dict]:
    text = _read_text(path)
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    header = [str(c).strip() or f"列{j+1}" for j, c in enumerate(rows[0])]
    result = []
    for i, row in enumerate(rows[1:], start=2):
        cells = [
            f"{header[j]}: {row[j]}"
            for j in range(min(len(header), len(row)))
            if str(row[j]).strip()
        ]
        if cells:
            result.append(
                {"text": "；".join(cells), "meta": {"page": None, "sheet": None, "row": i}}
            )
    return result


def _load_xlsx(path: Path) -> list[dict]:
    """Excel 逐行转"列名: 值"文本（电商商品信息表主场景），meta 记工作表+行号。"""
    import openpyxl

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    result = []
    for ws in wb.worksheets:
        header: list[str] = []
        for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if not header:
                header = [str(c).strip() or f"列{j+1}" for j, c in enumerate(row)]
                continue
            cells = [
                f"{header[j]}: {row[j]}"
                for j in range(len(row))
                if j < len(header) and row[j] not in (None, "")
            ]
            if cells:
                result.append(
                    {"text": "；".join(cells), "meta": {"page": None, "sheet": ws.title, "row": i}}
                )
    return result
