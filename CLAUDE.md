# クイズ自動作問プロジェクト

このリポジトリは、**Obsidian に蓄積した web クリップを一次的な題材源として、日本語クイズ（1問1答）を大量に作成・裏取り・レビューする**ための Claude Code 作業用プロジェクトです。

## このプロジェクトの前提

- 題材は原則として `config/settings.yaml` の `clip_dir` 配下のクリップから探す。web を無目的に探索しない。
- **クリップは二次情報である。** クリップに書いてある内容をそのまま事実として採用してはならない。必ず一次情報で裏を取る。
- クリップだけでは問題が成立しない場合（年号・正式名称・現在の状況・数値などが欠けている場合）は WebSearch / WebFetch で補完する。補完した情報の出典は必ず記録する。
- 出力は `m-uesaka/quiz-yaml-go` のスキーマに準拠した YAML。
- 生成物は**人間が後で必ず修正する**前提。修正された内容は `LEARNINGS.md` に還流させ、次の生成で使う。

## 必読ファイル（作問を始める前に必ず読む）

1. `LEARNINGS.md` — 過去の人手修正から抽出したルール。**最優先で従う。**
   （作問サブエージェントは全文ではなく、active セクションだけを抜粋した自動生成ファイル
   `config/learnings_active.md` を読む。トークン節約のため。中身の優先順位は同じ。）
2. `config/quiz_question_style_guide.md` — 問題文の形式・文体の方針。
3. `config/quiz_notation_rules.md` — answer/spell欄の表記・criteria の書式ルール（旧・style guide §8）。
4. `config/quiz_topic_taste_guide.md` — 題材選びの好み。
5. `config/quiz_topic_framing_guide.md` — 切り口の型・情報の組み合わせ方（旧・topic guide §3,4）。
6. `config/settings.yaml` — パスや各種上限値。

これらはサブエージェントごとに必要な範囲だけを読む設計になっている（各エージェント定義の
「必読」を参照）。すべてを毎回全文読む前提ではない。
優先順位が競合した場合は `LEARNINGS.md` > `quiz_question_style_guide.md`/`quiz_notation_rules.md`
> `quiz_topic_taste_guide.md`/`quiz_topic_framing_guide.md` の順で従う。
LEARNINGS のルールは新しいものほど優先する。

## ディレクトリ

| パス | 役割 |
| --- | --- |
| `work/batchNNN.yaml` | 作業用。メタ情報（出典・検証ログ・採否）込み。エージェントが書く。 |
| `output/batchNNN.yaml` | 提出用。quiz-yaml-go スキーマ準拠。`scripts/export_yaml.py` が生成。**手で編集しない。** |
| `reviewed/batchNNN.yaml` | 人間が修正した版。`output/` をコピーして編集する。 |
| `state/` | クリップ索引・既出レジストリ。スクリプトが管理する。手で編集しない。 |
| `archive/` | 確定済みの問題群。 |
| `config/` | 作問方針。`learnings_active.md` は `LEARNINGS.md` からの自動生成物（手で編集しない）。 |

## スクリプト

すべて `uv run scripts/xxx.py`（または `python3 scripts/xxx.py`、PyYAML 必須）で動く。

```bash
uv run scripts/clip_index.py --rebuild        # Obsidian のクリップを索引化
uv run scripts/clip_index.py --unused -n 30   # まだ使っていないクリップを列挙（使用済みタグ付きは自動除外）
uv run scripts/clip_index.py --mark-used "クリップ"  # 採用確定したクリップに使用済みタグを付ける
uv run scripts/registry.py rebuild            # 既出レジストリを再構築
uv run scripts/registry.py check "答え"        # 既出かどうか判定（終了コード 1 で既出）
uv run scripts/export_yaml.py work/batch001.yaml -o output/batch001.yaml
uv run scripts/review_diff.py output/batch001.yaml reviewed/batch001.yaml -o state/diff-batch001.yaml
uv run scripts/extract_active_learnings.py   # LEARNINGS.md の active だけを config/learnings_active.md に抽出
```

## 禁止事項

- `output/` を手で編集すること（`work/` を直して再エクスポートする）。
- `config/learnings_active.md` を手で編集すること（`LEARNINGS.md` を直して `extract_active_learnings.py` を再実行する）。
- 裏取りできていない主張を問題文に入れること。
- 問題文に答え（およびその一部・読み・言い換え）を漏らすこと。
- `state/registry.yaml` を LLM が直接書き換えること（必ずスクリプト経由）。
- 同一クリップから同一バッチ内に複数問を作ること。
- LEARNINGS.md のルールを「今回は例外」として黙って破ること。破る必要があるなら `work/` の `meta.notes` に理由を書く。

## 典型的な1サイクル

1. `clip-scout` が未使用クリップから題材候補を 4 件（＋補欠 2 件）出す
2. `quiz-writer` が問題文ドラフトを作る
3. `quiz-fact-checker` が一次情報で裏を取る
4. `quiz-adversarial-checker` が別解を潰し `criteria` を埋める
5. `quiz-style-reviewer` が文体と LEARNINGS 適合を見る
6. `quiz-final-editor` が採否を決め `work/batchNNN.yaml` に確定、`export_yaml.py` と `registry.py rebuild` を実行

詳細は `.claude/skills/quiz-batch/SKILL.md` を参照。
