# Codex Task Queue — v0.6-dev

Read `AGENTS.md`, `ARCHITECTURE_v06.md`, and `ARCHITECTURE_v05.md` before implementation.

## Current priority — local Windows acceptance
1. Pull branch `v0.6-dev` without touching `main`.
2. Run `python -m pytest -q`.
3. Run `python -m compileall -q .`.
4. Run `git diff --check`.
5. Run `python main.py --startup-check` if supported, then launch the real GUI with `python main.py`.
6. Load one real 15-track JSON for each available channel family and press `연구 기반 A/B/C 후보`.
7. Verify all 15 tracks receive exactly A_CONTROL / B_GROOVE / C_CHARACTER.
8. Save A/B/C JSON and diff them against the source:
   - title/lyrics/hook/story/scene unchanged
   - source vocal role preserved
   - stylePrompt <= 900 chars
   - A/B/C prompts are materially distinct
   - no stale candidate pack after source or genre changes
9. Do not commit private source JSON, generated user songs, master TXT, API keys, feedback DB or downloaded Suno audio.

## v0.6 invariants
- Official Suno documentation outranks community GitHub observations.
- Community rules are experiment hypotheses, never platform guarantees.
- A/B/C does not declare a winner before real audio feedback.
- Keep model/settings constant while testing a prompt axis.
- One experiment arm has one primary axis.
- Story / Scene / Title / Hook / relationship boundaries remain immutable.
- Fixed channel singer identity and vocal role must not drift.
- Research mode must work offline after the curated knowledge JSON files are present.
- No network scraping or private Suno API calls in the local app.
- `main` remains Stable; development work stays on `v0.6-dev`.

## Next implementation after acceptance — v0.6.1
1. Link `researchRecipe.variantId` and `primaryAxis` to the existing Feedback DB.
2. Add A/B/C feedback comparison by Channel + Genre + Axis.
3. Require paired evidence before showing an empirical preference:
   - observation only at tiny samples
   - never auto-apply a winner
4. Surface which prompt modules correlate with:
   - vocal identity
   - groove
   - hook
   - Bridge
   - Final
   - prompt adherence
5. Keep feedback descriptive and provenance-aware.

## Required regression commands
- `python -m pytest -q`
- `python -m compileall -q .`
- `git diff --check`
- Preserve all v0.4.2/v0.5 regression tests.

## Deferred
- Automatic master rewriting.
- Multi-armed bandit / online auto-optimization.
- Revenue-based optimization.
- Automatic web scraping.
- Private or unofficial Suno APIs.
- OpenAI API direct generation until the offline research/feedback loop is stable.
