"""word-01 自動チェッカー。使い方: python3 check.py <作業フォルダ>"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from bench.checks import main, norm  # noqa: E402
from bench.docx_text import docx_text  # noqa: E402

FILE = "通知文.docx"
VALUES = json.loads((HERE / "expected" / "values.json").read_text(encoding="utf-8"))
# メモ.txt の見出しラベル。行頭にこのまま残っていればメモの丸写しとみなす
MEMO_LABELS = ["文書番号", "日付", "宛名", "発信者", "件名", "日時", "場所", "対象", "内容",
               "持ち物", "雨天時", "回答", "問い合わせ先"]
_MEMO_LABEL = re.compile("^(?:" + "|".join(MEMO_LABELS) + ")[:：]")
_NUMBERED_ITEM = re.compile(r"^[（(]?\d+[）)．.、]?\S")


def build_checks(run_dir: Path):
    path = run_dir / FILE

    def text() -> str:
        return docx_text(path)

    def docx_exists():
        t = text()
        return len(norm(t)) > 0, f"{len(t)} 文字"

    def header_fields():
        t = norm(text())
        missing = [f"{k}({v})" for k, v in VALUES["header"].items() if norm(v) not in t]
        return not missing, "不足: " + ", ".join(missing) if missing else ""

    def ki_ijo_order():
        lines = [norm(line) for line in text().splitlines()]
        ki = next((i for i, l in enumerate(lines) if l == "記"), None)
        if ki is None:
            return False, "単独の行としての「記」がありません"
        ijo = next((i for i, l in enumerate(lines) if l == "以上" and i > ki), None)
        if ijo is None:
            return False, "「記」より後に単独の行としての「以上」がありません"
        return True, ""

    def body_content():
        t = norm(text())
        missing = [f"{k}({v})" for k, v in VALUES["body"].items() if norm(v) not in t]
        return not missing, "不足: " + ", ".join(missing) if missing else ""

    def phone():
        digits = re.sub(r"\D", "", text())
        return VALUES["phone_digits"] in digits, "" if VALUES["phone_digits"] in digits else "問い合わせ先の電話番号がありません"

    def not_memo_dump():
        lines = [norm(line) for line in text().splitlines()]
        if "作成メモ" in "".join(lines):
            return False, "「作成メモ」がそのまま残っています"
        labeled = [line for line in lines if _MEMO_LABEL.match(line)]
        if labeled:
            return False, "メモの見出しラベルが行頭に残っています: " + ", ".join(labeled[:3])
        ki = next((i for i, line in enumerate(lines) if line == "記"), None)
        ijo = next((i for i, line in enumerate(lines) if line == "以上" and ki is not None and i > ki), None)
        if ki is None or ijo is None:
            return False, "「記」と「以上」が揃っていないので項目立てを確認できません"
        if not any(_NUMBERED_ITEM.match(unicodedata.normalize("NFKC", line)) for line in lines[ki + 1:ijo]):
            return False, "「記」と「以上」の間に番号付きの項目がありません"
        return True, ""

    return [
        ("docx_exists", "通知文.docx が存在し本文がある", docx_exists),
        ("header_fields", "文書番号・日付・宛名・発信者・件名を含む", header_fields),
        ("ki_ijo_order", "「記」と「以上」がこの順で単独行にある", ki_ijo_order),
        ("body_content", "日時・場所・持ち物の内容を含む", body_content),
        ("phone", "問い合わせ先の電話番号を含む", phone),
        ("not_memo_dump", "メモの丸写しではなく通知文の体裁になっている", not_memo_dump),
    ]


if __name__ == "__main__":
    main(build_checks(Path(sys.argv[1])))
