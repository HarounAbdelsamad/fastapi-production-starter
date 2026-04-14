from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.core.oauth import configure_oauth

router = APIRouter()


@router.get("/google/login")
async def google_login(request: Request):
    client = configure_oauth().create_client("google")
    if client is None:
        raise HTTPException(status_code=404, detail="Google OAuth not configured")
    redirect_uri = request.url_for("google_callback")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    client = configure_oauth().create_client("google")
    if client is None:
        raise HTTPException(status_code=404, detail="Google OAuth not configured")
    await client.authorize_access_token(request)
    return RedirectResponse(url="/docs")


@router.get("/github/login")
async def github_login(request: Request):
    client = configure_oauth().create_client("github")
    if client is None:
        raise HTTPException(status_code=404, detail="GitHub OAuth not configured")
    redirect_uri = request.url_for("github_callback")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/github/callback", name="github_callback")
async def github_callback(request: Request):
    client = configure_oauth().create_client("github")
    if client is None:
        raise HTTPException(status_code=404, detail="GitHub OAuth not configured")
    await client.authorize_access_token(request)
    return RedirectResponse(url="/docs")
