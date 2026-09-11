"""web-02 自動チェッカー。使い方: python3 check.py <作業フォルダ>"""
from __future__ import annotations

import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from bench.checks import load_workbook_safe, main, norm  # noqa: E402

FILE = "祝日2027.xlsx"
VALUES = json.loads((HERE / "expected" / "values.json").read_text(encoding="utf-8"))
EXPECTED = {datetime.date.fromisoformat(h["date"]): h for h in VALUES["holidays"]}
WEEKDAYS = "月火水木金土日"
_DATE = re.compile(r"^(\d{4})[/\-.年](\d{1,2})[/\-.月](\d{1,2})日?$")
_URL = re.compile(r"https?://[^\s　<>\"']+")


def _to_date(value) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    m = _DATE.match(unicodedata.normalize("NFKC", norm(value)))
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def read_rows(ws) -> list[dict]:
    """見出し行(「日付」を含む行)の次から、日付として読める行を集める。"""
    header = None
    for row in ws.iter_rows(min_row=1, max_row=5):
        if any(norm(c.value) == "日付" for c in row):
            header = {norm(c.value): c.column for c in row if c.value is not None}
            header_row = row[0].row
            break
    if header is None:
        raise ValueError("「日付」の見出し行が見つかりません")
    col = {k: header.get(k) for k in ("日付", "曜日", "名称", "備考")}
    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        d = _to_date(ws.cell(row=r, column=col["日付"]).value) if col["日付"] else None
        if d is None:
            continue
        rows.append({
            "date": d,
            "weekday": norm(ws.cell(row=r, column=col["曜日"]).value) if col["曜日"] else "",
            "name": norm(ws.cell(row=r, column=col["名称"]).value) if col["名称"] else "",
            "note": norm(ws.cell(row=r, column=col["備考"]).value) if col["備考"] else "",
        })
    return rows


def build_checks(run_dir: Path):
    path = run_dir / FILE

    def sheet():
        return load_workbook_safe(path).worksheets[0]

    def xlsx_exists():
        ws = sheet()
        return ws.max_row >= 2, f"{ws.max_row} 行"

    def dates_match():
        found = {r["date"] for r in read_rows(sheet())}
        missing = sorted(set(EXPECTED) - found)
        extra = sorted(found - set(EXPECTED))
        detail = []
        if missing:
            detail.append("不足: " + ", ".join(d.isoformat() for d in missing))
        if extra:
            detail.append("余分: " + ", ".join(d.isoformat() for d in extra))
        return not detail, "; ".join(detail)

    def weekdays_consistent():
        bad = []
        for r in read_rows(sheet()):
            w = unicodedata.normalize("NFKC", r["weekday"]).replace("曜日", "").replace("曜", "").strip("()（）")
            if w != WEEKDAYS[r["date"].weekday()]:
                bad.append(f"{r['date'].isoformat()}: {r['weekday'] or '空'}")
        return not bad, "曜日が違う: " + ", ".join(bad[:3]) if bad else ""

    def names_match():
        bad = []
        for r in read_rows(sheet()):
            exp = EXPECTED.get(r["date"])
            if exp is None:
                continue
            ok = r["name"] == exp["name"] or (exp["substitute"] and "振替" in r["name"])
            if not ok:
                bad.append(f"{r['date'].isoformat()}: 期待「{exp['name']}」 実際「{r['name']}」")
        return not bad, "; ".join(bad[:3])

    def substitute_marked():
        subs = [d for d, h in EXPECTED.items() if h["substitute"]]
        rows = {r["date"]: r for r in read_rows(sheet())}
        bad = [d.isoformat() for d in subs if d not in rows or ("振替" not in rows[d]["note"] and "振替" not in rows[d]["name"])]
        return not bad, "振替休日の表示がない: " + ", ".join(bad) if bad else ""

    def source_is_cao():
        ws = sheet()
        urls = []
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str):
                    urls.extend(_URL.findall(c.value))

        def is_cao_host(url: str) -> bool:
            host = (urlparse(url).hostname or "").lower()
            return host == "cao.go.jp" or host.endswith(".cao.go.jp")

        ok = any(is_cao_host(u) for u in urls)
        return ok, "" if ok else f"内閣府(cao.go.jp)のURLがありません: {urls[:2]}"

    return [
        ("xlsx_exists", "祝日2027.xlsx が存在する", xlsx_exists),
        ("dates_match", "祝日の日付が過不足なく一致", dates_match),
        ("weekdays_consistent", "曜日が日付と整合", weekdays_consistent),
        ("names_match", "名称が一致", names_match),
        ("substitute_marked", "振替休日が備考付きで入っている", substitute_marked),
        ("source_is_cao", "出典が内閣府のURL", source_is_cao),
    ]


if __name__ == "__main__":
    main(build_checks(Path(sys.argv[1])))
