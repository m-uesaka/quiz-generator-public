#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""work/batchNNN.yaml（メタ情報つき）を quiz-yaml-go のスキーマに準拠した YAML に変換する。

使い方:
    uv run scripts/export_yaml.py work/batch001.yaml -o output/batch001.yaml
    uv run scripts/export_yaml.py work/*.yaml -o output/all.yaml --merge
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quizlib import ROOT, dump_yaml, load_settings, load_yaml, work_items

FIELD_ORDER = ["question", "answer", "spell", "tags", "comments", "criteria"]
CRITERIA_KEYS = ["ok", "ng", "repeat"]


def to_schema(item: dict, include_sources: bool) -> dict:
    out: dict = {}
    for key in FIELD_ORDER:
        val = item.get(key)
        if key == "criteria":
            crit = {k: [str(x) for x in (val or {}).get(k) or []] for k in CRITERIA_KEYS}
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
    errs = []
    if not item.get("question"):
        errs.append(f"{where}: question が空")
    if not item.get("answer"):
        errs.append(f"{where}: answer が空")
    q = str(item.get("question", ""))
    a = str(item.get("answer", ""))
    if a and len(a) >= 2 and a in q:
        errs.append(f"{where}: 問題文に答え『{a}』が含まれています")
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--merge", action="store_true", help="複数の入力を1ファイルにまとめる")
    ap.add_argument("--include-rejected", action="store_true")
    args = ap.parse_args()

    settings = load_settings()
    include_sources = bool((settings.get("output") or {}).get("include_sources_in_comments", True))

    items: list[dict] = []
    errors: list[str] = []
    for path in args.inputs:
        doc = load_yaml(Path(path))
        for i, item in enumerate(work_items(doc), 1):
            meta = item.get("meta") or {}
            status = str(meta.get("status", "accepted"))
            if status != "accepted" and not args.include_rejected:
                continue
            where = f"{Path(path).name}#{item.get('id', i)}"
            errors += validate(item, where)
            items.append(to_schema(item, include_sources))

    if errors:
        print("エラーがあるため出力しません:", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)

    out = Path(args.output)
    if not out.is_absolute():
        out = ROOT / out
    dump_yaml(items, out)
    print(f"{len(items)} 問を出力しました -> {out}")
    print("次: quiz-yaml-go でバリデーションしてください")
    print(f"  quiz-yaml-converter -input {out} -validate")


if __name__ == "__main__":
    main()
