"""asyncev: Named events for asyncio.

Asyncev is an event-dispatcher that allows developers to communicate between
objects using event objects with arbitrary payloads. A function or method
which takes an event object can be designated a listener by using bind(), which
will make it run every time an event is emit()ed.
"""

import asyncio
import logging
from abc import ABC
from collections.abc import Coroutine
from dataclasses import dataclass
from inspect import iscoroutinefunction, ismethod
from typing import Any, Callable, Optional, TypeVar, Union
from weakref import ReferenceType, WeakMethod, ref

log = logging.getLogger(__name__)


@dataclass
class BaseEvent(ABC):
    """Base class for event types."""

    def __init__(self, *args, **kwargs):
        if type(self) is BaseEvent:
            raise Exception("BaseEvent should not be instantiated directly")
        super().__init__(*args, **kwargs)


EventType = TypeVar("EventType", bound=BaseEvent)
Listener = Callable[[EventType], Coroutine[None, None, Any]]
Reference = Union[ReferenceType[Listener[EventType]], WeakMethod[Listener[EventType]]]


def funcref(
    listener: Listener[EventType],
    callback: Optional[Callable[[Reference[EventType]], None]] = None,
) -> Reference[EventType]:
    """Unified way to create a reference to a function or a bound method."""
    if ismethod(listener):
        return WeakMethod(listener, callback)
    return ref(listener, callback)


class AsyncEv:
    """AsyncEv uses the asyncio event loop to create Tk-style named events.

    Events can be emitted, awaited, and bound to.
    """

    def __init__(self):
        self.events: dict[type[BaseEvent], set[Reference[BaseEvent]]] = {}
        self.writelock: dict[type[BaseEvent], asyncio.Lock] = {}

    def bind(self, event: type[EventType], listener: Listener[EventType]) -> None:
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

    def unbind(self, event: type[EventType], listener: Listener[EventType]) -> None:
        """Unbind {listener} from {event}.
        Will error if event or listener doesn't exist."""
        log.debug("Removing binding: %r -> %s", event, listener)

        self.events[event].discard(funcref(listener))

    async def _emit(self, event: BaseEvent) -> list[Any]:
        """Call all valid {event} handlers with the provided events."""
        t = type(event)
        async with self.writelock[t]:
            # the weakref callback ensures that no Nones are left in the list.
            callbacks = [task()(event) for task in self.events[t]]

        log.debug("Emit %s!", t.__name__)
        return await asyncio.gather(*callbacks)

    def emit(self, event: BaseEvent) -> None:
        """Emit {event}, triggering all listeners as soon as possible."""
        log.debug("Scheduling emit(%s)", event)
        asyncio.create_task(self._emit(event))

    async def gather(self, event: BaseEvent) -> list[Any]:
        """Emit {event}, wait for all listeners to run, and return the result."""
        log.debug("Gather(%s)", event)
        return await self._emit(event)

    def gather_for(self, event: BaseEvent, func: Callable[[list[Any]], None]) -> None:
        """Emit {event}, wait for all listeners, and send their results to {func}.

        This is useful for passing results to synchronous functions.
        """

        async def callback() -> None:
            results = await self.gather(event)
            func(results)

        log.debug("Scheduling gather_for(%s)", event)
        asyncio.create_task(callback())

    async def wait_for(self, event: type[EventType]) -> EventType:
        """Sleep until an {event} occurs, then return it.

        wait_for creates a temporary handler for the given event that gets
        removed after the event has occurred once. This is more expensive
        than registering a proper event handler, so should probably only be
        used for events that don't occur very often.
        """
        future: asyncio.Future[EventType] = asyncio.Future()

        async def wait_trigger(event: EventType) -> None:
            future.set_result(event)

        self.bind(event, wait_trigger)
        try:
            return await future
        finally:
            self.unbind(event, wait_trigger)
