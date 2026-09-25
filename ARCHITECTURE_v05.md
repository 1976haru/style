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

## Immutable boundary

Title, localized title, lyrics, hook, story fields, scene/listener situation, emotion arc, episode boundary and relationship boundary fields are content authority. `merge_existing_upgrade` starts from a deep copy of the source and copies only allow-listed music fields from the proposed result. Therefore unrecognized content and private schema fields are also retained.

## Mutable music boundary

BPM, genre, vocal design, phonation, style/exclude prompts, performance signature, groove, drums, bass, instrumentation, harmony, verse/chorus behavior, Bridge, Final, duration and generation hints may be optimized. Each track must carry `promptOptimization` with the exact old and new style prompts, change reasons, expected improvements and addressed weaknesses.

## Version neutrality

Source fields such as `version`, `revision`, or `generationStandardVersion` may be retained as metadata but are never inputs to prompt-quality scoring. A field may remain unchanged only because its current content has no credible improvement opportunity, never because its label appears current.
