"""runs/ 配下の result.json / result.md を集計して Markdown の表を出す。

使い方: python3 tools/summary.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {"excel": "Excel", "word": "Word", "mail": "メール", "web": "Web調査", "update": "データ更新"}
_CHECKED = re.compile(r"^- \[[xX]\] ")
_UNCHECKED = re.compile(r"^- \[ \] ")


@dataclass
class RunResult:
    task_id: str
    agent: str
    date: str
    auto_pass: int
    auto_total: int
    manual_pass: int
    manual_total: int

    @property
    def total(self) -> int:
        return self.auto_total + self.manual_total

    @property
    def passed(self) -> int:
        return self.auto_pass + self.manual_pass

    @property
    def score(self) -> float:
        return round(self.passed / self.total * 100, 1) if self.total else 0.0

    @property
    def achieved(self) -> bool:
        return self.total > 0 and self.passed == self.total

    @property
    def domain(self) -> str:
        key = self.task_id.split("-", 1)[0]
        return DOMAINS.get(key, key)


def parse_manual(md_text: str) -> tuple[int, int]:
    checked = total = 0
    in_section = False
    for line in md_text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## 人の目チェック"
            continue
        if not in_section:
            continue
        if _CHECKED.match(line):
            checked += 1
            total += 1
        elif _UNCHECKED.match(line):
            total += 1
    return checked, total


def collect(root: Path) -> list[RunResult]:
    results = []
    for result_json in sorted(Path(root).glob("runs/*/*/result.json")):
        try:
            data = json.loads(result_json.read_text(encoding="utf-8"))
            md_path = result_json.with_name("result.md")
            manual_pass, manual_total = parse_manual(md_path.read_text(encoding="utf-8")) if md_path.exists() else (0, 0)
            manual_total = max(manual_total, int(data.get("manual_total", 0)))
            auto = data.get("auto", [])
            results.append(RunResult(
                task_id=data["task_id"], agent=data["agent"], date=data.get("date", result_json.parents[1].name[:10]),
                auto_pass=sum(1 for i in auto if i.get("pass")), auto_total=len(auto),
                manual_pass=manual_pass, manual_total=manual_total,
            ))
        except (json.JSONDecodeError, KeyError, OSError, TypeError) as e:  # 壊れた記録1件で全体を止めない
            print(f"警告: {result_json} を読めません({e})。スキップします", file=sys.stderr)
    return results


def latest(results: list[RunResult]) -> list[RunResult]:
    picked: dict[tuple[str, str], RunResult] = {}
    for r in results:
        key = (r.agent, r.task_id)
        if key not in picked or r.date >= picked[key].date:
            picked[key] = r
    return sorted(picked.values(), key=lambda r: (r.agent, r.task_id))


def _avg(rows: list[RunResult]) -> str:
    return f"{sum(r.score for r in rows) / len(rows):.1f}" if rows else "-"


def render(results: list[RunResult]) -> str:
    if not results:
        return "まだ実行記録がありません。tools/prepare.py → エージェント実行 → tools/score.py の順で記録を作ってください。\n"
    agents = sorted({r.agent for r in results})
    domains = list(DOMAINS.values())
    out = ["## エージェント別 × 領域別 平均点", "", "| エージェント | " + " | ".join(domains) + " | 全体 |",
           "|---|" + "---|" * (len(domains) + 1)]
    for a in agents:
        rows = [r for r in results if r.agent == a]
        cells = [_avg([r for r in rows if r.domain == d]) for d in domains]
        out.append(f"| {a} | " + " | ".join(cells) + f" | {_avg(rows)} |")
    out += ["", "## 達成タスク数(全項目 pass)/ 実行タスク数", "", "| エージェント | 達成 | 実行 |", "|---|---|---|"]
    for a in agents:
        rows = [r for r in results if r.agent == a]
        out.append(f"| {a} | {sum(1 for r in rows if r.achieved)} | {len(rows)} |")
    out += ["", "## タスク別明細", "",
            "| エージェント | タスク | 実行日 | 自動 | 人の目 | 点数 | 達成 |", "|---|---|---|---|---|---|---|"]
    for r in results:
        out.append(f"| {r.agent} | {r.task_id} | {r.date} | {r.auto_pass}/{r.auto_total} | "
                   f"{r.manual_pass}/{r.manual_total} | {r.score:.1f} | {'◎' if r.achieved else ''} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="runs/ の結果を集計する")
    ap.add_argument("--all", action="store_true", help="最新だけでなく全実行を表示")
    ap.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        results = collect(Path(args.root))
    except (ValueError, OSError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(render(results if args.all else latest(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
