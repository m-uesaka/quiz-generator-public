#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "typer"]
# ///
"""生成した YAML と、人間が修正した YAML の差分を構造化して出す。

/quiz-learn がこの出力を読んで LEARNINGS.md のルールに変換する。

使い方:
    uv run scripts/review_diff.py output/batch001.yaml reviewed/batch001.yaml
    uv run scripts/review_diff.py output/batch001.yaml reviewed/batch001.yaml \
        -o state/diff-batch001.yaml
    # git 管理下でその場で直した場合
    git show HEAD:output/batch001.yaml > /tmp/base.yaml
    uv run scripts/review_diff.py /tmp/base.yaml output/batch001.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
import yaml
from quiz_generator.common import ROOT, dump_yaml, load_yaml, work_items
from quiz_generator.review_diff import diff_item, hints_for, pair_items

app = typer.Typer(add_completion=False)


@app.command(help=__doc__)
def main(
    base: str = typer.Argument(..., help="生成した YAML（output/）"),
    revised: str = typer.Argument(..., help="人間が修正した YAML（reviewed/）"),
    output: str | None = typer.Option(
        None, "-o", "--output", help="結果の保存先。省略時は標準出力"
    ),
) -> None:
    """生成 YAML と修正済み YAML を突き合わせ、差分を構造化して出力する。

    Args:
        base: 生成した YAML（output/）のパス。
        revised: 人間が修正した YAML（reviewed/）のパス。
        output: 結果の保存先パス。省略時は標準出力に YAML を書き出す。

    Raises:
        SystemExit: `base` に問題が1つも含まれていない場合。

    """
    base_items = work_items(load_yaml(Path(base)))
    rev_items = work_items(load_yaml(Path(revised)))
    if not base_items:
        sys.exit(f"{base} に問題が入っていません")

    changes, stats = (
        [],
        {
            "total": len(base_items),
            "unchanged": 0,
            "modified": 0,
            "added": 0,
            "removed": 0,
        },
    )
    for i, j, how in pair_items(base_items, rev_items):
        if how == "removed":
            stats["removed"] += 1
            changes.append(
                {
                    "match": "removed",
                    "answer": str(base_items[i].get("answer", "")),
                    "question": str(base_items[i].get("question", "")),
                    "note": "人間が不採用にした問題。なぜ落ちたのかを推定すること。",
                }
            )
            continue
        if how == "added":
            stats["added"] += 1
            changes.append(
                {
                    "match": "added",
                    "answer": str(rev_items[j].get("answer", "")),
                    "question": str(rev_items[j].get("question", "")),
                    "note": "人間が書き足した問題。好みの直接的な手がかり。",
                }
            )
            continue
        fields = diff_item(base_items[i], rev_items[j])
        if not fields:
            stats["unchanged"] += 1
            continue
        stats["modified"] += 1
        changes.append(
            {
                "match": how,
                "answer": str(rev_items[j].get("answer", "")),
                "fields": fields,
                "hints": hints_for(fields, base_items[i], rev_items[j]),
            }
        )

    result = {
        "base": str(base),
        "revised": str(revised),
        "summary": stats,
        "changes": changes,
    }

    if output:
        out = Path(output)
        if not out.is_absolute():
            out = ROOT / out
        dump_yaml(result, out)
        print(f"差分 {len(changes)} 件 -> {out}")
        print(
            f"無修正 {stats['unchanged']} / 修正 {stats['modified']} / "
            f"追加 {stats['added']} / 削除 {stats['removed']}"
        )
    else:
        yaml.safe_dump(
            result, sys.stdout, allow_unicode=True, sort_keys=False, width=10**6
        )


if __name__ == "__main__":
    app()
