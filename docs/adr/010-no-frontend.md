# ADR-010: Why We Do Not Include a Frontend

## Status
Accepted

## Context

Many full-stack starter templates include a frontend: tiangolo's full-stack-fastapi-template ships React + Vite, create-t3-app ships Next.js + tRPC, and various others bundle Vue or SvelteKit. The question is whether this template should do the same.

The target audience is enterprise backend engineers and platform teams. They are explicitly not building a solo indie app where a bundled frontend is a convenience. They are building a backend service that will be consumed by:

- An existing frontend team with their own tech stack, component library, and design system
- A mobile app (iOS/Android)
- Other backend services (service-to-service)
- A third-party integration

## Decision

**This template is backend-only. No frontend is included. No frontend dependency is implied. The OpenAPI specification is the public contract.**

## Reasoning

### Enterprise Teams Have Their Own Frontend Stack

A company that has been running React for five years will not switch to the bundled template's React scaffold. They have:
- An internal component library (Figma + Storybook)
- An existing state management approach (Redux, Zustand, Jotai)
- An internal routing convention
- Specific build tooling (Vite, Webpack, Turbopack)
- A design system with brand tokens

Providing a frontend scaffold in a backend template does not help these teams — it creates noise they must delete. Deleting a frontend scaffold is a bad first impression.

### Frontend Choices Are High-Churn

The JavaScript ecosystem moves fast. A bundled React + Vite setup that is current today is outdated in 18 months. Maintaining a frontend scaffold alongside a backend foundation is a substantial ongoing burden with no upside for the target audience.

Compare: the backend architecture choices in this template (FastAPI, SQLAlchemy, OpenTelemetry) are stable for 5+ years. Frontend framework recommendations cycle much faster.

### The Backend-Only Position Is a Signal

Choosing to be backend-only is not a limitation — it is a design decision. It signals:

- This template has a focused opinion about what it is
- The maintainer is not trying to be everything to everyone
- Enterprise engineers will not find frontend concerns polluting the backend code

A template that says "no" clearly is more credible than one that says "yes" to everything. The tiangolo template is excellent at being a full-stack starter. This template is explicitly not competing on that axis.

### OpenAPI as the Contract

With frontend excluded, the API contract becomes the integration point. Every endpoint is documented via FastAPI's auto-generated OpenAPI spec. Frontend teams:

1. Reference the OpenAPI spec (or the generated docs at `/docs`)
2. Generate typed clients with `openapi-typescript`, `openapi-generator`, or similar
3. Are not constrained by this template's frontend choices

This is the correct enterprise model: backend teams own the API contract; frontend teams own the client.

### What This Means for the Demo / Reference Implementation

The reference implementation (Phase 7) will be a backend-only service with a documented API. If a demo UI is needed for presentations, it can be a minimal HTML page that hits the API directly — not a full frontend application. This keeps the demo honest about what the template provides.

## Explicit Non-Goals

The following are **explicitly out of scope** for this template:

- React, Vue, Svelte, Angular, or any other JavaScript framework
- Server-side rendering
- Static site generation
- Frontend build pipelines (Vite, Webpack, Parcel)
- CSS frameworks or component libraries
- Browser-facing session management (cookies are supported for auth; the session UI is not)
- Email templates (the pattern for sending email is documented; the template HTML is not provided)

These belong in the roadmap if the audience signals demand, or in a separate companion template.

## Consequences

**Positive:**
- Narrower scope means faster time to a high-quality v0.1.0.
- Backend engineers are not distracted by frontend decisions.
- Template stays current longer — backend choices are more stable than frontend choices.
- Clear positioning vs tiangolo's template (which is a full-stack choice).

**Negative:**
- Teams that want a full-stack starter will choose tiangolo's template instead. This is acceptable — they are not the target audience.
- Demo and showcase material requires more explanation ("here is the API, here is how to call it from a client") compared to a template with a bundled UI. The reference implementation and API docs compensate for this.

## References

- [tiangolo/full-stack-fastapi-template](https://github.com/tiangolo/full-stack-fastapi-template) — the full-stack alternative
- [ADR-012: Versioning & API Compatibility Policy](012-versioning-compatibility.md) — how the API contract is managed
