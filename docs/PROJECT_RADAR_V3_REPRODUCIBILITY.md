# Project Radar v3 reproducibility

A v3 publication is reproducible from the validated v2 dataset, versioned source and alert configurations, versioned profile template, optional cache, optional bounded GH Archive inputs, benchmark corpus, code commit, and generation timestamp.

The output manifest records SHA-256 digests and byte sizes for generated files. The status receipt identifies the source commit and confirms that v2 production rankings were not mutated. SQLite integrity, XML parsing, static API structure, profile pages, graph counts, signal contracts, and manifest hashes are validated before promotion.

Network sources may change between collection times, so exact regeneration requires the same cache or normalized evidence bundle. Offline mode intentionally performs no external enrichment and remains useful for deterministic testing and recovery.
