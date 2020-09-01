AsyncEv: asynchronous named events, tk style.
=============================================

AsyncEv leverages `asyncio` for creating named events that can be subscribed to and waited for.


```python
from dataclasses import dataclass
import asyncev
from typing import Any, Sequence


# Creating an event
class MyEvent(asyncev.BaseEvent):
    pass

# Creating an event handler
async def on_myevent(ev: MyEvent):
    print("Basic event handler called!")

# binding to an event
asyncev.bind(MyEvent, on_myevent)


# Events can be any object (but dataclasses are very practical)
@dataclass
class ValueEvent(asyncev.BaseEvent):
    value: Any


async def on_valueevent(ev: ValueEvent):
    print(f"Event handler called with a value: {ev.value}!")

asyncev.bind(ValueEvent, on_valueevent)


async def waiting_function():
    print("Waiting function called, waiting for value")

    ev = await asyncev.wait_for(ValueEvent)

    print(f"Waiting function got a value: {ev.value}!")


# Getting responses from events
async def doubler(ev: ValueEvent) -> float:
    print(f"doubler called with value {ev.value}")
    return ev.value * 2

async def halver(ev: ValueEvent) -> float:
    print(f"halver called with value {ev.value}")
    return ev.value / 2


async def gathering_function():
    # gather returns when all event handlers have run
    print("Gathering function called, sending an event")
    results: Sequence[float] = await asyncev.gather(ValueEvent(7))
    print(f"Gathering function got {len(results)} results: {results}")


# Sending responses to others
def gatherer(responses: Sequence[float]):
    # the function named in gather_for is run when all handlers are finished.
    print(f"Gatherer got {len(responses)} responses: {responses}")


def sender():
    # gather_for returns immediately. useful for emitting from synchronous functions.
    print("Synchronous sender called")
    asyncev.gather_for(ValueEvent(12), gatherer)
    print("sender exiting")


async def main():
    print("--- emit ---")
    print("Emitting simple event")
    asyncev.emit(MyEvent())
    await asyncio.sleep(0.1) #events are not emitted until method yields

    print("Emitting event with value")
    asyncev.emit(ValueEvent("asyncev"))
    await asyncio.sleep(0.1)

    # Events are automatically unbound when the bound object goes out of scope,
    # but they can also be unbound manually:
    asyncev.unbind(ValueEvent, on_valueevent)

    print("--- wait_for ---")
    # We queue the event up so that it is sent when the waiting function yields
    print("Waiting for queued event")
    asyncev.emit(ValueEvent("wait_for"))
    await waiting_function()

    print("--- gather ---")
    asyncev.bind(ValueEvent, doubler)
    asyncev.bind(ValueEvent, halver)
    await gathering_function()

    print("--- gather_for ---")
    print("Gathering responses for someone else")
    sender()

    # since sender is sync, the event is not emitted until the method yields
    await asyncio.sleep(.1)

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```
