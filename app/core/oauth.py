from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

oauth = OAuth()


def configure_oauth() -> OAuth:
    settings = get_settings()
    if settings.OAUTH_GOOGLE_CLIENT_ID and not oauth.create_client("google"):
        oauth.register(
            name="google",
            client_id=settings.OAUTH_GOOGLE_CLIENT_ID,
            client_secret=settings.OAUTH_GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    if settings.OAUTH_GITHUB_CLIENT_ID and not oauth.create_client("github"):
        oauth.register(
            name="github",
            client_id=settings.OAUTH_GITHUB_CLIENT_ID,
            client_secret=settings.OAUTH_GITHUB_CLIENT_SECRET,
            access_token_url="https://github.com/login/oauth/access_token",
            authorize_url="https://github.com/login/oauth/authorize",
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": "user:email"},
        )
    return oauth
