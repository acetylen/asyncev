from abc import ABC
import asyncio
import logging
from dataclasses import dataclass
from inspect import iscoroutinefunction, ismethod
from collections.abc import Coroutine
from typing import Any, Callable, Optional, TypeVar, Union
from weakref import ReferenceType, WeakMethod, ref


log = logging.getLogger(__name__)


class AsyncEvError(Exception):
    pass

@dataclass
class BaseEvent(ABC):
    def __post_init__(self):
        if type(self) is BaseEvent:
            raise Exception("BaseEvent should not be instantiated directly")

class SENTINEL(BaseEvent):
    pass

EventType = TypeVar("EventType", bound=BaseEvent)
Listener = Callable[[BaseEvent], Coroutine[None, None, Any]]
Reference = Union[ReferenceType[Listener], WeakMethod[Listener]]


def funcref(
    listener: Listener,
    callback: Optional[Callable[[Reference], None]] = None,
) -> Reference:
    """Unified way to create a reference to a function or a bound method."""
    if ismethod(listener):
        return WeakMethod(listener, callback)
    return ref(listener, callback)


class AsyncEv:
    """
    AsyncEv uses the asyncio event loop to create Tk-style named events.
    Events can be emitted, awaited, and bound to.
    """

    def __init__(self):
        self.events: dict[type[BaseEvent], set[Reference]] = {}
        self.writelock: dict[type[BaseEvent], asyncio.Lock] = {}
        # FIXME: Writelock can't be used in non-async methods...

    def bind(self, event: type[BaseEvent], listener: Listener):
        """Bind {listener} to a named {event}."""
        if not iscoroutinefunction(listener):
            raise TypeError("Event listeners must be async!")

        log.debug("Adding binding: %r -> %s", event, listener)
        if event not in self.events:
            self.events[event] = set()
            self.writelock[event] = asyncio.Lock()

        self.events[event].add(
            funcref(listener, lambda r: self.events[event].discard(r))
        )

    def unbind(self, event: type[BaseEvent], listener: Listener):
        """Unbind {listener} from {event}.
        Will error if event or listener doesn't exist."""
        log.debug("Removing binding: %r -> %s", event, listener)

        self.events[event].discard(funcref(listener))

    async def _emit(self, event: BaseEvent):
        """Call all valid {event} handlers with the provided events."""
        t = type(event)
        async with self.writelock[t]:
            # the weakref callback _should_ ensure that no Nones are left in the list.
            callbacks = [task()(event) for task in self.events[t]] # type: ignore

        log.debug("Emit %s!", t.__name__)
        return await asyncio.gather(*callbacks)

    def emit(self, event: BaseEvent):
        """Emit {event}, triggering all listeners as soon as possible."""
        log.debug("Scheduling emit(%s)", event)
        asyncio.create_task(self._emit(event))

    async def gather(self, event: BaseEvent) -> list[Any]:
        """emit {event}, wait for all listeners to run, and return the result."""

        log.debug("Gather(%s)", event)
        return await self._emit(event)

    def gather_for(self, event: BaseEvent, func: Callable[..., None]):
        """Emit {event}, wait for all listeners, and send their results to {func}.
        This is useful for passing results to synchronous functions.
        """

        async def _callback():
            results = await self.gather(event)
            func(results)

        log.debug("Scheduling gather_for(%s)", event)
        asyncio.create_task(_callback())

    async def wait_for(self, event: type[BaseEvent]) -> BaseEvent:
        """Sleep until {event} occurs.

        wait_for creates a temporary handler for the given event that gets
        removed after the event has occurred once. This is more expensive
        than registering a proper event handler, so should probably only be
        used for events that don't occur very often.
        """
        ev = asyncio.Event()

        out: Union[BaseEvent, SENTINEL] = SENTINEL()

        async def wait_trigger(event: BaseEvent):
            nonlocal out
            out = event
            ev.set()

        self.bind(event, wait_trigger)
        await ev.wait()
        self.unbind(event, wait_trigger)
        if type(out) is SENTINEL:
            raise AsyncEvError("wait_for triggered without passing an event! this is a bug!")
        return out
