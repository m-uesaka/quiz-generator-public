# quiz-generator

Claude Code で、**Obsidian に溜めた web クリップから日本語クイズを自動作問する**ための作業用リポジトリ雛形です。

このリポジトリは[AIによるクイズの自動作問](https://note.com/alocasia011/n/n11581c6e4dc7?sub_rt=share_pw)を参考にしていますが，以下の点が異なります．

参考にした仕組み（Codex + 6エージェント）からの主な変更点:

| | 参考記事 | このリポジトリ |
| --- | --- | --- |
| 題材源 | web から自動探索 | **Obsidian のクリップ**（不足分だけ web で補完） |
| 実行環境 | Codex CLI + TOML | **Claude Code の Skills + Subagents** |
| 出力形式 | JSONL | **quiz-yaml-go スキーマの YAML** |
| 人手修正 | 選定ソフトで採否 | 修正差分を **`LEARNINGS.md`** に還流して次の生成に効かせる |

## セットアップ

```bash
# 1. このディレクトリを好きな場所に置いて git 管理下にする
git init && git add -A && git commit -m "init"

# 2. クリップの場所を設定
$EDITOR config/settings.yaml   # paths.clip_dir を自分の Obsidian のパスに

# 3. 索引を作る（PyYAML が必要。uv があれば依存は自動で入る）
uv run scripts/clip_index.py --rebuild
uv run scripts/clip_index.py --unused -n 20

# 4. quiz-yaml-go を用意（バリデーションと変換に使う）
go install github.com/m-uesaka/quiz-yaml-go@latest   # または clone して go build

# 5. Claude Code を起動
claude
```

`uv` を使わない場合は `pip install pyyaml` して `python3 scripts/clip_index.py ...` でも動きます。

> サブエージェントは起動時にしか読み込まれません。`.claude/agents/` を編集したら Claude Code を再起動してください。

## 使い方

```
> /quiz-batch                      # 1バッチ（既定4問）作る
> /quiz-batch 地理と歴史で           # ジャンルを指定して作る
> /quiz-long-runner 今日の23時まで    # 時間を切って連続作問
> /quiz-long-runner 続きから
> /quiz-learn batch003             # 人手修正を LEARNINGS.md に反映
> /quiz-export all csv             # まとめて書き出し
```

## 1サイクルの流れ

```
Obsidian のクリップ
      │
      ▼
① clip-scout              未使用クリップから題材候補 4+2 件（既出チェック済み）
      ▼
② quiz-writer             問題文ドラフト（LEARNINGS + スタイルガイド適用）
      ▼
③ quiz-adversarial-checker 別解潰し → criteria (ok/ng/repeat) 確定
      ▼
④ quiz-style-reviewer     文体・ネタバレ・LEARNINGS 適合
      ▼
⑤ quiz-final-editor       採否確定 → work/batchNNN.yaml
      ▼
   export_yaml.py → output/batchNNN.yaml （quiz-yaml-go スキーマ準拠）
      ▼
   人間が cp して reviewed/batchNNN.yaml を編集
      ▼
   /quiz-learn → review_diff.py → LEARNINGS.md 更新 → ①に戻る
```

一次情報での裏取り（`quiz-fact-checker`）は通常サイクルには含まれません。人間のレビュー時
（`reviewed/batchNNN.yaml` を編集するとき）か、個別に依頼したときだけ動きます。

agentsの詳細は[リポジトリ全体構造](./docs/architecture.md)を参照してください。

## ファイルの役割

| パス | 役割 |
| --- | --- |
| `CLAUDE.md` | プロジェクト全体の方針。Claude Code が毎回読む |
| `LEARNINGS.md` | **人手修正から抽出したルール。生成時に最優先で参照される** |
| `config/quiz_question_style_guide.md` | 問題文の形式・文体（要カスタマイズ） |
| `config/quiz_notation_rules.md` | answer/spell/criteria の表記ルール（要カスタマイズ） |
| `config/quiz_topic_taste_guide.md` | 題材選びの好み（要カスタマイズ） |
| `config/quiz_topic_framing_guide.md` | 切り口の型・情報の組み合わせ方（要カスタマイズ） |
| `config/settings.yaml` | パス・上限値・しきい値 |
| `config/genre_targets.yaml` | ジャンル配分の目標（不要なら削除可） |
| `.claude/skills/*/SKILL.md` | `/quiz-batch` などのコマンド本体 |
| `.claude/agents/*.md` | 6体のサブエージェント定義 |
| `scripts/*.py` | 索引・重複判定・変換・差分抽出（LLM に任せない処理） |
| `work/` | メタ情報つきの作業ファイル。エージェントが書く |
| `output/` | 提出用 YAML。スクリプトが生成。手で触らない |
| `reviewed/` | 人間が修正した版 |
| `examples/` | 各ファイルのサンプル |

## 自分用ガイドの作り方（これをやると質が大きく変わります）

`config/` に入っている 4 つのガイド（`quiz_question_style_guide.md` / `quiz_notation_rules.md` /
`quiz_topic_taste_guide.md` / `quiz_topic_framing_guide.md`）は一般的な叩き台です。
あなたの作問を再現させるには、**自分の過去問を使って作り直す**のが最も効きます。
各ファイルは対応するサブエージェントだけが読む設計になっているので（`.claude/agents/*.md` 参照）、
まずは大枠の2ジャンル（文章の構造・文体／題材と切り口）で作り、
内容が肥大化してきたら実務的な表記ルール（ふりがな・spell・criteria）や
切り口の型を別ファイルに分けると、各サブエージェントが読む量を抑えられます。

1. 普段どおり自分で作った問題を Claude に投げ、事実確認・日本語の自然さ・別解の有無・
   ネタバレの有無を指摘させる。
2. 指摘を見ながら、自分でも修正案を出す。**「どこを直したか」「なぜその表現を避けたか」
   「どの情報を足すと答えが一意になるか」を毎回言語化する**（これがログになる）。
3. 50〜100 問ぶん溜まったら、次のように依頼して 2 つのガイドを生成し直す。

```
これまでのやりとりを分析して、私が作るような問題文をあなた一人で作れるようにするための
md ファイルを作ってください。題材ではなく、問題文の構造的なスタイルに絞ってください。
（1問1答、文章形式、ネタバレ厳禁、全体で答えが一意に確定すること）
→ config/quiz_question_style_guide.md に保存
```

```
次に、私がこれまで作ってきた題材・切り口の観点から、私の作問を再現できる情報を
別の md ファイルにまとめてください。形式ではなく、題材選び、切り口、情報の組み合わせ方に
注目してください。
→ config/quiz_topic_taste_guide.md に保存
```

ガイドが肥大化してきたら、`config/quiz_question_style_guide.md` の中の
「answer/spell欄・criteria の書式」だけを `config/quiz_notation_rules.md` に、
`config/quiz_topic_taste_guide.md` の中の「切り口の型・情報の組み合わせ方」だけを
`config/quiz_topic_framing_guide.md` に、それぞれ切り出すと良いです
（本リポジトリでの分割例も参考にしてください）。

これをやる時間がない場合でも、`/quiz-learn` を数バッチ回せば `LEARNINGS.md` に
同等の情報が自然に溜まっていきます。

## LEARNINGS の育ち方

```
1回目の修正      → watch に記録（まだ一般化しない）
2回目の同種修正  → active に昇格（以後すべての生成で強制される）
5回定着          → config/*.md 本体に昇格、LEARNINGS からは graduated へ
```

閾値は `config/settings.yaml` の `learnings` セクションで変えられます。
`active` が増えすぎるとプロンプトが肥大化して逆に効かなくなるので、
`max_active_rules`（既定 40）を超えたら統合するようになっています。

## スクリプト

```bash
uv run scripts/clip_index.py --rebuild             # クリップ索引を作る
uv run scripts/clip_index.py --unused -n 30 --tag 技術
uv run scripts/registry.py rebuild                 # 既出レジストリ再構築
uv run scripts/registry.py check "南部鉄器"          # 既出なら exit 1
uv run scripts/registry.py stats                   # ジャンル配分と目標の差分
uv run scripts/export_yaml.py work/batch001.yaml -o output/batch001.yaml
uv run scripts/review_diff.py output/batch001.yaml reviewed/batch001.yaml -o state/diff-batch001.yaml
```

重複判定・スキーマ変換・差分抽出は**意図的に LLM にやらせていません**。
LLM が「たぶん既出じゃない」と判断すると事故るためです。

## クリップの frontmatter

`scripts/clip_index.py` は Obsidian Web Clipper 系の frontmatter を想定しています。

```yaml
---
title: 記事タイトル
source: https://example.com/article
created: 2026-07-01
tags: [工芸, 岩手]
---
```

キー名が違う場合は `config/settings.yaml` の `clip_frontmatter_keys` に自分のキーを足してください。

## 運用上の注意

- クリップが尽きたらエージェントは停止します。web を勝手に漁らせない設計です。
- 同じクリップから作る問題は既定で 2 問まで（`limits.max_questions_per_clip`）。
- 生成された問題は**必ず人間が確認してから使ってください**。裏取り工程を入れてはいますが、
  誤りは残ります。特に年号・数値・「世界初」の類は自分の目で確認することをおすすめします。
- 同じ仕組みを他人が組むと似た問題が出る可能性があります（参考記事でも指摘されている懸念です）。
  自分のクリップを題材にするこの構成は、その点では有利なはずです。
