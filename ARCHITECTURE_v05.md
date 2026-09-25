# Architecture v0.5 — Prompt Intelligence Optimizer

## Existing JSON pipeline

1. Analyze Current Prompt from actual music fields.
2. Detect weaknesses without using source version labels as a quality signal.
3. Apply the compatible Channel/Vocal Master.
4. Apply the selected Genre Master.
5. Apply `data/prompt_intelligence_rules.json`.
6. Remove redundancy and positive/exclude conflicts.
7. Generate optimized music fields.
8. Attach per-track Old vs New audit data.
9. Restore and verify immutable content fields.
10. Save the complete Suno-ready JSON.

## Effectiveness gate

`validate_optimization_effectiveness(source, optimized, before_analysis, after_analysis)` compares the allow-listed music fields and checks that every actionable area has at least one related field change. An unresolved `exclude_efficiency` finding is a hard failure; an exclusion list over 16 atoms must be compressed to 16 or fewer. Claimed field changes and resolved weaknesses must match actual diffs and the after-analysis.

The set report calculates changed/unchanged tracks, per-field change counts, before/after weakness totals, resolved weakness count and `optimizationEffective`. New contradictions, duplicate-heavy prompts, wrong vocal role, genre drift, out-of-range BPM, missing Bridge/Final/performance signature and style prompts above the hard maximum fail finalization. A track with zero actionable findings may use `KEEP` only with a content-based `keepReason`.

Higher-order prompt analysis is conservative and content-based. It detects semantically repeated atoms, verifies that structured Bridge change axes are audible in the Bridge style text, compares repeated Finals with track-specific highlight payoffs, and measures set-level template similarity after removing shared singer-identity tokens. Shared recurring-vocal DNA is therefore allowed; only repeated non-singer groove, instrumentation, performance, Bridge and Final controls are actionable.

Local acceptance uses a sanitized 15-track male-story fixture with 37 exclusions per track. A matching private `남_002_CHILI_LAB_JAPAN_EP002_v15.0...json` may exist outside the repository, but acceptance does not ingest it and no private source JSON is included in the repository.

## Immutable boundary

Title, localized title, lyrics, hook, story fields, scene/listener situation, emotion arc, episode boundary and relationship boundary fields are content authority. `merge_existing_upgrade` starts from a deep copy of the source and copies only allow-listed music fields from the proposed result. Therefore unrecognized content and private schema fields are also retained.

## Mutable music boundary

BPM, genre, vocal design, phonation, style/exclude prompts, performance signature, groove, drums, bass, instrumentation, harmony, verse/chorus behavior, Bridge, Final, duration and generation hints may be optimized. Each track must carry `promptOptimization` with the exact old and new style prompts, change reasons, expected improvements and addressed weaknesses.

## Version neutrality

Source fields such as `version`, `revision`, or `generationStandardVersion` may be retained as metadata but are never inputs to prompt-quality scoring. A field may remain unchanged only because its current content has no credible improvement opportunity, never because its label appears current.
