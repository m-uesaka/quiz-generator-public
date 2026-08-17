---
name: quiz-batch
description: Obsidian のクリップから1バッチ分（既定4問）のクイズを作る。題材探し→作問→別解検証→文体確認→採否確定の1サイクルを回す（裏取りは通常省略し人間のレビュー時に行う）。「クイズを作って」「作問して」「1バッチ作って」と言われたときに使う。
argument-hint: "[ジャンルやテーマの指定（省略可）]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Task
---

# 1バッチ分のクイズを作る

作問サイクルを 1 回まわします。所要時間の目安は 20〜30 分です。

## 0. 準備（毎回必ず行う）

```bash
uv run scripts/clip_index.py --rebuild
uv run scripts/registry.py rebuild
uv run scripts/extract_active_learnings.py
```

続けて以下を読む。**読まずに始めないこと。**

- `config/learnings_active.md`（`LEARNINGS.md` の active セクションのみを抜粋した自動生成ファイル。
  サブエージェントにもこちらを読ませる。`LEARNINGS.md` 本体は人間が読む・`/quiz-learn` が更新する用で、
  watch / graduated / 統計まで含むため生成サイクルでは読まない）
- `config/quiz_question_style_guide.md`（問題文の構造・文体）
- `config/quiz_notation_rules.md`（answer/spell/criteria の表記ルール）
- `config/quiz_topic_taste_guide.md`（題材選びの好み）
- `config/quiz_topic_framing_guide.md`（切り口の型・情報の組み合わせ方）
- `config/settings.yaml`

  各サブエージェントは上記4ファイルのうち自分の工程に必要な範囲だけを読む
  （詳細は各 `.claude/agents/*.md` の「必読」）。ここでオーケストレーター自身が
  全文に目を通しておくのは、後工程の出力が方針からズレていないか判断できるようにするため。

`$ARGUMENTS` にジャンルやテーマの指定がある場合は、それを clip-scout に渡す。

## 1〜5. 各工程

各工程は Task ツールで対応するサブエージェントに委譲する。
**サブエージェントは互いに会話できない。** 前工程の出力を、次のエージェントへのプロンプトに
そのまま貼り付けて渡すこと（ファイルパス・URL・問題文の全文を省略しない）。
**例外は工程5（`quiz-final-editor`）への引き渡しだけ**（下記「工程5への引き渡しは確定レコードだけに絞る」参照）。

| # | エージェント | 入力 | 出力 |
| --- | --- | --- | --- |
| 1 | `clip-scout` | ジャンル指定 | 本命4件＋補欠2件の題材候補（`settings.yaml` の `batch.primary_candidates`/`backup_candidates`） |
| 2 | `quiz-writer` | 題材候補（全文） | 問題文ドラフト＋参考にした `sources`（URL） |
| 3 | `quiz-adversarial-checker` | ドラフト | 一意性判定と criteria |
| 4 | `quiz-style-reviewer` | ここまでの確定問題文 | 文体指摘と修正案＋**確定レコード**（pass/fix_to_passのみ） |
| 5 | `quiz-final-editor` | 確定レコード一式（＋reject理由一覧） | `work/batchNNN.yaml` と採否 |

工程 3〜4 は前の工程の修正を反映してから次に渡す。
工程 3 で `reject` が出て本命が `primary_candidates`（既定4）件を割ったら、補欠候補を工程 2 から投入する。

### 工程5への引き渡しは確定レコードだけに絞る（トークン節約）

工程 5（`quiz-final-editor`）は毎バッチで本命4件分の判定結果を受け取るため、
工程2〜4の出力をすべてそのまま貼り付けると入力トークンが膨らみやすい。
工程5に渡すのは以下だけにする。

- `quiz-style-reviewer` が候補ごとに出した**確定レコード**（pass / fix_to_pass の候補のみ）
- reject になった候補は、どの工程で reject したかと一言理由だけ（詳しい検討過程は渡さない）

`quiz-writer` の草稿本文、「試した別解」「検証してほしい主張」などの検討過程・修正のやりとりは
工程5には転記しない。工程3・4の間では引き続き必要な情報（問題文・criteria・sources 等）を
省略せず渡すこと。省略していいのは工程5への最終ハンドオフだけ。

### quiz-fact-checker は普段の1サイクルでは呼ばない

このプロジェクトは human-in-the-loop を前提にしており、事実の裏取りは人間がレビュー時
（`reviewed/batchNNN.yaml` を編集するとき）に行うか、複数バッチをまとめて後から行う想定。
毎バッチ律儀に裏取りすると時間がかかりすぎるため、通常サイクルでは省略する。

- 省略する代わりに、`quiz-writer` が出した `sources`（作問のために参照した URL。クリップ URL と
  web 補完先の両方）を必ず `work/batchNNN.yaml` の `meta.sources` にそのまま残し、
  人間がすぐ裏取りできるようにする。
- `quiz-writer` は「検証してほしい主張」がバッチ内で多い（半数以上、または裏取りが弱くなりがちな
  主張の型が2件以上重なる）場合、確定稿を出す前に自分で1〜2回の軽い WebSearch を行い、
  裏付けを試みる（`.claude/agents/quiz-writer.md` 手順4）。quiz-fact-checker を呼ぶほどではない
  軽量な自衛策であり、それでも裏取りできなかった主張は引き続き `sources` と共に人間のレビューに委ねる。
- `quiz-final-editor` は「fact-checker の pass」を採用条件にしない（下記の通り）。
- 明らかに怪しい主張（最上級表現・年号・因果関係など）に人間の目で気付いた場合や、
  人間から個別に指示があった場合は、その問題だけ `quiz-fact-checker` を呼んでよい。

## 6. 完了報告

`quiz-final-editor` の報告をそのまま人間に返す。加えて、採用した各問題の `meta.sources`
（quiz-writer が参照した URL）を一覧で示す。**この sources が唯一の裏取り材料であり、
未検証であることを明示する。** 続けて次の 1 行を必ず添える。

```
人間のレビュー待ち（sources は未検証）: cp output/batchNNN.yaml reviewed/batchNNN.yaml して編集し、終わったら /quiz-learn batchNNN
```

## 注意

- 1 サイクルで作るのは `settings.yaml` の `target_accepted` 問まで。多く作ろうとしない。
- fact-checker を通していない前提で、`sources` が 1 件もない問題は不採用にする。問題数を埋めるために採用基準を下げない。
- クリップに書かれていない事実を「たぶんこうだろう」で補わない。web で確認するか、落とす。
- 途中で人間から中断の指示があれば、その時点までの結果を `work/` に書いてから止める。
