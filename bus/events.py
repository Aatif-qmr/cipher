"""
bus/events.py
─────────────
Typed event dataclasses for Cipher's async event bus.

All inter-component communication flows through these types so:
  - Producers and consumers are decoupled (no direct imports)
  - Events are serialisable for replay / debugging
  - Type checkers catch schema mismatches at PR time
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class EventType(StrEnum):
    CANDLE = "candle"
    SIGNAL = "signal"
    TRADE_OPEN = "trade_open"
    TRADE_CLOSE = "trade_close"
    RISK_ALERT = "risk_alert"
    SENTIMENT_UPDATE = "sentiment_update"
    MACRO_UPDATE = "macro_update"
    HYPEROPT_RESULT = "hyperopt_result"
    SYSTEM_HEALTH = "system_health"


@dataclass
class BaseEvent:
    type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = ""


@dataclass
class CandleEvent(BaseEvent):
    """New OHLCV candle available from exchange."""
    pair: str = ""
    timeframe: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    type: EventType = EventType.CANDLE


@dataclass
class SignalEvent(BaseEvent):
    """Strategy generated an entry or exit signal."""
    strategy: str = ""
    pair: str = ""
    direction: str = ""       # "long" | "short" | "exit"
    confidence: float = 0.0   # 0.0–1.0, from do_predict or rust_signal strength
    tag: str = ""
    type: EventType = EventType.SIGNAL


@dataclass
class TradeEvent(BaseEvent):
    """Trade opened or closed."""
    trade_id: int = 0
    strategy: str = ""
    pair: str = ""
    profit_ratio: float = 0.0
    profit_abs: float = 0.0
    type: EventType = EventType.TRADE_OPEN


@dataclass
class RiskAlertEvent(BaseEvent):
    """Risk gate triggered."""
    gate: str = ""            # e.g. "max_drawdown", "correlation", "position_size"
    value: float = 0.0
    threshold: float = 0.0
    action: str = ""          # "warn" | "halt"
    type: EventType = EventType.RISK_ALERT


@dataclass
class SentimentEvent(BaseEvent):
    """Sentiment pipeline completed a refresh cycle."""
    score: float = 0.0        # composite [-1, +1]
    components: dict = field(default_factory=dict)
    type: EventType = EventType.SENTIMENT_UPDATE


@dataclass
class MacroEvent(BaseEvent):
    """Macro covariate snapshot refreshed."""
    dxy_24h_change: float = 0.0
    btc_funding_rate: float = 0.0
    btc_open_interest: float = 0.0
    type: EventType = EventType.MACRO_UPDATE


@dataclass
class HyperoptResultEvent(BaseEvent):
    """Distributed hyperopt study completed."""
    strategy: str = ""
    best_params: dict = field(default_factory=dict)
    best_value: float = 0.0
    n_trials: int = 0
    type: EventType = EventType.HYPEROPT_RESULT


@dataclass
class SystemHealthEvent(BaseEvent):
    """Periodic system heartbeat."""
    freqtrade_processes: int = 0
    open_trades: int = 0
    balance_usdt: float = 0.0
    type: EventType = EventType.SYSTEM_HEALTH


# Union type for type checkers
Event = (
    CandleEvent
    | SignalEvent
    | TradeEvent
    | RiskAlertEvent
    | SentimentEvent
    | MacroEvent
    | HyperoptResultEvent
    | SystemHealthEvent
)
