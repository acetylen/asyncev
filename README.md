AsyncEv: asynchronous named events, tk style.
=============================================

AsyncEv leverages `asyncio` for creating named events that can be subscribed to and waited for.


```python
from dataclasses import dataclass
import asyncev


# Creating an event

class MyEvent(asyncev.BaseEvent):
    pass


async def on_myevent(ev: MyEvent):
    print("hello!")


asyncev.bind(MyEvent, on_myevent)


asyncev.emit(MyEvent())
# prints "hello!"


# Events can have payloads

@dataclass
class NameEvent(asyncev.BaseEvent):
    value

async def on_valueevent(ev: ValueEvent):
    print(f"hello {ev.value}!")

asyncev.bind(ValueEvent, on_valueevent)

asyncev.emit(ValueEvent("asyncev"))
# prints "hello asyncev!"

# Events are automatically unbound when the bound object goes out of scope,
# but they can also be unbound manually:
asyncev.unbind(ValueEvent, on_valueevent)

# Pausing until events happen

async def waiting_function():
    print("Waiting for value")

    ev = await asyncev.wait_for(ValueEvent)

    print(f"Got value {ev.value}!")


# Getting responses from events

async def doubler(ev: ValueEvent):
    return ev.value * 2

async def halver(ev: ValueEvent):
    return ev.value / 2

asyncev.bind(ValueEvent, doubler)
asyncev.bind(ValueEvent, halver)

async def gathering_function():
    # gather returns when all event handlers have run
    results = await asyncev.gather(ValueEvent(7))
    print(f"got {len(results)} results: {results}")
    # prints "got 2 results: [14, 3.5]"

# Sending responses to others

async def gatherer(evs: List[ValueEvent]):
    # the function named in gather_for is run when all handlers are finished.
    print("gatherer called")
    for ev in evs:
        print(ev.value)

def sender():
    # gather_for returns immediately
    print("gathering")
    asyncev.gather_for(ValueEvent(12), gatherer)
    print("sender exiting")

```
