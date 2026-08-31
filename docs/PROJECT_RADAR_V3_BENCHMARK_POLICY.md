# Project Radar v3 benchmark policy

V3 ranking evaluation uses a versioned, reviewable corpus rather than treating one subjective list as ground truth.

Labels may cover domain relevance, practical usefulness, stewardship quality, descriptive novelty, new-project recall, and false-positive or catalog-contamination risk. Each label records repository, catalog, dimension, rating, rationale, evidence, reviewer status, and affiliation disclosure.

The benchmark runner publishes precision at k, normalized discounted cumulative gain, coverage, catalog-local overlap, rank correlation, score-distribution movement, and ablation results where the corpus supports them. Bootstrap labels are explicitly marked uncalibrated until reviewed.

A new shadow formula cannot replace production weights solely because it changes rankings or improves one metric. Promotion requires deterministic results, adequate label coverage, stability, missing-evidence sensitivity, anomaly sensitivity, diversity checks, and documented trade-offs.
