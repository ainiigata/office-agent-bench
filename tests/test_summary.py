import json

from tools.summary import RunResult, collect, latest, main, parse_manual, render


def _write_run(root, date, agent, task_id, auto, manual_md):
    d = root / "runs" / f"{date}-{agent}" / task_id
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps({
        "task_id": task_id, "agent": agent, "date": date, "run_dir": "x", "checked_at": "t",
        "auto": [{"id": f"i{n}", "name": f"項目{n}", "pass": p, "detail": ""} for n, p in enumerate(auto)],
        "manual_total": manual_md.count("- ["),
    }, ensure_ascii=False), encoding="utf-8")
    (d / "result.md").write_text(
        f"# {task_id} / {agent} / {date}\n\n## 自動判定\n\n| 項目 | 合否 | 詳細 |\n|---|---|---|\n\n"
        f"## 人の目チェック\n\n{manual_md}\n## 補助指標\n\n所要時間: 10分\n質問回数: 0\nトークン: \nメモ: - [ ] これは数えない\n",
        encoding="utf-8")


def test_parse_manual_counts_only_manual_section():
    md = "## 人の目チェック\n\n- [x] A\n- [ ] B\n- [X] C\n\n## 補助指標\n\nメモ: - [ ] no\n"
    assert parse_manual(md) == (2, 3)
    assert parse_manual("## 人の目チェック\n\n(なし)\n") == (0, 0)


def test_run_result_score_and_domain():
    r = RunResult("excel-01", "a", "2026-09-11", 4, 5, 1, 2)
    assert r.total == 7 and r.passed == 5 and r.score == 71.4 and r.achieved is False
    assert r.domain == "Excel"
    assert RunResult("web-02", "a", "d", 6, 6, 2, 2).achieved is True


def test_collect_and_latest(tmp_path):
    _write_run(tmp_path, "2026-09-10", "claude-code", "excel-01", [True, False], "- [x] A\n- [ ] B\n")
    _write_run(tmp_path, "2026-09-11", "claude-code", "excel-01", [True, True], "- [x] A\n- [x] B\n")
    _write_run(tmp_path, "2026-09-11", "codex", "mail-03", [True, False, False], "- [ ] A\n")
    results = collect(tmp_path)
    assert len(results) == 3
    picked = latest(results)
    assert len(picked) == 2
    cc = next(r for r in picked if r.agent == "claude-code")
    assert cc.date == "2026-09-11" and cc.score == 100.0
    cx = next(r for r in picked if r.agent == "codex")
    assert cx.auto_pass == 1 and cx.manual_total == 1 and cx.score == 25.0


def test_render_tables(tmp_path):
    _write_run(tmp_path, "2026-09-11", "claude-code", "excel-01", [True, True], "- [x] A\n- [x] B\n")
    _write_run(tmp_path, "2026-09-11", "claude-code", "mail-03", [True, False], "- [ ] A\n")
    md = render(latest(collect(tmp_path)))
    assert "| claude-code |" in md
    assert "Excel" in md and "メール" in md and "全体" in md
    assert "100.0" in md and "33.3" in md
    assert "excel-01" in md and "mail-03" in md


def test_collect_skips_broken_result_json(tmp_path, capsys):
    """壊れた result.json が1つあっても、他の実行記録の集計は続く。"""
    _write_run(tmp_path, "2026-09-11", "claude-code", "excel-01", [True, True], "- [x] A\n- [x] B\n")
    broken = tmp_path / "runs" / "2026-09-11-claude-code" / "word-01"
    broken.mkdir(parents=True)
    (broken / "result.json").write_text('{"task_id": "word-01", "auto": [', encoding="utf-8")
    no_task_id = tmp_path / "runs" / "2026-09-11-codex" / "mail-03"
    no_task_id.mkdir(parents=True)
    (no_task_id / "result.json").write_text('{"agent": "codex", "auto": []}', encoding="utf-8")
    results = collect(tmp_path)
    assert [r.task_id for r in results] == ["excel-01"]
    err = capsys.readouterr().err
    assert err.count("警告:") == 2 and "word-01" in err and "mail-03" in err
    assert "スキップします" in err


def test_main_renders_despite_broken_result_json(tmp_path, capsys):
    _write_run(tmp_path, "2026-09-11", "claude-code", "excel-01", [True, True], "- [x] A\n- [x] B\n")
    broken = tmp_path / "runs" / "2026-09-11-codex" / "excel-01"
    broken.mkdir(parents=True)
    (broken / "result.json").write_text("これは JSON ではない", encoding="utf-8")
    assert main(["--root", str(tmp_path)]) == 0
    captured = capsys.readouterr()
    assert "| claude-code |" in captured.out and "100.0" in captured.out
    assert "警告:" in captured.err


def test_render_empty():
    assert "まだ実行記録がありません" in render([])
