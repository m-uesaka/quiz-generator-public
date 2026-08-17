#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""LEARNINGS.md の active セクションだけを config/learnings_active.md に抽出する。

生成系エージェント（clip-scout / quiz-writer / quiz-style-reviewer）は毎サイクル
LEARNINGS.md を読む必要があるが、実際に使うのは active セクションだけ。watch /
graduated / 統計表はバッチを重ねるほど際限なく伸びるため、そこまで含めて全文を
読むと無駄なトークン消費になる。このスクリプトで active だけを抜き出した小さい
ファイルを作り、エージェントにはそちらを読ませる。

source of truth は常に LEARNINGS.md。config/learnings_active.md は生成物なので
手で編集しない。

使い方:
    uv run scripts/extract_active_learnings.py
"""

from __future__ import annotations

from quiz_generator.common import ROOT
from quiz_generator.learnings import DST, HEADER, SRC, extract_active


def main() -> None:
    """`LEARNINGS.md` の active セクションを `learnings_active.md` に抜き出す。"""
    text = SRC.read_text(encoding="utf-8")
    body = extract_active(text)
    DST.write_text(HEADER + body + "\n", encoding="utf-8")
    print(f"wrote {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
