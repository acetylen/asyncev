import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from inspect import iscoroutinefunction, ismethod
from typing import Any, Awaitable, Callable, List, Type, TypeVar
from weakref import WeakMethod, ref

Coroutine = Callable[..., Awaitable]

log = logging.getLogger(__name__)


def funcref(f: Callable):
    if ismethod(f):
        return WeakMethod(f)
    return ref(f)


@dataclass
class BaseEvent:
    def __init__(self):
        if type(self) == BaseEvent:
            raise Exception("BaseEvent should not be instantiated directly")


Event = TypeVar("Event", bound=BaseEvent)


class AsyncEv:
    """
    AsyncEv uses the asyncio event loop to create Tk-style named events.
    Events can be emitted, awaited, and bound to.
    """

    def __init__(self):
        self.events = defaultdict(set)
        self.writelock = asyncio.Lock()
        # FIXME: Writelock can't be used in non-async methods...

    def bind(self, event: Type[Event], listener: Coroutine):
        """Bind listener to a named event."""
        if not iscoroutinefunction(listener):
            raise TypeError("Event listeners must be async!")

        log.debug("Adding binding: %r -> %s", event, listener)
        self.events[event].add(funcref(listener))

    def unbind(self, event: Type[Event], listener: Coroutine):
        """Unbind listener from event.
        Will error if event or listener doesn't exist."""
        log.debug("Removing binding: %r -> %s", event, listener)

        self.events[event] -= {funcref(listener)}

    async def _emit(self, event: Event):
        """Call all valid {event} handlers with provided args.

        If any reference has decayed, trigger a pruning session
        after the event has been emitted.
        """
        callbacks = []
        decayed = 0
        t = type(event)
        async with self.writelock:
            for taskref in self.events[t]:
                task = taskref()
                if task is None:
                    decayed += 1
                    continue
                log.debug("Queueing callback %r(%r)", task, event)
                callbacks.append(task(event))
        log.debug("Emit %s!", t.__name__)
        results = await asyncio.gather(*callbacks)
        if decayed:
            log.debug("%d of %r's handlers have decayed.", decayed, t.__name__)
            asyncio.create_task(self._prune(t))
        return results

    def emit(self, event: Event):
        """Emit an event, passing any provided arguments to all listeners."""
        log.debug("Scheduling emit(%s)", event)
        asyncio.create_task(self._emit(event))

    async def gather(self, event: Event) -> List[Any]:
        """emit an event, wait for all handlers to run, and return the result."""

        log.debug("Gather(%s)", event)
        return await self._emit(event)

    def gather_for(self, event: Event, func: Callable):
        """Emit an event, wait for all handlers to run, and send them to func."""

        async def _callback():
            results = await self.gather(event)
            func(results)

        log.debug("Scheduling gather_for(%s)", event)
        asyncio.create_task(_callback())

    async def _prune(self, event: Type[Event]):
        """Find and remove dead handlers for {event}"""
        diff = {r for r in self.events[event] if r() is None}
        async with self.writelock:
            self.events[event] -= diff

    async def wait_for(self, event: Type[Event]) -> Event:
        """Sleep until event occurs.

        wait_for creates a temporary handler for the given event that gets
        removed after the event has occurred once. This is more expensive
        than registering a proper event handler, so should probably only be
        used for events that don't occur very often.
        """
        ev = asyncio.Event()

        out: Event

        async def wait_trigger(event: Event):
            nonlocal out
            out = event
            ev.set()

        self.bind(event, wait_trigger)
        await ev.wait()
        self.unbind(event, wait_trigger)
        return out


# Default event handler exposed through the methods in event.__init__
_default = AsyncEv()
