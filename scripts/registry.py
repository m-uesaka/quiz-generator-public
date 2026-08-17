#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "typer"]
# ///
"""既出レジストリの管理。重複判定を LLM に任せず、ここで機械的に行う。

使い方:
    uv run scripts/registry.py rebuild
        # work/ reviewed/ archive/ past_questions.yaml から再構築
    uv run scripts/registry.py check "南部鉄器"     # 既出なら終了コード 1
    uv run scripts/registry.py check --question "..." --answer "..."
    uv run scripts/registry.py stats              # ジャンル配分と目標の差分
"""

from __future__ import annotations

import difflib

import typer
from quiz_generator.common import (
    ROOT,
    dump_yaml,
    load_settings,
    load_yaml,
    normalize_answer,
)
from quiz_generator.registry import REGISTRY, collect, load_registry

app = typer.Typer(add_completion=False, help=__doc__)


@app.command("rebuild")
def cmd_rebuild() -> None:
    """work/ reviewed/ archive/ past_questions.yaml から再構築する。"""
    reg = collect()
    dump_yaml(reg, REGISTRY)
    print(f"{reg['count']} 問を登録しました -> {REGISTRY.relative_to(ROOT)}")


@app.command("check")
def cmd_check(
    value: str | None = typer.Argument(None, help="答え（位置引数）"),
    answer: str | None = typer.Option(None, help="既出判定する答え"),
    question: str | None = typer.Option(None, help="既出判定する問題文"),
    threshold: float = typer.Option(0.82, help="問題文の類似度判定のしきい値"),
) -> None:
    """既出かどうかを判定する。既出なら終了コード 1。

    答えの完全一致（正規化後）と、問題文の類似度（`difflib`）の両方で
    判定する。

    Args:
        value: 位置引数で渡された答え（`--answer` の簡易版）。
        answer: 既出判定する答え。
        question: 既出判定する問題文。
        threshold: 問題文の類似度判定のしきい値（0〜1）。

    Raises:
        typer.Exit: 既出が見つかった場合（終了コード1）。

    """
    reg = load_registry()
    ans = answer or value
    q = question or ""
    hits = []
    if ans:
        norm = normalize_answer(ans)
        if norm in reg.get("answers", {}):
            hits.append(("same_answer", reg["answers"][norm]))
    if q:
        for item in reg.get("questions", []):
            ratio = difflib.SequenceMatcher(
                None, normalize_answer(q), normalize_answer(item["question"])
            ).ratio()
            if ratio >= threshold:
                hits.append(
                    (f"similar_question({ratio:.2f})", [f"{item['file']}#{item['id']}"])
                )
    if hits:
        for kind, where in hits:
            print(f"DUPLICATE {kind}: {', '.join(where)}")
        raise typer.Exit(code=1)
    print("OK 既出なし")


@app.command("stats")
def cmd_stats() -> None:
    """ジャンル配分と目標の差分を表示する。"""
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


if __name__ == "__main__":
    app()
