import json

from bench import checks


def test_run_checks_collects_pass_and_fail():
    result = checks.run_checks([
        ("a", "合格する項目", lambda: (True, "")),
        ("b", "不合格の項目", lambda: (False, "値が違う")),
    ])
    assert result == [
        {"id": "a", "name": "合格する項目", "pass": True, "detail": ""},
        {"id": "b", "name": "不合格の項目", "pass": False, "detail": "値が違う"},
    ]


def test_run_checks_catches_exception():
    def boom():
        raise FileNotFoundError("成果物がありません: x.xlsx")
    result = checks.run_checks([("c", "例外項目", boom)])
    assert result[0]["pass"] is False
    assert "成果物がありません" in result[0]["detail"]


def test_main_prints_json(capsys):
    checks.main([("a", "項目", lambda: (True, ""))])
    out = json.loads(capsys.readouterr().out)
    assert out[0]["id"] == "a"


def test_norm_and_approx():
    assert checks.norm(" 佐藤　健一 ") == "佐藤健一"
    assert checks.norm(None) == ""
    assert checks.norm(12) == "12"
    assert checks.approx(100, 100.9)
    assert not checks.approx(100, 102)


def test_load_workbook_safe_missing(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError, match="成果物がありません"):
        checks.load_workbook_safe(tmp_path / "none.xlsx")


def test_repo_root_points_to_repo(repo_root):
    assert checks.repo_root() == repo_root
