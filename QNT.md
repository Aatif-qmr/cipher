# MasterBot Project Context (QNT Brain)

MasterBot is a sophisticated algorithmic trading platform built on top of the Freqtrade framework. It integrates AI-driven sentiment analysis, regime detection, and advanced risk management to execute high-probability trades.

## Project Architecture

- **Core Engine:** Freqtrade (located in `freqtrade/`)
- **Intelligence Layer:**
  - **Sentiment Analysis (`sentiment/`):** Processes external data sources to gauge market mood.
  - **Regime Detection (`strategies/regime_detector.py`):** Identifies market phases (bull, bear, sideways) to adjust strategy parameters.
- **Risk Management (`risk/`):** Real-time exposure tracking and capital preservation logic.
- **Automation (`automation/`):** Scripts for health checks, backups, and hyperoptimization.
- **QNT Integration (`qnt/`):** A custom Gemini CLI fork integrated directly into the project for research and automation.

## Tech Stack

- **Languages:** Python (Core/Strategies), TypeScript (QNT CLI)
- **Frameworks:** Freqtrade, React (Ink) for CLI, Node.js
- **Data:** SQLite for trades, Parquet for market data
- **APIs:** Binance, Telegram (for RPC)

## Development Workflow

1. **Strategy Development:** New strategies are developed in `strategies/candidates/`.
2. **Backtesting:** Use Freqtrade's backtesting suite to validate performance.
3. **Hyperopt:** Run `automation/weekly_hyperopt.sh` to fine-tune parameters.
4. **Sentiment Testing:** `run_sentiment_tests.py` verifies data pipeline integrity.
5. **Deployment:** `start_bot.sh` launches the system using `supervisord` for process management.

## Key Directories

- `strategies/active/`: Strategies currently deployed or being finalized.
- `sentiment/sources/`: Scrapers and processors for sentiment data.
- `logs/`: System and strategy logs.
- `user_data/`: Freqtrade data (backtest results, plots, etc.)

## Usage Instructions for QNT

When helping with MasterBot:
- Always check `strategies/active/` before suggesting strategy changes.
- Refer to `freqtrade/docs/` for framework-specific questions.
- Use `automation/` scripts for repetitive tasks.
- Prioritize risk management logic in `risk/` for any trade execution modifications.

## Current State (Auto-Generated)

### Active Strategies
- TrendFollowV1.py
- MeanReversionV1.py

### Available Automation
- weekly_hyperopt.sh
- weekly_report.py
- parse_hyperopt.py
- backup.sh
- run_sentiment.sh
- update_qnt_brain.py
- verify_api_permissions.py
- health_check.py
- security_check.sh
