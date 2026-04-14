# OAuth Setup (Google/GitHub)

OAuth routes are enabled when client credentials are configured in `.env`:

- `OAUTH_GOOGLE_CLIENT_ID`
- `OAUTH_GOOGLE_CLIENT_SECRET`
- `OAUTH_GITHUB_CLIENT_ID`
- `OAUTH_GITHUB_CLIENT_SECRET`

## Endpoints

- `GET /api/v1/auth/google/login`
- `GET /api/v1/auth/google/callback`
- `GET /api/v1/auth/github/login`
- `GET /api/v1/auth/github/callback`

## Notes

- For local testing, configure callback URLs in provider dashboards to match your app host.
- The scaffold currently redirects to `/docs` after callback; customize this to issue JWTs and redirect to your frontend session flow.
