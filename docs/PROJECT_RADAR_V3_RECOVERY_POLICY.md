# Project Radar v3 recovery policy

A failed v3 build must not damage the last known-good v2 or v3 publication.

The publisher generates into isolated staging directories and promotes only after validation. Recovery first revalidates the prior committed manifest and status receipt. Network evidence can be rebuilt from the same normalized cache; it must not be silently recollected into a different snapshot during a rollback.

When a source fails, the corresponding receipt records the failure or partial coverage and the rest of the evidence layer continues. When final validation fails, the staged bundle is discarded and no production artifacts are committed. Operators should preserve the failure logs, source receipts, source commit, and configuration versions needed to reproduce the incident.
