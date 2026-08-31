# Project Radar v3 data retention

The committed repository stores current normalized v3 evidence and compact reproducibility artifacts. It does not retain unlimited raw provider responses or raw GH Archive event streams.

Current snapshots, manifests, source receipts, benchmark metadata, identity links, and selected historical summaries may remain in Git history. Large longitudinal observations should move to partitioned releases or object storage with documented checksums and retention periods before repository size becomes operationally harmful.

Private subscriber or delivery data is outside the default public repository and must have its own consent, deletion, access, and retention controls if a separate service is deployed.
