from app.core.events import on


@on("auth.login")
def _auth_login_event(**kwargs) -> None:
    _ = kwargs


@on("auth.password_reset")
def _auth_password_reset_event(**kwargs) -> None:
    _ = kwargs
