# Project Radar v3 OpenSSF Scorecard policy

OpenSSF Scorecard evidence is retained as a provider-scoped security signal, not as a complete security verdict.

The collector records the provider, repository identifier, score or check values returned by the documented endpoint, observation time, provider timestamp when available, coverage, confidence, and provenance. A missing result may mean the project is outside provider coverage, temporarily unavailable, renamed, or not yet analyzed. It is not represented as a zero score.

Scorecard data remains separate from popularity, adoption, maintenance, governance, and momentum. It remains shadow-only unless a future production change passes the ranking and coverage gates. Public profiles and alerts must attribute Scorecard findings to the provider and avoid broader unsupported conclusions.
