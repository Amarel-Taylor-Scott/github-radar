# Project Radar v3 release evidence policy

Release evidence is collected from authoritative GitHub release metadata for a bounded, catalog-balanced subset of repositories.

Signals may include latest release identifier, publication time, prerelease or draft state, release cadence, asset count, and aggregate asset-download counts when GitHub reports them. The evidence retains repository, release identifier, observation time, freshness, provider, unit, window, confidence, coverage, and provenance.

Projects that publish through registries, rolling branches, external download sites, or non-GitHub forges may have incomplete GitHub release evidence. Missing releases therefore remain unknown rather than becoming a negative score. Release evidence is additive and shadow-only by default.
