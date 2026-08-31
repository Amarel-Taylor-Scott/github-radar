# Project Radar v3 API contract

The v3 API is a read-only view over a validated static snapshot.

Static routes expose status, projects, catalogs, graph data, profiles, alerts, evidence signals, source receipts, events, and shadow-evaluation summaries. Every response identifies the schema version, generation timestamp, and source commit directly or through its enclosing snapshot metadata.

The included local server uses Python’s standard library, serves only generated files beneath the configured API root, rejects path traversal, rejects POST, PUT, PATCH, and DELETE, and adds CORS, `X-Content-Type-Options: nosniff`, and cache headers.

The static API is suitable for local analysis, demos, mirror sites, and downstream ingestion. It is not an authenticated multi-tenant service, mutation API, subscription database, or guarantee of availability. Consumers should verify the publication manifest before relying on a downloaded snapshot.
