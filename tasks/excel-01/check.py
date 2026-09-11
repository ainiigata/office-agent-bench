"""excel-01 自動チェッカー。使い方: python3 check.py <作業フォルダ>"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from bench.checks import approx, load_workbook_safe, main, norm  # noqa: E402

FILE = "売上明細_2026上期.xlsx"
VALUES = json.loads((HERE / "expected" / "values.json").read_text(encoding="utf-8"))
_MONTH = re.compile(r"^(?:2026[年/\-.])?0?([4-9])(?:月(?:度|分)?)?$")


def _month_of(value) -> int | None:
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.month if 4 <= value.month <= 9 else None
    m = _MONTH.match(unicodedata.normalize("NFKC", norm(value)))
    return int(m.group(1)) if m else None


def detail_rows(ws) -> list[tuple]:
    """「明細」シートのデータ行(7列)を取り出す。"""
    return [tuple(r[:7]) for r in ws.iter_rows(min_row=2, max_col=7, values_only=True) if r and r[0] is not None]


def detail_digest(ws) -> str:
    """「明細」シートのセル値のダイジェスト。make_fixtures.py が正解値を作るのにも使う。"""
    text = "\n".join("\t".join(str(v) if v is not None else "" for v in row) for row in detail_rows(ws))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_layout(ws):
    """集計シートから (担当者→行, 月→列, 合計列, 構成比列) を探す。"""
    month_cols: dict[int, int] = {}
    header_row = None
    for row in ws.iter_rows(min_row=1, max_row=10):
        cols = {m: c.column for c in row if (m := _month_of(c.value))}
        if len(cols) >= 6:
            month_cols, header_row = cols, row[0].row
            break
    if not month_cols:
        raise ValueError("4月〜9月の見出し行が見つかりません")
    total_col = share_col = None
    for c in ws[header_row]:
        v = norm(c.value)
        if "構成比" in v:
            share_col = c.column
        elif "合計" in v and total_col is None:
            total_col = c.column
    staff_rows: dict[str, int] = {}
    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
        for c in row:
            for s in VALUES["staff"]:
                if norm(c.value) == norm(s):
                    staff_rows[s] = c.row
    return staff_rows, month_cols, total_col, share_col


def _num(ws, row: int, col: int) -> float:
    """セルの数値。桁区切り・「円」付き・「18.8%」のような文字列も数値として受け取る。"""
    cell = ws.cell(row=row, column=col)
    value = cell.value
    if value is None:
        raise ValueError(f"{cell.coordinate} が空です(数式のまま保存されていて値が無い可能性。値貼り付けが必要)")
    if isinstance(value, str):
        text = unicodedata.normalize("NFKC", value).strip()
        for ch in (" ", ",", "¥", "円"):
            text = text.replace(ch, "")
        if text.endswith("%"):
            return float(text[:-1]) / 100
        return float(text)
    return float(value)


def build_checks(run_dir: Path):
    path = run_dir / FILE

    def sheet_exists():
        wb = load_workbook_safe(path)
        return "集計" in wb.sheetnames, f"シート: {wb.sheetnames}"

    def pivot_match():
        ws = load_workbook_safe(path)["集計"]
        staff_rows, month_cols, _, _ = find_layout(ws)
        missing = [s for s in VALUES["staff"] if s not in staff_rows]
        if missing:
            return False, f"担当者の行が見つかりません: {missing}"
        bad = []
        for s, cols in VALUES["pivot"].items():
            for m, expected in cols.items():
                actual = _num(ws, staff_rows[s], month_cols[int(m)])
                if not approx(actual, expected):
                    bad.append(f"{s}×{m}月: 期待 {expected:,} 実際 {actual:,.0f}")
        return not bad, "; ".join(bad[:3])

    def total_match():
        ws = load_workbook_safe(path)["集計"]
        staff_rows, _, total_col, _ = find_layout(ws)
        if total_col is None:
            return False, "「合計」列が見つかりません"
        bad = []
        for s, cols in VALUES["pivot"].items():
            if s not in staff_rows:
                bad.append(f"{s}: 行なし")
                continue
            expected = sum(cols.values())
            actual = _num(ws, staff_rows[s], total_col)
            if not approx(actual, expected):
                bad.append(f"{s}: 期待 {expected:,} 実際 {actual:,.0f}")
        return not bad, "; ".join(bad[:3])

    def share_sum():
        ws = load_workbook_safe(path)["集計"]
        staff_rows, _, _, share_col = find_layout(ws)
        if share_col is None:
            return False, "「構成比」列が見つかりません"
        shares = {s: _num(ws, r, share_col) for s, r in staff_rows.items()}
        if all(v <= 1.0 for v in shares.values()):
            shares = {s: v * 100 for s, v in shares.items()}
        total = sum(shares.values())
        if abs(total - 100) > 0.5:
            return False, f"構成比の合計が {total:.1f}%"
        grand = VALUES["grand_total"]
        bad = [f"{s}: 期待 {sum(VALUES['pivot'][s].values()) / grand * 100:.1f}% 実際 {v:.1f}%"
               for s, v in shares.items() if abs(v - sum(VALUES["pivot"][s].values()) / grand * 100) > 0.2]
        return not bad, "; ".join(bad[:3])

    def detail_intact():
        wb = load_workbook_safe(path)
        if "明細" not in wb.sheetnames:
            return False, "「明細」シートがありません"
        ws = wb["明細"]
        rows = detail_rows(ws)
        amount_total = sum(r[6] for r in rows if isinstance(r[6], (int, float)))
        detail = (f"行数 {len(rows)}(期待 {VALUES['detail_rows']}), "
                  f"金額合計 {amount_total:,.0f}(期待 {VALUES['grand_total']:,})")
        if detail_digest(ws) != VALUES["detail_digest"]:
            return False, detail + " / セル値が元と違います(明細は編集しない)"
        return True, detail

    return [
        ("sheet_exists", "「集計」シートが存在する", sheet_exists),
        ("pivot_match", "担当者×月の金額が明細と一致", pivot_match),
        ("total_match", "担当者ごとの合計が一致", total_match),
        ("share_sum", "構成比が正しく合計100%", share_sum),
        ("detail_intact", "「明細」シートが改変されていない", detail_intact),
    ]


if __name__ == "__main__":
    main(build_checks(Path(sys.argv[1])))
