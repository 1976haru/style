# AGENTS.md — Suno Master Prompt Studio

## Goal
Maintain a conservative, testable compiler that turns large user directives and public Suno prompting knowledge into structured 15-track plans and paste-ready generation instructions.

## Non-negotiable invariants
- Story, scene, title and hook are locked by default after parsing. Never silently rewrite them.
- Music fields (BPM, genre, vocal, role, structure, performance signature) may be recomputed, but preserve old and new values plus a reason.
- HYBRID mode must not re-inject the full legacy multi-thousand-line directive into the active prompt.
- External references may contribute abstract DNA only. Do not copy expressive lyric wording, titles or melodies.
- Feedback is evidence, not truth. Do not activate local-learning guidance until the minimum sample threshold is met.
- Market scores are experimental-priority heuristics, never revenue guarantees.
- Keep the app usable offline with Python standard library only. Do not add dependencies without a clear reason.
- Windows remains the primary user environment.

## Development workflow
1. Read README.md and ARCHITECTURE_v05.md before changing architecture.
2. Make focused changes; avoid large rewrites unless requested.
3. Run `python -m pytest -q` before finalizing when pytest is available.
4. Also run `python -m compileall -q .`.
5. Add/adjust tests for parser locks, recomputation, feedback thresholding and compiler output.
6. Never commit real user feedback databases or private instruction files.

## Code style
- Python 3.11+.
- Standard library preferred.
- Keep core logic in `core/`; UI orchestration stays in `main.py`.
- Store user-mutable data under `user_data/`, which is gitignored.


## Desktop build invariants
- Windows portable desktop build is a first-class release target.
- Keep source execution and PyInstaller execution compatible.
- Bundled read-only assets must resolve through `core.app_paths.RESOURCE_ROOT`.
- User-mutable registry/settings must resolve through `core.app_paths.USER_DATA_ROOT`, not a temporary PyInstaller extraction directory.
- Preserve `SunoMasterPromptStudio.spec`, `build_windows_desktop.bat`, and `.github/workflows/windows-desktop.yml`.
- Runtime/core/UI/data changes are not complete until pytest, compileall, startup-check, and Windows desktop packaging pass.
- Use `CODEX_UPGRADE_TEMPLATE.md` as the default Codex task contract.

## CHILI sectional music hard gate
- For vocal Chill Rap tracks, actual `stylePrompt` must expose Hook, Bridge, and Final money-chord progression(s).
- One or multiple progressions per section are valid; never force exactly one.
- Bridge requires at least 2 audible axes, or 3 on Anchor tracks.
- Final Highlight requires General A+B or Anchor A+B+C/equivalent, full-pocket return, root-bass/cadence motion, and explicit Final resolution.
- Metadata-only Bridge/Money Chord/Highlight controls must fail final QA if absent from the actual stylePrompt.
