"""作業フォルダを作る: runs/<日付>-<エージェント名>/<task-id>/ に input と task.md をコピー。

使い方: python3 tools/prepare.py TASK_ID AGENT [--work-root DIR] [--date YYYY-MM-DD] [--force]

--work-root DIR を付けると DIR/<日付>-<エージェント名>/<task-id>/ に作る(リポジトリ外での作業を推奨)。
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(root: Path, task_id: str, agent: str, date: str | None = None, force: bool = False,
            work_root: Path | None = None) -> Path:
    task = root / "tasks" / task_id
    if not (task / "task.md").exists():
        raise ValueError(f"タスクがありません: {task_id}(tasks/{task_id}/task.md が必要です)")
    date = date or datetime.date.today().isoformat()
    base = Path(work_root) if work_root else root / "runs"
    run_dir = base / f"{date}-{agent}" / task_id
    if run_dir.exists():
        if not force:
            raise FileExistsError(f"作業フォルダが既にあります: {run_dir}(上書きするなら --force)")
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    src = task / "input"
    if src.exists():
        shutil.copytree(src, run_dir, dirs_exist_ok=True)
    shutil.copy2(task / "task.md", run_dir / "task.md")
    return run_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ベンチマークの作業フォルダを作る")
    ap.add_argument("task_id", help="例: excel-01")
    ap.add_argument("agent", help="例: claude-code, codex, claude-code-2")
    ap.add_argument("--work-root", help="作業フォルダを作る場所(既定はリポジトリの runs/)。リポジトリ外を推奨")
    ap.add_argument("--date", help="YYYY-MM-DD(既定は今日)")
    ap.add_argument("--force", action="store_true", help="既存の作業フォルダを消して作り直す")
    ap.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        run_dir = prepare(Path(args.root), args.task_id, args.agent, args.date, args.force,
                          Path(args.work_root).expanduser() if args.work_root else None)
    except (ValueError, FileExistsError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(run_dir)
    print("次の手順: この作業フォルダでエージェントを起動し「task.md を読んで実行して」と頼んでください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
