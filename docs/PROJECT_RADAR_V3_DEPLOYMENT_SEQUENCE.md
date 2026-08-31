# Project Radar v3 deployment sequence

1. Validate the current v2 publication.
2. Run compile, configuration, schema, v3, and complete regression tests.
3. Build v3 offline against the real v2 snapshot.
4. Validate SQLite, XML, profiles, graph, API, sitemap, and checksums.
5. Push one coherent feature implementation.
6. Run feature-branch workflows.
7. Open an integration pull request and run the complete CI matrix.
8. Promote by fast-forward or reviewed merge.
9. Run the main-branch v3 workflow with bounded network enrichment.
10. Commit only the validated generated bundle.
11. Verify the final status, source receipts, project count, source commit, and manifest.
12. Preserve v2 as the last known-good base if any optional v3 stage fails.
