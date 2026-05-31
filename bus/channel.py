"""
bus/channel.py
──────────────
Async publish/subscribe channel for Cipher's event bus.

Design:
  - Single EventBus singleton per process (use get_bus())
  - Producers call `await bus.publish(event)`
  - Consumers call `bus.subscribe(EventType.CANDLE, handler_coroutine)`
  - All handlers for a given event type run concurrently via asyncio.gather
  - Dead-letter queue: failed handlers log to DLQ without crashing the bus
  - Optional replay: events buffered in a deque for post-mortem debugging

Usage:
    bus = get_bus()
    bus.subscribe(EventType.SIGNAL, log_signal)
    bus.subscribe(EventType.SIGNAL, risk_gate_check)
    await bus.publish(SignalEvent(strategy="ScalpV1", pair="BTC/USDT", ...))
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from bus.events import BaseEvent, EventType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

Handler = Callable[[BaseEvent], Awaitable[None]]

_MAX_REPLAY_BUFFER = 1000


class EventBus:
    def __init__(self, replay: bool = False) -> None:
        self._handlers: dict[EventType, list[Handler]] = defaultdict(list)
        self._wildcard: list[Handler] = []
        self._dlq: list[tuple[BaseEvent, Exception]] = []
        self._replay_buffer: deque[BaseEvent] = (
            deque(maxlen=_MAX_REPLAY_BUFFER) if replay else deque(maxlen=0)
        )
        self._replay_enabled = replay

    def subscribe(
        self,
        event_type: EventType | None,
        handler: Handler,
    ) -> None:
        """
        Register an async handler for an event type.
        Pass event_type=None to subscribe to ALL events (wildcard).
        """
        if event_type is None:
            self._wildcard.append(handler)
        else:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType | None, handler: Handler) -> None:
        if event_type is None:
            self._wildcard = [h for h in self._wildcard if h is not handler]
        else:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h is not handler]

    async def publish(self, event: BaseEvent) -> None:
        """
        Broadcast event to all registered handlers concurrently.
        Handler exceptions are caught, logged, and added to the DLQ.
        """
        if self._replay_enabled:
            self._replay_buffer.append(event)

        handlers = list(self._handlers.get(event.type, [])) + list(self._wildcard)
        if not handlers:
            return

        results = await asyncio.gather(
            *[h(event) for h in handlers],
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    "Handler %s failed for %s: %s",
                    getattr(handler, "__name__", repr(handler)),
                    event.type,
                    result,
                )
                self._dlq.append((event, result))

    async def replay(self, event_type: EventType | None = None) -> None:
        """Re-publish all buffered events (for testing / post-mortem)."""
        if not self._replay_enabled:
            raise RuntimeError("EventBus created without replay=True")
        events = (
            [e for e in self._replay_buffer if e.type == event_type]
            if event_type
            else list(self._replay_buffer)
        )
        for event in events:
            await self.publish(event)

    @property
    def dead_letter_queue(self) -> list[tuple[BaseEvent, Exception]]:
        return list(self._dlq)

    def clear_dlq(self) -> None:
        self._dlq.clear()

    def subscriber_count(self, event_type: EventType) -> int:
        return len(self._handlers.get(event_type, [])) + len(self._wildcard)


# ── Global singleton ──────────────────────────────────────────────────────────

_bus: EventBus | None = None


def get_bus(replay: bool = False) -> EventBus:
    """Return process-level EventBus singleton."""
    global _bus
    if _bus is None:
        _bus = EventBus(replay=replay)
    return _bus


def reset_bus() -> None:
    """Replace singleton with a fresh bus (test isolation)."""
    global _bus
    _bus = None
