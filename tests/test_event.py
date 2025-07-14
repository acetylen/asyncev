from dataclasses import dataclass
from typing import Any
from weakref import ref, WeakMethod
import asyncio
import logging
import asyncev

from unittest import IsolatedAsyncioTestCase

yield_for = 0.01  # how long to allow the event handler to run after setup

log = logging.getLogger(__name__)


@dataclass
class ValueEvent(asyncev.Event):
    value: Any


class EventTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.eventhandler = asyncev.AsyncEv()
        self.arg_value = None
        self.method_called = False
        self.arg_input = "argument value"

    async def test_bound_function(self):
        """Test that
        * a function bound to an event receives events of that type,
        * unbinding removes the function from the listeners and no longer receives events.
        """

        # check that there are no listeners for our event
        self.assertNotIn(ValueEvent, self.eventhandler.events)

        async def function(ev: ValueEvent):
            self.arg_value = ev.value

        self.eventhandler.bind(ValueEvent, function)

        # check that there is now a bound listener for the event.
        self.assertIn(ValueEvent, self.eventhandler.events)
        self.assertIn(ref(function), self.eventhandler.events[ValueEvent])

        # check that the before-value is correct
        self.assertIsNone(self.arg_value)

        # check that the bound listener receives the event.
        self.eventhandler.emit(ValueEvent(self.arg_input))
        await asyncio.sleep(yield_for)
        self.assertEqual(self.arg_input, self.arg_value)

        # check that unbinding makes the event not arrive to the listener.
        self.eventhandler.unbind(ValueEvent, function)
        self.arg_value = None
        self.eventhandler.emit(ValueEvent(self.arg_input))
        await asyncio.sleep(yield_for)
        self.assertIsNone(self.arg_value)

    async def test_bound_method(self):
        """Same as test_bound_function, but for methods."""

        # check that there are no listeners for our event
        self.assertNotIn(ValueEvent, self.eventhandler.events)

        # set up an class that binds to an event on instantiation
        class BindObject:
            def __init__(this, eventhandler):
                eventhandler.bind(ValueEvent, this.listener)
                this.arg_value = None

            async def listener(self, ev: ValueEvent):
                self.arg_value = ev.value

        obj = BindObject(self.eventhandler)

        # check that there is now a bound listener for the event.
        self.assertIn(ValueEvent, self.eventhandler.events)
        self.assertIn(WeakMethod(obj.listener), self.eventhandler.events[ValueEvent])

        # check that the before-value is correct
        self.assertIsNone(self.arg_value)

        # check that the bound listener receives the event.
        self.eventhandler.emit(ValueEvent(self.arg_input))
        await asyncio.sleep(yield_for)
        self.assertEqual(self.arg_input, obj.arg_value)

        # check that unbinding makes the event not arrive to the listener.
        self.eventhandler.unbind(ValueEvent, obj.listener)
        self.arg_value = None
        self.eventhandler.emit(ValueEvent(self.arg_input))
        await asyncio.sleep(yield_for)
        self.assertIsNone(self.arg_value)

    async def test_wait_for(self):
        """test that wait_for cleans up after itself"""

        async def waiter():
            self.method_called = True
            ev = await self.eventhandler.wait_for(ValueEvent)
            self.arg_value = ev.value

        # check that there are no registered listeners for the event
        self.assertNotIn(ValueEvent, self.eventhandler.events)
        # check before-values
        self.assertFalse(self.method_called)
        self.assertNotEqual(self.arg_input, self.arg_value)

        # check that the listener has started and is blocking
        task = asyncio.create_task(waiter())
        await asyncio.sleep(yield_for)
        self.assertTrue(self.method_called)
        self.assertNotEqual(self.arg_input, self.arg_value)

        # check that the listener has received the event
        self.eventhandler.emit(ValueEvent(self.arg_input))
        await asyncio.sleep(yield_for)
        self.assertEqual(self.arg_value, self.arg_input)

        # check that the wait_for ephemeral listener has been removed
        self.assertFalse(self.eventhandler.events[ValueEvent])
        await task  # clean up waiter

    async def test_gather(self):
        """test that gather returns all results"""

        def factory(i: int):
            async def f(ev: ValueEvent) -> int:
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
        def factory(i: int):
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
        await asyncio.sleep(yield_for)

        self.assertTrue(self.method_called)

    async def test_prune(self):
        """Check that listeners are cleaned up when they go out of scope"""
        class BindObject:
            def __init__(this, eventhandler):
                eventhandler.bind(ValueEvent, this.bound_method)
                this.arg_value = None

            async def bound_method(self, ev: ValueEvent):
                self.arg_value = ev.value

        # check that there are no listeners already
        self.assertNotIn(ValueEvent, self.eventhandler.events)

        obj = BindObject(self.eventhandler)

        # check that our listener has been added
        self.assertIn(ValueEvent, self.eventhandler.events)
        self.assertIn(
            WeakMethod(obj.bound_method), self.eventhandler.events[ValueEvent]
        )

        del obj
        # check that the listener was immediately deleted
        self.assertSetEqual(self.eventhandler.events[ValueEvent], set())

    def test_non_async_handler(self):
        def non_async_handler(ev: ValueEvent):
            pass

        with self.assertRaises(TypeError):
            self.eventhandler.bind(ValueEvent, non_async_handler)
