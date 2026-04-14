import pytest

from app.core.events import emit, on

_EVENTS: list[str] = []


@on("test.event")
def _test_handler(value: str) -> None:
    _EVENTS.append(value)


@pytest.mark.asyncio
async def test_emit_event_calls_handler():
    await emit("test.event", value="ok")
    assert "ok" in _EVENTS
