"""docx から段落と表セルの文字列を順に取り出す。"""
from __future__ import annotations

from pathlib import Path


def docx_text(path: Path) -> str:
    from docx import Document

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"成果物がありません: {path.name}")
    doc = Document(str(path))
    parts: list[str] = []
    # 段落と表を文書内の出現順に辿る
    for block in doc.element.body.iterchildren():
        tag = block.tag.rsplit("}", 1)[-1]
        if tag == "p":
            parts.append("".join(t.text or "" for t in block.iter() if t.tag.endswith("}t")))
        elif tag == "tbl":
            for t in block.iter():
                if t.tag.endswith("}p"):
                    parts.append("".join(x.text or "" for x in t.iter() if x.tag.endswith("}t")))
    return "\n".join(parts)
