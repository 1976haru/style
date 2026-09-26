# CODEX Upgrade Template — Suno Master Prompt Studio

이 문서를 Codex 작업 시작 프롬프트로 사용한다.

## Repository
- Repository: https://github.com/1976haru/style
- Working branch: `v0.5-dev`
- Current desktop line: `v0.5.2-dev`
- Windows is the primary user environment.
- Default user-facing UI is `SimpleApp`.

## Start-of-task procedure
1. `git fetch origin`
2. `git checkout v0.5-dev`
3. `git pull --ff-only origin v0.5-dev`
4. Read `AGENTS.md`, `ARCHITECTURE_v05.md`, `README.md`, `CHANGELOG.md`.
5. Inspect the files directly related to the requested change before editing.
6. Do not use version/revision labels as proof of quality.

## Non-negotiable content locks
For existing JSON upgrades, never rewrite or normalize:
- title / titleLocalized
- lyrics
- hookPhrase
- story / scene / listenerSituation
- emotionArc / centralImage / seasonMoment / distinctChoice
- relationship/event boundaries
- YouTube metadata and other non-music content

Start finalization from the source JSON and merge only allow-listed music fields.

## Music fields that may be improved
- BPM / genre
- vocal identity / phonation
- groove / drums / bass
- instrumentation
- harmonicDesign / moneyChordDesign
- stylePrompt / excludePrompt
- performanceSignature
- bridgeDesign
- highlightDesign / finalDesign
- durationDesign
- generationRunHint
- promptOptimization audit

## CHILI LAB Chill Rap hard gate
Bridge / Money Chord / Final Highlight are first-class generation controls, not side metadata.

For every vocal Chill Rap track:
1. The actual `stylePrompt` must contain section-functional money-chord progression(s) for:
   - Hook
   - Bridge
   - Final resolution
2. Money chords are NOT limited to one progression.
   - One progression is valid.
   - Multiple progressions are also valid.
   - `moneyChordDesign` may use arrays/lists.
3. `moneyChordDesign` alone is never enough. If the progression is absent from actual `stylePrompt`, final QA must FAIL.
4. Bridge must expose audible contrast:
   - General: at least 2 axes
   - Anchor: at least 3 axes
   - usable axes include drum density, bass motion, harmonic color, vocal distance, texture/instrumentation, space, lyric viewpoint
5. Final Highlight must be sustained:
   - General: Final A+B
   - Anchor: Final A+B+C or equivalent post-hook
   - restore full pocket/groove after Bridge reduction
   - root-bass or cadence motion
   - explicit Final money-chord resolution(s)
   - no one-bar swell then collapse
6. Keep track-level differentiation. Do not clone the same Bridge/Final/performance template across 15 songs.

## Vocal rules
- Preserve source male/female/duet allocation exactly.
- Recurring channel singer identity should remain stable across a set.
- Female Solo positive fields must stay affirmative single-female only; wrong-gender/multi-vocal failure terms belong in negative/exclude fields.
- Japanese vocal prompts must explicitly state close-mic, JP-native diction, mora timing and natural sentence/pitch accent when applicable.
- English sets use connected English, natural stress, relaxed consonants and idiomatic reductions instead of Japanese mora controls.

## Desktop invariants
- The app must run both from source and from the Windows PyInstaller desktop build.
- Read-only bundled assets come from the application resource root.
- User-mutable files must not be stored inside temporary PyInstaller extraction paths.
- Master registry and portable user settings live under the desktop app's `user_data` directory.
- Do not break `SunoMasterPromptStudio.spec`, `build_windows_desktop.bat`, or the Windows desktop GitHub Action.
- If an update changes runtime code, core rules, UI, or data files, rebuild and validate the desktop package.

## Required validation before saying complete
Run all of these:
1. `python -m pytest -q`
2. `python -m compileall -q .`
3. `git diff --check`
4. `python main.py --startup-check`
5. On Windows: `build_windows_desktop.bat`
6. Confirm desktop EXE exists:
   `dist/SunoMasterPromptStudio_v0.5.2/SunoMasterPromptStudio_v0.5.2.exe`
7. Confirm portable ZIP exists:
   `dist/SunoMasterPromptStudio_v0.5.2_WINDOWS.zip`
8. Confirm Windows desktop GitHub Action passes when the branch is pushed.

Do not report completion if any required validation fails.

## Git procedure
After all validation passes:
1. Review `git status` and `git diff --check`.
2. Commit only intended files with a concise message.
3. Push to `origin/v0.5-dev`.
4. Report:
   - branch
   - commit SHA
   - pytest count
   - compileall result
   - startup-check result
   - desktop build result
   - EXE/ZIP paths
   - GitHub Actions result
   - changed files

## Current task
Replace this section each time with the user's new request:

> [여기에 이번 업그레이드 요청을 그대로 붙여넣기]
