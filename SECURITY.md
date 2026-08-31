# Security policy

## Supported version

Security fixes are applied to the current `main` branch. The project is an evolving data collector and publisher rather than a long-lived binary release line.

## Reporting a vulnerability

Please avoid opening a public issue for an unpatched vulnerability that could expose credentials, modify published data, bypass branch protections, execute untrusted code, or compromise the publication workflow.

Use GitHub private vulnerability reporting from the repository’s **Security** tab when available. If that channel is unavailable, email `amarel.taylor.s@gmail.com` with:

- the affected file, workflow, or endpoint;
- reproduction steps;
- impact and prerequisites;
- a suggested mitigation, when possible;
- whether disclosure is time-sensitive.

Do not include live credentials or personal data in a report.

## Security boundaries

`github-radar` is designed to:

- make read-only HTTP requests;
- treat all discovered repositories and manifests as untrusted data;
- never clone, install, import, build, or execute discovered code;
- read tokens only from the environment;
- avoid writing tokens into logs or generated artifacts;
- isolate source failures;
- validate output before commit;
- publish only from `main`;
- pin third-party GitHub Actions to full commit SHAs.

A repository’s appearance or ranking is not a security endorsement. Community-health and metadata-quality signals do not prove that source code is safe.

## High-priority report classes

Reports are especially useful when they demonstrate:

- token disclosure or credential forwarding to a third party;
- command, template, path, HTML, Markdown, JSON, or XML injection;
- arbitrary file writes outside configured output directories;
- execution of discovered repository content;
- a way for feature branches or pull requests to publish production data;
- publication-manifest bypass or checksum confusion;
- unsafe deserialization;
- a denial-of-service path that can overwrite a healthy feed;
- dependency or GitHub Actions supply-chain compromise.

## Disclosure

Confirmed issues will be acknowledged and assessed as promptly as practical. A fix, test, and advisory will be prepared before public disclosure when the issue presents a material exploitation risk.
