# Contributing to github-radar

Thank you for improving GitHub discovery. Contributions are welcome across collectors, catalogs, tests, documentation, ranking methodology, and publication tooling.

## Ground rules

- Keep discovery read-only. Never install or execute a discovered repository, extension, hook, plugin, or MCP server.
- Preserve raw evidence. A new blended score must not hide or overwrite its component signals.
- Distinguish observed facts from estimates and inferences.
- Keep popularity, momentum, quality, relevance, confidence, and security separate.
- Do not add paid placement or undisclosed affiliation bonuses.
- Respect GitHub rate limits and bounded-search budgets.
- Avoid adding runtime dependencies unless the capability cannot reasonably be implemented with the standard library.

## Nominate a project

Use the **Nominate a GitHub project** issue form. Include the canonical `owner/repository`, best-fit catalog, practical use cases, and any relevant evidence. Disclose affiliations.

A nomination is a discovery lead. It does not guarantee inclusion or improve a score.

## Add or improve a catalog

Catalogs live in `project_radars.json`. A good catalog has:

- a specific technical scope;
- at least one productive GitHub topic or bounded query;
- keywords and negative terms that improve relevance;
- realistic minimum counts;
- explicit project-type exclusions;
- enough distinction from existing catalogs to justify a separate product.

Before opening a pull request:

```bash
python -m json.tool project_radars.json >/dev/null
python -m unittest discover -s tests -v
python -m compileall -q github_radar scripts
```

For live validation on a branch named `feature/**`, the Project Radar workflow runs collection and bundle validation but cannot publish over production.

## Change ranking logic

Ranking changes require:

1. a clear statement of the failure mode being corrected;
2. raw inputs and component dimensions remaining visible;
3. deterministic behavior;
4. tests showing the intended ranking change;
5. no representation of missing evidence as zero;
6. documentation updates in `docs/PROJECT_RADARS.md` or `docs/AGENT_EXTENSION_RADAR.md`.

Avoid tuning against a handful of favorite repositories. Prefer invariants, synthetic fixtures, catalog-level audits, and measured history.

## Add a source adapter

A source adapter should provide:

- bounded pagination;
- caching where appropriate;
- request pacing and retry behavior;
- provenance and source-health receipts;
- schema fixtures and offline tests;
- failure isolation;
- no credential serialization;
- no execution of discovered code.

Third-party sources must be clearly labeled. Do not silently fabricate unavailable metrics.

## Pull requests

Keep changes focused and explain:

- what changed;
- why the current behavior was insufficient;
- how the change was tested;
- expected publication or schema effects;
- backward-compatibility considerations;
- any new rate-limit or security implications.

Generated feeds should normally be produced by the workflow rather than hand-edited in a pull request.
