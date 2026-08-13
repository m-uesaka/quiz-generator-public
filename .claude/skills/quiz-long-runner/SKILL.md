---
name: quiz-long-runner
description: 指定した時刻まで、または指定したバッチ数だけ作問サイクルを繰り返す。「○時まで作問して」「10バッチ作って」「続きから作問して」と言われたときに使う。
argument-hint: "[終了時刻 または バッチ数] [ジャンル指定（省略可）]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Task
disable-model-invocation: true
---

# 長時間の連続作問

`quiz-batch` のサイクルを繰り返します。

## 開始時に一度だけ行うこと

1. 終了条件を確定する。
   - `$ARGUMENTS` が時刻（例: `JST 20:59`、`今日の23時`）なら、`date` コマンドで現在時刻を確認し、
     残り時間から実行可能なサイクル数の目安を出して人間に伝える。
   - `$ARGUMENTS` がバッチ数なら、その回数。
   - 「続きから」と言われた場合は `work/` の最大 batch 番号を確認し、その次から始める。
2. `uv run scripts/clip_index.py --rebuild` と `uv run scripts/registry.py rebuild` を実行する。
3. 未使用クリップの残数を確認する。`uv run scripts/clip_index.py --unused -n 200 | wc -l`
   残りが `目標バッチ数 × 4` に満たない場合、**その旨を先に人間に伝えてから**始める
   （クリップが尽きたら勝手に web から題材を探してはいけない）。
4. `LEARNINGS.md` と `config/*.md` を読む。**サイクルごとに読み直す必要はないが、
   `/quiz-learn` が走った直後は必ず読み直すこと。**

## ループ

各サイクルで:

1. `.claude/skills/quiz-batch/SKILL.md` の手順を実行する。
2. サイクル終了ごとに 1 行だけ進捗を出す。
   `batch007 完了: 採用3/生成4 (自然科学, 地理, 生活) 累計 28問 残り約4サイクル`
3. 終了条件を満たしたら停止する。

## 停止条件（終了時刻の前でも止まる）

- 未使用クリップが 4 件を切った → 停止し、クリップの追加を促す
- 3 サイクル連続で採用数が 2 問以下 → 停止し、原因（クリップの質・LEARNINGS の矛盾・裏取り失敗）を報告
- 同じエラーが 2 回続いた → 停止して報告
- 人間から「止めて」と言われた → 現在のサイクルの結果を `work/` に保存してから停止

## 終了時

- 累計の採用数、ジャンル配分（`uv run scripts/registry.py stats`）、未使用クリップの残数を報告する。
- レビュー待ちのバッチ一覧を出す。

## 注意

- 途中で `LEARNINGS.md` や `config/` を勝手に書き換えない。ルールの更新は `/quiz-learn` の仕事。
- 品質が落ちてきたと感じたら、数を作るより止めて報告する方がよい。
