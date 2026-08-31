## What changed

<!-- Describe the implementation, configuration, documentation, or generated-output change. -->

## Why

<!-- Identify the failure mode, missing capability, or user need. -->

## Evidence and tests

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python -m compileall -q github_radar scripts`
- [ ] Configuration JSON validates
- [ ] Ranking or schema changes include focused tests
- [ ] Documentation reflects user-visible behavior

## Safety and publication review

- [ ] Discovery remains read-only
- [ ] No discovered code is executed
- [ ] Missing evidence is not represented as zero
- [ ] Tokens and secrets are not serialized
- [ ] Feature branches cannot publish production output
- [ ] Rate-limit and failure behavior remain bounded

## Schema / compatibility

<!-- Note publication-schema changes, migrations, or backward-compatibility considerations. -->
