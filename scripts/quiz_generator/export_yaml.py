"""work/batchNNN.yaml を quiz-yaml-go スキーマ準拠 YAML に変換するロジック。

CLI エントリポイントは `scripts/export_yaml.py`。
"""

from __future__ import annotations

FIELD_ORDER = ["question", "answer", "spell", "tags", "comments", "criteria"]
CRITERIA_KEYS = ["ok", "ng", "repeat"]
MIN_LEAK_CHECK_LEN = 2


def to_schema(item: dict, include_sources: bool) -> dict:
    """work/ の1問分の辞書を quiz-yaml-go スキーマの辞書に変換する。

    Args:
        item: `work/batchNNN.yaml` 内の1問分の辞書（meta を含む）。
        include_sources: `True` の場合、`meta.sources` を「出典: ...」
            として comments に追記する。

    Returns:
        `FIELD_ORDER` の順にキーを並べた、スキーマ準拠の辞書。

    """
    out: dict = {}
    for key in FIELD_ORDER:
        val = item.get(key)
        if key == "criteria":
            crit = {
                k: [str(x) for x in (val or {}).get(k) or []] for k in CRITERIA_KEYS
            }
            crit = {k: v for k, v in crit.items() if v}
            if crit:
                out["criteria"] = crit
            continue
        if key == "comments":
            comments = [str(c) for c in (val or [])]
            if include_sources:
                for src in (item.get("meta") or {}).get("sources") or []:
                    s = f"出典: {src}"
                    if s not in comments:
                        comments.append(s)
            if comments:
                out["comments"] = comments
            continue
        if val in (None, "", []):
            continue
        out[key] = [str(v) for v in val] if isinstance(val, list) else str(val)
    return out


def validate(item: dict, where: str) -> list[str]:
    """1問分のデータを検証し、問題があればエラーメッセージを返す。

    question / answer の欠落と、問題文への答えの漏洩をチェックする。

    Args:
        item: 検証対象の1問分の辞書。
        where: エラーメッセージに含める、問題を特定する文字列
            （例: `"batch001.yaml#1"`）。

    Returns:
        エラーメッセージのリスト。問題なければ空リスト。

    """
    errs = []
    if not item.get("question"):
        errs.append(f"{where}: question が空")
    if not item.get("answer"):
        errs.append(f"{where}: answer が空")
    q = str(item.get("question", ""))
    a = str(item.get("answer", ""))
    if a and len(a) >= MIN_LEAK_CHECK_LEN and a in q:
        errs.append(f"{where}: 問題文に答え『{a}』が含まれています")
    return errs
