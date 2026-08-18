# Changelog

*[日本語版](CHANGELOG.md)*

This document summarizes the notable changes in each version of the `quiz-generator`
repository. It follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
format.

## [v1.1] - 2026-08-17

### Added

- Introduced `pyproject.toml`, so `uv sync` can build a local virtual environment for
  editor autocompletion/type checking, lint (ruff), and tests (pytest).
- Added `uv.lock` to pin dependency versions.

### Changed

- Split `scripts/*.py` into a CLI layer (command definitions via typer) and a logic
  layer under `scripts/quiz_generator/*.py`.
  - Removed the single-file `scripts/quizlib.py`.
  - Reorganized the contents of `quizlib.py` into several files under
    `scripts/quiz_generator/`.
- Split up the files under `config/`.
  - Split the answer/spell field and criteria notation rules out of
    `config/quiz_question_style_guide.md` into `config/quiz_notation_rules.md`.
  - Split the angle patterns / how information is combined out of
    `config/quiz_topic_taste_guide.md` into `config/quiz_topic_framing_guide.md`.
  - Updated the subagent definitions (`.claude/agents/*.md`) to reference the new
    file layout.
  - As a result, each subagent now only needs to read the files relevant to it,
    reducing token cost.

### Fixed

- `CLAUDE.md` / `README.md` described a 6-stage cycle that included
  `quiz-fact-checker`, while `docs/architecture.md` and the actual implementation
  (`SKILL.md` and the agent definitions) were designed to exclude
  `quiz-fact-checker` from the normal cycle — a contradiction. Corrected the
  descriptions to match the implementation.
- The candidate-topic count in `quiz-batch/SKILL.md` was hardcoded to `8`, which did
  not match the value configured in `config/settings.yaml` (default `4`). Fixed.
- `.gitignore` was mistakenly ignoring `dist/`, the output directory used by
  `/quiz-export`. Fixed.
- The script list in `docs/architecture.md` listed a nonexistent `quizlib.py` as the
  shared helper module. Updated it to match the actual `scripts/quiz_generator/`
  package layout. Also added local-environment setup instructions for the
  post-`pyproject.toml` workflow (`uv sync` / venv activate / `ruff` / `pytest`) to
  `README.md`.

## [v1.0] - 2026-08-14

Initial release. Includes the scripts for clip indexing, the duplicate registry, YAML
conversion, and diff extraction; the five-stage subagent pipeline `clip-scout` →
`quiz-writer` → `quiz-adversarial-checker` → `quiz-style-reviewer` →
`quiz-final-editor`; and the feedback loop into `LEARNINGS.md`.
