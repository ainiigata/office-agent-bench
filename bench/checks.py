"""チェック項目の実行と JSON 出力。タスク固有の知識は持たない。"""
from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Callable

CheckFn = Callable[[], tuple[bool, str]]
CheckSpec = tuple[str, str, CheckFn]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_checks(checks: list[CheckSpec]) -> list[dict]:
    results = []
    for check_id, name, fn in checks:
        try:
            passed, detail = fn()
        except Exception as e:  # noqa: BLE001 — 成果物の欠損や破損は不合格として扱う
            passed, detail = False, f"例外: {e}"
            if not isinstance(e, (FileNotFoundError, ValueError, KeyError)):
                detail += " / " + traceback.format_exc().splitlines()[-1]
        results.append({"id": check_id, "name": name, "pass": bool(passed), "detail": detail or ""})
    return results


def main(checks: list[CheckSpec]) -> None:
    print(json.dumps(run_checks(checks), ensure_ascii=False, indent=2))


def norm(value) -> str:
    if value is None:
        return ""
    return str(value).replace("　", "").replace(" ", "").strip()


def approx(a, b, tol: float = 1) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def load_workbook_safe(path: Path, data_only: bool = True):
    import openpyxl

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"成果物がありません: {path.name}")
    return openpyxl.load_workbook(path, data_only=data_only)
