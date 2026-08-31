# Project Radar v3 deprecation policy

Adapters, fields, routes, and artifact formats may be deprecated when an upstream endpoint disappears, terms change, evidence semantics become misleading, or a replacement contract is available.

Deprecation should be announced in the changelog and status metadata, preserve historical readability, and provide a migration path where feasible. A deprecated source is disabled independently; its absence must not be converted into a negative project score. Removed experimental shadow signals do not alter the v2 production ranking.

Breaking schema changes require a new schema version and updated validation fixtures. Permanent profile URLs should redirect or retain tombstone metadata when a repository is renamed or transferred rather than silently becoming unrelated content.
