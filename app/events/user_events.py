from app.core.events import on


@on("user.created")
def _user_created_event(**kwargs) -> None:
    _ = kwargs


@on("user.deleted")
def _user_deleted_event(**kwargs) -> None:
    _ = kwargs
