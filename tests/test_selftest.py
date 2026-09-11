from tests.conftest import make_dummy_task
from tools.selftest import build_run_dir, main, run_selftest


def test_build_run_dir_copies_input_and_expected_without_values_json(tmp_path):
    task = make_dummy_task(tmp_path)
    d = build_run_dir(task, tmp_path / "a", with_expected=True)
    assert (d / "data.txt").exists() and (d / "output.txt").exists()
    assert not (d / "values.json").exists()
    e = build_run_dir(task, tmp_path / "b", with_expected=False)
    assert (e / "data.txt").exists() and not (e / "output.txt").exists()


def test_run_selftest_ok_for_sound_checker(tmp_path):
    make_dummy_task(tmp_path)
    [r] = run_selftest(tmp_path)
    assert r["task_id"] == "dummy-01"
    assert r["expected_all_pass"] and r["untouched_not_all_pass"] and r["error"] is None


def test_run_selftest_flags_checker_that_always_passes(tmp_path):
    task = make_dummy_task(tmp_path, "loose-01")
    (task / "check.py").write_text(
        "import json; print(json.dumps([{'id': 'a', 'name': '甘い', 'pass': True, 'detail': ''}]))\n",
        encoding="utf-8")
    [r] = run_selftest(tmp_path, ["loose-01"])
    assert r["expected_all_pass"] and not r["untouched_not_all_pass"]


def test_run_selftest_flags_checker_failing_on_expected(tmp_path):
    task = make_dummy_task(tmp_path, "strict-01")
    (task / "check.py").write_text(
        "import json; print(json.dumps([{'id': 'a', 'name': '厳しすぎ', 'pass': False, 'detail': 'x'}]))\n",
        encoding="utf-8")
    [r] = run_selftest(tmp_path, ["strict-01"])
    assert not r["expected_all_pass"] and r["expected_failures"] == ["厳しすぎ"]


def test_main_exit_code(tmp_path, capsys):
    make_dummy_task(tmp_path)
    assert main(["--root", str(tmp_path)]) == 0
    assert "OK" in capsys.readouterr().out
    task = make_dummy_task(tmp_path, "loose-01")
    (task / "check.py").write_text(
        "import json; print(json.dumps([{'id': 'a', 'name': 'x', 'pass': True, 'detail': ''}]))\n", encoding="utf-8")
    assert main(["--root", str(tmp_path)]) == 1
    assert "NG" in capsys.readouterr().out
