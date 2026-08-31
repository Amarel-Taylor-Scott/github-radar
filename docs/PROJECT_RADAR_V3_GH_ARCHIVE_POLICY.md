# Project Radar v3 GH Archive policy

The optional GH Archive importer processes only locally supplied public event files and is disabled by default.

The importer accepts bounded `.jsonl` or `.jsonl.gz` inputs, limits files and events, and extracts only configured public event types relevant to repository momentum or maintenance. Raw archives are not committed. Counts retain the event type, repository, time window, observation source, and coverage limitations.

GH Archive evidence is reconciled with current GitHub repository metadata and remains shadow-only. Missing event files or partial archive coverage are not converted into zero activity. The daily v2 and v3 base publications do not depend on GH Archive availability.
