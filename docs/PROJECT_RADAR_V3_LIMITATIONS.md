# Project Radar v3 limitations

Project Radar v3 is intentionally explicit about what its evidence does not establish.

- Package mappings cover configured packages, not every package a repository may publish.
- Registry download statistics can reflect mirrors, CI, bots, bundled dependencies, and ecosystem-specific counting rules; values are not directly comparable across registries.
- GitHub release evidence does not capture projects that release elsewhere or use rolling delivery.
- OpenSSF Scorecard is provider-scoped evidence and not a complete security assessment.
- GH Archive import is optional and depends on locally supplied public event files; it is not required for the daily base publication.
- Deterministic profiles summarize public source bundles and include clearly separated interpretation. They are not maintainer-approved descriptions.
- Graph edges reflect discovered and configured evidence, not proof of corporate ownership, employment, endorsement, or financial relationships.
- Shadow scores are experimental and cannot replace production weights without passing the versioned benchmark and ranking gates.
- Static alert files provide public matching results; account-based delivery, private subscriptions, and notification administration are outside the default repository.
- Parquet output requires the optional `pyarrow` dependency. When unavailable, the publisher emits an explicit capability receipt rather than a mislabeled file.
- Standalone mirror repository creation and GitHub Pages administration require GitHub capabilities not exposed by the connected integration.
