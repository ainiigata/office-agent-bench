import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def repo_root() -> Path:
    return ROOT


def make_dummy_task(root: Path, task_id: str = "dummy-01") -> Path:
    """tools/ のテスト用に、最小構成のタスクフォルダを root/tasks/<task_id>/ に作る。
    成果物 output.txt に 'hello' が書いてあれば合格、無ければ不合格になる check.py を持つ。"""
    task = root / "tasks" / task_id
    (task / "input").mkdir(parents=True)
    (task / "expected").mkdir()
    (task / "input" / "data.txt").write_text("元データ\n", encoding="utf-8")
    (task / "expected" / "output.txt").write_text("hello\n", encoding="utf-8")
    (task / "expected" / "values.json").write_text('{"word": "hello"}', encoding="utf-8")
    (task / "task.md").write_text("# ダミー\n\noutput.txt に hello と書いて。\n", encoding="utf-8")
    (task / "rubric.md").write_text(
        "# 人の目チェック: dummy-01\n- 文字が丁寧\n- 余計なファイルがない\n", encoding="utf-8"
    )
    (task / "check.py").write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "run = Path(sys.argv[1])\n"
        "p = run / 'output.txt'\n"
        "ok = p.exists() and 'hello' in p.read_text(encoding='utf-8')\n"
        "print(json.dumps([{'id': 'has_hello', 'name': 'hello がある', 'pass': ok, 'detail': ''},"
        " {'id': 'always', 'name': '常に合格', 'pass': True, 'detail': ''}], ensure_ascii=False))\n",
        encoding="utf-8",
    )
    return task
