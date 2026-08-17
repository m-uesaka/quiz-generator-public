"""LEARNINGS.md の active セクション抽出ロジック。

CLI エントリポイントは `scripts/extract_active_learnings.py`。
"""

from __future__ import annotations

import re

from quiz_generator.common import ROOT

SRC = ROOT / "LEARNINGS.md"
DST = ROOT / "config" / "learnings_active.md"

HEADER = (
    "<!-- 自動生成ファイル。手で編集しない。 -->\n"
    "<!-- 元データ: LEARNINGS.md の active セクション。"
    " scripts/extract_active_learnings.py で再生成する"
    "（quiz-learn / quiz-batch が実行する）。 -->\n\n"
    "# LEARNINGS（active のみ）\n\n"
)


def extract_active(text: str) -> str:
    """LEARNINGS.md の全文から `## active` セクションの本文だけを抜き出す。

    Args:
        text: `LEARNINGS.md` の全文。

    Returns:
        `## active` セクションの本文（前後の空行・末尾の `---` を除去済み）。

    Raises:
        SystemExit: `## active` セクションが見つからない場合。

    """
    m = re.search(r"^## active\s*$", text, re.MULTILINE)
    if not m:
        raise SystemExit("LEARNINGS.md に '## active' セクションが見つかりません")
    start = m.end()
    m2 = re.search(r"^## ", text[start:], re.MULTILINE)
    body = text[start : start + m2.start()] if m2 else text[start:]
    body = re.sub(r"\n---\s*$", "", body)
    return body.strip("\n")
