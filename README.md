AsyncEv: asynchronous event objects
===================================

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/asyncev)

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

# Create a handler
async def on_myevent(ev: MyEvent):
    print(f"Got a MyEvent with the value {ev.value}!")

asyncev.bind(MyEvent, on_myevent)

# Emit event (requires a running asyncio event loop)
async def main():
    asyncev.emit(MyEvent(value="hello world"))
    
asyncio.run(main())
```

## Development

Recommended tooling is [`uv`](https://astral.sh/uv).

### Building

    $ uv build

### Testing

    $ uv run tox
