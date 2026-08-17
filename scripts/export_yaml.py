#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "typer"]
# ///
"""work/batchNNN.yaml を quiz-yaml-go のスキーマ準拠 YAML に変換する。

使い方:
    uv run scripts/export_yaml.py work/batch001.yaml -o output/batch001.yaml
    uv run scripts/export_yaml.py work/*.yaml -o output/all.yaml --merge
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from quiz_generator.common import ROOT, dump_yaml, load_settings, load_yaml, work_items
from quiz_generator.export_yaml import to_schema, validate

app = typer.Typer(add_completion=False)


@app.command(help=__doc__)
def main(
    inputs: Annotated[
        list[str], typer.Argument(help="入力 YAML（work/batchNNN.yaml など）")
    ],
    output: str = typer.Option(..., "-o", "--output", help="出力先"),
    merge: bool = typer.Option(
        False, "--merge", help="複数の入力を1ファイルにまとめる"
    ),
    include_rejected: bool = typer.Option(False, "--include-rejected"),
) -> None:
    """work/ の YAML を読み込み、検証してから提出用 YAML を出力する。

    Args:
        inputs: 入力 YAML ファイルのパスのリスト（`work/batchNNN.yaml` 等）。
        output: 出力先のパス。
        merge: `True` の場合、複数の入力を1つの出力にまとめる
            （現状の実装では常に1つにまとめて出力する）。
        include_rejected: `True` の場合、`meta.status` が `rejected` の
            問題も出力に含める。

    Raises:
        typer.Exit: 検証エラーがある場合（終了コード1）。

    """
    settings = load_settings()
    include_sources = bool(
        (settings.get("output") or {}).get("include_sources_in_comments", True)
    )

    items: list[dict] = []
    errors: list[str] = []
    for path in inputs:
        doc = load_yaml(Path(path))
        for i, item in enumerate(work_items(doc), 1):
            meta = item.get("meta") or {}
            status = str(meta.get("status", "accepted"))
            if status != "accepted" and not include_rejected:
                continue
            where = f"{Path(path).name}#{item.get('id', i)}"
            errors += validate(item, where)
            items.append(to_schema(item, include_sources))

    if errors:
        print("エラーがあるため出力しません:", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        raise typer.Exit(code=1)

    out = Path(output)
    if not out.is_absolute():
        out = ROOT / out
    dump_yaml(items, out)
    print(f"{len(items)} 問を出力しました -> {out}")
    print("次: quiz-yaml-go でバリデーションしてください")
    print(f"  quiz-yaml-converter -input {out} -validate")


if __name__ == "__main__":
    app()
