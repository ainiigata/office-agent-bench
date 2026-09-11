import pytest

from tests.conftest import make_dummy_task
from tools.prepare import main, prepare


def test_prepare_copies_input_and_task_md(tmp_path):
    make_dummy_task(tmp_path)
    run_dir = prepare(tmp_path, "dummy-01", "claude-code", date="2026-09-11")
    assert run_dir == tmp_path / "runs" / "2026-09-11-claude-code" / "dummy-01"
    assert (run_dir / "data.txt").read_text(encoding="utf-8") == "元データ\n"
    assert (run_dir / "task.md").exists()
    assert not (run_dir / "expected").exists()


def test_prepare_work_root_creates_folder_outside_repo(tmp_path):
    """--work-root: リポジトリの外に作業フォルダを作る(正解データに相対パスで届かせない)。"""
    make_dummy_task(tmp_path)
    ext = tmp_path / "ext"
    run_dir = prepare(tmp_path, "dummy-01", "claude-code", date="2026-09-11", work_root=ext)
    assert run_dir == ext / "2026-09-11-claude-code" / "dummy-01"
    assert (run_dir / "data.txt").read_text(encoding="utf-8") == "元データ\n"
    assert (run_dir / "task.md").exists()
    assert not (run_dir / "expected").exists()
    assert not (tmp_path / "runs").exists()


def test_prepare_work_root_refuses_existing_without_force(tmp_path):
    make_dummy_task(tmp_path)
    ext = tmp_path / "ext"
    prepare(tmp_path, "dummy-01", "codex", date="2026-09-11", work_root=ext)
    with pytest.raises(FileExistsError, match="--force"):
        prepare(tmp_path, "dummy-01", "codex", date="2026-09-11", work_root=ext)
    run_dir = prepare(tmp_path, "dummy-01", "codex", date="2026-09-11", work_root=ext, force=True)
    assert (run_dir / "data.txt").exists()


def test_main_accepts_work_root_option(tmp_path, capsys):
    make_dummy_task(tmp_path)
    ext = tmp_path / "ext"
    assert main(["dummy-01", "x", "--root", str(tmp_path), "--date", "2026-09-11",
                 "--work-root", str(ext)]) == 0
    assert (ext / "2026-09-11-x" / "dummy-01" / "task.md").exists()
    assert str(ext) in capsys.readouterr().out


def test_prepare_unknown_task(tmp_path):
    with pytest.raises(ValueError, match="タスクがありません"):
        prepare(tmp_path, "nope-99", "x", date="2026-09-11")


def test_prepare_refuses_existing_without_force(tmp_path):
    make_dummy_task(tmp_path)
    prepare(tmp_path, "dummy-01", "codex", date="2026-09-11")
    with pytest.raises(FileExistsError, match="--force"):
        prepare(tmp_path, "dummy-01", "codex", date="2026-09-11")
    run_dir = prepare(tmp_path, "dummy-01", "codex", date="2026-09-11", force=True)
    assert (run_dir / "data.txt").exists()


def test_prepare_default_date_is_today(tmp_path):
    import datetime
    make_dummy_task(tmp_path)
    run_dir = prepare(tmp_path, "dummy-01", "a")
    assert run_dir.parent.name == f"{datetime.date.today().isoformat()}-a"


def test_main_reports_error_code(tmp_path, capsys):
    assert main(["nope-99", "x", "--root", str(tmp_path)]) == 1
    assert "エラー" in capsys.readouterr().err
    make_dummy_task(tmp_path)
    assert main(["dummy-01", "x", "--root", str(tmp_path), "--date", "2026-09-11"]) == 0
    assert "dummy-01" in capsys.readouterr().out
