"""メールファイル(.txt)の解析。ヘッダ行、空行、本文の順を前提とする。"""
from __future__ import annotations

import re
from pathlib import Path

_ADDR = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def parse_mail(text: str) -> tuple[dict[str, str], str]:
    headers: dict[str, str] = {}
    lines = text.splitlines()
    body_start = len(lines)
    for i, line in enumerate(lines):
        if line.strip() == "":
            body_start = i + 1
            break
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    body = "\n".join(lines[body_start:]).lstrip("\n")
    return headers, body


def read_mail(path: Path) -> tuple[dict[str, str], str]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"成果物がありません: {path.name}")
    return parse_mail(path.read_text(encoding="utf-8"))


def addresses(value: str) -> set[str]:
    return {m.lower() for m in _ADDR.findall(value or "")}
