#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""生成した YAML と、人間が修正した YAML の差分を構造化して出す。

/quiz-learn がこの出力を読んで LEARNINGS.md のルールに変換する。

使い方:
    uv run scripts/review_diff.py output/batch001.yaml reviewed/batch001.yaml
    uv run scripts/review_diff.py output/batch001.yaml reviewed/batch001.yaml -o state/diff-batch001.yaml
    # git 管理下でその場で直した場合
    git show HEAD:output/batch001.yaml > /tmp/base.yaml
    uv run scripts/review_diff.py /tmp/base.yaml output/batch001.yaml
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from quizlib import ROOT, dump_yaml, load_yaml, normalize_answer, work_items

TEXT_FIELDS = ["question", "answer", "spell"]
LIST_FIELDS = ["tags", "comments"]
CRIT_KEYS = ["ok", "ng", "repeat"]


def inline_diff(a: str, b: str) -> str:
    """変更箇所を - / + で示す短い説明を作る。"""
    sm = difflib.SequenceMatcher(None, a, b)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag in ("replace", "delete") and a[i1:i2]:
            out.append(f"-「{a[i1:i2]}」")
        if tag in ("replace", "insert") and b[j1:j2]:
            out.append(f"+「{b[j1:j2]}」")
    return " ".join(out)


def pair_items(base: list[dict], rev: list[dict]):
    """答え一致 → 問題文の類似度 → 残りは追加/削除、の順で対応づける。"""
    pairs, used_rev = [], set()

    rev_by_ans: dict[str, list[int]] = {}
    for j, r in enumerate(rev):
        rev_by_ans.setdefault(normalize_answer(r.get("answer", "")), []).append(j)

    unmatched_base = []
    for i, b in enumerate(base):
        cand = rev_by_ans.get(normalize_answer(b.get("answer", "")), [])
        cand = [j for j in cand if j not in used_rev]
        if cand:
            used_rev.add(cand[0])
            pairs.append((i, cand[0], "answer"))
        else:
            unmatched_base.append(i)

    for i in unmatched_base:
        bq = normalize_answer(base[i].get("question", ""))
        best, best_ratio = None, 0.0
        for j, r in enumerate(rev):
            if j in used_rev:
                continue
            ratio = difflib.SequenceMatcher(None, bq, normalize_answer(r.get("question", ""))).ratio()
            if ratio > best_ratio:
                best, best_ratio = j, ratio
        if best is not None and best_ratio >= 0.55:
            used_rev.add(best)
            pairs.append((i, best, f"question({best_ratio:.2f})"))
        else:
            pairs.append((i, None, "removed"))

    for j in range(len(rev)):
        if j not in used_rev:
            pairs.append((None, j, "added"))
    return pairs


def hints_for(fields: dict, before: dict, after: dict) -> list[str]:
    hints = []
    if "answer" in fields:
        hints.append("fact")
    if "criteria" in fields:
        hints.append("unique")
    if "question" in fields:
        bq, aq = fields["question"]["before"], fields["question"]["after"]
        ans = str(after.get("answer", ""))
        if ans and len(ans) >= 2 and ans in bq and ans not in aq:
            hints.append("spoiler")
        if len(aq) - len(bq) <= -15:
            hints.append("length")
        hints.append("style")
    if "tags" in fields or "spell" in fields or "comments" in fields:
        hints.append("meta")
    return sorted(set(hints))


def diff_item(b: dict, r: dict) -> dict:
    fields: dict = {}
    for k in TEXT_FIELDS:
        bv, rv = str(b.get(k, "") or ""), str(r.get(k, "") or "")
        if bv != rv:
            fields[k] = {"before": bv, "after": rv, "diff": inline_diff(bv, rv)}
    for k in LIST_FIELDS:
        bv = [str(x) for x in (b.get(k) or [])]
        rv = [str(x) for x in (r.get(k) or [])]
        if bv != rv:
            fields[k] = {
                "before": bv,
                "after": rv,
                "added": [x for x in rv if x not in bv],
                "removed": [x for x in bv if x not in rv],
            }
    bc, rc = b.get("criteria") or {}, r.get("criteria") or {}
    crit = {}
    for k in CRIT_KEYS:
        bv = [str(x) for x in (bc.get(k) or [])]
        rv = [str(x) for x in (rc.get(k) or [])]
        if bv != rv:
            crit[k] = {"added": [x for x in rv if x not in bv], "removed": [x for x in bv if x not in rv]}
    if crit:
        fields["criteria"] = crit
    return fields


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base", help="生成した YAML（output/）")
    ap.add_argument("revised", help="人間が修正した YAML（reviewed/）")
    ap.add_argument("-o", "--output", default=None, help="結果の保存先。省略時は標準出力")
    args = ap.parse_args()

    base = work_items(load_yaml(Path(args.base)))
    rev = work_items(load_yaml(Path(args.revised)))
    if not base:
        sys.exit(f"{args.base} に問題が入っていません")

    changes, stats = [], {"total": len(base), "unchanged": 0, "modified": 0, "added": 0, "removed": 0}
    for i, j, how in pair_items(base, rev):
        if how == "removed":
            stats["removed"] += 1
            changes.append(
                {
                    "match": "removed",
                    "answer": str(base[i].get("answer", "")),
                    "question": str(base[i].get("question", "")),
                    "note": "人間が不採用にした問題。なぜ落ちたのかを推定すること。",
                }
            )
            continue
        if how == "added":
            stats["added"] += 1
            changes.append(
                {
                    "match": "added",
                    "answer": str(rev[j].get("answer", "")),
                    "question": str(rev[j].get("question", "")),
                    "note": "人間が書き足した問題。好みの直接的な手がかり。",
                }
            )
            continue
        fields = diff_item(base[i], rev[j])
        if not fields:
            stats["unchanged"] += 1
            continue
        stats["modified"] += 1
        changes.append(
            {
                "match": how,
                "answer": str(rev[j].get("answer", "")),
                "fields": fields,
                "hints": hints_for(fields, base[i], rev[j]),
            }
        )

    result = {
        "base": str(args.base),
        "revised": str(args.revised),
        "summary": stats,
        "changes": changes,
    }

    if args.output:
        out = Path(args.output)
        if not out.is_absolute():
            out = ROOT / out
        dump_yaml(result, out)
        print(f"差分 {len(changes)} 件 -> {out}")
        print(
            f"無修正 {stats['unchanged']} / 修正 {stats['modified']} / 追加 {stats['added']} / 削除 {stats['removed']}"
        )
    else:
        import yaml

        yaml.safe_dump(result, sys.stdout, allow_unicode=True, sort_keys=False, width=10**6)


if __name__ == "__main__":
    main()
