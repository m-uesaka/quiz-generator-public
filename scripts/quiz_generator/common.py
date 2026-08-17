"""共通ヘルパ。`quiz_generator` 内の各モジュール・`scripts/*.py` から import される。"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SETTINGS = ROOT / "config" / "settings.yaml"
MIN_QUOTED_LEN = 2


def load_settings(path: Path | None = None) -> dict:
    """設定 YAML を読み込む。

    Args:
        path: 設定ファイルのパス。省略時は `config/settings.yaml`。

    Returns:
        設定内容の辞書。ファイルが空なら空の辞書。

    """
    path = path or DEFAULT_SETTINGS
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def expand(p: str) -> Path:
    """`~` を含むパス文字列を展開し、絶対パスにする。

    Args:
        p: 展開対象のパス文字列。

    Returns:
        ユーザーディレクトリ展開・絶対化済みの `Path`。

    """
    return Path(os.path.expanduser(str(p))).resolve()


_KATA = str.maketrans(
    {chr(c): chr(c + 0x60) for c in range(0x3041, 0x3097)}  # ひらがな -> カタカナ
)

_STRIP_RE = re.compile(
    r"[\s　「」『』（）\(\)\[\]【】・,、,\.。!！?？'\"’”\-ー–—_/／]+"
)


def normalize_answer(s: str) -> str:
    """既出判定用の正規化。全半角・かな/カナ・記号・大文字小文字を吸収する。

    Args:
        s: 正規化対象の文字列（`None` も許容する）。

    Returns:
        正規化後の文字列。`s` が `None` なら空文字列。

    """
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = s.casefold()
    s = s.translate(_KATA)
    s = _STRIP_RE.sub("", s)
    return s


def load_yaml(path: Path) -> object:
    """YAML ファイルを読み込む。

    Args:
        path: 読み込む YAML ファイルのパス。

    Returns:
        パース結果（辞書・リストなど、内容に応じた型）。

    """
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class IndentDumper(yaml.SafeDumper):
    """リストを親キーより深くインデントする（YAML_GUIDE の推奨形式に合わせる）。"""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        """`indentless` を常に `False` にしてリスト項目をインデントさせる。

        Args:
            flow: フロースタイルかどうか（`yaml.SafeDumper` から渡される）。
            indentless: 呼び出し元からの指定は無視し、常に `False` を使う。

        Returns:
            親クラスの `increase_indent` の戻り値。

        """
        return super().increase_indent(flow, False)


def dump_yaml(data: object, path: Path) -> None:
    """データを YAML として `path` に書き出す（親ディレクトリは自動作成）。

    Args:
        data: 書き出す対象のデータ（辞書・リストなど）。
        path: 出力先のパス。

    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            Dumper=IndentDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=10**6,
        )


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Markdown の YAML frontmatter を (dict, 本文) に分解する。

    Args:
        text: frontmatter を含む可能性がある Markdown 全文。

    Returns:
        `(frontmatter, body)` のタプル。frontmatter が無い・壊れている場合は
        `({}, text)`。

    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n")
    if parts[0].strip() != "---":
        return {}, text
    for i in range(1, len(parts)):
        if parts[i].strip() in ("---", "..."):
            raw = "\n".join(parts[1:i])
            body = "\n".join(parts[i + 1 :])
            try:
                fm = yaml.safe_load(raw) or {}
            except yaml.YAMLError:
                fm = {}
            if not isinstance(fm, dict):
                fm = {}
            return fm, body
    return {}, text


def pick(fm: dict, keys: list[str]) -> object:
    """Frontmatter から最初に見つかったキーの値を返す。

    Args:
        fm: `parse_frontmatter` などで得た frontmatter の辞書。
        keys: 優先順に試すキーのリスト。

    Returns:
        最初に空でない値が見つかったキーの値。見つからなければ `None`。

    """
    for k in keys:
        if k in fm and fm[k] not in (None, "", []):
            return fm[k]
    return None


def _read_frontmatter_lines(path: Path) -> tuple[list[str], list[str]]:
    """Markdown ファイルを frontmatter 部分とそれ以降に分割する。

    Args:
        path: 対象の Markdown ファイルのパス。

    Returns:
        `(fm_lines, rest_lines)` のタプル。`rest_lines` は閉じの "---" 以降
        （本文含む）。

    Raises:
        ValueError: frontmatter が存在しない、または閉じられていない場合。

    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"frontmatter が見つかりません: {path}")

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end_idx = i
            break
    if end_idx is None:
        raise ValueError(f"frontmatter が閉じられていません: {path}")

    return lines[1:end_idx], lines[end_idx:]


def _strip_quotes(s: str) -> str:
    """前後の引用符（`'` `"`）を1組だけ取り除く。"""
    s = s.strip()
    if len(s) >= MIN_QUOTED_LEN and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _find_tags_key(fm_lines: list[str], tags_key: str) -> tuple[int | None, str]:
    """`tags_key` の行番号とインライン値部分を探す。

    Returns:
        `(key_idx, inline_rest)` のタプル。見つからなければ `(None, "")`。

    """
    key_re = re.compile(rf"^{re.escape(tags_key)}\s*:(.*)$")
    for i, line in enumerate(fm_lines):
        m = key_re.match(line)
        if m:
            return i, m.group(1).strip()
    return None, ""


def _block_list_item_idxs(fm_lines: list[str], key_idx: int) -> list[int]:
    """`tags:` 直後に続くブロックリスト項目（`  - ...`）の行番号を集める。"""
    item_idxs = []
    j = key_idx + 1
    while j < len(fm_lines) and re.match(r"^\s+-\s+\S", fm_lines[j]):
        item_idxs.append(j)
        j += 1
    return item_idxs


def _add_to_block_list(fm_lines: list[str], item_idxs: list[int], tag: str) -> bool:
    """既存のブロックリスト形式の tags に `tag` を追加する（`fm_lines` を書き換える）。

    Returns:
        追加したら `True`、既に含まれていれば `False`。

    """
    existing = [_strip_quotes(re.sub(r"^\s+-\s+", "", fm_lines[k])) for k in item_idxs]
    if tag in existing:
        return False
    indent_m = re.match(r"^(\s+)-\s+", fm_lines[item_idxs[0]])
    indent = indent_m.group(1) if indent_m else "  "
    fm_lines.insert(item_idxs[-1] + 1, f'{indent}- "{tag}"')
    return True


def _add_to_inline_list(
    fm_lines: list[str], key_idx: int, inline_rest: str, tag: str, tags_key: str
) -> bool:
    """インライン形式（`[a, b]` またはカンマ区切り）の tags に `tag` を追加する。

    `fm_lines` を書き換える。

    Returns:
        追加したら `True`、既に含まれていれば `False`。

    """
    if inline_rest.startswith("[") and inline_rest.endswith("]"):
        inner = inline_rest[1:-1]
        items = [_strip_quotes(x) for x in inner.split(",") if _strip_quotes(x)]
        if tag in items:
            return False
        items.append(tag)
        fm_lines[key_idx] = (
            f"{tags_key}: [" + ", ".join(f'"{it}"' for it in items) + "]"
        )
        return True

    items = [_strip_quotes(x) for x in inline_rest.split(",") if _strip_quotes(x)]
    if tag in items:
        return False
    items.append(tag)
    fm_lines[key_idx : key_idx + 1] = [f"{tags_key}:"] + [f'  - "{it}"' for it in items]
    return True


def add_frontmatter_tag(path: Path, tag: str, tags_key: str = "tags") -> bool:
    """Markdown ファイルの YAML frontmatter にタグを追加する（冪等）。

    本文・他のキーの書式（クォート・改行等）はできるだけ変更せず、
    tags キーの周辺だけを行単位で編集する。既に付いていれば何もしない。

    Args:
        path: 対象の Markdown ファイルのパス。
        tag: 追加するタグの値。
        tags_key: frontmatter 中のタグを表すキー名。

    Returns:
        実際にファイルを書き換えたら `True`、既にタグ済みなら `False`。

    Raises:
        ValueError: frontmatter が存在しない、または閉じられていない場合。

    """
    path = Path(path)
    fm_lines, rest_lines = _read_frontmatter_lines(path)

    key_idx, inline_rest = _find_tags_key(fm_lines, tags_key)
    if key_idx is None:
        # tags キー自体が存在しない → frontmatter の末尾に新設する
        fm_lines = [*fm_lines, f"{tags_key}:", f'  - "{tag}"']
        path.write_text("\n".join(["---", *fm_lines, *rest_lines]), encoding="utf-8")
        return True

    item_idxs = _block_list_item_idxs(fm_lines, key_idx)
    if item_idxs:
        added = _add_to_block_list(fm_lines, item_idxs, tag)
    elif inline_rest and inline_rest not in ("~", "null", "Null", "NULL"):
        added = _add_to_inline_list(fm_lines, key_idx, inline_rest, tag, tags_key)
    else:
        # tags: （空・null）→ ブロックリストに変換して1件追加
        fm_lines[key_idx] = f"{tags_key}:"
        fm_lines.insert(key_idx + 1, f'  - "{tag}"')
        added = True

    if not added:
        return False
    path.write_text("\n".join(["---", *fm_lines, *rest_lines]), encoding="utf-8")
    return True


def work_items(doc: object) -> list[dict]:
    """work/*.yaml と output/*.yaml の両方を受け取り、問題のリストを返す。

    Args:
        doc: `load_yaml` で読み込んだ YAML の内容。`{"items": [...]}` の
            辞書形式（work/）、問題のリスト形式（output/）のどちらも受け付ける。

    Returns:
        問題（辞書）のリスト。想定外の型なら空リスト。

    """
    if isinstance(doc, dict):
        return list(doc.get("items") or [])
    if isinstance(doc, list):
        return list(doc)
    return []
