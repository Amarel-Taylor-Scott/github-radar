# Contributing to Project Radar v3

Contributions may add source adapters, mappings, evidence contracts, profiles, graph relationships, exports, API routes, alerts, benchmarks, tests, documentation, or operator tooling.

Every network source needs an authoritative upstream, terms review, bounded budget, cache policy, receipt, stable identifier, freshness, missing-data behavior, offline fixture, graceful-degradation test, and confirmation that discovered code is never executed. New evidence remains shadow-only unless separately promoted.

Ranking changes require benchmark and ablation evidence. Profile changes must preserve the observed-fact and generated-interpretation boundary. Graph changes must not imply unsupported personal or corporate relationships. Alert changes must remain deterministic and privacy-preserving.

Run compile checks, the v3 suite, the complete regression suite, and an end-to-end offline build before opening a pull request.
