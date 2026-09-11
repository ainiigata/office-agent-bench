"""自動判定を実行し、作業フォルダに result.json と result.md を書く。

使い方: python3 tools/score.py RUN_DIR [--force]

作業フォルダがリポジトリの runs/ の外(prepare.py --work-root)にある場合は、
採点後に runs/<日付>-<エージェント名>/<task-id>/ へまるごとコピーして記録を残す。
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_RUN_PARENT = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")


def run_checker(root: Path, task_id: str, run_dir: Path) -> list[dict]:
    check = root / "tasks" / task_id / "check.py"
    if not check.exists():
        raise RuntimeError(f"チェッカーがありません: tasks/{task_id}/check.py")
    env = dict(os.environ, PYTHONPATH=str(root))
    proc = subprocess.run(
        [sys.executable, str(check), str(run_dir)],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"tasks/{task_id}/check.py が異常終了しました(code {proc.returncode})\n{proc.stderr}")
    try:
        items = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"tasks/{task_id}/check.py の出力が JSON ではありません: {e}\n標準出力: {proc.stdout[:500]}\n標準エラー: {proc.stderr}") from e
    if not isinstance(items, list):
        raise RuntimeError(f"tasks/{task_id}/check.py の出力が配列ではありません")
    return items


def parse_rubric(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line[2:].strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("- ") and line[2:].strip()]


def parse_run_dir(run_dir: Path) -> tuple[str, str, str]:
    run_dir = Path(run_dir)
    m = _RUN_PARENT.match(run_dir.parent.name)
    if not m:
        raise ValueError(f"作業フォルダは runs/<YYYY-MM-DD>-<agent>/<task-id> の形にしてください: {run_dir}")
    return run_dir.name, m.group(2), m.group(1)


def render_result_md(result: dict, rubric: list[str]) -> str:
    lines = [f"# {result['task_id']} / {result['agent']} / {result['date']}", "", "## 自動判定", "",
             "| 項目 | 合否 | 詳細 |", "|---|---|---|"]
    for item in result["auto"]:
        mark = "✅" if item["pass"] else "❌"
        detail = str(item.get("detail", "")).replace("|", "／").replace("\n", " ")
        lines.append(f"| {item['name']} | {mark} | {detail} |")
    lines += ["", "## 人の目チェック", ""]
    lines += [f"- [ ] {r}" for r in rubric] or ["(なし)"]
    lines += ["", "## 補助指標", "", "所要時間: ", "質問回数: ", "トークン: ", "メモ: ", ""]
    return "\n".join(lines)


def score(root: Path, run_dir: Path, force: bool = False) -> dict:
    root, run_dir = Path(root).resolve(), Path(run_dir).resolve()
    if not run_dir.is_dir():
        raise ValueError(f"作業フォルダがありません: {run_dir}")
    task_id, agent, date = parse_run_dir(run_dir)
    md_path = run_dir / "result.md"
    if md_path.exists() and not force:
        raise FileExistsError(f"result.md が既にあります(人の目チェックの記入が消えます)。上書きするなら --force: {md_path}")
    record_dir = None
    if not run_dir.is_relative_to(root / "runs"):  # リポジトリ外で作業した場合は記録用にコピーする
        record_dir = root / "runs" / f"{date}-{agent}" / task_id
        if record_dir.exists() and not force:
            raise FileExistsError(f"記録先が既にあります: {record_dir}(上書きするなら --force)")
    rubric = parse_rubric(root / "tasks" / task_id / "rubric.md")
    result = {
        "task_id": task_id,
        "agent": agent,
        "date": date,
        "run_dir": str(run_dir.relative_to(root)) if run_dir.is_relative_to(root) else str(run_dir),
        "checked_at": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "auto": run_checker(root, task_id, run_dir),
        "manual_total": len(rubric),
        "recorded_to": str(record_dir.relative_to(root)) if record_dir else None,
    }
    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_result_md(result, rubric), encoding="utf-8")
    if record_dir:
        if record_dir.exists():
            shutil.rmtree(record_dir)
        record_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(run_dir, record_dir, dirs_exist_ok=False)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="自動判定を実行して result.json / result.md を書く")
    ap.add_argument("run_dir")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        result = score(Path(args.root), Path(args.run_dir), args.force)
    except (ValueError, RuntimeError, OSError) as e:  # OSError は FileExistsError / FileNotFoundError を含む
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    passed = sum(1 for i in result["auto"] if i["pass"])
    print(f"自動判定: {passed}/{len(result['auto'])} 合格")
    for i in result["auto"]:
        print(f"  {'✅' if i['pass'] else '❌'} {i['name']}" + (f" — {i['detail']}" if i["detail"] else ""))
    if result["recorded_to"]:
        print(f"記録を {result['recorded_to']} にコピーしました")
    print(f"result.md の人の目チェック({result['manual_total']}項目)と補助指標を記入してください: {Path(args.run_dir) / 'result.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
