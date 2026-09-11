# office-agent-bench

AIエージェントの事務仕事ベンチマーク。使い方・構成は README.md、タスク仕様は CATALOG.md、設計の経緯はワークスペースの `docs/superpowers/specs/2026-09-11-office-agent-bench-design.md`。

## 作業時の注意

- 採点用の正解データはエージェントの作業フォルダから参照させない。ベンチマークを回すときは README の隔離手順(`prepare.py --work-root`)に従い、リポジトリの外で作業させる
- チェッカーを直したら `python3 tools/selftest.py` と `python3 -m pytest tests/ -q` を必ず通す
- フィクスチャは `make_fixtures.py` から再生成する。生成物を手で直さない
- フィクスチャの自治体・団体・学校・人物はすべて架空(市は「みなと市」に統一)。実在の役所名・団体名を書かない
- Web調査タスクの正解は確認日付き。正解を変えたら `values.json` の `verified_on` も更新する
- 有料API・従量課金の仕組みは使わない(全プロジェクト共通ルール)
