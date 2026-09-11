import json
from pathlib import Path

import pytest

from tests.conftest import make_dummy_task
from tools.prepare import prepare
from tools.score import main, parse_rubric, parse_run_dir, render_result_md, run_checker, score


def _run(tmp_path, with_output=True):
    make_dummy_task(tmp_path)
    run_dir = prepare(tmp_path, "dummy-01", "claude-code", date="2026-09-11")
    if with_output:
        (run_dir / "output.txt").write_text("hello\n", encoding="utf-8")
    return run_dir


def test_run_checker_returns_items(tmp_path):
    run_dir = _run(tmp_path)
    items = run_checker(tmp_path, "dummy-01", run_dir)
    assert [i["id"] for i in items] == ["has_hello", "always"]
    assert all(i["pass"] for i in items)


def test_run_checker_reports_broken_checker(tmp_path):
    run_dir = _run(tmp_path)
    (tmp_path / "tasks" / "dummy-01" / "check.py").write_text("raise SystemExit(3)\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="check.py"):
        run_checker(tmp_path, "dummy-01", run_dir)


def test_parse_rubric(tmp_path):
    make_dummy_task(tmp_path)
    assert parse_rubric(tmp_path / "tasks" / "dummy-01" / "rubric.md") == ["文字が丁寧", "余計なファイルがない"]


def test_parse_run_dir(tmp_path):
    assert parse_run_dir(tmp_path / "runs" / "2026-09-11-claude-code-2" / "excel-01") == (
        "excel-01", "claude-code-2", "2026-09-11")
    with pytest.raises(ValueError, match="runs/"):
        parse_run_dir(tmp_path / "somewhere" / "excel-01")


def test_score_writes_json_and_md(tmp_path):
    run_dir = _run(tmp_path)
    result = score(tmp_path, run_dir)
    data = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert data["task_id"] == "dummy-01" and data["agent"] == "claude-code"
    assert data["manual_total"] == 2
    assert sum(i["pass"] for i in data["auto"]) == 2
    md = (run_dir / "result.md").read_text(encoding="utf-8")
    assert md.startswith("# dummy-01 / claude-code / 2026-09-11")
    assert "## 自動判定" in md and "✅" in md
    assert "- [ ] 文字が丁寧" in md
    assert "所要時間: " in md and "質問回数: " in md and "トークン: " in md and "メモ: " in md
    assert result["run_dir"].endswith("dummy-01")


def test_score_marks_missing_output_as_fail(tmp_path):
    run_dir = _run(tmp_path, with_output=False)
    result = score(tmp_path, run_dir)
    assert [i["pass"] for i in result["auto"]] == [False, True]
    assert "❌" in (run_dir / "result.md").read_text(encoding="utf-8")


def test_score_refuses_overwrite_without_force(tmp_path):
    run_dir = _run(tmp_path)
    score(tmp_path, run_dir)
    with pytest.raises(FileExistsError, match="--force"):
        score(tmp_path, run_dir)
    score(tmp_path, run_dir, force=True)


def _external_run(tmp_path, agent="claude-code"):
    """リポジトリ外(work_root)の作業フォルダを作り、成果物を置く。"""
    make_dummy_task(tmp_path)
    run_dir = prepare(tmp_path, "dummy-01", agent, date="2026-09-11", work_root=tmp_path / "ext")
    (run_dir / "output.txt").write_text("hello\n", encoding="utf-8")
    return run_dir


def test_score_copies_external_run_into_runs(tmp_path):
    run_dir = _external_run(tmp_path)
    result = score(tmp_path, run_dir)
    recorded = tmp_path / "runs" / "2026-09-11-claude-code" / "dummy-01"
    assert result["recorded_to"] == str(Path("runs") / "2026-09-11-claude-code" / "dummy-01")
    for name in ("result.json", "result.md", "output.txt", "task.md"):
        assert (run_dir / name).exists(), name
        assert (recorded / name).exists(), name
    copied = json.loads((recorded / "result.json").read_text(encoding="utf-8"))
    assert copied["task_id"] == "dummy-01" and sum(i["pass"] for i in copied["auto"]) == 2


def test_score_external_refuses_existing_record_without_force(tmp_path):
    run_dir = _external_run(tmp_path)
    score(tmp_path, run_dir)
    with pytest.raises(FileExistsError, match="--force"):
        score(tmp_path, run_dir)
    assert score(tmp_path, run_dir, force=True)["recorded_to"].endswith("dummy-01")


def test_score_in_repo_run_is_not_copied(tmp_path):
    run_dir = _run(tmp_path)
    result = score(tmp_path, run_dir)
    assert result["recorded_to"] is None
    assert sorted(p.name for p in (tmp_path / "runs").iterdir()) == ["2026-09-11-claude-code"]


def test_main_reports_copy_destination(tmp_path, capsys):
    run_dir = _external_run(tmp_path, agent="codex")
    assert main([str(run_dir), "--root", str(tmp_path)]) == 0
    assert "runs/2026-09-11-codex/dummy-01" in capsys.readouterr().out.replace("\\", "/")


def test_score_reports_missing_run_dir(tmp_path, capsys):
    """打ち間違えた作業フォルダ名でもトレースバックを出さずエラーにする。"""
    make_dummy_task(tmp_path)
    missing = tmp_path / "runs" / "2026-09-99-typo" / "dummy-01"
    with pytest.raises(ValueError, match="作業フォルダがありません"):
        score(tmp_path, missing)
    assert main([str(missing), "--root", str(tmp_path)]) == 1
    assert "エラー:" in capsys.readouterr().err


def test_render_result_md_shape():
    result = {"task_id": "x-01", "agent": "a", "date": "2026-09-11",
              "auto": [{"id": "i", "name": "項目A", "pass": False, "detail": "理由"}]}
    md = render_result_md(result, ["丁寧"])
    assert "| 項目A | ❌ | 理由 |" in md
    assert "- [ ] 丁寧" in md


def test_run_checker_includes_stderr_on_json_error(tmp_path):
    run_dir = _run(tmp_path)
    (tmp_path / "tasks" / "dummy-01" / "check.py").write_text(
        "import sys\nprint('警告', file=sys.stderr)\nprint('not json')\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError) as exc_info:
        run_checker(tmp_path, "dummy-01", run_dir)
    error_msg = str(exc_info.value)
    assert "check.py" in error_msg
    assert "警告" in error_msg
