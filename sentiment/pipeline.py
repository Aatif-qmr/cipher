import os
import json
import time
import requests
from datetime import datetime, timezone

# --- CONFIGURATION ---
BASE_DIR = "/Users/azmatsaif/masterbot"
OUTPUT_PATH = os.path.join(BASE_DIR, "sentiment/scores/current_score.json")
HISTORY_PATH = os.path.join(BASE_DIR, "sentiment/scores/history.csv")

# Weights as per documentation
WEIGHTS = {
    "reddit": 0.36,
    "coingecko": 0.27,
    "feargreed": 0.22,
    "funding": 0.15
}

def get_fear_greed():
    """Fetch Fear & Greed Index (0-100)"""
    try:
        url = "https://api.alternative.me/fng/"
        res = requests.get(url, timeout=10)
        data = res.json()
        val = int(data['data'][0]['value'])
        # Normalize to -1 to 1
        return (val - 50) / 50.0
    except Exception as e:
        print(f"Error fetching Fear & Greed: {e}")
        return 0.0

def get_binance_funding():
    """Fetch average funding rate from Binance Futures"""
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        res = requests.get(url, timeout=10)
        data = res.json()
        # Average top 20 symbols
        rates = [float(item['lastFundingRate']) for item in data[:20]]
        avg_rate = sum(rates) / len(rates)
        # Funding is usually small (e.g. 0.0001). 
        # Normalize: 0.0001 (neutral) -> 0. 0.0003 -> 1. -0.0001 -> -1.
        normalized = (avg_rate - 0.0001) / 0.0002
        return max(-1.0, min(1.0, normalized))
    except Exception as e:
        print(f"Error fetching Binance Funding: {e}")
        return 0.0

def get_coingecko_sentiment():
    """Heuristic from Coingecko Trending"""
    try:
        # We'll look at the number of 'positive' vs 'negative' coins in top trending if possible,
        # but the trending API is limited. We'll use a simpler proxy: 24h volume change of BTC/ETH.
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=10)
        data = res.json()
        btc_change = data['bitcoin']['usd_24h_change']
        eth_change = data['ethereum']['usd_24h_change']
        avg_change = (btc_change + eth_change) / 2.0
        # Normalize: 5% change -> 1.0, -5% -> -1.0
        return max(-1.0, min(1.0, avg_change / 5.0))
    except Exception as e:
        print(f"Error fetching Coingecko: {e}")
        return 0.0

def get_reddit_sentiment():
    """Simple sentiment from r/CryptoCurrency hot titles"""
    try:
        url = "https://www.reddit.com/r/CryptoCurrency/hot.json"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        titles = [post['data']['title'].lower() for post in data['data']['children']]
        
        bullish_words = ['bull', 'moon', 'up', 'pump', 'buy', 'long', 'ath', 'profit', 'gain']
        bearish_words = ['bear', 'crash', 'down', 'dump', 'sell', 'short', 'dip', 'loss', 'rekt']
        
        bull_count = sum(1 for t in titles if any(w in t for w in bullish_words))
        bear_count = sum(1 for t in titles if any(w in t for w in bearish_words))
        
        if bull_count + bear_count == 0: return 0.0
        return (bull_count - bear_count) / float(bull_count + bear_count)
    except Exception as e:
        print(f"Error fetching Reddit: {e}")
        return 0.0

def run_pipeline():
    print(f"[{datetime.now()}] Starting Sentiment Pipeline...")
    
    scores = {
        "reddit": get_reddit_sentiment(),
        "coingecko": get_coingecko_sentiment(),
        "feargreed": get_fear_greed(),
        "funding": get_binance_funding()
    }
    
    final_score = sum(scores[s] * WEIGHTS[s] for s in scores)
    
    result = {
        "score": round(final_score, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources_used": list(scores.keys()),
        "component_scores": scores,
        "weights": WEIGHTS
    }
    
    # Ensure dir exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(result, f, indent=2)
        
    # Append to history
    with open(HISTORY_PATH, 'a') as f:
        if os.path.getsize(HISTORY_PATH) == 0:
            f.write("timestamp,score,reddit,coingecko,feargreed,funding\n")
        f.write(f"{result['timestamp']},{result['score']},{scores['reddit']},{scores['coingecko']},{scores['feargreed']},{scores['funding']}\n")
        
    print(f"Pipeline complete. Final Score: {result['score']}")

if __name__ == "__main__":
    run_pipeline()
