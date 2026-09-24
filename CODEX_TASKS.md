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
