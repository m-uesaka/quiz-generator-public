---
name: quiz-batch
description: Obsidian のクリップから1バッチ分（既定4問）のクイズを作る。題材探し→作問→裏取り→別解検証→文体確認→採否確定の1サイクルを回す。「クイズを作って」「作問して」「1バッチ作って」と言われたときに使う。
argument-hint: "[ジャンルやテーマの指定（省略可）]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Task
---

# 1バッチ分のクイズを作る

作問サイクルを 1 回まわします。所要時間の目安は 20〜30 分です。

## 0. 準備（毎回必ず行う）

```bash
uv run scripts/clip_index.py --rebuild
uv run scripts/registry.py rebuild
```

続けて以下を読む。**読まずに始めないこと。**

- `LEARNINGS.md` の active セクション
- `config/quiz_question_style_guide.md`
- `config/quiz_topic_taste_guide.md`
- `config/settings.yaml`

`$ARGUMENTS` にジャンルやテーマの指定がある場合は、それを clip-scout に渡す。
指定がなければ `uv run scripts/registry.py stats` を見て、目標に対して不足しているジャンルを狙う。

## 1〜6. 各工程

各工程は Task ツールで対応するサブエージェントに委譲する。
**サブエージェントは互いに会話できない。** 前工程の出力を、次のエージェントへのプロンプトに
そのまま貼り付けて渡すこと（ファイルパス・URL・問題文の全文を省略しない）。

| # | エージェント | 入力 | 出力 |
| --- | --- | --- | --- |
| 1 | `clip-scout` | ジャンル指定 | 本命4件＋補欠2件の題材候補 |
| 2 | `quiz-writer` | 題材候補（全文） | 問題文ドラフト |
| 3 | `quiz-fact-checker` | ドラフト＋検証してほしい主張＋quiz-writer の `sources`（省略せず渡す） | pass / fix_to_pass / reject と出典 |
| 4 | `quiz-adversarial-checker` | 裏取り後のドラフト | 一意性判定と criteria |
| 5 | `quiz-style-reviewer` | ここまでの確定問題文 | 文体指摘と修正案 |
| 6 | `quiz-final-editor` | 全工程の結果 | `work/batchNNN.yaml` と採否 |

工程 3〜5 は前の工程の修正を反映してから次に渡す。
工程 3 で `reject` が出て本命が 4 件を割ったら、補欠候補を工程 2 から投入する。

## 7. 完了報告

`quiz-final-editor` の報告をそのまま人間に返す。加えて次の 1 行を必ず添える。

```
人間のレビュー待ち: cp output/batchNNN.yaml reviewed/batchNNN.yaml して編集し、終わったら /quiz-learn batchNNN
```

## 注意

- 1 サイクルで作るのは `settings.yaml` の `target_accepted` 問まで。多く作ろうとしない。
- 裏取りが取れないなら不採用にする。問題数を埋めるために採用基準を下げない。
- クリップに書かれていない事実を「たぶんこうだろう」で補わない。web で確認するか、落とす。
- 途中で人間から中断の指示があれば、その時点までの結果を `work/` に書いてから止める。
