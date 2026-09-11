"""mail-03 のフィクスチャ生成。python3 make_fixtures.py で input/ と expected/ を再生成する。"""
from __future__ import annotations

import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

HERE = Path(__file__).resolve().parent

MAILS = {
    "01_佐藤.txt": """From: 佐藤 健一 <sato@example.co.jp>
To: 山田 太郎 <yamada@example.co.jp>
Cc:
Date: 2026-09-10 09:12
Subject: Re: 来週の打合せについて

山田さん

お疲れさまです。来週の都合です。

9/14(月) 終日不可(出張)
9/15(火) 終日OK
9/16(水) 14時以降なら大丈夫です
9/17(木) 午前中のみ空いています
9/18(金) 終日不可(休暇)

よろしくお願いします。
佐藤
""",
    "02_鈴木.txt": """From: 鈴木 美咲 <suzuki@example.co.jp>
To: 山田 太郎 <yamada@example.co.jp>
Cc:
Date: 2026-09-10 11:40
Subject: Re: 来週の打合せについて

山田さん、お疲れさまです。鈴木です。

来週は基本的に空いていますが、以下の時間は入れないでください。
・9/14(月) 休暇
・9/15(火) 10:00-12:00 と 15:00-17:00 会議
・9/16(水) 午前中 出張(午後は戻ります)
・9/17(木) 13:00以降 不可
・9/18(金) 9:00-11:00 面談

以上、よろしくお願いします。
""",
    "03_高橋.txt": """From: 高橋 大輔 <takahashi@example.co.jp>
To: 山田 太郎 <yamada@example.co.jp>
Cc:
Date: 2026-09-10 14:05
Subject: Re: 来週の打合せについて

お疲れさまです。高橋です。

月曜は休みです。火曜は午後イチ(13時〜14時)以外なら空いてます。
水曜は15時から17時までなら大丈夫です。木曜は9時半から11時まで会議で、それ以外は空いてます。
金曜は午後から外出します。

よろしくお願いします。
""",
}

MY_SCHEDULE = [
    ("2026-09-14", "09:00", "12:00", "部内会議"),
    ("2026-09-14", "12:00", "13:00", "昼休憩"),
    ("2026-09-14", "13:00", "15:00", "資料作成(集中時間)"),
    ("2026-09-14", "16:00", "18:00", "来客対応"),
    ("2026-09-15", "09:00", "10:00", "朝会"),
    ("2026-09-15", "12:00", "13:00", "昼休憩"),
    ("2026-09-15", "14:00", "15:30", "課内ミーティング"),
    ("2026-09-15", "17:00", "18:00", "業者打合せ"),
    ("2026-09-16", "09:00", "10:30", "週次報告作成"),
    ("2026-09-16", "12:00", "13:00", "昼休憩"),
    ("2026-09-16", "16:00", "17:30", "来客対応"),
    ("2026-09-17", "09:00", "10:30", "経理との打合せ"),
    ("2026-09-17", "12:00", "13:00", "昼休憩"),
    ("2026-09-17", "14:00", "16:00", "研修"),
    ("2026-09-18", "09:00", "10:00", "朝会"),
    ("2026-09-18", "12:00", "13:00", "昼休憩"),
    ("2026-09-18", "15:00", "18:00", "外出(取引先訪問)"),
]

REPLY = """From: 山田 太郎 <yamada@example.co.jp>
To: 佐藤 健一 <sato@example.co.jp>, 鈴木 美咲 <suzuki@example.co.jp>, 高橋 大輔 <takahashi@example.co.jp>
Cc:
Date: 2026-09-11 10:00
Subject: 【日程調整】下期販促企画の打合せ(来週)

佐藤さん、鈴木さん、高橋さん

お疲れさまです。山田です。
ご都合の連絡ありがとうございました。皆さんの予定を合わせたところ、全員が揃う候補は次の2つでした。

候補① 9月16日(水) 15:00〜16:00
候補② 9月17日(木) 11:00〜12:00

場所は3階の会議室Aを押さえる予定です。
恐れ入りますが、9月14日(月)の午前中までにどちらが良いかご返信ください。

よろしくお願いします。
山田
"""

VALUES = {
    "to": ["sato@example.co.jp", "suzuki@example.co.jp", "takahashi@example.co.jp"],
    "subject_prefix": "【日程調整】",
    "slots": [[9, 16, 15, 0, 16, 0], [9, 17, 11, 0, 12, 0]],
}


def main() -> None:
    inbox = HERE / "input" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (HERE / "expected").mkdir(exist_ok=True)
    for name, body in MAILS.items():
        (inbox / name).write_text(body, encoding="utf-8")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "予定"
    ws.append(["日付", "開始", "終了", "予定"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for row in MY_SCHEDULE:
        ws.append(list(row))
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["D"].width = 24
    wb.save(HERE / "input" / "自分の予定表.xlsx")
    (HERE / "expected" / "reply.txt").write_text(REPLY, encoding="utf-8")
    (HERE / "expected" / "values.json").write_text(json.dumps(VALUES, ensure_ascii=False, indent=2), encoding="utf-8")
    print("生成完了")


if __name__ == "__main__":
    main()
