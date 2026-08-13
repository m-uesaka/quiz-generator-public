"""共通ヘルパ。各スクリプトから import される。"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS = ROOT / "config" / "settings.yaml"


def load_settings(path: Path | None = None) -> dict:
    path = path or DEFAULT_SETTINGS
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def expand(p: str) -> Path:
    return Path(os.path.expanduser(str(p))).resolve()


_KATA = str.maketrans(
    {chr(c): chr(c + 0x60) for c in range(0x3041, 0x3097)}  # ひらがな -> カタカナ
)

_STRIP_RE = re.compile(r"[\s　「」『』（）\(\)\[\]【】・,、,\.。!！?？'\"’”\-ー–—_/／]+")


def normalize_answer(s: str) -> str:
    """既出判定用の正規化。全半角・かな/カナ・記号・大文字小文字を吸収する。"""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = s.casefold()
    s = s.translate(_KATA)
    s = _STRIP_RE.sub("", s)
    return s


def load_yaml(path: Path):
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class IndentDumper(yaml.SafeDumper):
    """リストを親キーより深くインデントする（YAML_GUIDE の推奨形式に合わせる）。"""

    def increase_indent(self, flow=False, indentless=False):  # noqa: ARG002
        return super().increase_indent(flow, False)


def dump_yaml(data, path: Path) -> None:
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
    """Markdown の YAML frontmatter を (dict, 本文) に分解する。"""
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


def pick(fm: dict, keys: list[str]):
    """frontmatter から最初に見つかったキーの値を返す。"""
    for k in keys:
        if k in fm and fm[k] not in (None, "", []):
            return fm[k]
    return None


def work_items(doc) -> list[dict]:
    """work/*.yaml と output/*.yaml の両方を受け取り、問題のリストを返す。"""
    if isinstance(doc, dict):
        return list(doc.get("items") or [])
    if isinstance(doc, list):
        return list(doc)
    return []
