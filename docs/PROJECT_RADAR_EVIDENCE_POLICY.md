# Project Radar evidence and correction policy

Project Radar is a discovery and monitoring system, not a certification service. Its output combines public repository facts, measured history, deterministic transformations, provisional estimates, and explicit review prompts.

## Evidence classes

Every published field should fit one of four classes:

1. **Observed fact** — returned by GitHub or another named authoritative source at a recorded time.
2. **Measured history** — calculated from two or more stored observations of the same repository.
3. **Provisional estimate** — derived from currently available facts when a measurement window is not yet available.
4. **Deterministic interpretation** — a documented score, classification, or rule-derived label based on published inputs.

Future model-generated summaries or use-case analysis must be labeled as **generated interpretation** and kept separate from these four evidence classes.

## Momentum language

- `observed-7d` means a historical baseline at or before the seven-day target was available.
- `observed-short-window` means a prior observation exists but a full seven-day history is not yet available.
- `lifetime-estimate` means total stars divided by repository age; it is not a recent-growth measurement.
- `measurement_confidence` controls how strongly velocity, acceleration, and relative growth affect rankings.
- Missing deltas are `null`, not zero.

## Community-health language

Community-health fields come from GitHub's official repository community-profile endpoint. A profile that was not sampled is unknown. Absence of an observed file is not reported as absence unless the official profile was queried.

Community health does not certify code security, maintainer integrity, legal compliance, project quality, or future support.

## Review flags

Review flags are quality-control prompts. They identify records where evidence, classification, or ranking deserves human checking. They do not allege fraud, manipulation, malicious behavior, insecurity, or poor intent.

Examples include:

- high provisional lifetime velocity;
- low measurement confidence with a high momentum score;
- missing license declaration;
- incomplete metadata;
- weak catalog relevance;
- broad catalog overlap;
- unusual star/fork ratios.

A reviewer should inspect the authoritative repository and supporting evidence before proposing a correction.

## Corrections

Corrections should be narrow, evidence-backed, and reproducible. Valid correction requests include:

- repository transfer or rename;
- incorrect source metadata;
- duplicate identity;
- wrong catalog assignment;
- classification error;
- broken source link;
- stale or malformed history;
- false-positive review flag caused by incorrect inputs.

Ranking disagreement alone is not a factual correction. Ranking methodology changes belong in a proposal with examples, expected effects, and benchmark evidence.

## Conflicts and affiliations

Nominators and correction reporters must disclose affiliations with a repository or organization. Affiliation does not invalidate evidence, but undisclosed promotion undermines trust.

No paid, sponsored, nominated, affiliated, or manually submitted repository receives an automatic ranking advantage.

## Source disputes

When authoritative sources disagree, Project Radar should:

1. retain the raw source values and timestamps;
2. prefer the current official repository or registry for current-state facts;
3. preserve historical observations rather than rewriting the past;
4. document the conflict in provenance or a review note;
5. avoid confident interpretation until the conflict is resolved.

## Security boundary

Project Radar does not clone, install, import, build, execute, or dynamically scan discovered code. A repository's inclusion is not a security endorsement. Future external security verdicts must retain their provider, version, timestamp, scope, and methodology.
