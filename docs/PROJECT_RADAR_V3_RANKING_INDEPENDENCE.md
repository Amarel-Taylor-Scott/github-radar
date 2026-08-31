# Project Radar v3 ranking independence

Project Radar v3 reads the validated v2 snapshot and publishes experimental evidence alongside it. It does not rewrite v2 project scores, reorder v2 leaderboards, or backfill missing external evidence with zero.

The v3 shadow report stores production rank, experimental rank, score deltas, top-k overlap, rank correlation, movement, and ablations. This allows maintainers to evaluate whether adoption, release, event, security, or stewardship evidence improves discovery without silently changing the public product.

Any future production promotion requires a separately reviewed, versioned ranking change and the documented benchmark, stability, sensitivity, coverage, and diversity gates.
