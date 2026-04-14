# TODO - `app/internal/`

Internal/admin-only endpoints and platform operations belong here.

## Usage
- Add endpoints that are not public product APIs (admin, maintenance, diagnostics).
- Protect routes with strict role checks (`require_role("admin")` or stronger).

## Rule
- Never expose internal routes without authentication/authorization.
