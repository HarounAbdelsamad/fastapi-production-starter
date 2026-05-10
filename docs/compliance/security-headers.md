# Security Headers

`SecurityHeadersMiddleware` in `app/core/middleware.py` adds the following headers to every response.

## Headers applied

| Header | Value | Rationale |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing — browsers must honour the declared `Content-Type`. Stops script injection via misidentified content. |
| `X-Frame-Options` | `DENY` | Prevents the app from being embedded in an iframe. Mitigates clickjacking attacks. |
| `X-XSS-Protection` | `1; mode=block` | Legacy browser XSS filter — tells older browsers to block reflected XSS. Modern browsers use CSP instead; this covers older clients. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Sends the full referrer URL on same-origin requests; only the origin on cross-origin requests. Prevents leaking internal paths to third parties. |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Disables hardware APIs the backend API doesn't need. Prevents malicious scripts from accessing camera/mic/location. |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Forces HTTPS for 2 years (63 072 000 seconds) on the domain and all subdomains. **Applied in non-development environments only.** |

## Not included (intentional)

| Header | Why omitted |
|---|---|
| `Content-Security-Policy` | This is a backend-only API. CSP is meaningful for HTML responses; a JSON API has no inline scripts or styles. If you add a docs UI or admin panel, add CSP for those routes only. |
| `Cross-Origin-Opener-Policy` | Relevant for cross-origin pop-ups — not applicable to API-only responses. |
| `Cross-Origin-Resource-Policy` | Set to `same-origin` only if you serve static assets from the same origin. Not applicable for API-only. |

## Customising

The middleware lives in [app/core/middleware.py](../../app/core/middleware.py). Add or modify headers in `SecurityHeadersMiddleware.dispatch`:

```python
response.headers["Cache-Control"] = "no-store"  # prevent caching of API responses
```

## Verifying

```bash
curl -I http://localhost:8000/health/live | grep -i "x-frame\|x-content\|referrer\|strict"
```

Or use [securityheaders.com](https://securityheaders.com) against your deployed URL.
