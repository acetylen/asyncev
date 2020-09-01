from dataclasses import dataclass
from aiounittest import AsyncTestCase
from weakref import ref, WeakMethod
import asyncio
import logging
import asyncev


log = logging.getLogger(__name__)

@dataclass
class ValueEvent(asyncev.BaseEvent):
    value: str

class EventTest(AsyncTestCase):
    def setUp(self):
        self.eventhandler = asyncev.AsyncEv()
        self.arg_value = None
        self.method_called = False
        self.arg_input = "argument value"

    async def test_bound_function(self):

        self.assertNotIn(ValueEvent, self.eventhandler.events)

        async def function(ev: ValueEvent):
            self.arg_value = ev.value

        self.eventhandler.bind(ValueEvent, function)

        self.assertIn(ValueEvent, self.eventhandler.events)
        self.assertIn(ref(function), self.eventhandler.events[ValueEvent])

        self.eventhandler.emit(ValueEvent(self.arg_input))
        await asyncio.sleep(0.5)

        self.assertEqual(self.arg_input, self.arg_value)

        self.eventhandler.unbind(ValueEvent, function)

        self.assertNotIn(ref(function), self.eventhandler.events[ValueEvent])

    async def test_bound_method(self):

        self.assertNotIn(ValueEvent, self.eventhandler.events)

        class BindObject:
            def __init__(this, eventhandler):
                eventhandler.bind(ValueEvent, this.bound_method)
                this.arg_value = None

            async def bound_method(self, ev: ValueEvent):
                self.arg_value = ev.value

        obj = BindObject(self.eventhandler)

        self.assertIn(
            ValueEvent, self.eventhandler.events,
        )
        self.assertIn(
            WeakMethod(obj.bound_method), self.eventhandler.events[ValueEvent],
        )

        self.assertIsNone(obj.arg_value)

        self.eventhandler.emit(ValueEvent(self.arg_input))
        await asyncio.sleep(0.5)

        self.assertEqual(self.arg_input, obj.arg_value)


    async def test_wait_for(self):
        async def waiter():
            ev = await self.eventhandler.wait_for(ValueEvent)
            self.arg_value = ev.value

        self.assertNotIn(ValueEvent, self.eventhandler.events)
        self.assertFalse(self.method_called)

        task = asyncio.create_task(waiter())

        self.assertFalse(self.method_called)
        self.eventhandler.emit(ValueEvent(self.arg_input))
        await asyncio.sleep(0.5)

        self.assertTrue(self.arg_value, self.arg_input)
        self.assertFalse(self.eventhandler.events[ValueEvent])  # check if empty
        await task

    async def test_gather(self):
        def factory(i):
            async def f(ev: ValueEvent):
                return i + ev.value

            return f

        funcs = []
        for i in range(10):
            f = factory(i)
            funcs.append(f)
            self.eventhandler.bind(ValueEvent, f)

        results = await self.eventhandler.gather(ValueEvent(10))
        self.assertEqual(sorted(results), list(range(10, 20)))

    async def test_gather_for(self):
        def factory(i):
            async def f(ev: ValueEvent):
                return i + ev.value

            return f

        funcs = []
        for i in range(10):
            f = factory(i)
            funcs.append(f)
            self.eventhandler.bind(ValueEvent, f)

        def gatherer(results):
            self.method_called = True
            self.assertEqual(sorted(results), list(range(10, 20)))

        self.eventhandler.gather_for(ValueEvent(10), gatherer)
        await asyncio.sleep(0.5)

        self.assertTrue(self.method_called)

    async def test_prune(self):
        class BindObject:
            def __init__(this, eventhandler):
                eventhandler.bind(ValueEvent, this.bound_method)
                this.arg_value = None

            async def bound_method(self, ev: ValueEvent):
                self.arg_value = ev.value

        obj = BindObject(self.eventhandler)

        self.assertIn(ValueEvent, self.eventhandler.events)

        del obj
        self.assertIsNone(list(self.eventhandler.events[ValueEvent])[0]())

        self.eventhandler.emit(ValueEvent(2)) #prune is only called after emit
        await asyncio.sleep(0.5)
        self.assertFalse(self.eventhandler.events[ValueEvent])

    def test_non_async_handler(self):
        def non_async_handler():
            pass

        with self.assertRaises(TypeError):
            self.eventhandler.bind(ValueEvent, non_async_handler)
