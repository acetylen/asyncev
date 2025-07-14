AsyncEv: asynchronous event objects
===================================

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/asyncev)![PyPI - Types](https://img.shields.io/pypi/types/asyncev)


AsyncEv leverages `asyncio` to create events that can be subscribed to and waited for.

## Installation

    pip install asyncev

## Usage

```python
import asyncio
import asyncev
from dataclasses import dataclass

# Create an event
@dataclass
class MyEvent(asyncev.Event):
    value: str

# Create a listener
async def on_myevent(ev: MyEvent):
    print(f"Got a MyEvent with the value {ev.value}!")

# also works for methods, with binds possible at init time.
class Listener:
    def __init__(self, name: str):
        self.name = name
        asyncev.bind(MyEvent, self.on_myevent)
    async def on_myevent(self, ev: MyEvent):
        print(f"{self.name} got a MyEvent with the value {ev.value}!")

asyncev.bind(MyEvent, on_myevent)


# Emit event (requires a running asyncio event loop)
async def main():
    jeff = Listener("Jeff")
    asyncev.emit(MyEvent(value="hello"))
    await asyncio.sleep(.1)

    del jeff  # cleanup of event listeners is automatic
    asyncev.emit(MyEvent("goodbye"))
    await asyncio.sleep(.1)
    
asyncio.run(main())
```

## Development

Recommended tooling is [`uv`](https://astral.sh/uv). install it with `pip`.

### Building

    $ uv build

### Testing

    $ uv run tox
