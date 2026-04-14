import asyncio
from collections.abc import Callable
from typing import Any

_handlers: dict[str, list[Callable[..., Any]]] = {}


def on(event_name: str):
    def decorator(func: Callable[..., Any]):
        _handlers.setdefault(event_name, []).append(func)
        return func

    return decorator


async def emit(event_name: str, **kwargs: Any) -> None:
    for handler in _handlers.get(event_name, []):
        if asyncio.iscoroutinefunction(handler):
            await handler(**kwargs)
        else:
            handler(**kwargs)
