# Changelog

## 0.4.0
- Added local SQLite Feedback DB.
- Added KEEP/MAYBE/REGEN and 1-5 ratings for overall, vocal identity, hook, groove and prompt adherence.
- Added failure tags and runtime/notes.
- Added feedback-aware market recipe reranking after minimum 3 samples.
- Added compact local performance evidence injection into compiler as a soft prior.
- Added Feedback UI tab and JSON/CSV export.
- Added GitHub-ready `.gitignore`, `AGENTS.md`, `CODEX_TASKS.md`, and CI workflow.
- Preserved v0.3 Story/Scene/Title/Hook lock semantics.
- Compiler version bumped to 0.4.0.

## 0.3.0
See prior release documentation.

## 0.4.1 — real-input stress-test hotfix
- Fixed BPM parser misreading lyric-length ranges such as `Anchor 460~560 chars` as tempo.
- Added BPM plausibility QA gate (30–240 BPM).
- Preserved Male Solo / Female Solo / Duet role in CHILI dual Track Plans while refreshing shared voice signatures.
- Removed duplicate `tint tint` suffix when importing an already-tinted genre.
- Added real-input regression tests for master BPM parsing and dual vocal-role preservation.
