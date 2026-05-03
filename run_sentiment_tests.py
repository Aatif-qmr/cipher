import json
import os
import subprocess
import time

PATH = 'sentiment/scores/current_score.json'

def set_score(score):
    with open(PATH, 'r') as f:
        data = json.load(f)
    data['score'] = score
    data['timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(PATH, 'w') as f:
        json.dump(data, f)

def run_test(name, strategy):
    print(f"\n--- Running {name} for {strategy} ---")
    timeframe = '1h' if 'Mean' in strategy else '4h'
    cmd = [
        "./venv/bin/freqtrade", "backtesting",
        "--strategy", strategy,
        "--strategy-path", "strategies/candidates/",
        "--config", "config/config_paper.json",
        "--timerange", "20230601-20230602",
        "--timeframe", timeframe,
        "--datadir", "data"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Print the log output containing our sentiment messages
    print(result.stdout)
    if "[Sentiment BLOCK]" in result.stdout or "[Sentiment]" in result.stdout:
        print("✅ Log Found")
    else:
        print("❌ Log Not Found")

# Ensure dummy exists
os.makedirs('sentiment/scores', exist_ok=True)
if not os.path.exists(PATH):
    with open(PATH, 'w') as f:
        json.dump({"score": 0.0, "timestamp": "", "sources_used": ["test"], "warning": None}, f)

# 1. Bearish Block Test
set_score(-0.8)
run_test("Bearish Block", "MeanReversionV1")

# 2. Neutral Block Test
set_score(0.1)
run_test("Neutral Block", "TrendFollowV1")

# 3. Normal Operation
set_score(-0.0944)
run_test("Neutral Allow", "MeanReversionV1")
