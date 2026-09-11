# office-agent-bench

AIエージェント(Claude Code / Codex など)が、普通のサラリーマン・公務員が毎日やっている事務仕事をどこまでこなせるかを測るベンチマーク。
Excel・Word・メール・Web調査・データ更新の5領域、15タスクの仕様カタログ(`CATALOG.md`)と、そのうち5タスクを実際に回せる実行キット(`tasks/`)からなる。

- ファイルベース: 入力ファイルを渡し、成果物ファイルを採点する。GUI操作は測らない
- 採点は Python の自動チェック + 人の目チェックリスト。追加コストゼロ
- 日本語。題材は会社員業務と市役所業務を半々

## セットアップ

```bash
pip3 install -r requirements.txt
python3 tools/selftest.py     # チェッカーの健全性確認(全部 OK になること)
python3 tools/selftest.py excel-01 word-01   # タスクIDを並べるとそのタスクだけ確認する
python3 -m pytest tests/ -q   # 開発用テスト
```

## 実行手順(どのエージェントでも同じ)

1. 作業フォルダを作る(推奨: リポジトリの外に作る)

   ```bash
   python3 tools/prepare.py excel-01 claude-code --work-root ~/office-agent-bench-work
   ```

   `~/office-agent-bench-work/<今日>-claude-code/excel-01/` に入力ファイルと `task.md` がコピーされる。

   リポジトリの外で作業させるのは、採点の答えがエージェントから見えないようにするため。Claude Code は作業フォルダの上位フォルダにある `CLAUDE.md` を自動で読み込むし、リポジトリ内に作業フォルダを置くと `../../../tasks/<id>/expected/` という相対パスで正解データにも届いてしまう。採点後の記録は `score.py` が自動で `runs/` にコピーするので、実行記録は今までどおり残る。

   簡単に済ませたいなら `--work-root` を省いてもよい(`runs/<今日>-claude-code/excel-01/` にできる)。その場合は `runs/CLAUDE.md` の指示でエージェントに作業フォルダの外を見ないよう念押ししている。

   オプション: `--date YYYY-MM-DD`(実行日を指定。既定は今日)、`--force`(既存の作業フォルダを消して作り直す)。同じ日に同じタスクをもう一度回すならエージェント名を `claude-code-2` のように変える。

2. その作業フォルダでエージェントを起動し、「task.md を読んで実行して」と頼む。作業中に所要時間と、エージェントが人に確認を求めた回数を控える。エージェントには作業フォルダの外(特にこのリポジトリの中)を見せない。

3. 自動判定を実行する

   ```bash
   python3 tools/score.py ~/office-agent-bench-work/<今日>-claude-code/excel-01
   ```

   作業フォルダに `result.json` と `result.md` ができる。作業フォルダがリポジトリの `runs/` の外にある場合は、そのフォルダ一式が `runs/<今日>-claude-code/excel-01/` にコピーされる(コピー先が既にあるときは `--force` で作り直す)。`--force` は `result.md` の上書きにも必要。

4. 記録用フォルダ(`runs/<今日>-<エージェント名>/<task-id>/`)の `result.md` の「人の目チェック」のチェックボックスを埋め(合格は `- [x]`)、「補助指標」の所要時間・質問回数・トークン・メモを書く。集計はこの `runs/` 側を読む。

5. 集計する

   ```bash
   python3 tools/summary.py
   ```

   エージェント別×領域別の平均点、達成タスク数、タスク別明細が Markdown で出る。同じエージェント・同じタスクは最新の実行日だけ採用(`--all` で全部)。

## 採点の考え方

- 各タスクは自動項目 + 人の目項目の 5〜10 項目。全項目 pass/fail、等ウェイト
- タスク点 = pass 数 ÷ 項目数 × 100。全項目 pass で「達成」
- 所要時間・質問回数・トークンは記録するだけで点数には入れない
- Web調査タスクの正解には確認日が付いている。サイト改編で変わったら `expected/values.json` と `make_fixtures.py` を直す

## 構成

```
tasks/<task-id>/
├── task.md          エージェントに渡す指示文
├── input/           渡すファイル
├── expected/        模範成果物と正解値(values.json)。エージェントには見せない
├── check.py         自動チェッカー: python3 check.py <作業フォルダ> → JSON
├── rubric.md        人の目チェックリスト
└── make_fixtures.py input/ と expected/ を再生成する
tools/prepare.py   作業フォルダを作る
tools/score.py     自動判定 → result.json / result.md
tools/summary.py   runs/ を集計
tools/selftest.py  「模範成果物なら満点・未着手なら満点にならない」を確認
bench/             共通ライブラリ(チェック実行・メール解析・docx テキスト抽出)
runs/              実行記録(成果物ごと git 管理)。CLAUDE.md でエージェントに作業フォルダの外を見ないよう指示している
```

## タスクを追加するには

1. `CATALOG.md` に仕様を書く(内容・入力・成果物・自動チェック・人の目チェック)
2. `tasks/<id>/make_fixtures.py` で `input/` と `expected/` を生成(乱数はシード固定)
3. `task.md`(上司がチャットで頼む口調。手順は書かない)、`rubric.md`(`- ` 箇条書き)
4. `check.py` に `build_checks(run_dir)` を書き、`bench.checks.main` で出力
5. `tests/test_task_checkers.py` の `KIT_TASKS` に追加し、壊した成果物で落ちるテストも書く
6. `python3 tools/selftest.py` が OK になることを確認
