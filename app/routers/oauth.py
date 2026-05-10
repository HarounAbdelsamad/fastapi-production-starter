"""OAuth 2.0 / OpenID Connect provider callbacks.

Supported providers: Google, GitHub.
Pattern for adding a new provider: see docs/identity/oauth.md.

Each callback flow:
  1. Exchange authorization code for tokens
  2. Fetch user info from the provider
  3. Find or create a local User (linked via OAuthAccount)
  4. Issue JWT access + refresh tokens
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, create_refresh_token
from app.core.oauth import configure_oauth
from app.db.database import get_session
from app.services.oauth_service import get_or_create_oauth_user

router = APIRouter()


@router.get("/google/login")
async def google_login(request: Request) -> RedirectResponse:
    client = configure_oauth().create_client("google")
    if client is None:
        raise HTTPException(status_code=404, detail="Google OAuth not configured")
    redirect_uri = request.url_for("google_callback")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    client = configure_oauth().create_client("google")
    if client is None:
        raise HTTPException(status_code=404, detail="Google OAuth not configured")
    token = await client.authorize_access_token(request)
    userinfo = token.get("userinfo") or await client.userinfo(token=token)

    email = userinfo.get("email", "")
    username = userinfo.get("name") or userinfo.get("login") or email.split("@")[0]
    provider_user_id = str(userinfo.get("sub", email))

    user, _ = await get_or_create_oauth_user(
        db,
        provider="google",
        provider_user_id=provider_user_id,
        email=email,
        username=username,
    )
    return JSONResponse(
        content={
            "access_token": create_access_token(user.user_id),
            "refresh_token": create_refresh_token(user.user_id),
            "token_type": "bearer",
        }
    )


@router.get("/github/login")
async def github_login(request: Request) -> RedirectResponse:
    client = configure_oauth().create_client("github")
    if client is None:
        raise HTTPException(status_code=404, detail="GitHub OAuth not configured")
    redirect_uri = request.url_for("github_callback")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/github/callback", name="github_callback")
async def github_callback(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    client = configure_oauth().create_client("github")
    if client is None:
        raise HTTPException(status_code=404, detail="GitHub OAuth not configured")
    token = await client.authorize_access_token(request)

    resp = await client.get("user", token=token)
    github_user = resp.json()

    # GitHub may not expose primary email in /user; fetch separately if needed
    email = github_user.get("email") or f"{github_user['login']}@users.noreply.github.com"
    username = github_user.get("login", "")
    provider_user_id = str(github_user["id"])

    user, _ = await get_or_create_oauth_user(
        db,
        provider="github",
        provider_user_id=provider_user_id,
        email=email,
        username=username,
    )
    return JSONResponse(
        content={
            "access_token": create_access_token(user.user_id),
            "refresh_token": create_refresh_token(user.user_id),
            "token_type": "bearer",
        }
    )
