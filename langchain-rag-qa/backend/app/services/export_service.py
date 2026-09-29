"""会话导出：Markdown 格式（含引用来源清单），支持下载留存。"""
from app.models import ChatSession, Message


def _loc_text(source: dict) -> str:
    parts = []
    if source.get("page"):
        parts.append(f"第 {source['page']} 页")
    if source.get("sheet"):
        parts.append(f"工作表 {source['sheet']}")
    if source.get("row"):
        parts.append(f"第 {source['row']} 行")
    return "，".join(parts)


def build_markdown(session: ChatSession, messages: list[Message]) -> str:
    lines = [f"# 会话：{session.title}", "", f"- 创建时间：{session.created_at}", ""]
    for m in messages:
        role = "用户" if m.role == "user" else "助手"
        lines.append(f"## {role}")
        lines.append("")
        lines.append(m.content or "")
        if m.sources:
            lines.append("")
            lines.append("**引用来源：**")
            for s in m.sources:
                loc = _loc_text(s)
                suffix = f"，{loc}" if loc else ""
                lines.append(
                    f"- [{s.get('index')}] {s.get('document_name')}{suffix}"
                    f"（相关度 {s.get('relevance_score', 0)}）"
                )
        lines.append("")
    return "\n".join(lines)
