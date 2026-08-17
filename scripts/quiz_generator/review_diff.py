"""生成した YAML と、人間が修正した YAML の差分を構造化するロジック。

CLI エントリポイントは `scripts/review_diff.py`。
"""

from __future__ import annotations

import difflib

from quiz_generator.common import normalize_answer

TEXT_FIELDS = ["question", "answer", "spell"]
LIST_FIELDS = ["tags", "comments"]
CRITERIA_KEYS = ["ok", "ng", "repeat"]
QUESTION_MATCH_THRESHOLD = 0.55
MIN_SPOILER_ANSWER_LEN = 2
LENGTH_DROP_THRESHOLD = -15


def create_inline_diff(string_before_change: str, string_after_change: str) -> str:
    """変更箇所を - / + で示す短い説明を作る。

    Args:
        string_before_change: 変更前の文字列。
        string_after_change: 変更後の文字列。

    Returns:
        `-「削除された部分」 +「追加された部分」` の形式の説明文字列。
        差分がなければ空文字列。

    """
    sm = difflib.SequenceMatcher(None, string_before_change, string_after_change)
    out = []
    for (
        tag,
        start_index_before_change,
        end_index_before_change,
        start_index_after_change,
        end_index_after_change,
    ) in sm.get_opcodes():
        if tag == "equal":
            continue
        if (
            tag in ("replace", "delete")
            and string_before_change[start_index_before_change:end_index_before_change]
        ):
            out.append(
                f"-「{string_before_change[start_index_before_change:end_index_before_change]}」"
            )
        if (
            tag in ("replace", "insert")
            and string_after_change[start_index_after_change:end_index_after_change]
        ):
            out.append(
                f"+「{string_after_change[start_index_after_change:end_index_after_change]}」"
            )
    return " ".join(out)


def pair_items(
    base_questions_list: list[dict], reviewed_questions_list: list[dict]
) -> list[tuple[int | None, int | None, str]]:
    """答え一致 → 問題文の類似度 → 残りは追加/削除、の順で対応づける。

    Args:
        base_questions_list: 生成された YAML（output/）の問題リスト。
        reviewed_questions_list: 人間が修正した YAML（reviewed/）の問題リスト。

    Returns:
        `(base_index, rev_index, how)` のタプルのリスト。`how` は
        `"answer"` / `"question(比率)"` / `"removed"` / `"added"` のいずれか。
        `removed` の場合 `rev_index` は `None`、`added` の場合
        `base_index` は `None`。

    """
    pairs, used_reviewed_questions = [], set()

    reviewed_by_answer: dict[str, list[int]] = {}
    for reviewed_question_index, reviewed_question in enumerate(
        reviewed_questions_list
    ):
        reviewed_by_answer.setdefault(
            normalize_answer(reviewed_question.get("answer", "")), []
        ).append(reviewed_question_index)

    unmatched_base = []
    for base_question_index, base_question in enumerate(base_questions_list):
        answer_candidates = reviewed_by_answer.get(
            normalize_answer(base_question.get("answer", "")), []
        )
        answer_candidates = [
            answer
            for answer in answer_candidates
            if answer not in used_reviewed_questions
        ]
        if answer_candidates:
            used_reviewed_questions.add(answer_candidates[0])
            pairs.append((base_question_index, answer_candidates[0], "answer"))
        else:
            unmatched_base.append(base_question_index)

    for base_question_index in unmatched_base:
        base_question_answer = normalize_answer(
            base_questions_list[base_question_index].get("question", "")
        )
        best_fitted_question_index, best_ratio = None, 0.0
        for reviewed_question_index, reviewed_question in enumerate(
            reviewed_questions_list
        ):
            if reviewed_question_index in used_reviewed_questions:
                continue
            ratio = difflib.SequenceMatcher(
                None,
                base_question_answer,
                normalize_answer(reviewed_question.get("question", "")),
            ).ratio()
            if ratio > best_ratio:
                best_fitted_question_index, best_ratio = reviewed_question_index, ratio
        if (
            best_fitted_question_index is not None
            and best_ratio >= QUESTION_MATCH_THRESHOLD
        ):
            used_reviewed_questions.add(best_fitted_question_index)
            pairs.append(
                (
                    base_question_index,
                    best_fitted_question_index,
                    f"question({best_ratio:.2f})",
                )
            )
        else:
            pairs.append((base_question_index, None, "removed"))

    for reviewed_question_index in range(len(reviewed_questions_list)):
        if reviewed_question_index not in used_reviewed_questions:
            pairs.append((None, reviewed_question_index, "added"))
    return pairs


def guess_hint_tag(
    diff_per_field: dict, question_before_change: dict, question_after_change: dict
) -> list[str]:
    """変更されたフィールドから、修正の性質を表すヒントタグを推定する。

    Args:
        diff_per_field: `diff_item` が返すフィールドごとの差分。
        question_before_change: 修正前の問題（`meta` 等を含む元の辞書）。
        question_after_change: 修正後の問題。

    Returns:
        `"fact"` / `"unique"` / `"spoiler"` / `"length"` / `"style"` /
        `"meta"` のうち該当するものをソートしたリスト。

    """
    hints = []
    if "answer" in diff_per_field:
        hints.append("fact")
    if "criteria" in diff_per_field:
        hints.append("unique")
    if "question" in diff_per_field:
        question_before, question_after = (
            diff_per_field["question"]["before"],
            diff_per_field["question"]["after"],
        )
        answer_after_change = str(question_after_change.get("answer", ""))
        if (
            answer_after_change
            and len(answer_after_change) >= MIN_SPOILER_ANSWER_LEN
            and answer_after_change in question_before
            and answer_after_change not in question_after
        ):
            hints.append("spoiler")
        if len(question_after) - len(question_before) <= LENGTH_DROP_THRESHOLD:
            hints.append("length")
        hints.append("style")
    if (
        "tags" in diff_per_field
        or "spell" in diff_per_field
        or "comments" in diff_per_field
    ):
        hints.append("meta")
    return sorted(set(hints))


def return_structured_diff_per_question(
    base_question_data: dict, reviewed_question_data: dict
) -> dict:
    """対応づけられた1問について、フィールドごとの差分を構造化する。

    Args:
        base_question_data: 修正前の問題（output/ 側）。
        reviewed_question_data: 修正後の問題（reviewed/ 側）。

    Returns:
        変更があったフィールドのみを含む辞書。`question` / `answer` /
        `spell` は `before` / `after` / `diff`、`tags` / `comments` は
        `before` / `after` / `added` / `removed`、`criteria` は各キー
        （ok/ng/repeat）ごとの `added` / `removed` を持つ。変更がなければ
        空の辞書。

    """
    fields: dict = {}
    for key in TEXT_FIELDS:
        base_value, reviewed_value = (
            str(base_question_data.get(key, "") or ""),
            str(reviewed_question_data.get(key, "") or ""),
        )
        if base_value != reviewed_value:
            fields[key] = {
                "before": base_value,
                "after": reviewed_value,
                "diff": create_inline_diff(base_value, reviewed_value),
            }
    for key in LIST_FIELDS:
        base_value = [str(x) for x in (base_question_data.get(key) or [])]
        reviewed_value = [str(x) for x in (reviewed_question_data.get(key) or [])]
        if base_value != reviewed_value:
            fields[key] = {
                "before": base_value,
                "after": reviewed_value,
                "added": [x for x in reviewed_value if x not in base_value],
                "removed": [x for x in base_value if x not in reviewed_value],
            }
    base_criteria, reviewed_criteria = (
        base_question_data.get("criteria") or {},
        reviewed_question_data.get("criteria") or {},
    )
    criteria_dict = {}
    for key in CRITERIA_KEYS:
        base_value = [str(x) for x in (base_criteria.get(key) or [])]
        reviewed_value = [str(x) for x in (reviewed_criteria.get(key) or [])]
        if base_value != reviewed_value:
            criteria_dict[key] = {
                "added": [x for x in reviewed_value if x not in base_value],
                "removed": [x for x in base_value if x not in reviewed_value],
            }
    if criteria_dict:
        fields["criteria"] = criteria_dict
    return fields
