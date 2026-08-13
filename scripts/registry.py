#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""既出レジストリの管理。重複判定を LLM に任せず、ここで機械的に行う。

使い方:
    uv run scripts/registry.py rebuild            # work/ reviewed/ archive/ past_questions.yaml から再構築
    uv run scripts/registry.py check "南部鉄器"     # 既出なら終了コード 1
    uv run scripts/registry.py check --question "..." --answer "..."
    uv run scripts/registry.py stats              # ジャンル配分と目標の差分
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import sys
from collections import Counter
from pathlib import Path

from quizlib import ROOT, dump_yaml, load_settings, load_yaml, normalize_answer, work_items

REGISTRY = ROOT / "state" / "registry.yaml"
SOURCE_DIRS = ["reviewed", "work", "archive"]
PAST = ROOT / "past_questions.yaml"


def collect() -> dict:
    answers: dict[str, list[str]] = {}
    questions: list[dict] = []
    clip_usage: Counter = Counter()
    tag_counts: Counter = Counter()

    files: list[Path] = []
    for d in SOURCE_DIRS:
        files += sorted((ROOT / d).glob("*.yaml"))
    if PAST.exists():
        files.append(PAST)

    seen_ids = set()
    for path in files:
        try:
            doc = load_yaml(path)
        except Exception as e:  # noqa: BLE001
            print(f"skip {path.name}: {e}", file=sys.stderr)
            continue
        for item in work_items(doc):
            if not isinstance(item, dict):
                continue
            meta = item.get("meta") or {}
            if str(meta.get("status", "accepted")) == "rejected":
                continue
            qid = item.get("id") or f"{path.stem}:{item.get('answer','')}"
            ans = str(item.get("answer", "")).strip()
            norm = normalize_answer(ans)
            if ans:
                answers.setdefault(norm, []).append(f"{path.name}#{qid}")
            # 同じ問題が work/ と reviewed/ の両方にある場合は先勝ち（reviewed が優先）
            key = norm or qid
            if key in seen_ids:
                continue
            seen_ids.add(key)

            questions.append(
                {"id": qid, "file": path.name, "question": str(item.get("question", "")), "answer": ans}
            )
            clip = meta.get("source_clip")
            if clip:
                clip_usage[str(clip)] += 1
            for t in item.get("tags") or []:
                tag_counts[str(t)] += 1

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "count": len(questions),
        "answers": {k: v for k, v in sorted(answers.items())},
        "questions": questions,
        "clip_usage": dict(clip_usage.most_common()),
        "tag_counts": dict(tag_counts.most_common()),
    }


def load_registry() -> dict:
    if not REGISTRY.exists():
        return collect()
    return load_yaml(REGISTRY) or {}


def cmd_rebuild(_args):
    reg = collect()
    dump_yaml(reg, REGISTRY)
    print(f"{reg['count']} 問を登録しました -> {REGISTRY.relative_to(ROOT)}")


def cmd_check(args):
    reg = load_registry()
    answer = args.answer or args.value
    question = args.question or ""
    hits = []
    if answer:
        norm = normalize_answer(answer)
        if norm in reg.get("answers", {}):
            hits.append(("same_answer", reg["answers"][norm]))
    if question:
        for q in reg.get("questions", []):
            ratio = difflib.SequenceMatcher(
                None, normalize_answer(question), normalize_answer(q["question"])
            ).ratio()
            if ratio >= args.threshold:
                hits.append((f"similar_question({ratio:.2f})", [f"{q['file']}#{q['id']}"]))
    if hits:
        for kind, where in hits:
            print(f"DUPLICATE {kind}: {', '.join(where)}")
        sys.exit(1)
    print("OK 既出なし")


def cmd_stats(_args):
    reg = load_registry()
    settings = load_settings()
    targets_path = ROOT / "config" / "genre_targets.yaml"
    total = max(reg.get("count", 0), 1)
    counts = reg.get("tag_counts", {})
    print(f"総問題数: {reg.get('count', 0)}")
    if targets_path.exists():
        targets = (load_yaml(targets_path) or {}).get("targets") or {}
        print(f"{'ジャンル':<10}{'現在':>6}{'割合':>8}{'目標':>8}{'差分':>8}")
        for genre, target in targets.items():
            c = counts.get(genre, 0)
            pct = c / total * 100
            print(f"{genre:<10}{c:>6}{pct:>7.1f}%{target:>7}%{pct - target:>+7.1f}")
    unused_note = settings.get("limits", {}).get("max_questions_per_clip")
    print(f"\nクリップ利用上限: {unused_note} 問/クリップ")
    top = list(reg.get("clip_usage", {}).items())[:10]
    if top:
        print("よく使ったクリップ:")
        for path, n in top:
            print(f"  {n}\t{path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rebuild").set_defaults(func=cmd_rebuild)
    c = sub.add_parser("check")
    c.add_argument("value", nargs="?", default=None, help="答え（位置引数）")
    c.add_argument("--answer", default=None)
    c.add_argument("--question", default=None)
    c.add_argument("--threshold", type=float, default=0.82)
    c.set_defaults(func=cmd_check)
    sub.add_parser("stats").set_defaults(func=cmd_stats)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
