AsyncEv: asynchronous event objects
===================================

AsyncEv leverages `asyncio` to create events that can be subscribed to and waited for.
Events are arbitrary objects.


```python
import asyncio
import asyncev
from dataclasses import dataclass

# Create an event
@dataclass
class MyEvent(asyncev.BaseEvent):
    value: str

# Create a handler
async def on_myevent(ev: MyEvent):
    print("Got a MyEvent with the value {ev.value}!")

asyncev.bind(MyEvent, on_myevent)

# Emit event (requires a running asyncio event loop)
async def main():
    asyncev.emit(MyEvent(value="hello world"))
    
asyncio.run(main())
```

