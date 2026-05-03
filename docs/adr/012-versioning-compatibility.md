# ADR-012: Versioning and API Compatibility Policy

## Status
Accepted

## Context

This template serves two distinct versioning concerns:

1. **Template versioning**: When the template itself changes (new features, bug fixes, breaking changes to patterns), how are versions communicated to teams that have adopted it?
2. **API versioning**: For services built from this template, how is the API version communicated to consumers?

Both require explicit policies. Enterprise teams evaluate templates partly on whether the maintainer has thought through these questions — "will adopting this template lock us into a pattern we can't evolve from?"

## Decision

**Template versioning: Semantic versioning (SemVer) with a 12-month deprecation window for breaking changes. API versioning: URL path versioning (`/api/v1/`, `/api/v2/`) as the default, with guidance for teams that prefer header versioning.**

## Template Versioning

### Semantic Versioning

```
MAJOR.MINOR.PATCH

0.1.0 — first stable release (MVD complete, all Phase 1-6 deliverables done)
0.1.x — bug fixes, documentation corrections, dependency updates
0.2.0 — new backward-compatible features (e.g., SCIM support)
1.0.0 — first release with a long-term support commitment
```

### What Constitutes a Breaking Change in a Template

A template is different from a library. There is no runtime import; teams clone or fork the template and own the code thereafter. However, "breaking changes" still exist:

- **Structural changes**: Renaming directories (`core/` → `foundation/`) that break a team's extensions
- **Interface changes**: Changing a protocol's method signatures that teams implement
- **Migration pattern changes**: Altering how Alembic migrations are structured in a way that breaks existing migration histories
- **Configuration key renames**: Renaming `CACHE_ENABLED` to `REDIS_CACHE_ENABLED` without providing a migration path

### What Does NOT Require a Major Version

- Adding new optional features
- Adding new ADRs
- Updating dependencies within a major version
- Adding new env-time toggles (additive)
- Updating the reference implementation

### Deprecation Policy

Before any breaking change in a `0.x` release:
1. The change is announced in a GitHub issue tagged `breaking-change` with at least 30 days notice.
2. The change is described in `CHANGELOG.md` with a migration guide.
3. For `1.x` and above: 12-month deprecation window with the old pattern still working but emitting warnings.

### Communication Channels

Breaking changes are communicated via:
- GitHub release notes (required)
- `CHANGELOG.md` entry with migration steps (required)
- GitHub Discussions announcement (for `0.x` series)
- Blog post (for `1.0.0` and any major version)

## API Versioning

For services built from this template, URL path versioning is the default:

```
/api/v1/users
/api/v1/auth/login
/api/v2/users  ← new version, when needed
```

### Why URL Path Versioning

**Discoverability**: The version is visible in every URL. Browser tools, logs, API documentation, and copy-paste examples all show the version without additional configuration.

**Caching**: Reverse proxies, CDNs, and load balancers can route by URL prefix without custom configuration.

**Client simplicity**: Clients don't need to set headers or query parameters. The URL is self-describing.

**Alternatives considered:**

| Approach | Pros | Cons |
|---|---|---|
| URL path (`/api/v1/`) | Discoverable, cache-friendly | Version is "in the resource path" (REST purist objection) |
| Header (`Accept: application/vnd.api.v1+json`) | REST-pure | Invisible in logs, requires client SDK to set correctly, poor browser support |
| Query parameter (`?version=1`) | Easy to test in browser | Pollutes query space, less conventional |
| Subdomain (`v1.api.example.com`) | Clean separation | DNS management overhead, CORS complexity |

The REST purist objection to URL versioning (the URL should identify a resource, not a version of the API) is noted but deprioritized. Pragmatic discoverability and caching behavior outweigh the philosophical concern for this audience.

### Versioning Scope

Each major version (`v1`, `v2`) covers the entire API. **We do not version individual endpoints** (no `/api/users/v2`). Per-endpoint versioning leads to combinatorial complexity and is difficult to document coherently.

### v1 Stability Commitment

`/api/v1/` is considered stable from `v0.1.0`. Breaking changes to the v1 interface require:
1. Introducing the change in `/api/v2/`
2. Announcing v1 deprecation with a migration guide
3. Maintaining v1 for at least 12 months (6 months for `0.x` releases)

### When to Introduce v2

Introduce `/api/v2/` when:
- A resource's schema changes in a backward-incompatible way (field rename, type change, field removal)
- An endpoint's behavior changes semantically (not just a bug fix)
- The auth model changes in a way that affects existing clients

Do not introduce v2 for:
- Adding new optional fields (backward-compatible addition)
- Adding new endpoints
- Bug fixes that bring behavior in line with documented behavior

### Content Negotiation

If a team prefers content-type header versioning, the template can be adapted. The router structure is contained in `app/routers/`, making it straightforward to add header-based routing alongside URL versioning. This is not the default but is documented.

## OpenAPI Specification

The OpenAPI spec at `/openapi.json` covers all versions. The spec uses `info.version` for the template version, not the API version. API version appears in path prefixes. Both are included in the spec.

## Consequences

**Positive:**
- Clear, predictable version cadence. Enterprise teams can plan upgrades.
- URL versioning requires no custom client configuration.
- 12-month deprecation window gives adopting teams time to migrate.
- Documented breaking change process builds trust with evaluators.

**Negative:**
- URL versioning with `/api/v1/` means routing configuration (load balancers, API gateways) must be updated when introducing v2. This is operational overhead compared to header versioning. Documented.
- SemVer for a template is less mechanically enforceable than for a library (there's no runtime import to catch). The policy is enforced by human review and convention.
- Maintaining two API versions simultaneously (v1 + v2) during deprecation periods adds maintenance burden. This is the cost of the stability commitment.
