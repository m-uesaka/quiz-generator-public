# LEARNINGS

人間が生成物を修正した内容から抽出したルール集。**作問エージェントは毎サイクル、作業開始前にこのファイルを読むこと。**

## 運用ルール

- 更新は `/quiz-learn`（`.claude/skills/quiz-learn/SKILL.md`）が行う。人間が直接書き足してもよい。
- ルールには `R-NNNN` の連番 ID を振る。**ID は再利用しない**（削除したら欠番のまま）。
- 状態は 3 つ。
  - `watch` … 1 回だけ観測された修正。まだ一般化しない。
  - `active` … 再発したので生成時に必ず従うルール（`settings.yaml: promote_to_active_after` 回で昇格）。
  - `graduated` … `config/*.md` のガイド本体に反映済み。履歴として残すだけで、参照しなくてよい。
- 生成時は **active セクションだけ**を読めばよい。watch は `/quiz-learn` 実行時のみ参照する。
- 矛盾するルールがある場合、**新しい ID（大きい番号）を優先**する。古い方は `superseded_by` を書いて `graduated` に落とす。
- active が `max_active_rules` を超えたら、似たルールを統合するか `config/` のガイドへ昇格させる。

## ルールのカテゴリ

| カテゴリ | 意味 | 主な検査担当 |
| --- | --- | --- |
| `fact` | 事実誤り・出典の質 | 人間（レビュー時）／個別依頼時のみ quiz-fact-checker |
| `unique` | 別解・一意性・criteria の不足 | quiz-adversarial-checker |
| `style` | 文体・語順・長さ・疑問詞 | quiz-style-reviewer |
| `spoiler` | 問題文への答えの漏れ | quiz-style-reviewer |
| `topic` | 題材選び・切り口の好み | clip-scout |
| `meta` | tags / spell / comments / criteria の書式 | quiz-final-editor |
| `clip` | クリップの読み方・補完の要否判断 | clip-scout |

---

## active

<!-- ここに書かれたルールは生成時に必ず適用する。テンプレートは下記フォーマットに従うこと。 -->

_(まだありません。最初の `/quiz-learn` 実行後に埋まります。)_

<!--
### R-0001 | style | 「有名な」で始まる前フリを使わない
- 状態: active
- 初出: 2026-08-12 / batch001-02
- 再発: 3 回 (batch001-02, batch003-01, batch004-04)
- Before: 有名なフランスの画家で、睡蓮の連作で知られる人物は誰でしょう？
- After: 睡蓮を主題とする連作を晩年まで描き続けたフランスの画家は誰でしょう？
- 理由: 「有名な」は情報量がゼロで、早押しの押しポイントを潰す。
- 適用条件: すべての問題文
- 検査担当: quiz-style-reviewer
- superseded_by: なし
-->

---

## watch

<!-- 1 回しか観測されていない修正。再発したら active に昇格させる。 -->

_(まだありません。)_

---

## graduated

<!-- config/ のガイドに反映済み。参照不要。 -->

_(まだありません。)_

---

## 統計

`/quiz-learn` が毎回更新する。人間の修正がどこに集中しているかを見て、
どのエージェントのプロンプトを直すべきかを判断するために使う。

| バッチ | 生成数 | 無修正で通った数 | 修正された数 | 削除された数 | 主な修正カテゴリ |
| --- | --- | --- | --- | --- | --- |
| _(未集計)_ | | | | | |
