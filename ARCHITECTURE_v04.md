# Architecture v0.4 — Closed-loop Prompt Learning

## Pipeline

1. **Market Recipe**: public/current market hypothesis.
2. **Reference DNA**: abstract structure/production traits only.
3. **Legacy Directive Parser**: extracts trusted content and Track Plan.
4. **Story Lock Layer**: story/scene/title/hook default locked.
5. **Current Master Parser**: reads voice fingerprint and BPM ranges.
6. **Music Recompute Layer**: updates BPM/genre/vocal/role/structure/performance signature.
7. **Feedback Evidence Layer (NEW)**: stores real Suno generation outcomes in SQLite.
8. **Recipe Re-ranker (NEW)**: after >=3 samples for a recipe, blends local feedback with market prior.
9. **Feedback Prompt Guidance (NEW)**: after threshold, injects compact local evidence into the compiler.
10. **QA/Export**.

## Feedback is intentionally conservative
Local feedback should not rewrite story data or automatically mutate masters. It provides a soft prior. The user can still select another recipe or override a track manually.

### Ranking
Before 3 samples: `adjustedScore = market prior`.
After 3 samples: local feedback starts at 20% weight and grows gradually, capped at 55% around a dozen evaluated tracks.

### Track score
Weighted from overall, vocal identity, hook, groove and prompt adherence, with KEEP bonus and REGEN penalty. The exact weights are code-level policy and should be changed only with a documented reason.

## Storage
`user_data/feedback.sqlite3` is local and gitignored. Portable JSON/CSV exports can be created from the UI.
