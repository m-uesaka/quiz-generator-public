#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "typer"]
# ///
"""Obsidian の web クリップを索引化し、未使用のクリップを列挙する。

使い方:
    uv run scripts/clip_index.py --rebuild
    uv run scripts/clip_index.py --unused -n 30
    uv run scripts/clip_index.py --unused -n 30 --tag 技術
    uv run scripts/clip_index.py --mark-used "大倧教 - Wikipedia.md"

`--mark-used` は、settings.yaml の `paths.used_tag`（既定 "question_made"）タグを
実際の Obsidian クリップファイルの frontmatter に書き込む。このタグが付いたクリップは
`--unused` の候補から自動的に除外される。作問で採用が確定したクリップに対して
quiz-final-editor が実行する想定。
"""

from __future__ import annotations

from pathlib import Path

import typer
from quiz_generator.clip_index import cmd_mark_used, cmd_rebuild, cmd_unused
from quiz_generator.common import load_settings

app = typer.Typer(add_completion=False)


@app.command(help=__doc__)
def main(  # noqa: PLR0913, PLR0917 (typer CLI オプションのため引数が多い)
    rebuild: bool = typer.Option(False, "--rebuild", help="索引を作り直す"),
    unused: bool = typer.Option(False, "--unused", help="未使用クリップを列挙する"),
    n: int = typer.Option(20, "-n", help="列挙する件数"),
    tag: str | None = typer.Option(None, "--tag", help="このタグを持つクリップに絞る"),
    min_chars: int = typer.Option(
        200, "--min-chars", help="本文がこの文字数未満のクリップを除く"
    ),
    include_used: bool = typer.Option(
        False,
        "--include-used",
        help="使用済みタグ（paths.used_tag）が付いたクリップも --unused の結果に含める",
    ),
    mark_used: str | None = typer.Option(
        None,
        "--mark-used",
        metavar="PATH",
        help="このクリップ（clip_index.yaml の path と一致する相対パス）"
        "に使用済みタグを付ける",
    ),
    settings_path: str | None = typer.Option(None, "--settings"),
) -> None:
    """CLI エントリポイント。`--rebuild` / `--unused` / `--mark-used` を実行する。

    Args:
        rebuild: `True` なら索引を作り直す。
        unused: `True` なら未使用クリップを列挙する。
        n: `--unused` で列挙する件数。
        tag: `--unused` の絞り込みタグ。
        min_chars: `--unused` の本文文字数の下限。
        include_used: `--unused` に使用済みクリップも含めるか。
        mark_used: 使用済みタグを付けるクリップのパス。
        settings_path: 設定ファイルのパス（省略時は既定値）。

    """
    settings = load_settings(Path(settings_path) if settings_path else None)
    if rebuild:
        cmd_rebuild(settings)
    if mark_used:
        cmd_mark_used(settings, mark_used)
        raise typer.Exit()
    if unused or not rebuild:
        cmd_unused(settings, n, tag, min_chars, include_used)


if __name__ == "__main__":
    app()
