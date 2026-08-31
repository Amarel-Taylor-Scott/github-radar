# Project Radar v3 security boundaries

Project Radar v3 collects metadata and external evidence. It is not a malware scanner, penetration-testing system, or guarantee that a ranked project is safe.

## Collector boundary

The collector never clones, imports, installs, builds, executes, or dynamically loads code from discovered repositories. Package registries are queried only through documented metadata endpoints. Explicit package mappings are required; repository names are not guessed as package names.

## Credential boundary

GitHub credentials may be attached only to requests sent to GitHub API hosts. Registry adapters receive no GitHub authorization header. Generated artifacts never contain access tokens.

## Security evidence

OpenSSF Scorecard and future advisory, signature, SBOM, provenance, or attestation signals retain provider, scope, timestamp, stable identifier, coverage, confidence, and evidence class. Missing security evidence is unknown—not a failing score.

## Ranking boundary

V3 external security and adoption signals remain shadow-only by default. They do not modify the v2 production ranking until benchmark, ablation, stability, sensitivity, and coverage gates have passed.

## Alert boundary

Security-related alerts describe a change in published evidence, such as an archival event or changed provider result. They must not be phrased as accusations of malicious intent or definitive findings outside the provider’s documented scope.
