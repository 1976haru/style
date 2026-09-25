# AGENTS.md — Suno Master Prompt Studio

## Goal
Maintain a conservative, testable Suno production system that combines locked story content, channel/genre masters, curated public prompting knowledge, controlled A/B/C prompt experiments, and real user feedback.

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
1. Read README.md and ARCHITECTURE_v04.md before changing architecture.
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

## v0.6 research rules
- Preserve source provenance for every external research rule.
- Official Suno documentation outranks community observations.
- Do not copy lyrics, titles, melodies, or expressive prompt prose from public examples; extract only abstract production behavior.
- Research candidates are experiments, not quality claims. Do not label a winner before audio feedback.
- Keep A/B/C model/settings stable when the goal is to test a prompt axis.
- Candidate application must deep-copy source data and mutate only allowed music fields plus audit metadata.
- Curated research data must remain usable offline.
