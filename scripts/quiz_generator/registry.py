"""既出レジストリの構築ロジック。重複判定を LLM に任せず、ここで機械的に行う。

CLI エントリポイントは `scripts/registry.py`。
"""

from __future__ import annotations

import datetime as dt
import sys
from collections import Counter
from typing import TYPE_CHECKING

from quiz_generator.common import ROOT, load_yaml, normalize_answer, work_items

if TYPE_CHECKING:
    from pathlib import Path

REGISTRY = ROOT / "state" / "registry.yaml"
SOURCE_DIRS = ["reviewed", "work", "archive"]
PAST = ROOT / "past_questions.yaml"


def _register_item(
    item: object,
    path: Path,
    answers: dict[str, list[str]],
    entries: dict[str, dict],
    order: list[str],
) -> None:
    """1件の問題を `answers` / `entries` / `order` に反映する。

    reject 済みや不正な形式の item は無視する。既に同じキーの entry が
    あれば `clip` / `tags` の欠けている部分だけ補完する（先勝ち）。

    Args:
        item: `work_items` が返す1件分の問題データ。
        path: `item` の出典ファイルのパス。
        answers: 正規化した答えをキーにした出典リストの辞書（更新される）。
        entries: 正規化キーごとの確定エントリの辞書（更新される）。
        order: `entries` のキーが最初に登場した順序のリスト（更新される）。

    """
    if not isinstance(item, dict):
        return
    meta = item.get("meta") or {}
    if str(meta.get("status", "accepted")) == "rejected":
        return
    qid = item.get("id") or f"{path.stem}:{item.get('answer', '')}"
    ans = str(item.get("answer", "")).strip()
    norm = normalize_answer(ans)
    if ans:
        answers.setdefault(norm, []).append(f"{path.name}#{qid}")
    clip = meta.get("source_clip")
    tags = [str(t) for t in (item.get("tags") or [])]
    # 同じ問題が work/ と reviewed/ の両方にある場合、問題文・答えは先勝ち
    # （reviewed が優先）。ただし reviewed には meta（source_clip等）が
    # 無いため、clip_usage / tag_counts は後続の重複
    # （work/archive）から補完する。
    key = norm or qid
    if key not in entries:
        entries[key] = {
            "id": qid,
            "file": path.name,
            "question": str(item.get("question", "")),
            "answer": ans,
            "clip": str(clip) if clip else None,
            "tags": tags,
        }
        order.append(key)
    else:
        existing = entries[key]
        if not existing["clip"] and clip:
            existing["clip"] = str(clip)
        if not existing["tags"] and tags:
            existing["tags"] = tags


def collect() -> dict:
    """`reviewed/` `work/` `archive/` から既出レジストリの内容を組み立てる。

    `past_questions.yaml` も走査対象に含める。同一問題が複数ファイルに存在する場合、
    答えの正規化キーで名寄せし、`reviewed/` を優先しつつ `work/`・`archive/` から
    `clip` / `tags` を補完する。

    Returns:
        `generated_at` / `count` / `answers` / `questions` / `clip_usage` /
        `tag_counts` を持つ辞書。

    """
    answers: dict[str, list[str]] = {}
    entries: dict[str, dict] = {}
    order: list[str] = []

    files: list[Path] = []
    for d in SOURCE_DIRS:
        files += sorted((ROOT / d).glob("*.yaml"))
    if PAST.exists():
        files.append(PAST)

    for path in files:
        try:
            doc = load_yaml(path)
        except Exception as e:
            print(f"skip {path.name}: {e}", file=sys.stderr)
            continue
        for item in work_items(doc):
            _register_item(item, path, answers, entries, order)

    questions: list[dict] = []
    clip_usage: Counter = Counter()
    tag_counts: Counter = Counter()
    for key in order:
        e = entries[key]
        questions.append(
            {
                "id": e["id"],
                "file": e["file"],
                "question": e["question"],
                "answer": e["answer"],
            }
        )
        if e["clip"]:
            clip_usage[e["clip"]] += 1
        for t in e["tags"]:
            tag_counts[t] += 1

    return {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "count": len(questions),
        "answers": {k: v for k, v in sorted(answers.items())},
        "questions": questions,
        "clip_usage": dict(clip_usage.most_common()),
        "tag_counts": dict(tag_counts.most_common()),
    }


def load_registry() -> dict:
    """既出レジストリを読み込む。無ければその場で `collect()` して代用する。

    Returns:
        レジストリの内容（`collect()` の戻り値と同じ形の辞書）。

    """
    if not REGISTRY.exists():
        return collect()
    return load_yaml(REGISTRY) or {}
