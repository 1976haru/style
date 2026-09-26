# Changelog

## 0.5.2-dev — Bridge / Money Chord / Final Highlight Engine
- Promoted Bridge, section-functional Money Chord and Final Highlight from metadata hints to hard Prompt Intelligence quality gates for Chill Rap vocal tracks.
- Requires actual stylePrompt to contain Hook progression(s), Bridge progression(s), and Final resolution progression(s); money chords may be singular or multiple per section.
- Counts Bridge harmonic progression as an audible contrast axis and requires at least 2 Bridge axes, or 3 for Anchor tracks.
- Requires sustained General Final A+B and Anchor A+B+C (or equivalent post-hook), full-pocket/groove return, root-bass/cadence motion and explicit Final resolution.
- Added moneyChordDesign to mutable/audited music fields and applied the same sectional gates to Haru Studio completed JSON validation.
- Strengthened Chill Rap Genre Master and optimizer instructions so Bridge / Money Chord / Highlight must be audible in actual stylePrompt, not merely present as side fields.
- Added regression coverage for multiple money-chord progressions, metadata-only false positives, and Anchor Bridge/Final requirements.

## 0.5.0-dev — Prompt Intelligence Optimizer
- Replaced the existing-JSON “latest master” framing with content-based prompt analysis and optimization.
- Added version-neutral analysis rules in `data/prompt_intelligence_rules.json` across required music/prompt areas.
- Added UI actions for current prompt analysis and AI music prompt upgrade.
- Added per-track old/new stylePrompt, change reasons and expected-improvement audit data.
- Expanded mutable music fields while retaining deep-copy/allow-list protection for all content fields.
- Added immutable verification for title, lyrics, hook, story, scene and relationship boundaries.

## 0.4.2 — Stable E2E validation
- Added full E2E validation harness in `core/e2e.py`.
- Added male / female / dual-story end-to-end fixtures.
- Added 2,100-line-equivalent legacy directive regression coverage for HYBRID non-reinjection.
- Added final-output checks for 15-track count, Story/Scene/Title/Hook locks, vocal gender/role, role BPM ranges, legacy BPM/vocal leakage, genre policy, stylePrompt length, Bridge/Final, Anchor Final, duplicate titles/hooks, language and generic vocal signatures.
- Added negative tests proving required QA failures are actually detected.
- Hardened Windows SQLite handle cleanup and regression tests.
- Verification baseline: 23 tests PASS locally; compileall PASS; git diff --check PASS.
- GitHub Actions verified on Windows 3.11/3.12 and Ubuntu 3.11/3.12.
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
