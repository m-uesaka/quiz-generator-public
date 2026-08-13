#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Obsidian の web クリップを索引化し、未使用のクリップを列挙する。

使い方:
    uv run scripts/clip_index.py --rebuild
    uv run scripts/clip_index.py --unused -n 30
    uv run scripts/clip_index.py --unused -n 30 --tag 技術
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import sys
from pathlib import Path

from quizlib import ROOT, dump_yaml, expand, load_settings, load_yaml, parse_frontmatter, pick

INDEX = ROOT / "state" / "clip_index.yaml"
REGISTRY = ROOT / "state" / "registry.yaml"


def iter_clip_files(settings: dict):
    paths = settings.get("paths", {})
    clip_dir = expand(paths.get("clip_dir", "~/Obsidian"))
    if not clip_dir.exists():
        sys.exit(f"clip_dir が存在しません: {clip_dir}\nconfig/settings.yaml を確認してください。")
    pattern = "**/*.md" if paths.get("recursive", True) else "*.md"
    excludes = paths.get("exclude") or []
    for p in sorted(clip_dir.glob(pattern)):
        rel = p.relative_to(clip_dir).as_posix()
        if any(fnmatch.fnmatch(rel, ex) for ex in excludes):
            continue
        yield clip_dir, p


def build_index(settings: dict) -> list[dict]:
    keys = settings.get("clip_frontmatter_keys", {})
    entries = []
    for clip_dir, path in iter_clip_files(settings):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        fm, body = parse_frontmatter(text)
        title = pick(fm, keys.get("title") or ["title"])
        if isinstance(title, list):
            title = title[0] if title else None
        tags = pick(fm, keys.get("tags") or ["tags"]) or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        clipped_at = pick(fm, keys.get("clipped_at") or ["created"])
        entries.append(
            {
                "id": hashlib.sha1(path.as_posix().encode()).hexdigest()[:10],
                "path": path.relative_to(clip_dir).as_posix(),
                "abspath": path.as_posix(),
                "title": str(title) if title else path.stem,
                "url": str(pick(fm, keys.get("url") or ["source"]) or ""),
                "tags": [str(t) for t in tags],
                "clipped_at": str(clipped_at) if clipped_at else "",
                "mtime": dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "chars": len(body),
            }
        )
    return entries


def used_counts() -> dict[str, int]:
    if not REGISTRY.exists():
        return {}
    reg = load_yaml(REGISTRY) or {}
    return dict(reg.get("clip_usage") or {})


def cmd_rebuild(settings):
    entries = build_index(settings)
    dump_yaml(
        {"generated_at": dt.datetime.now().isoformat(timespec="seconds"), "clips": entries},
        INDEX,
    )
    print(f"{len(entries)} 件のクリップを索引化しました -> {INDEX.relative_to(ROOT)}")


def cmd_unused(settings, n: int, tag: str | None, min_chars: int):
    if not INDEX.exists():
        cmd_rebuild(settings)
    data = load_yaml(INDEX) or {}
    used = used_counts()
    cap = int((settings.get("limits") or {}).get("max_questions_per_clip", 2))
    rows = []
    for c in data.get("clips", []):
        cnt = used.get(c["path"], 0)
        if cnt >= cap:
            continue
        if tag and tag not in c.get("tags", []):
            continue
        if c.get("chars", 0) < min_chars:
            continue
        rows.append((cnt, c))
    # 未使用 → 新しい順
    rows.sort(key=lambda r: (r[0], r[1].get("mtime", "")), reverse=False)
    rows.sort(key=lambda r: r[1].get("mtime", ""), reverse=True)
    rows.sort(key=lambda r: r[0])
    for cnt, c in rows[:n]:
        tags = ",".join(c.get("tags", []))
        print(f"[{cnt}/{cap}] {c['path']}\t{c['title']}\t{tags}\t{c.get('url','')}")
    if not rows:
        print("条件に合う未使用クリップがありません。", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true", help="索引を作り直す")
    ap.add_argument("--unused", action="store_true", help="未使用クリップを列挙する")
    ap.add_argument("-n", type=int, default=20, help="列挙する件数")
    ap.add_argument("--tag", default=None, help="このタグを持つクリップに絞る")
    ap.add_argument("--min-chars", type=int, default=200, help="本文がこの文字数未満のクリップを除く")
    ap.add_argument("--settings", default=None)
    args = ap.parse_args()

    settings = load_settings(Path(args.settings) if args.settings else None)
    if args.rebuild:
        cmd_rebuild(settings)
    if args.unused or not args.rebuild:
        cmd_unused(settings, args.n, args.tag, args.min_chars)


if __name__ == "__main__":
    main()
