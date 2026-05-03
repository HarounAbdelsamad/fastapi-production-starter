# ADR-006: SAML Library Choice

## Status
Accepted

## Context

SAML 2.0 is the dominant enterprise SSO protocol. It is required for integration with corporate identity providers (Okta, Azure AD, OneLogin, Ping Identity, ADFS). Most FastAPI templates duck SAML because the implementation is complex — this template specifically does not.

Implementing SAML from scratch is inadvisable. SAML's XML signature verification, replay attack prevention, and IdP metadata parsing have subtle security requirements. A custom implementation is almost certain to have vulnerabilities.

The candidate Python SAML libraries are:

1. **python3-saml** (OneLogin's library, also known as `python3-saml`)
2. **pysaml2** — a comprehensive SAML 2.0 implementation
3. **djangosaml2** — Django-specific wrapper around pysaml2
4. **social-auth-core** — social auth abstraction that includes SAML

## Decision

**Use `python3-saml` (the OneLogin library).**

## Reasoning

### python3-saml

`python3-saml` is the SAML library maintained by OneLogin, a major enterprise SSO provider. It is:

- **Actively maintained** by engineers who use it in production at enterprise scale (OneLogin itself)
- **Battle-tested**: runs in production at thousands of enterprise companies via OneLogin's integration catalog
- **Well-documented**: official documentation covers SP-initiated and IdP-initiated flows, attribute mapping, signature verification
- **Focused scope**: does one thing (SAML 2.0 SP implementation) and does it well. No framework coupling.
- **Security track record**: CVEs are addressed promptly. The library's security model is reviewed by enterprise security teams as part of OneLogin's compliance process.

The main dependency is `xmlsec1` (a C library for XML signature verification). This is a system package that must be installed separately. The documentation covers setup for common environments (Debian/Ubuntu, macOS, Docker).

### pysaml2

`pysaml2` is a more comprehensive SAML implementation that can act as both SP and IdP. For a backend that is only ever a Service Provider (SP), this is unnecessary scope. Additional concerns:

- **Complexity**: pysaml2 has a steeper configuration curve. The configuration format is Python dicts with many options, making mistakes easy and debugging hard.
- **Framework coupling**: pysaml2's integration patterns are better documented for Django. FastAPI integration requires more glue code.
- **LDAP coupling in docs**: Much of pysaml2's documentation and examples assume LDAP attribute mapping, which is not relevant here.

pysaml2 is the right choice if you need to act as a SAML IdP (not the case here) or if pysaml2's attribute processing covers a specific edge case that python3-saml doesn't handle.

### djangosaml2

A wrapper around pysaml2 for Django. Not applicable — this template uses FastAPI.

### social-auth-core

`social-auth-core` provides a unified abstraction over OAuth, OIDC, and SAML. For a template that needs SAML specifically and deeply (not just "SAML as one of many SSO options"), the abstraction layer adds indirection without benefit. Debugging SAML-specific issues through an abstraction layer is harder. Ruled out.

## Implementation Notes

### SP-Initiated Flow

1. User accesses a protected resource
2. App redirects to `/saml/login?idp=<idp-slug>`
3. App generates SAML `AuthnRequest`, redirects to IdP's SSO URL
4. IdP authenticates user, POSTs SAML `Response` to `/saml/acs`
5. App verifies signature, extracts attributes, issues JWT
6. User is redirected to original resource with JWT cookie/header

### IdP-Initiated Flow

1. User authenticates directly at the IdP portal
2. IdP POSTs SAML `Response` to the app's ACS URL directly
3. App verifies, extracts attributes, issues JWT
4. User is redirected to the default post-login page

### Keycloak Demo IdP

The docker-compose stack includes Keycloak as a demo IdP. This allows developers to test the full SAML flow locally without an enterprise IdP. The Keycloak realm configuration is committed to the repo.

### IdP Metadata Management

IdP metadata (containing the signing certificate and SSO URL) is loaded from a URL or a local XML file, configurable per IdP. The template supports multiple IdPs (useful for multi-tenant apps where each tenant has their own IdP).

## Consequences

**Positive:**
- SAML implementation is handled by a library with a strong security track record.
- SP-initiated and IdP-initiated flows are both supported.
- Multi-IdP support (one per tenant) is achievable with the library's configuration model.
- Local testing with Keycloak means developers don't need access to an enterprise IdP.

**Negative:**
- `xmlsec1` is a C library that must be installed as a system package. Not pure Python. The Docker image handles this; local development without Docker requires the package installed on the host.
- `python3-saml` does not support `asyncio` natively (XML parsing and signature verification are synchronous). We run SAML processing in a thread pool executor to avoid blocking the event loop: `await asyncio.to_thread(process_saml_response, ...)`. This is a known pattern and is documented.
- SAML attribute mapping varies significantly between IdPs. The template provides a mapper interface but enterprise teams will need to customize it for their specific IdP attribute names. Documented with examples for Okta, Azure AD, and Keycloak.

## References

- [python3-saml on PyPI](https://pypi.org/project/python3-saml/)
- [python3-saml documentation](https://github.com/SAML-Toolkits/python3-saml)
- [SAML 2.0 specification](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf)
- [Keycloak SAML documentation](https://www.keycloak.org/docs/latest/server_admin/#saml-clients)
