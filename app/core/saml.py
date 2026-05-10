"""SAML 2.0 SP (Service Provider) support.

Uses python3-saml (OneLogin library). Install the optional extra to enable:

    uv pip install "python3-saml>=1.16.0"

On Linux/Docker (recommended for SAML development):
    apt-get install -y xmlsec1 libxmlsec1-dev pkg-config

See docs/identity/saml-setup.md for full Keycloak setup walkthrough.

When SAML_ENABLED=false (default) or the library is not installed, all
SAML endpoints return 503 with a clear message.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SAML_AVAILABLE = False
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-not-found]

    SAML_AVAILABLE = True
except ImportError:
    logger.debug("python3-saml not installed — SAML endpoints disabled")


def _saml_settings() -> dict[str, Any]:
    cfg = get_settings()
    return {
        "strict": True,
        "debug": cfg.is_development,
        "sp": {
            "entityId": f"{cfg.BASE_URL}/api/v1/auth/saml/metadata",
            "assertionConsumerService": {
                "url": f"{cfg.BASE_URL}/api/v1/auth/saml/callback",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": f"{cfg.BASE_URL}/api/v1/auth/saml/slo",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": cfg.SAML_SP_CERT,
            "privateKey": cfg.SAML_SP_KEY,
        },
        "idp": {
            "entityId": cfg.SAML_IDP_ENTITY_ID,
            "singleSignOnService": {
                "url": cfg.SAML_IDP_SSO_URL,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": cfg.SAML_IDP_SLO_URL,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": cfg.SAML_IDP_CERT,
        },
        "security": {
            "authnRequestsSigned": bool(cfg.SAML_SP_KEY),
            "wantAssertionsSigned": True,
            "wantMessagesSigned": False,
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
        },
    }


async def _prepare_request(request: Request) -> dict[str, Any]:
    """Normalize a FastAPI request into the dict python3-saml expects."""
    body = await request.body()
    form = await request.form() if request.method == "POST" else {}
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.url.netloc,
        "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": dict(form),
        "body": body,
    }


def _require_saml() -> None:
    cfg = get_settings()
    if not cfg.SAML_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAML is not enabled (set SAML_ENABLED=true and configure IdP settings)",
        )
    if not SAML_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="python3-saml is not installed. Run: uv pip install 'python3-saml>=1.16.0'",
        )


def build_saml_auth(prepared_request: dict[str, Any]) -> Any:
    """Construct a python3-saml auth object (extracted for test mocking)."""
    return OneLogin_Saml2_Auth(prepared_request, _saml_settings())  # type: ignore[name-defined]


async def initiate_sso(request: Request) -> str:
    """Return the redirect URL to the IdP for SP-initiated SSO."""
    _require_saml()
    prepared = await _prepare_request(request)
    auth = build_saml_auth(prepared)
    return auth.login()  # type: ignore[no-any-return]


async def process_callback(request: Request) -> dict[str, Any]:
    """Process the POST from the IdP. Returns a dict with ``nameid`` and ``attributes``."""
    _require_saml()
    prepared = await _prepare_request(request)
    auth = build_saml_auth(prepared)
    auth.process_response()

    errors = auth.get_errors()
    if errors:
        logger.warning("SAML errors: %s — %s", errors, auth.get_last_error_reason())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"SAML authentication failed: {', '.join(errors)}",
        )
    if not auth.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SAML: not authenticated",
        )

    return {
        "nameid": auth.get_nameid(),
        "attributes": auth.get_attributes(),
    }


def get_sp_metadata() -> tuple[str, list[str]]:
    """Return (metadata_xml, errors)."""
    _require_saml()
    try:
        from onelogin.saml2.settings import (  # type: ignore[import-not-found]
            OneLogin_Saml2_Settings,
        )

        saml_settings = OneLogin_Saml2_Settings(_saml_settings(), sp_validation_only=True)
        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)
        return metadata, errors
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate SAML metadata: {exc}",
        ) from exc
