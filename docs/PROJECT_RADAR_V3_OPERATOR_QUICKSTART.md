# Project Radar v3 operator quickstart

Run the additive layer from a validated v2 publication:

```bash
python scripts/project_radar_v3.py \
  --feed-dir feeds/projects \
  --site-dir docs/projects \
  --sources-config project_v3_sources.json \
  --alerts-config project_v3_alerts.json \
  --benchmark benchmarks/project-radar-v3/corpus.json
```

Run deterministically without network enrichment:

```bash
python scripts/project_radar_v3.py --offline
```

Validate an existing bundle:

```bash
python scripts/project_radar_v3.py --offline --validate-only
```

Serve the generated read-only static API locally:

```bash
python scripts/serve_project_radar_api.py --root docs/projects/v3/api
```

Before publication, run the complete offline suite and compile checks. Production promotion remains blocked unless status, XML, SQLite, static API, profile, graph, and SHA-256 manifest checks pass.
