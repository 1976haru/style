# Changelog

## 0.6.1-dev — Channel Consistency Finalizer
### Female Voice Isolation Gate
- Added female-only positive-prompt isolation checks after real Suno renders produced unintended male voices.
- Female Solo positive fields now reject male/duet/self-response/self-answer/self-double/vocal-stack cues.
- Added affirmative single-female continuity requirement across Verse/Chorus/Bridge/Final.
- Wrong-gender terms stay in dedicated negative fields only.
- Final merge safely normalizes bracketed `Female Self-Response/Self-Answer/Self-Double` labels to `Same Solo Female Voice` without changing lyric body text.
- Research A/B/C candidate role locks now use affirmative single-voice wording.

- Added `core/v061_quality_gate.py` for JP-native positive-control checks and stylePrompt↔vocalDesign phonation consistency.
- Corrected Chill Rap prompt ordering to genre/tint → BPM+groove → singer/phonation → JP-native/rap pocket → arrangement/sections/harmony/runtime.
- Optimizer instructions now explicitly require close-mic, native Japanese diction, mora timing and natural sentence/pitch-accent behavior in actual Japanese vocal prompts.
- Final import validation rejects missing JP-native positive controls and conflicting breath/grain coordinates.
- Updated v0.6 Research A/B/C engine to `0.6.1-dev` and inject JP-native controls for Japanese source metadata.
- Preserved immutable title/lyrics/hook/story/scene protections and main branch stability.

## 0.6.0-dev — Research-Driven Prompt Engine
- Added provenance-aware `data/research_prompt_knowledge.json` with official Suno v6/Variety/Max Mode/Inspire/Style Influence/Custom Model guidance and clearly-labeled community hypotheses.
- Added `data/style_compatibility_matrix.json` for one-dominant-genre + one-secondary-tint controlled exploration across all current genres.
- Added `core/research_prompt_engine.py` to produce three controlled experiment arms per track: A_CONTROL, B_GROOVE, C_CHARACTER.
- Added generation recipes that hold model/settings stable so prompt-axis changes can be evaluated cleanly.
- Added safe variant application that deep-copies the source and changes only style/exclude prompt fields plus research audit metadata.
- Added Simple UI actions for research candidate generation and A/B/C JSON export.
- Added dedicated v0.6 research-engine regression tests.
- Added feedbackBinding metadata to exported research variants and descriptive A_CONTROL/B_GROOVE/C_CHARACTER feedback analysis with no auto-winner or auto-apply behavior.\n
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
