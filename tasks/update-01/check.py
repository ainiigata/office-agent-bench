"""update-01 自動チェッカー。使い方: python3 check.py <作業フォルダ>"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from bench.checks import load_workbook_safe, main, norm  # noqa: E402

VALUES = json.loads((HERE / "expected" / "values.json").read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digits(s: str) -> str:
    return re.sub(r"\D", "", unicodedata.normalize("NFKC", s or ""))


def read_table(ws) -> list[dict]:
    """「氏名」を含む行を見出しとして、その下の行を {見出し: norm済み値} で返す。"""
    header_row = None
    for row in ws.iter_rows(min_row=1, max_row=10):
        if any(norm(c.value) == "氏名" for c in row):
            header_row = row[0].row
            headers = {c.column: norm(c.value) for c in row if c.value is not None}
            break
    if header_row is None:
        raise ValueError("「氏名」の見出し行が見つかりません")
    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        rec = {h: norm(ws.cell(row=r, column=col).value) for col, h in headers.items()}
        if any(v for k, v in rec.items() if k != "No"):
            rows.append(rec)
    return rows


def _all_cells(wb) -> list[str]:
    return [norm(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None]


def build_checks(run_dir: Path):
    out_path = run_dir / VALUES["file_out"]
    in_path = run_dir / VALUES["file_in"]

    def file_exists():
        wb = load_workbook_safe(out_path)
        return True, f"シート: {wb.sheetnames}"

    def original_untouched():
        if not in_path.exists():
            return False, "元ファイルが消えています"
        ok = _sha(in_path) == _sha(HERE / "input" / VALUES["file_in"])
        return ok, "" if ok else "元ファイルが変更されています"

    def title_updated():
        ws = load_workbook_safe(out_path).worksheets[0]
        top = [norm(c.value) for row in ws.iter_rows(min_row=1, max_row=3) for c in row if c.value is not None]
        has_new = any("令和8年度" in v and "委員名簿" in v for v in top)
        has_old = any("令和7年" in v for v in top)
        return has_new and not has_old, f"先頭3行: {top}"

    def retired_absent():
        cells = _all_cells(load_workbook_safe(out_path))
        left = [n for n in VALUES["retired"] if any(norm(n) == v for v in cells)]
        return not left, "残っている退任者: " + ", ".join(left) if left else ""

    def new_members_correct():
        rows = {r.get("氏名"): r for r in read_table(load_workbook_safe(out_path).worksheets[0])}
        bad = []
        for m in VALUES["new_members"]:
            r = rows.get(norm(m["name"]))
            if r is None:
                bad.append(f"{m['name']}: 行なし")
                continue
            problems = []
            if r.get("所属") != norm(m["org"]):
                problems.append(f"所属「{r.get('所属')}」")
            if r.get("役職") != norm(m["title"]):
                problems.append(f"役職「{r.get('役職')}」")
            term = r.get("任期", "")
            if norm(m["term_from"]) not in term or norm(m["term_to"]) not in term:
                problems.append(f"任期「{term}」")
            if problems:
                bad.append(f"{m['name']}: " + "、".join(problems))
        return not bad, "; ".join(bad)

    def changes_applied():
        wb = load_workbook_safe(out_path)
        rows = {r.get("氏名"): r for r in read_table(wb.worksheets[0])}
        cells = _all_cells(wb)
        bad = []
        pc, oc = VALUES["phone_change"], VALUES["org_change"]
        r = rows.get(norm(pc["name"]))
        if r is None or _digits(r.get("電話", "")) != _digits(pc["new"]):
            bad.append(f"{pc['name']} の電話が新番号 {pc['new']} になっていない")
        old_digits = _digits(pc["old"])
        if any(_digits(v) == old_digits for v in cells if _digits(v)):
            bad.append(f"旧電話番号 {pc['old']} が残っている")
        r = rows.get(norm(oc["name"]))
        if r is None or r.get("所属") != norm(oc["new"]):
            bad.append(f"{oc['name']} の所属が「{oc['new']}」になっていない")
        if any(v == norm(oc["old"]) for v in cells):
            bad.append(f"旧所属名「{oc['old']}」が残っている")
        return not bad, "; ".join(bad)

    def numbering():
        rows = read_table(load_workbook_safe(out_path).worksheets[0])
        nums = []
        for r in rows:
            try:
                nums.append(int(float(unicodedata.normalize("NFKC", r.get("No", "")))))
            except ValueError:
                nums.append(None)
        expected = list(range(1, VALUES["member_count"] + 1))
        ok = nums == expected
        return ok, "" if ok else f"No 列: {nums}(期待 1〜{VALUES['member_count']} の連番、{len(rows)} 行)"

    return [
        ("file_exists", "令和8年度_委員名簿.xlsx が存在する", file_exists),
        ("original_untouched", "元の令和7年度ファイルが変更されていない", original_untouched),
        ("title_updated", "タイトルが令和8年度になっている", title_updated),
        ("retired_absent", "退任者の氏名が残っていない", retired_absent),
        ("new_members_correct", "新任委員の所属・役職・任期が正しい", new_members_correct),
        ("changes_applied", "電話番号と所属名の変更が反映されている", changes_applied),
        ("numbering", "No が1からの連番で人数が合っている", numbering),
    ]


if __name__ == "__main__":
    main(build_checks(Path(sys.argv[1])))
