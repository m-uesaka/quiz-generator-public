# 更新履歴

*[English version](CHANGELOG.en.md)*

このドキュメントは `quiz-generator` リポジトリのバージョンごとの主な変更点をまとめたものです。
[Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [v1.1] - 2026-08-17

### Added

- `pyproject.toml` を導入し、`uv sync` でエディタ補完・型チェック・lint（ruff）・テスト（pytest）用の
  ローカル仮想環境を作れるようにした。
- 依存関係を固定する `uv.lock` を追加。

### Changed

- `scripts/*.py` を CLI 層（typer によるコマンド定義）と `scripts/quiz_generator/*.py` のロジック層に分離。
  - 従来 1 ファイルにまとまっていた `scripts/quizlib.py` を廃止．
  - `quizlib.py`の内容を`scripts/quiz_generator/`内で複数ファイルに分割して整理した．
- `config/`にあるファイルの分割
  - `config/quiz_question_style_guide.md` から answer/spell 欄・criteria の表記ルールを
  `config/quiz_notation_rules.md` に切り出した．
  - `config/quiz_topic_taste_guide.md` から切り口の型・情報の組み合わせ方を `config/quiz_topic_framing_guide.md` に切り出した。
  - 各サブエージェント定義 （`.claude/agents/*.md`）も新しいファイル構成を参照するよう更新。
  - これにより，各サブエージェントが必要なファイルだけを読む設計にしてコストを節約している．

### Fixed

- `CLAUDE.md` / `README.md` が `quiz-fact-checker` を含む 6 工程のサイクルを記述していたが、
  `docs/architecture.md` と実装（`SKILL.md`・各エージェント定義）は通常サイクルから
  `quiz-fact-checker` を除外する設計になっており矛盾していた。記述を実装に合わせて修正。
- `quiz-batch/SKILL.md` の題材候補数が `8` 件に決め打ちされていたが、`config/settings.yaml` の
  設定値（既定 `4` 件）と食い違っていたため修正。
- `.gitignore` が `/quiz-export` の出力先である `dist/` を誤って無視していたため修正。
- `docs/architecture.md` のスクリプト一覧が、存在しない `quizlib.py` を共通ヘルパとして
  挙げていたため、実際の `scripts/quiz_generator/` パッケージ構成に合わせて修正。あわせて
  `README.md` に `pyproject.toml` 導入後のローカル環境構築手順（`uv sync` / venv activate /
  `ruff` / `pytest`）を追記。

## [v1.0] - 2026-08-14

最初のリリース。クリップ索引化・既出レジストリ・YAML 変換・差分抽出のスクリプト群と、
`clip-scout` → `quiz-writer` → `quiz-adversarial-checker` → `quiz-style-reviewer` →
`quiz-final-editor` の 5 段階サブエージェント連携、および `LEARNINGS.md` への還流ループを含む。
