# Architecture v0.6 — Research-Driven Prompt Engine

## Product goal

v0.5 was primarily a prompt analyzer, safe music-field optimizer and validation gate. v0.6 adds a separate research/experiment layer so the application can explore better prompt combinations instead of only repairing the current prompt.

The v0.6 engine does not claim that a text prompt is "best" before listening to audio. It creates controlled A/B/C experiment arms, keeps the generation environment stable, and is designed to learn from later Suno feedback.

## Evidence hierarchy

1. Official Suno documentation
2. User's approved masters and channel hard locks
3. User feedback / accepted renders
4. Community GitHub research and prompt experiments

Community material is stored as an experiment hypothesis, not a platform guarantee.

## Research knowledge files

- `data/research_prompt_knowledge.json`
  - provenance for every external rule
  - official v6 / Variety / Max Mode / Inspire / Style Influence / Custom Model guidance
  - community co-occurrence and iterative-testing hypotheses
- `data/style_compatibility_matrix.json`
  - one dominant genre + at most one secondary tint
  - controlled groove modules, rhythm section, character colors and avoid lists
  - current supported genres: Chill Rap, Soft Old Pop Ballad, Soft Soul, Cafe Pop, French Chanson, Deep House

## A/B/C experiment design

Each track receives three prompt candidates:

### A_CONTROL
Reconstruct the current concept into a high-control prompt. Keep the current compatible secondary tint and recurring singer identity.

### B_GROOVE
Change only the primary groove/secondary-tint direction while keeping singer, story and core harmony stable. This tests whether a compatible rhythmic/color shift improves the render.

### C_CHARACTER
Keep genre/tint/groove stable and strengthen one recognizable track-specific performance habit. This tests vocal individuality without replacing the singer identity.

No candidate is declared the winner before audio feedback.

## Generation recipe

All experiment arms keep model/settings stable by default:

- model: v6
- Variety: 0 for strict style-tag control
- Style Influence: Strong
- Max Mode: recommended for production-length tracks and identity consistency
- Inspire: recommend 3-5 approved user-made songs
- Custom Model: consider after at least 6 approved channel tracks

This keeps the experiment focused on the prompt axis instead of changing both prompt and model settings at the same time.

## Safety / preservation boundary

`apply_research_candidate_variant()` deep-copies the source JSON and changes only:

- stylePrompt
- excludePrompt / negativeStyleText when present
- researchRecipe audit metadata

Title, lyrics, hook, story, scene, relationship boundaries and all other source content remain untouched.

## UI

The existing JSON tab now adds:

- `연구 기반 A/B/C 후보`
- `A 저장`
- `B 저장`
- `C 저장`

The original v0.5 analysis → ChatGPT upgrade → validation workflow remains available. v0.6 research candidates are an additional experimental path, not a replacement for the safe optimizer.

## Feedback linkage

Saved research variants now include a `researchRecipe.feedbackBinding` block with `experiment_arm`, `experiment_axis`, and provenance-aware context. `core.learning.analyze_research_abc_results()` can summarize A_CONTROL / B_GROOVE / C_CHARACTER observations while explicitly refusing to declare or auto-apply a winner.

The next v0.6.1 UI step is to auto-prefill those fields in the existing Feedback screen and show the descriptive three-way comparison in the application. Tiny samples remain observation-only.
