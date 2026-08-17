---
name: quiz-learn
description: 人間が修正した YAML と生成物の差分を読み、修正の意図をルール化して LEARNINGS.md を更新する。「学習して」「LEARNINGSを更新して」「レビュー結果を反映して」と言われたときに使う。
argument-hint: "[バッチID（例: batch001）。省略時は未処理のバッチすべて]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# 人手修正から学ぶ

このスキルが、生成 → 人手修正 → 次の生成、のループを閉じます。

## 1. 差分を取る

```bash
uv run scripts/review_diff.py output/batchNNN.yaml reviewed/batchNNN.yaml -o state/diff-batchNNN.yaml
```

`reviewed/` がなく、`output/` を git 管理下で直接編集している場合:

```bash
git show HEAD:output/batchNNN.yaml > /tmp/base-batchNNN.yaml
uv run scripts/review_diff.py /tmp/base-batchNNN.yaml output/batchNNN.yaml -o state/diff-batchNNN.yaml
```

バッチ ID の指定がない場合は、`reviewed/*.yaml` のうち対応する `state/diff-*.yaml` が
まだ無いものをすべて処理する。

## 2. 差分を読む

`state/diff-batchNNN.yaml` を読む。あわせて、その問題の `work/batchNNN.yaml` の
`meta`（出典・検証ログ・適用した LEARNINGS）も読む。**なぜその生成物になったのか**が分からないと、
正しいルールは書けない。

`hints` はスクリプトの機械的な推定にすぎない。鵜呑みにせず自分で分類する。

## 3. 分類する — ここが一番大事

各差分を次の 3 つに仕分ける。

### (a) 一般化できる修正 → ルールにする

同種の生成物に対して次回も同じ判断が下せるもの。

- 文体・語順・長さ・疑問詞の選び方
- ネタバレの判定基準（「この種の語は答えの一部とみなす」）
- criteria の入れ方の癖（「かな表記は常に ok に入れる」）
- tags の粒度・語彙
- 題材の好み（「この種の題材は毎回落とされている」）
- 出典の質の基準（「この種の媒体は根拠にならない」）

### (b) その問題固有の修正 → ルールにしない

- 単発の事実誤り（「その年号が間違っていた」）
- 特定の固有名詞の表記
- 特定の別解の追加

ただし**同種の誤りが 3 回以上出ていれば (a) に昇格させる**。
例: 単発の事実誤りが続く場合 → 「企業名は法人格の有無まで公式サイトで確認する」というルールにできる。

### (c) 意図が読めない修正 → 人間に聞く

推測でルールを書かない。1 回の実行につき**最大 3 問まで**、人間に質問してよい。

> batch003-02 の「1969年に誕生した」を「1969年に発売された」に直されていますが、
> これは(1) 事実として誕生≠発売だったからですか、(2) 商品には「発売」を使う方針ですか？

聞けない状況（非対話実行）なら `watch` に「意図不明」と明記して置く。

## 4. LEARNINGS.md を更新する

- 新しい観測は `watch` に追加する。
- `watch` にある既存ルールと同じ内容なら、再発回数を増やす。
  `settings.yaml` の `promote_to_active_after` に達したら `active` に移す。
- `active` のルールが `graduate_to_guide_after` 回以上定着したら、内容に応じて
  `config/quiz_question_style_guide.md`（問題文の構造・文体）、
  `config/quiz_notation_rules.md`（answer/spell/criteria の表記）、
  `config/quiz_topic_taste_guide.md`（題材選び）、
  `config/quiz_topic_framing_guide.md`（切り口の型）のいずれかに本文として書き、
  LEARNINGS 側は `graduated` に移す（本文はガイドに一本化し、二重管理しない）。
- 既存ルールと矛盾する新ルールが出たら、古い方に `superseded_by: R-NNNN` を書いて `graduated` に落とす。
- `active` が `max_active_rules` を超えたら、似たルールを統合する。

ルールの書式は `LEARNINGS.md` 冒頭のコメント例に厳密に従う。ID は既存の最大値 + 1。**ID は再利用しない。**

`LEARNINGS.md` の active セクションを書き換えたら（追加・昇格・統合・superseded_by の付与など、
active の内容が変わる操作をしたら）必ず以下を実行し、生成エージェント用の抜粋ファイルを更新する。
これを忘れると `quiz-batch` のサブエージェントが古いルールを読み続ける。

```bash
uv run scripts/extract_active_learnings.py
```

### 良いルールの条件

- 生成時に**そのまま適用できる**こと。「もっと自然な日本語にする」は不可。
  「『〜において』は『〜で』に置き換える」は可。
- どのエージェントが検査するか書いてあること。
- Before / After の実例がついていること。
- 「なぜ」が書いてあること（理由が分かるとエージェントが応用できる）。

## 5. 統計を更新する

`LEARNINGS.md` 末尾の統計表に 1 行足す。

| バッチ | 生成数 | 無修正 | 修正 | 削除 | 主な修正カテゴリ |

`review_diff.py` の `summary` の数字をそのまま使う。

## 6. 報告する

- 追加したルール ID と一行要約
- 昇格・統合・廃止したルール
- 人間に確認したいこと（あれば）
- **どのエージェントの指示を直すべきかの提案**
  （例: 修正の 7 割が style だった → `quiz-style-reviewer.md` の検査項目が足りていない）

## やってはいけないこと

- 差分を見ずに「よくある注意点」を一般論として書くこと。**必ず実際の差分だけを根拠にする。**
- 1 件の修正から大げさな一般則を作ること（それは `watch` 止まり）。
- 人間が消した問題を「不採用の理由が分からないから」と無視すること。
  削除は最も強いシグナルなので、必ず仮説を立てるか質問する。
- `output/` や `reviewed/` を書き換えること。このスキルは `LEARNINGS.md` と `config/` だけを書く。
- `config/learnings_active.md` を直接編集すること。これは `LEARNINGS.md` から自動生成される
  ファイルなので、必ず `LEARNINGS.md` を直してから `scripts/extract_active_learnings.py` を実行する。
