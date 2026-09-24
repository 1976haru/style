# v0.5 Development Plan — Evidence-guided A/B Learning

## Goal
Turn local Suno feedback into conservative, auditable experiment suggestions without allowing feedback to rewrite creative locks or fixed channel voice identity.

## Safety rails
- Story / Scene / Title / Hook remain immutable.
- Fixed channel vocal fingerprint is never replaced automatically.
- No auto master rewrite in v0.5.
- Fewer than 30 evaluated tracks: observations only, no empirical A/B activation.
- A/B suggestions modify only metadata/proposals until the user explicitly applies them.
- Every proposed experiment must be attributable to local evidence.

## Phase 1 — Learning core
- Analyze KEEP/MAYBE/REGEN records.
- Rank BPM windows, genre families, music roles and repeated performance-signature atoms.
- Track recurring failure tags.
- Confidence stages: insufficient <30, early 30–59, medium 60–119, high >=120.

## Phase 2 — 15-track A/B planner
- Stable deterministic track selection.
- Baseline A vs exploration B.
- One main axis per B track: BPM / performance signature / genre / structure.
- Proposal only; do not mutate current recomputed Track Plan.
- Clamp any later BPM application to current master role range.

## Phase 3 — UI/reporting
- Show evidence N, confidence, KEEP rate and top failure tags.
- Display A/B arm and axis next to each Track Plan row.
- Export experiment manifest with the generated package.

## Phase 4 — Closed-loop evaluation
- Store experiment arm/axis in feedback metadata in a backward-compatible way.
- Compare A vs B only after enough observations per arm.
- Never call a single winning generation a proven recipe.

## Promotion gate to v0.5 Stable
- Existing v0.4.2 tests remain green.
- New learning tests pass on Windows 3.11/3.12 and Ubuntu 3.11/3.12.
- Lock-preservation regression stays zero.
- No feedback DB schema migration unless explicitly reviewed.
