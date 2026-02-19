import asyncio
from weakref import WeakKeyDictionary

_shutdown_events: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Event] = WeakKeyDictionary()
_background_tasks: WeakKeyDictionary[asyncio.AbstractEventLoop, set[asyncio.Task]] = WeakKeyDictionary()


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


def register_background_task(task: asyncio.Task) -> None:
    loop = asyncio.get_running_loop()
    tasks = _background_tasks.get(loop)
    if tasks is None:
        tasks = set()
        _background_tasks[loop] = tasks
    tasks.add(task)

    def _discard(done_task: asyncio.Task) -> None:
        tasks.discard(done_task)

    task.add_done_callback(_discard)


async def drain_background_tasks() -> None:
    loop = asyncio.get_running_loop()
    tasks = list(_background_tasks.get(loop, set()))
    if not tasks:
        return
    for task in tasks:
        if not task.done():
            task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
