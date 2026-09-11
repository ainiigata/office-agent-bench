"""mail-03 自動チェッカー。使い方: python3 check.py <作業フォルダ>"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from bench.checks import main  # noqa: E402
from bench.mail import addresses, read_mail  # noqa: E402

FILE = "reply.txt"
VALUES = json.loads((HERE / "expected" / "values.json").read_text(encoding="utf-8"))
EXPECTED_SLOTS = {tuple(s) for s in VALUES["slots"]}
_WEEKDAY = r"(?:[（(]?[月火水木金土日](?:曜日?)?[）)]?)?"
_TIME = r"(\d{1,2})(?:[:：](\d{2})|時(?:(\d{1,2})分)?)"  # 15:00 / 15時 / 15時00分
_SLOT = re.compile(
    rf"(\d{{1,2}})月(\d{{1,2}})日\s*{_WEEKDAY}\s*{_TIME}\s*[〜~～\-–ー]\s*{_TIME}"
)


def extract_slots(body: str) -> set[tuple[int, int, int, int, int, int]]:
    text = unicodedata.normalize("NFKC", body)
    slots = set()
    for m in _SLOT.finditer(text):
        month, day, sh, sm1, sm2, eh, em1, em2 = m.groups()
        slots.add((int(month), int(day), int(sh), int(sm1 or sm2 or 0), int(eh), int(em1 or em2 or 0)))
    return slots


def _fmt(slot) -> str:
    m, d, sh, sm, eh, em = slot
    return f"{m}月{d}日 {sh:02d}:{sm:02d}〜{eh:02d}:{em:02d}"


def build_checks(run_dir: Path):
    path = run_dir / FILE

    def reply_parsable():
        headers, body = read_mail(path)
        ok = "to" in headers and "subject" in headers and bool(body.strip())
        return ok, "" if ok else f"ヘッダ {sorted(headers)} / 本文 {len(body)} 文字"

    def to_all():
        headers, _ = read_mail(path)
        found = addresses(headers.get("to", "")) | addresses(headers.get("cc", ""))
        missing = sorted(set(VALUES["to"]) - found)
        return not missing, "宛先に無い: " + ", ".join(missing) if missing else ""

    def subject_prefix():
        headers, _ = read_mail(path)
        subject = headers.get("subject", "")
        return subject.startswith(VALUES["subject_prefix"]), f"件名: {subject}"

    def no_wrong_slot():
        _, body = read_mail(path)
        found = extract_slots(body)
        if not found:
            return False, "本文に「9月16日(水) 15:00〜16:00」形式の候補が見つかりません"
        wrong = found - EXPECTED_SLOTS
        return not wrong, "誰かの都合が悪い候補: " + ", ".join(_fmt(s) for s in sorted(wrong)) if wrong else ""

    def all_correct_slots():
        _, body = read_mail(path)
        missing = EXPECTED_SLOTS - extract_slots(body)
        return not missing, "挙がっていない正解: " + ", ".join(_fmt(s) for s in sorted(missing)) if missing else ""

    return [
        ("reply_parsable", "reply.txt が存在しヘッダと本文を解析できる", reply_parsable),
        ("to_all", "To/Cc に3名全員のアドレスを含む", to_all),
        ("subject_prefix", "件名が「【日程調整】」で始まる", subject_prefix),
        ("no_wrong_slot", "都合の悪い候補を挙げていない", no_wrong_slot),
        ("all_correct_slots", "全員が空いている候補を両方挙げている", all_correct_slots),
    ]


if __name__ == "__main__":
    main(build_checks(Path(sys.argv[1])))
