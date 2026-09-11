"""各タスクのチェッカーが「模範成果物なら全項目 pass」「未着手なら全項目 pass にはならない」ことを確認する。

使い方: python3 tools/selftest.py [TASK_ID ...]
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.score import run_checker  # noqa: E402


def build_run_dir(task_dir: Path, dest: Path, with_expected: bool) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    src_input = task_dir / "input"
    if src_input.exists():
        shutil.copytree(src_input, dest, dirs_exist_ok=True)
    if (task_dir / "task.md").exists():
        shutil.copy2(task_dir / "task.md", dest / "task.md")
    if with_expected:
        for p in (task_dir / "expected").rglob("*"):
            if p.is_dir() or p.name == "values.json":
                continue
            target = dest / p.relative_to(task_dir / "expected")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    return dest


def run_selftest(root: Path, task_ids: list[str] | None = None) -> list[dict]:
    root = Path(root)
    tasks = sorted(p.parent for p in root.glob("tasks/*/check.py"))
    if task_ids:
        tasks = [t for t in tasks if t.name in task_ids]
    reports = []
    for task in tasks:
        report = {"task_id": task.name, "expected_all_pass": False, "untouched_not_all_pass": False,
                  "expected_failures": [], "error": None}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                good = build_run_dir(task, Path(tmp) / "2000-01-01-selftest" / task.name, with_expected=True)
                items = run_checker(root, task.name, good)
                report["expected_failures"] = [i["name"] for i in items if not i["pass"]]
                report["expected_all_pass"] = bool(items) and not report["expected_failures"]
                bare = build_run_dir(task, Path(tmp) / "2000-01-02-selftest" / task.name, with_expected=False)
                items = run_checker(root, task.name, bare)
                report["untouched_not_all_pass"] = any(not i["pass"] for i in items)
        except RuntimeError as e:
            report["error"] = str(e)
        reports.append(report)
    return reports


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="チェッカーの健全性確認")
    ap.add_argument("task_ids", nargs="*")
    ap.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    reports = run_selftest(Path(args.root), args.task_ids or None)
    if not reports:
        print("check.py を持つタスクがありません")
        return 1
    bad = 0
    for r in reports:
        ok = r["expected_all_pass"] and r["untouched_not_all_pass"] and r["error"] is None
        bad += not ok
        line = f"{'OK' if ok else 'NG'} {r['task_id']}"
        if r["error"]:
            line += f" — 実行エラー: {r['error'].splitlines()[0]}"
        elif not r["expected_all_pass"]:
            line += f" — 模範成果物で不合格: {', '.join(r['expected_failures']) or '項目なし'}"
        elif not r["untouched_not_all_pass"]:
            line += " — 未着手でも全項目合格(チェックが甘い)"
        print(line)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
