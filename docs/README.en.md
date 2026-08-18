# quiz-generator

A working-repository template for Claude Code that **automatically writes Japanese
quizzes from web clips accumulated in Obsidian**.

This repository is inspired by [AIによるクイズの自動作問](https://note.com/alocasia011/n/n11581c6e4dc7?sub_rt=share_pw)
(a Japanese article on AI-driven automated quiz writing), but differs in the following
ways.

Main changes from the reference approach (Codex + 6 agents):

| | Reference article | This repository |
| --- | --- | --- |
| Source material | Automated web exploration | **Obsidian clips** (web used only to fill gaps) |
| Runtime | Codex CLI + TOML | **Claude Code Skills + Subagents** |
| Output format | JSONL | **YAML conforming to the quiz-yaml-go schema** |
| Human correction | Adopt/reject via a selection tool | Correction diffs are fed back into **`LEARNINGS.md`** to inform future generation |

## Setup

```bash
# 1. Put this directory wherever you like and bring it under git
git init && git add -A && git commit -m "init"

# 2. Configure where your clips live
$EDITOR config/settings.yaml   # set paths.clip_dir to your Obsidian path

# 3. Build the index (requires PyYAML / typer; uv installs these automatically)
uv run scripts/clip_index.py --rebuild
uv run scripts/clip_index.py --unused -n 20

# 4. Install quiz-yaml-go (used for validation and conversion)
go install github.com/m-uesaka/quiz-yaml-go@latest   # or clone it and go build

# 5. Launch Claude Code
claude
```

Every script under `scripts/*.py` carries PEP 723 inline metadata (`pyyaml` / `typer`)
at the top of the file, so simply running `uv run scripts/xxx.py` resolves dependencies
automatically. There is no need to run `uv sync` beforehand.

### Local environment (pyproject.toml)

If you want editor autocompletion / type checking, want to run scripts with plain
`python3` instead of typing `uv run` every time, or want to run lint / tests, you can
build a virtual environment from the `pyproject.toml` at the repository root (requires
Python 3.12+).

```bash
uv sync                          # create .venv, install pyyaml / typer plus dev deps (pytest, ruff)
source .venv/bin/activate        # afterwards, python3 scripts/xxx.py works without uv run

uv run ruff check .              # lint (uses the [tool.ruff.lint] settings in pyproject.toml)
uv run pytest                    # tests (no test code is set up yet at this point)
```

If you'd rather use plain `pip` instead of `uv`, run `pip install pyyaml typer` and then
use `python3 scripts/clip_index.py ...`.

> Subagents are only loaded at startup. If you edit `.claude/agents/`, restart Claude Code.

## Usage

```
> /quiz-batch                      # write one batch (default 4 questions)
> /quiz-batch geography and history  # write with a specified genre
> /quiz-long-runner until 11pm today  # write continuously until a cutoff time
> /quiz-long-runner continue
> /quiz-learn batch003             # feed human corrections back into LEARNINGS.md
> /quiz-export all csv             # export everything at once
```

## Flow of one cycle

```
Obsidian clips
      │
      ▼
① clip-scout              4+2 candidate topics from unused clips (already deduped)
      ▼
② quiz-writer             question drafts (applying LEARNINGS + style guide)
      ▼
③ quiz-adversarial-checker  rule out alternative answers → finalize criteria (ok/ng/repeat)
      ▼
④ quiz-style-reviewer     style, spoilers, LEARNINGS compliance
      ▼
⑤ quiz-final-editor       finalize adoption → work/batchNNN.yaml
      ▼
   export_yaml.py → output/batchNNN.yaml (conforms to the quiz-yaml-go schema)
      ▼
   human copies it and edits reviewed/batchNNN.yaml
      ▼
   /quiz-learn → review_diff.py → update LEARNINGS.md → back to ①
```

Verifying claims against primary sources (`quiz-fact-checker`) is not part of the
normal cycle. It only runs during human review (when editing `reviewed/batchNNN.yaml`)
or when explicitly requested.

See [Repository Architecture](./architecture.en.md) for details on the agents.

## Role of each file

| Path | Role |
| --- | --- |
| `CLAUDE.md` | Project-wide policy. Read by Claude Code every time |
| `LEARNINGS.md` | **Rules extracted from human corrections. Referenced with top priority during generation** |
| `config/quiz_question_style_guide.md` | Question format / writing style (customize this) |
| `config/quiz_notation_rules.md` | Notation rules for the answer/spell/criteria fields (customize this) |
| `config/quiz_topic_taste_guide.md` | Preferences for topic selection (customize this) |
| `config/quiz_topic_framing_guide.md` | Angle patterns / how to combine information (customize this) |
| `config/settings.yaml` | Paths, limits, thresholds |
| `config/genre_targets.yaml` | Genre-distribution targets (delete if not needed) |
| `.claude/skills/*/SKILL.md` | Bodies of commands like `/quiz-batch` |
| `.claude/agents/*.md` | Definitions for the 6 subagents |
| `scripts/*.py` | Indexing, duplicate detection, conversion, diff extraction (kept out of LLM judgment) |
| `work/` | Working files with metadata. Written by the agents |
| `output/` | Submission-ready YAML. Generated by scripts. Do not touch by hand |
| `reviewed/` | Human-edited version |
| `examples/` | Sample files |

## Building your own guides (this makes the biggest difference in quality)

The four guides under `config/` (`quiz_question_style_guide.md` /
`quiz_notation_rules.md` / `quiz_topic_taste_guide.md` /
`quiz_topic_framing_guide.md`) are generic starting points. The most effective way to
have generation reproduce your own style is to **rebuild them from your own past
questions**. Each file is designed to be read only by its corresponding subagent (see
`.claude/agents/*.md`), so start with the two broad genres (sentence structure/style,
and topic/angle), and once a file grows too large, split out practical notation rules
(furigana, spell, criteria) or angle patterns into a separate file to keep the amount
each subagent has to read down.

1. Feed Claude questions you wrote the normal way, and have it point out factual
   issues, unnatural Japanese, possible alternative answers, and spoilers.
2. Looking at its feedback, propose your own corrections too. **Each time, put into
   words what you changed, why you avoided a certain phrasing, and what information
   would make the answer uniquely determined** (this becomes your log).
3. Once you've accumulated 50–100 questions, ask as follows to regenerate the two
   guides.

```
Analyze our conversation history so far, and write an md file that would let you alone
reproduce the kind of questions I write. Focus not on topics, but on the structural
style of the question text (one-question-one-answer, sentence form, absolutely no
spoilers, and the answer must be uniquely determined overall).
→ save to config/quiz_question_style_guide.md
```

```
Next, summarize into a separate md file the information needed to reproduce my
question-writing from the perspective of the topics and angles I've used so far. Focus
not on format, but on topic selection, angles, and how information is combined.
→ save to config/quiz_topic_taste_guide.md
```

Once a guide grows too large, it helps to split out just the "answer/spell field and
criteria formatting" part of `config/quiz_question_style_guide.md` into
`config/quiz_notation_rules.md`, and just the "angle patterns / how information is
combined" part of `config/quiz_topic_taste_guide.md` into
`config/quiz_topic_framing_guide.md` (see this repository's own split as an example).

Even if you don't have time to do this, running `/quiz-learn` over a few batches will
naturally accumulate equivalent information in `LEARNINGS.md`.

## How LEARNINGS grows

```
1st correction        → recorded in watch (not yet generalized)
2nd same-kind correction → promoted to active (enforced in all subsequent generation)
established after 5   → promoted into config/*.md itself, moved from LEARNINGS to graduated
```

Thresholds can be changed in the `learnings` section of `config/settings.yaml`. If
`active` grows too large, the prompt bloats and becomes less effective, so entries are
consolidated once `max_active_rules` (default 40) is exceeded.

## Scripts

```bash
uv run scripts/clip_index.py --rebuild             # build the clip index
uv run scripts/clip_index.py --unused -n 30 --tag technology
uv run scripts/registry.py rebuild                 # rebuild the duplicate registry
uv run scripts/registry.py check "Nanbu ironware"   # exits 1 if already used
uv run scripts/registry.py stats                   # genre distribution vs. targets
uv run scripts/export_yaml.py work/batch001.yaml -o output/batch001.yaml
uv run scripts/review_diff.py output/batch001.yaml reviewed/batch001.yaml -o state/diff-batch001.yaml
```

Duplicate detection, schema conversion, and diff extraction are **deliberately not
left to the LLM** — an LLM judging "probably not a duplicate" is a recipe for mistakes.

## Clip frontmatter

`scripts/clip_index.py` assumes frontmatter in the style produced by Obsidian Web
Clipper-type tools.

```yaml
---
title: Article title
source: https://example.com/article
created: 2026-07-01
tags: [craft, Iwate]
---
```

If your key names differ, add your own keys to `clip_frontmatter_keys` in
`config/settings.yaml`.

## Operational notes

- Agents stop once clips run out — this is by design, so they never go rummaging
  around the web on their own.
- By default, at most 2 questions may be made from the same clip
  (`limits.max_questions_per_clip`).
- **Always have a human check generated questions before use.** A fact-checking step
  is included, but errors can still slip through. It's especially worth verifying
  years, numbers, and claims like "world's first" with your own eyes.
- If someone else builds the same kind of pipeline, similar questions could come out
  (a concern also raised in the reference article). Since this setup draws on your own
  clips as source material, it should have an advantage in that respect.
