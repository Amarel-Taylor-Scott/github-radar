# Project Radar v3 promotion policy

The v3 evidence layer is additive. Its experimental scores do not replace Project Radar v2 production rankings by default.

A shadow signal or formula may be promoted only after all of the following are documented and reproduced:

1. authoritative source and evidence contracts;
2. offline fixtures and graceful-degradation tests;
3. coverage and missing-data analysis;
4. score-distribution comparison;
5. catalog-local top-25 overlap;
6. relevance, usefulness, quality, novelty, and contamination benchmark results;
7. new-project recall comparison;
8. stale-project, giant-repository, anomalous-star, and missing-evidence sensitivity checks;
9. owner and cross-domain diversity comparison;
10. ablation showing the marginal effect of each new dimension;
11. deterministic implementation and source snapshot checksums;
12. an explicit versioned change to the production ranking contract.

Until those gates pass, the v3 status receipt must continue to report `production_ranking_mutated: false`.
