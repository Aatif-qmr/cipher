# Cipher — Autonomous Crypto Trading System

[![CI](https://github.com/aatifqmr/cipher/actions/workflows/ci.yml/badge.svg)](https://github.com/aatifqmr/cipher/actions/workflows/ci.yml)
[![Strategy Tests](https://github.com/aatifqmr/cipher/actions/workflows/strategy_test.yml/badge.svg)](https://github.com/aatifqmr/cipher/actions/workflows/strategy_test.yml)

## Overview

Cipher is a multi-strategy autonomous cryptocurrency trading system built on [Freqtrade](https://www.freqtrade.io/) and [FreqAI](https://www.freqtrade.io/en/stable/freqai/). It combines a Rust-accelerated pattern-matching engine, distributed hyperparameter optimisation, an async event bus, an MCP server for AI agent control, and a real-time sentiment pipeline.

---

## Features

### Core Trading Engine
- **7 Active Strategies** — DailyTrendV1, TrendFollowV1, MeanReversionV1, ScalpV1, MicroScalpV1, SwingV1, VectorVaultV1
- **Multi-timeframe** — 1m, 5m, 15m, 1h, 4h, 1d
- **FreqAI integration** — ML-driven signal via nearest-neighbour vault (Rust engine)
- **Modular indicators** — shared `indicators/` library (RSI, EMA, MACD, BB, macro merge, time features)

### Distributed Hyperopt
- **Ray + Optuna** — Bayesian TPE search with MedianPruner, parallel workers
- **Resumable** — SQLite-backed study survives interrupts (`storage/hyperopt/`)
- **Fitness** — Sharpe × (1 − drawdown_penalty) scoring
- Search spaces defined for all 5 non-FreqAI strategies

### MCP Server (AI Agent Interface)
- FastMCP server on port 9010 (`python -m mcp.server --port 9010`)
- 10 tools: open trades, PnL, sentiment, macro, risk gates, vault recall, system health, hyperopt control
- `mcp/agent_rules.md` — guardrails for AI agents operating on live system

### Async Event Bus
- Typed event dataclasses: Candle, Signal, Trade, RiskAlert, Sentiment, Macro, HyperoptResult
- Publish/subscribe with wildcard, dead-letter queue, replay buffer
- `CandleFeedProducer`, `risk_gate_consumer`, `vault_writer` consumers

### Rust Engine
- `rust_engine/` — PyO3 + rayon parallel Euclidean nearest-neighbour
- Powers VectorVaultV1 pattern matching (`find_all_closest_matches`)
- CI: `cargo clippy -D warnings` + `cargo test --release` on every push

### Intelligence Layer (QNT)
- **Oracle** — macro data, HMM regime detection, order flow, calendar events
- **Vault** — semantic trade lesson storage in Qdrant, post-mortem analysis
- **Memory** — persistent trade history, Telegram webhook, pattern recognition
- **Shield** — circuit breakers, drawdown limits, correlation guards
- **Agent CLI** — `python qnt/agent.py ask "what is the current regime?"`

### Sentiment Pipeline
- FinBERT deep learning sentiment scoring
- Multi-source: Reddit, news, CoinGecko, Fear & Greed, funding rates
- Composite score [-1, +1] injected as strategy feature

### Risk Management
- Kelly criterion, fixed fractional, volatility-adjusted position sizing
- Correlation guard (blocks correlated entries)
- Max drawdown circuit breaker (soft 8%, hard 15%)

---

## Project Structure

```
cipher/
├── strategies/active/    # 7 production Freqtrade strategies
├── indicators/           # Shared indicator library
│   ├── macro_merge.py   # DXY / funding / OI merge (canonical)
│   ├── ta_wrappers.py   # RSI, EMA, MACD, BB (ta-lib + scikit-ta)
│   └── time_features.py # Day-of-week, hour-of-day features
├── bus/                  # Async event bus
│   ├── channel.py       # EventBus singleton (pub/sub/replay/DLQ)
│   ├── events.py        # Typed event dataclasses
│   ├── producers/       # CandleFeedProducer
│   └── consumers/       # signal_handler, risk_gate, vault_writer
├── mcp/                  # MCP server for AI agent control
│   ├── server.py        # FastMCP, port 9010
│   ├── agent_rules.md   # Agent guardrails
│   └── tools/           # trades, strategy, sentiment, hyperopt tools
├── qnt/                  # Intelligence orchestration layer
│   ├── freqai/          # VaultFreqaiModel (nearest-neighbour)
│   ├── hyperopt/        # Ray + Optuna distributed hyperopt
│   ├── oracle/          # Regime detection, macro, order flow
│   ├── vault/           # Qdrant trade lesson store
│   ├── memory/          # Persistent state, Telegram, reports
│   ├── shield/          # Allocator, circuit breakers
│   ├── polars_indicators.py  # Polars-native indicator library
│   └── agent.py         # Pydantic AI agent CLI
├── rust_engine/          # PyO3 + rayon nearest-neighbour engine
├── risk/                 # Risk manager, stake sizer, correlation guard
├── sentiment/            # FinBERT + multi-source sentiment pipeline
├── automation/           # Scheduled tasks, reporting
├── config/               # Per-strategy Freqtrade JSON configs
├── tests/                # pytest suite
├── .github/workflows/    # CI: Rust, ruff, pytest, strategy backtest
├── pyproject.toml        # Dependencies (uv-managed)
├── start_bot.sh          # Start all strategies via supervisor
└── stop_bot.sh           # Graceful shutdown
```

---

## Installation

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — `pip install uv`
- Rust stable — `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- ta-lib C library — `brew install ta-lib` (macOS) / `apt install libta-lib-dev` (Linux)

### Quick Start

```bash
git clone https://github.com/aatifqmr/cipher.git
cd cipher

# Install Python dependencies
uv sync

# Install freqtrade from local submodule
uv pip install -e ./freqtrade

# Build Rust engine
cd rust_engine && cargo build --release && cd ..

# Configure environment
cp .env.example .env
# Edit .env with API keys

# Download historical data
freqtrade download-data \
  --pairs BTC/USDT ETH/USDT \
  --timeframes 1h 4h 1d \
  --days 365 \
  --exchange binance

# Start all strategies
./start_bot.sh
```

---

## Configuration

### Environment Variables (`.env`)

```bash
# Exchange
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Qdrant (vector DB for VaultV1)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Sentiment
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret

# Risk limits
MAX_DRAWDOWN_PCT=8.0
DAILY_LOSS_LIMIT=500
```

### Strategy Configs (`config/`)

Each strategy has a JSON config: `config_scalp.json`, `config_mean.json`, `config_daily.json`, `config_swing.json`, `config_trend.json`, `config_micro.json`, `config_vectorvault.json`.

---

## Usage

### Run strategies

```bash
./start_bot.sh                    # all strategies via supervisor
./stop_bot.sh                     # graceful shutdown

# single strategy
freqtrade trade \
  --config config/config_scalp.json \
  --strategy ScalpV1 \
  --strategy-path strategies/active/
```

### Backtesting

```bash
freqtrade backtesting \
  --strategy ScalpV1 \
  --strategy-path strategies/active/ \
  --timeframe 5m \
  --timerange 20260101-20260601 \
  --datadir user_data/data/binance
```

### Distributed Hyperopt

```bash
# via Python
python -c "
from qnt.hyperopt.distributed import run_study
best = run_study('ScalpV1', n_trials=100, n_workers=4)
print(best)
"

# via MCP agent tool
# cipher_control_hyperopt(action='start', strategy='ScalpV1')
```

### MCP Server (AI agent interface)

```bash
python -m mcp.server --port 9010
# Connect any MCP client to http://localhost:9010/mcp
```

### Agent CLI

```bash
python qnt/agent.py ask "What is the current regime and sentiment?"
python qnt/agent.py pnl daily
python qnt/agent.py shadow status
python qnt/agent.py vault-stats
```

---

## CI/CD

Two pipelines run on every push:

| Workflow | Triggers | Checks |
|---|---|---|
| `ci.yml` | push/PR to `main` | Rust clippy + cargo test, ruff format, ruff lint, pytest |
| `strategy_test.yml` | changes to `strategies/active/` | freqtrade backtest on changed strategies |

---

## Performance Targets

| Metric | Target |
|---|---|
| Win Rate | > 55% |
| Profit Factor | > 1.5 |
| Sharpe Ratio | > 1.0 |
| Max Drawdown | < 10% |
| Expectancy | > $20/trade |

---

## Development

### Adding a new strategy

1. Create `strategies/active/YourStrategyV1.py` — inherit `IStrategy`
2. Import shared indicators: `from indicators.macro_merge import merge_macro_data`
3. Subscribe to bus if needed: `bus.subscribe(EventType.SIGNAL, your_handler)`
4. Run: `freqtrade backtesting --strategy YourStrategyV1`
5. CI will auto-validate on push

### Adding a new indicator

Create `indicators/your_indicator.py`, export from `indicators/__init__.py`. Do not add inline to strategy files.

### Running tests

```bash
uv run pytest                                        # all tests
uv run pytest tests/test_event_bus.py -v             # event bus
uv run pytest tests/test_indicators.py -v            # indicators
uv run pytest risk/test_risk_manager.py -v           # risk
cd rust_engine && cargo test --release               # Rust
```

---

## Security

- Never commit `.env` — contains API keys
- Use read-only exchange keys for dry-run
- Risk gates hard-halt at 15% drawdown
- MCP server bound to localhost by default (`--host 127.0.0.1`)

---

## License

Proprietary. All rights reserved.

## Disclaimer

Trading cryptocurrencies involves substantial risk of loss. This software is provided "as is" without warranty. Past performance does not guarantee future results. Only trade with capital you can afford to lose.

---

**Version**: 3.0.0 | **Updated**: June 2026
