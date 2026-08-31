# Project Radar v3 acceptance gates

A v3 feature is not production-ready merely because it adds more data. It must improve usefulness without weakening provenance, comparability, failure isolation, or safety.

## Source adapter gates

Every new external source must provide:

- a named authoritative upstream;
- documented endpoint and data license or usage terms;
- bounded pagination and request budget;
- caching strategy;
- retry and backoff behavior;
- source-health receipt;
- explicit freshness timestamp;
- stable external identifier where available;
- offline fixture and schema-change test;
- graceful degradation when unavailable;
- no execution of discovered project code.

## Signal gates

Every new signal must declare:

- evidence class: observed, measured, provisional, inferred, or generated interpretation;
- unit and time window;
- entity level: repository, package, release, organization, component, or catalog;
- missing-data behavior;
- confidence or coverage metric;
- normalization strategy;
- anti-gaming considerations;
- whether it may affect ranking by default.

Signals must remain visible in raw form even when blended into a score.

## Ranking gates

A production ranking change requires:

- deterministic implementation;
- offline regression coverage;
- shadow output against the current production formula;
- score-distribution comparison;
- catalog-local top-25 overlap;
- new-project recall comparison;
- stale-project and giant-repository sensitivity checks;
- missing-evidence sensitivity checks;
- owner and cross-domain diversity comparison;
- documented expected behavior before sufficient history exists.

## Editorial-profile gates

Generated project descriptions or use-case analysis must:

- cite factual sources;
- distinguish quoted facts from model interpretation;
- identify generation time and model/provider configuration;
- avoid claims of security, legality, financial value, or maintainer intent without evidence;
- never overwrite repository metadata;
- be removable without changing measured rankings;
- support deterministic regeneration from a versioned prompt and source bundle.

## Publication gates

Every new format or mirror must agree on:

- source commit;
- generation timestamp;
- schema version;
- project and catalog counts;
- stable IDs;
- checksums;
- history mode;
- source-health status.

Publication remains blocked on malformed JSON/XML, duplicate IDs, unexpected count collapse, missing required files, or checksum failure.

## Privacy and safety gates

- No private user data is collected for public rankings.
- No repository code is executed during discovery or enrichment.
- Maintainer-level analytics use only public professional activity and avoid sensitive-person inference.
- Security findings retain provider, scope, timestamp, and methodology.
- Review flags remain quality-control prompts rather than allegations.
- Paid placement, sponsorship, nomination, or affiliation cannot create an automatic ranking advantage.

## Operational gates

- Runtime and API use fit documented daily budgets.
- Historical storage growth is measured before enabling the feature.
- The feature can be disabled independently without breaking base publication.
- Recovery from partial publication is documented and tested.
- The last known-good publication remains available during upstream failure.
