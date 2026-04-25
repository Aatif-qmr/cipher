#!/bin/bash
# Masterbot Weekly Hyperopt Automation

BASE_DIR="/Users/azmatsaif/masterbot"
LOG="$BASE_DIR/logs/hyperopt_log.txt"
mkdir -p "$BASE_DIR/logs"

echo "[$(date)] === Weekly Hyperopt Started ===" >> "$LOG"

# 1. Setup
set -a
source "$BASE_DIR/.env"
set +a
source "$BASE_DIR/venv/bin/activate"
cd "$BASE_DIR"

# 2. Data Download
freqtrade download-data --config config/config_paper.json --pairs BTC/USDT ETH/USDT --timeframes 1h 4h --days 7 --datadir data/
echo "[$(date)] Data download complete" >> "$LOG"

# 3. Hyperopt MeanReversionV1 (10 epochs for smoke test, will change to 200)
freqtrade hyperopt --strategy MeanReversionV1 --strategy-path strategies/active/ --config config/config_paper.json --hyperopt-loss SharpeHyperOptLoss --spaces buy sell stoploss roi --epochs 200 --timerange 20240101-20260101 --datadir data/ -j -1 2>> "$LOG"
MEAN_EXIT=$?
echo "[$(date)] MeanReversion Hyperopt exit: $MEAN_EXIT" >> "$LOG"

# 4. Hyperopt TrendFollowV1
freqtrade hyperopt --strategy TrendFollowV1 --strategy-path strategies/active/ --config config/config_paper.json --hyperopt-loss SharpeHyperOptLoss --spaces buy sell stoploss roi --epochs 200 --timerange 20240101-20260101 --datadir data/ -j -1 2>> "$LOG"
TREND_EXIT=$?
echo "[$(date)] TrendFollow Hyperopt exit: $TREND_EXIT" >> "$LOG"

# 5. Parse
python "$BASE_DIR/automation/parse_hyperopt.py"
PARSE_EXIT=$?
echo "[$(date)] Parse complete: $PARSE_EXIT" >> "$LOG"

# 6. Telegram Report
SUMMARY=$(python3 -c "
import json
try:
    with open('$BASE_DIR/logs/hyperopt_summary.json') as f:
        s = json.load(f)
    m = s['MeanReversionV1']
    t = s['TrendFollowV1']
    print(f'''📊 Weekly Hyperopt Report
Date: {s['date']}

MeanReversionV1:
Decision: {m['decision']}
Sharpe: {m.get('old_sharpe','N/A')} → {m.get('new_sharpe','N/A')}
Improvement: {m.get('improvement_pct','N/A')}%

TrendFollowV1:
Decision: {t['decision']}
Sharpe: {t.get('old_sharpe','N/A')} → {t.get('new_sharpe','N/A')}
Improvement: {t.get('improvement_pct','N/A')}%

Review candidates in strategies/candidates/''')
except Exception as e:
    print(f'Error generating summary: {e}')
")

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" -d chat_id="${TELEGRAM_CHAT_ID}" -d text="$SUMMARY"

echo "[$(date)] === Weekly Hyperopt Complete ===" >> "$LOG"
deactivate
