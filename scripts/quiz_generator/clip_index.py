"""クリップ索引の構築・未使用クリップの列挙・使用済みタグ付けのロジック。

CLI エントリポイントは `scripts/clip_index.py`。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

import fnmatch

from quiz_generator.common import (
    ROOT,
    add_frontmatter_tag,
    dump_yaml,
    expand,
    load_yaml,
    parse_frontmatter,
    pick,
)

INDEX = ROOT / "state" / "clip_index.yaml"
REGISTRY = ROOT / "state" / "registry.yaml"


def iterator_for_clip_files(settings: dict) -> Iterator[tuple[Path, Path]]:
    """`clip_dir` 配下のクリップファイルを列挙する。

    Args:
        settings: `config/settings.yaml` を読み込んだ設定辞書。

    Yields:
        `(clip_dir, clip_path)` のタプル。`clip_dir` はクリップ全体の
        ルート、`clip_path` は個々の Markdown ファイルの絶対パス。

    Raises:
        SystemExit: `clip_dir` が存在しない場合。

    """
    paths = settings.get("paths", {})
    clip_dir = expand(paths.get("clip_dir", "~/Obsidian"))
    if not clip_dir.exists():
        sys.exit(
            f"clip_dir が存在しません: {clip_dir}\n"
            "config/settings.yaml を確認してください。"
        )
    pattern = "**/*.md" if paths.get("recursive", True) else "*.md"
    excludes = paths.get("exclude") or []
    for clip_path in sorted(clip_dir.glob(pattern)):
        rel = clip_path.relative_to(clip_dir).as_posix()
        if any(fnmatch.fnmatch(rel, ex) for ex in excludes):
            continue
        yield clip_dir, clip_path


def build_index(settings: dict) -> list[dict]:
    """クリップファイルを走査し、索引エントリのリストを組み立てる。

    Args:
        settings: `config/settings.yaml` を読み込んだ設定辞書。

    Returns:
        各クリップの id・path・title・url・tags・clipped_at・mtime・
        chars・hash を持つ辞書のリスト。

    """
    keys = settings.get("clip_frontmatter_keys", {})
    entries = []
    for clip_dir, clip_path in iterator_for_clip_files(settings):
        try:
            text = clip_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        frontmatter, body = parse_frontmatter(text)
        content_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
        title = pick(frontmatter, keys.get("title") or ["title"])
        if isinstance(title, list):
            title = title[0] if title else None
        tags = pick(frontmatter, keys.get("tags") or ["tags"]) or []
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        clipped_at = pick(frontmatter, keys.get("clipped_at") or ["created"])
        entries.append(
            {
                "id": hashlib.sha1(clip_path.as_posix().encode()).hexdigest()[:10],
                "path": clip_path.relative_to(clip_dir).as_posix(),
                "abspath": clip_path.as_posix(),
                "title": str(title) if title else clip_path.stem,
                "url": str(pick(frontmatter, keys.get("url") or ["source"]) or ""),
                "tags": [str(t) for t in tags],
                "clipped_at": str(clipped_at) if clipped_at else "",
                "mtime": dt.datetime.fromtimestamp(clip_path.stat().st_mtime)
                .astimezone()
                .isoformat(timespec="seconds"),
                "chars": len(body),
                "hash": content_hash,
            }
        )
    return entries


def used_counts() -> dict[str, int]:
    """既出レジストリからクリップごとの使用回数を取得する。

    Returns:
        クリップの相対パスをキー、使用回数を値とする辞書。レジストリが
        まだ無ければ空の辞書。

    """
    if not REGISTRY.exists():
        return {}
    reg = load_yaml(REGISTRY) or {}
    return dict(reg.get("clip_usage") or {})


def cmd_rebuild(settings: dict) -> None:
    """クリップ索引を作り直し、`state/clip_index.yaml` に書き出す。

    Args:
        settings: `config/settings.yaml` を読み込んだ設定辞書。

    """
    entries = build_index(settings)
    dump_yaml(
        {
            "generated_at": dt.datetime.now()
            .astimezone()
            .isoformat(timespec="seconds"),
            "clips": entries,
        },
        INDEX,
    )
    print(f"{len(entries)} 件のクリップを索引化しました -> {INDEX.relative_to(ROOT)}")


def used_tag_of(settings: dict) -> str:
    """設定から「使用済み」を表す frontmatter タグ名を取得する。

    Args:
        settings: `config/settings.yaml` を読み込んだ設定辞書。

    Returns:
        タグ名。未設定なら `"question_made"`。

    """
    return str((settings.get("paths") or {}).get("used_tag") or "question_made")


def cmd_unused(
    settings: dict, n: int, tag: str | None, min_chars: int, include_used: bool
) -> None:
    """条件に合う未使用クリップを標準出力に列挙する。

    Args:
        settings: `config/settings.yaml` を読み込んだ設定辞書。
        n: 列挙する最大件数。
        tag: 指定時、このタグを持つクリップのみに絞り込む。
        min_chars: 本文の文字数がこれ未満のクリップは除外する。
        include_used: `True` の場合、使用済みタグが付いたクリップも含める。

    """
    if not INDEX.exists():
        cmd_rebuild(settings)
    data = load_yaml(INDEX) or {}
    used = used_counts()
    cap = int((settings.get("limits") or {}).get("max_questions_per_clip", 2))
    used_tag = used_tag_of(settings)
    rows = []
    for c in data.get("clips", []):
        if not include_used and used_tag in c.get("tags", []):
            continue
        cnt = used.get(c["path"], 0)
        if cnt >= cap:
            continue
        if tag and tag not in c.get("tags", []):
            continue
        if c.get("chars", 0) < min_chars:
            continue
        rows.append((cnt, c))
    # 未使用 → クリップ本文のハッシュ値順（新旧に偏らないよう疑似ランダムに均一化する）
    rows.sort(key=lambda r: (r[0], r[1].get("hash", "")))
    for cnt, c in rows[:n]:
        tags = ",".join(c.get("tags", []))
        print(f"[{cnt}/{cap}] {c['path']}\t{c['title']}\t{tags}\t{c.get('url', '')}")
    if not rows:
        print("条件に合う未使用クリップがありません。", file=sys.stderr)


def find_clip_entry(data: dict, name: str) -> dict | None:
    """索引から `name` に対応するクリップエントリを探す。

    完全一致 → 大小文字を無視した一致 → ファイル名(stem)・title 一致の
    順に緩く照合する。

    Args:
        data: `state/clip_index.yaml` を読み込んだ索引データ。
        name: 探すクリップのパスまたはタイトル。

    Returns:
        見つかったエントリの辞書。見つからなければ `None`。

    """
    clips = data.get("clips", [])
    for c in clips:
        if c["path"] == name:
            return c
    # 拡張子・大小文字の揺れなどに寛容な二次照合
    for c in clips:
        if c["path"].lower() == name.lower():
            return c
    for c in clips:
        if Path(c["path"]).stem == Path(name).stem or c.get("title") == name:
            return c
    return None


def cmd_mark_used(settings: dict, name: str) -> None:
    """指定したクリップに使用済みタグを付ける。

    Args:
        settings: `config/settings.yaml` を読み込んだ設定辞書。
        name: `state/clip_index.yaml` の `path` と一致するクリップの
            相対パス（またはタイトル）。

    Raises:
        SystemExit: 索引内に対応するクリップが見つからない場合。

    """
    if not INDEX.exists():
        cmd_rebuild(settings)
    data = load_yaml(INDEX) or {}
    entry = find_clip_entry(data, name)
    if entry is None:
        sys.exit(
            f"クリップが見つかりません: {name!r}\n"
            "meta.source_clip が clip_index.yaml の path と完全一致\n"
            "しているか確認してください"
            "（uv run scripts/clip_index.py --unused で\n"
            "実際のファイル名を確認できます）。"
        )

    used_tag = used_tag_of(settings)
    abspath = Path(entry["abspath"])
    changed = add_frontmatter_tag(abspath, used_tag)

    if used_tag not in entry.get("tags", []):
        entry.setdefault("tags", []).append(used_tag)
        dump_yaml(data, INDEX)

    if changed:
        print(f"タグ付けしました: {entry['path']} に「{used_tag}」を追加 -> {abspath}")
    else:
        print(f"既にタグ済みでした: {entry['path']}（「{used_tag}」）")
