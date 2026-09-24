# Codex Task Queue — v0.5-dev

Read `AGENTS.md`, `ARCHITECTURE_v04.md`, and `V05_PLAN.md` before implementation.

## Current priority
1. Keep `core/learning.py` pure and deterministic.
2. Add UI read-only view for learning confidence, top BPM windows, genres, signature atoms and failure tags.
3. Add Track Plan A/B columns that show `experiment.arm`, `axis`, and proposed changes without applying them automatically.
4. Add experiment manifest export.
5. Only after UI/reporting is stable, design backward-compatible experiment metadata storage for feedback.

## Required invariants
- Story / Scene / Title / Hook locks are immutable.
- Fixed channel voice fingerprint cannot be replaced by learning.
- Under 30 feedback samples, A/B empirical activation stays off.
- v0.5 does not auto-rewrite master prompts.
- Proposed BPM must later be clamped to current master role range.
- One B track tests one primary axis.

## Regression requirements
- Run `python -m pytest -q`.
- Run `python -m compileall -q .`.
- Run `git diff --check`.
- Preserve all v0.4.2 E2E tests.

## Deferred until enough real data exists
- Automatic master evolution.
- Multi-armed bandit/online optimization.
- Revenue-based optimization.
- Network scraping or private Suno APIs.

## Prior v0.4 queue
# Codex Task Queue

Use this file for small, reviewable repository tasks. Ask Codex for one task at a time unless the tasks are tightly coupled.

## Good first Codex tasks after v0.4 is on GitHub
- Add unit tests for malformed Track Plan tables and mixed JSON/Markdown inputs.
- Add a bulk feedback entry screen for 15 tracks without changing the SQLite schema.
- Add export/import for `user_data/feedback.sqlite3` through portable JSON backup.
- Add per-channel feedback filters and a date-range filter.
- Add a diff view for original vs recomputed vocal/genre/structure, not only BPM.
- Add CI test matrix for Python 3.11/3.12 on Windows and Ubuntu.

## Do NOT delegate blindly
- Changing story-lock semantics.
- Changing score weights or minimum feedback sample thresholds.
- Replacing the compiler priority stack.
- Adding automatic network scraping or private APIs.
- Changing external-reference copyright/originality rules.

For those, first write a short design note and review it before implementation.

