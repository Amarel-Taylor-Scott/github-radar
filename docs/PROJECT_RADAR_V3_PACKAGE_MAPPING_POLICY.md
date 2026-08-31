# Project Radar v3 package mapping policy

Package registry adapters operate only on explicit repository-to-package mappings.

Each mapping records repository, ecosystem, canonical package name, optional registry-specific namespace, and source of the mapping. The system does not assume that `owner/repository`, repository basename, import module, container image, or homepage domain is the published package identity.

Mappings may be proposed through evidence-backed configuration changes and should be verified against authoritative repository or registry metadata. A repository may publish several packages and a package may move between repositories; both cases require explicit versioned mappings.

Unmapped repositories are not assigned zero adoption. They simply lack package-registry coverage until a mapping is verified.
