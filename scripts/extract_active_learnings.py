#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
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

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "LEARNINGS.md"
DST = ROOT / "config" / "learnings_active.md"

HEADER = (
    "<!-- 自動生成ファイル。手で編集しない。 -->\n"
    "<!-- 元データ: LEARNINGS.md の active セクション。"
    " scripts/extract_active_learnings.py で再生成する（quiz-learn / quiz-batch が実行する）。 -->\n\n"
    "# LEARNINGS（active のみ）\n\n"
)


def extract_active(text: str) -> str:
    m = re.search(r"^## active\s*$", text, re.MULTILINE)
    if not m:
        raise SystemExit("LEARNINGS.md に '## active' セクションが見つかりません")
    start = m.end()
    m2 = re.search(r"^## ", text[start:], re.MULTILINE)
    body = text[start : start + m2.start()] if m2 else text[start:]
    body = re.sub(r"\n---\s*$", "", body)
    return body.strip("\n")


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    body = extract_active(text)
    DST.write_text(HEADER + body + "\n", encoding="utf-8")
    print(f"wrote {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
