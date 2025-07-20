from functools import wraps
from typing import Any, Callable

from .asyncev import AsyncEv, BaseEvent as Event, Listener, EventType

_default = AsyncEv()


@wraps(_default.bind)
def bind(event: type[EventType], func: Listener[EventType]) -> None:
    _default.bind(event, func)


@wraps(_default.unbind)
def unbind(event: type[EventType], func: Listener[EventType]) -> None:
    _default.unbind(event, func)


@wraps(_default.emit)
def emit(event: Event) -> None:
    _default.emit(event)


@wraps(_default.gather)
async def gather(event: Event) -> list[Any]:
    return await _default.gather(event)


@wraps(_default.gather_for)
def gather_for(event: Event, func: Callable[[list[Any]], None]) -> None:
    _default.gather_for(event, func)


@wraps(_default.wait_for)
async def wait_for(event: type[EventType]) -> EventType:
    return await _default.wait_for(event)


__all__ = [
    "AsyncEv",
    "Event",
    "Listener",
    "bind",
    "unbind",
    "emit",
    "gather",
    "gather_for",
    "wait_for",
]
