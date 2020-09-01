from functools import wraps
from typing import Any, Callable, List, Type

from .asyncev import AsyncEv, BaseEvent, Coroutine
from .asyncev import Event as _ev
from .asyncev import _default


@wraps(_default.bind)
def bind(event: Type[_ev], func: Coroutine):
    _default.bind(event, func)


@wraps(_default.unbind)
def unbind(event: Type[_ev], func: Coroutine):
    _default.unbind(event, func)


@wraps(_default.emit)
def emit(event: _ev):
    _default.emit(event)


@wraps(_default.gather)
async def gather(event: _ev) -> List[Any]:
    return await _default.gather(event)


@wraps(_default.gather_for)
def gather_for(event: _ev, func: Callable):
    _default.gather_for(event, func)


@wraps(_default.wait_for)
async def wait_for(event: Type[_ev]) -> _ev:
    return await _default.wait_for(event)
