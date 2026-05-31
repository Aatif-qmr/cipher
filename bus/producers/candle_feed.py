"""
bus/producers/candle_feed.py
─────────────────────────────
Polls freqtrade's DataProvider for new candles and publishes CandleEvents.

Decouples candle delivery from strategy logic — strategies subscribe to
the bus instead of pulling from DataProvider directly.  This enables:
  - Multiple strategies to share one data poll
  - Event replay for backtesting without touching strategy code
  - Candle buffering when a strategy is temporarily unavailable
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from bus.channel import get_bus
from bus.events import CandleEvent

logger = logging.getLogger(__name__)


class CandleFeedProducer:
    """
    Periodically fetch candle data and publish to the event bus.

    Args:
        pairs:       List of trading pairs to track
        timeframes:  List of timeframe strings (e.g. ["1m", "5m", "1h"])
        poll_secs:   How often to poll for new candles (default: 60s)
        data_fn:     Callable that returns OHLCV dict — injected for testability
    """

    def __init__(
        self,
        pairs: list[str],
        timeframes: list[str],
        poll_secs: int = 60,
        data_fn=None,
    ) -> None:
        self.pairs = pairs
        self.timeframes = timeframes
        self.poll_secs = poll_secs
        self._data_fn = data_fn or self._fetch_from_freqtrade
        self._running = False

    async def start(self) -> None:
        """Run the candle polling loop. Call stop() to shut down cleanly."""
        self._running = True
        logger.info(
            "CandleFeedProducer starting — pairs=%s timeframes=%s poll=%ds",
            self.pairs, self.timeframes, self.poll_secs,
        )
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.error("CandleFeedProducer tick error: %s", exc)
            await asyncio.sleep(self.poll_secs)

    async def stop(self) -> None:
        self._running = False

    async def _tick(self) -> None:
        bus = get_bus()
        for pair in self.pairs:
            for tf in self.timeframes:
                candle = await asyncio.get_event_loop().run_in_executor(
                    None, self._data_fn, pair, tf
                )
                if candle:
                    await bus.publish(
                        CandleEvent(
                            source="candle_feed",
                            pair=pair,
                            timeframe=tf,
                            open=candle.get("open", 0.0),
                            high=candle.get("high", 0.0),
                            low=candle.get("low", 0.0),
                            close=candle.get("close", 0.0),
                            volume=candle.get("volume", 0.0),
                            timestamp=datetime.now(UTC),
                        )
                    )

    @staticmethod
    def _fetch_from_freqtrade(pair: str, timeframe: str) -> dict | None:
        """
        Fetch last closed candle from freqtrade data directory.
        Returns None if data is unavailable.
        """
        try:
            import json
            from pathlib import Path
            data_dir = Path(__file__).resolve().parent.parent.parent / "user_data" / "data"
            pair_file = data_dir / "binance" / f"{pair.replace('/', '_')}_{timeframe}.json"
            if not pair_file.exists():
                return None
            with open(pair_file) as f:
                rows = json.load(f)
            if not rows:
                return None
            last = rows[-2]  # -2: last *closed* candle (not current open)
            return {
                "open": last[1], "high": last[2], "low": last[3],
                "close": last[4], "volume": last[5],
            }
        except Exception:
            return None
