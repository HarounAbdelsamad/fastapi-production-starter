# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x (current) | ✅ |
| Earlier | ❌ |

Security fixes are backported to the current minor release only.

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report via GitHub Security Advisories:

1. Go to the [Security tab](https://github.com/HarounAbdelsamad/fastapi-production-starter/security/advisories/new)
2. Click **"Report a vulnerability"**
3. Fill in the details (description, reproduction steps, impact, affected versions)

You will receive an acknowledgement within **48 hours**.  We aim to release a patch
within **7 days** for critical issues and **30 days** for moderate/low severity.

We follow coordinated disclosure: please give us time to patch before making the issue
public.

## Scope

The following are in scope:

- Authentication / authorisation bypass
- SQL injection or arbitrary query execution
- JWT signing / verification flaws
- SAML assertion forgery or bypass
- HMAC audit log signature forgery
- Secret / credential leakage from logs or API responses
- SSRF or RCE via webhook or file upload
- Dependency vulnerabilities with public PoC

The following are **out of scope**:

- Vulnerabilities requiring valid admin credentials to exploit (admin-only routes
  are intentionally privileged)
- Rate limiting bypass on endpoints that are explicitly documented as unrestricted
- Theoretical issues with no practical impact
- Issues in development-only code paths (`DEBUG=true`, `/docs` endpoint)

## Security Hardening Checklist (deployment)

Before deploying to production:

- [ ] Rotate `SECRET_KEY` — never use the default
- [ ] Set `APP_ENV=production` — disables `/docs` and `/redoc`
- [ ] Set `TRUSTED_HOSTS` to your domain(s)
- [ ] Configure `CORS_ORIGINS` to your frontend domain(s)
- [ ] Enable `TOKEN_REVOCATION_ENABLED=true` if you need explicit logout
- [ ] Enable `RATE_LIMIT_ENABLED=true` with Redis backend
- [ ] Set `LOG_PII_REDACT=true` in production logs
- [ ] Review `SAML_SP_KEY` rotation if using SAML
- [ ] Ensure `DEBUG=false`

## Dependency scanning

The CI pipeline runs `pip-audit` on every pull request.  Subscribe to
[GitHub Dependabot alerts](https://github.com/HarounAbdelsamad/fastapi-production-starter/security/dependabot)
for this repository to receive automated vulnerability notifications.

## OWASP Top-10 coverage

| Category | Mitigation |
|---|---|
| A01 Broken Access Control | RBAC + `require_role` dependency; route-level auth guards |
| A02 Cryptographic Failures | JWT HS256, HMAC-SHA256 audit signatures, bcrypt passwords |
| A03 Injection | SQLAlchemy ORM (parameterised); Pydantic input validation |
| A04 Insecure Design | ADRs document every security-sensitive decision |
| A05 Security Misconfiguration | `validate_config()` checks at startup; env validation |
| A06 Vulnerable Components | `pip-audit` in CI; Dependabot enabled |
| A07 Auth Failures | Login throttle, token revocation, SAML assertion validation |
| A08 Software Integrity | `uv.lock` pinned deps; GHCR multi-arch signed images |
| A09 Logging Failures | Structured audit log with HMAC integrity; PII redaction filter |
| A10 SSRF | Webhook URLs validated; no proxy-through endpoints |
