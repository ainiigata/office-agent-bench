from bench.mail import addresses, parse_mail, read_mail

SAMPLE = """From: 佐藤 花子 <sato@example.co.jp>
To: 山田 太郎 <yamada@example.co.jp>, suzuki@example.co.jp
Cc:
Date: 2026-09-08 10:15
Subject: 打合せ日程の件

お世話になっております。

本文2行目
"""


def test_parse_mail_headers_and_body():
    headers, body = parse_mail(SAMPLE)
    assert headers["from"] == "佐藤 花子 <sato@example.co.jp>"
    assert headers["subject"] == "打合せ日程の件"
    assert headers["cc"] == ""
    assert body.startswith("お世話になっております。")
    assert "本文2行目" in body


def test_parse_mail_without_blank_line_is_all_headers_no_body():
    headers, body = parse_mail("Subject: x\nFrom: a@b")
    assert headers["subject"] == "x"
    assert body == ""


def test_addresses_extracts_bracketed_and_bare():
    assert addresses("山田 太郎 <Yamada@example.co.jp>, suzuki@example.co.jp") == {
        "yamada@example.co.jp",
        "suzuki@example.co.jp",
    }
    assert addresses("") == set()


def test_read_mail(tmp_path):
    p = tmp_path / "m.txt"
    p.write_text(SAMPLE, encoding="utf-8")
    headers, _ = read_mail(p)
    assert headers["date"] == "2026-09-08 10:15"
