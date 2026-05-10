"""SAML 2.0 SP endpoints.

Routes:
    GET  /api/v1/auth/saml/login      — SP-initiated SSO (redirects to IdP)
    POST /api/v1/auth/saml/callback   — ACS: IdP posts assertion here
    GET  /api/v1/auth/saml/metadata   — SP metadata XML

Requires SAML_ENABLED=true and the python3-saml library.
See docs/identity/saml-setup.md for Keycloak setup.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, create_refresh_token
from app.core.saml import get_sp_metadata, initiate_sso, process_callback
from app.db.database import get_session
from app.schemas.auth import TokenResponse
from app.services.oauth_service import get_or_create_oauth_user

router = APIRouter(prefix="/saml", tags=["SAML"])


@router.get("/login")
async def saml_login(request: Request) -> RedirectResponse:
    """Initiate SP-initiated SSO — redirects the browser to the configured IdP."""
    redirect_url = await initiate_sso(request)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post("/callback", response_model=TokenResponse)
async def saml_callback(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Assertion Consumer Service (ACS).

    The IdP POSTs the SAMLResponse here after successful authentication.
    Returns JWT tokens that the client can use for subsequent API calls.
    """
    result = await process_callback(request)

    nameid: str = result["nameid"]
    attributes: dict = result.get("attributes", {})

    # Extract email and username from assertion attributes
    _ws_email = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
    _ws_name = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
    email_list = attributes.get("email", attributes.get(_ws_email, [nameid]))
    email = email_list[0] if email_list else nameid
    username_list = attributes.get("username", attributes.get(_ws_name, []))
    username = username_list[0] if username_list else email.split("@")[0]

    user, _ = await get_or_create_oauth_user(
        db,
        provider="saml",
        provider_user_id=nameid,
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


@router.get("/metadata")
async def saml_metadata() -> Response:
    """Return the SP metadata XML for IdP registration."""
    metadata, errors = get_sp_metadata()
    if errors:
        return Response(
            content=f"Metadata errors: {', '.join(errors)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="text/plain",
        )
    return Response(content=metadata, media_type="application/xml")
