---
name: quiz-export
description: レビュー済みのクイズをまとめて1つの YAML に書き出し、quiz-yaml-go で CSV / HTML / Markdown に変換する。「書き出して」「CSVにして」「まとめて出力して」と言われたときに使う。
argument-hint: "[バッチID または all] [csv|html|markdown]"
allowed-tools: Read, Write, Bash, Glob
---

# 書き出し

## 1. まとめる

レビュー済み（`reviewed/`）を優先し、未レビューのバッチは `output/` を使う。

```bash
uv run scripts/export_yaml.py work/batch*.yaml -o output/all.yaml --merge
```

すでにレビュー済みのものを含める場合は、`reviewed/*.yaml` をそのまま結合してよい
（`reviewed/` は既にスキーマ準拠のため変換不要）。

## 2. 検証する

```bash
quiz-yaml-converter -input output/all.yaml -validate
```

エラーが出たら該当箇所を直してから先に進む。`output/` を直す場合でも、
元になった `work/` にも同じ修正を反映すること（次回の差分が汚れるため）。

## 3. 変換する

```bash
quiz-yaml-converter -input output/all.yaml -output dist/quiz.csv
quiz-yaml-converter -input output/all.yaml -output dist/quiz.html -format html
quiz-yaml-converter -input output/all.yaml -output dist/quiz.md -format markdown
```

## 4. アーカイブする

確定した問題群は `archive/` に移す。移した後に必ずレジストリを更新する。

```bash
uv run scripts/registry.py rebuild
uv run scripts/registry.py stats
```

## 注意

- `quiz-yaml-converter` が PATH にない場合は、リポジトリを clone して
  `go run main.go -input ... -validate` を使う。
- 出典 URL を成果物に含めたくない場合は、`config/settings.yaml` の
  `output.include_sources_in_comments` を `false` にしてから再エクスポートする。
