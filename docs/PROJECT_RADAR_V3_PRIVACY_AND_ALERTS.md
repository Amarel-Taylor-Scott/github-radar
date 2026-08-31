# Project Radar v3 privacy and alert policy

The public v3 alert product is static and account-free by default.

## Public alerts

Alert rules operate only on the public Project Radar snapshot and its public evidence. They can match catalogs, topics, languages, score thresholds, repository identifiers, measured momentum, new-project status, review flags, archival state, or security-evidence changes.

The publisher emits:

- machine-readable alert matches;
- an Atom alert feed;
- a JSON Feed alert stream;
- deterministic webhook payload artifacts that an operator may deliver separately.

## Data minimization

The default system does not collect subscriber identities, browsing profiles, email addresses, private repositories, personal health data, location history, or cross-site tracking identifiers. It does not infer sensitive traits about maintainers or users.

## Optional delivery

A future delivery service must remain separate from the public ranking dataset. It should store the minimum subscription information required, provide deletion and unsubscribe controls, avoid behavioral advertising, and never use private subscription data to influence public rankings.

## Maintainer analytics

Owner and maintainer nodes use public repository identity and organization metadata only. The system does not score personal character, political beliefs, health, protected traits, or private intent.
