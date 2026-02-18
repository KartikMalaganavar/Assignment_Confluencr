import asyncio
from weakref import WeakKeyDictionary

_shutdown_events: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Event] = WeakKeyDictionary()


def get_shutdown_event() -> asyncio.Event:
    loop = asyncio.get_running_loop()
    event = _shutdown_events.get(loop)
    if event is None:
        event = asyncio.Event()
        _shutdown_events[loop] = event
    return event


def clear_shutdown_signal() -> None:
    get_shutdown_event().clear()


def set_shutdown_signal() -> None:
    get_shutdown_event().set()
