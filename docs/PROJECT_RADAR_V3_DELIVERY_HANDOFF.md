# Project Radar v3 delivery handoff

The v3 public alert artifacts are designed to feed external delivery systems without coupling private subscriber data to the public ranking engine.

A delivery worker may consume Atom, JSON Feed, static alert matches, or deterministic webhook payloads. It should implement idempotency, retry limits, destination allowlists, unsubscribe and deletion controls, secret isolation, delivery receipts, and dead-letter handling. It must not expose delivery credentials in the repository or generated public artifacts.

Delivery success, clicks, opens, user identity, and private preferences do not feed back into the public ranking by default. A future personalized service should remain an independent data boundary with explicit consent and retention controls.
