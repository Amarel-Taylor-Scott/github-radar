# Project Radar v3 webhook policy

The public v3 publisher generates deterministic webhook payload artifacts but does not transmit them by default.

A separate delivery worker must use destination allowlists, HTTPS, secret isolation, signed requests, idempotency keys, bounded retries, timeout limits, dead-letter handling, and delivery receipts. Payloads identify the v3 source commit, generation timestamp, alert rule, matched repository, evidence class, and public source references.

Webhook delivery failures must not affect public ranking or snapshot publication. Endpoints, secrets, private responses, and subscriber identity are never committed to the public repository.
