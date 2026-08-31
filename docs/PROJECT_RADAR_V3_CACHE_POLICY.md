# Project Radar v3 cache policy

Registry, release, security, and event caches reduce upstream load and support deterministic recovery.

Each cached record retains source, stable external identifier, observation time, freshness or expiration, and normalized value. Cache hits are counted in source-health receipts. Expired evidence may be retained for historical comparison but is labeled stale and cannot be represented as current.

Offline mode reads only available normalized cache and local inputs. Missing cache remains missing evidence. Cache files never contain GitHub tokens or other authorization headers and should not include unnecessary upstream response fields.
