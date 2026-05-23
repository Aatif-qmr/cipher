import os
import sqlite3
import json
import requests
import subprocess
import pandas as pd
from datetime import datetime, timedelta, timezone
from mistralai.client import Mistral
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration
DB_FILES = [
    '/Users/aatifquamre/masterbot/user_data/micro.sqlite',
    '/Users/aatifquamre/masterbot/user_data/scalp.sqlite',
    '/Users/aatifquamre/masterbot/user_data/mean_reversion.sqlite',
    '/Users/aatifquamre/masterbot/user_data/trend_follow.sqlite',
    '/Users/aatifquamre/masterbot/user_data/daily.sqlite',
    '/Users/aatifquamre/masterbot/user_data/swing.sqlite'
]
SENTIMENT_PATH = '/Users/aatifquamre/masterbot/sentiment/scores/history.csv'
REPORTS_FOLDER_ID = '1Vdst3YI9wFFfFPurpVVGJfrA3y2aT9BI'
DEST_EMAIL = 'aatifqmr@gmail.com'

# API Keys from env
from dotenv import load_dotenv
load_dotenv('/Users/aatifquamre/masterbot/.env')

MISTRAL_API_KEY = "buk3FCIeMTkBXiweHG6xuRmcQ0VeeczB"
# MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
TELEGRAM_TOKEN = os.getenv('QNT_TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('QNT_TELEGRAM_CHAT_ID')

def gather_data():
    """Gathers all relevant data from MasterBot databases and sentiment files."""
    total_trades = 0
    total_profit_abs = 0.0
    open_trades_list = []
    closed_trades_list = []
    by_strategy = {}
    
    for db_path in DB_FILES:
        if not os.path.exists(db_path): continue
            
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
            if not cursor.fetchone():
                conn.close()
                continue

            # Open trades
            cursor.execute("SELECT pair, strategy, open_date FROM trades WHERE is_open = 1")
            for row in cursor.fetchall():
                open_trades_list.append(f"{row['pair']} ({row['strategy']})")

            # Closed trades summary
            cursor.execute("SELECT COUNT(*), SUM(close_profit_abs) FROM trades WHERE is_open = 0")
            count, profit_abs = cursor.fetchone()
            if count:
                total_trades += count
                total_profit_abs += (profit_abs if profit_abs else 0.0)
            
            # Strategy Breakdown
            cursor.execute("SELECT strategy, COUNT(*) as count, SUM(close_profit_abs) as profit FROM trades WHERE is_open = 0 GROUP BY strategy")
            for row in cursor.fetchall():
                s = row['strategy']
                if s not in by_strategy: by_strategy[s] = {"trades": 0, "profit": 0.0}
                by_strategy[s]["trades"] += row['count']
                by_strategy[s]["profit"] += row['profit']

            conn.close()
        except Exception as e:
            print(f"Error reading {db_path}: {e}")

    # Sentiment
    sentiment_data = "N/A"
    if os.path.exists(SENTIMENT_PATH):
        try:
            df = pd.read_csv(SENTIMENT_PATH)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            last_week = df[df['timestamp'] >= (datetime.now() - timedelta(days=7))]
            if not last_week.empty:
                avg = last_week['score'].mean()
                sentiment_data = f"{avg:.3f} ({'BULLISH' if avg > 0.3 else 'BEARISH' if avg < -0.3 else 'NEUTRAL'})"
        except: pass

    return {
        "summary": {
            "total_trades": total_trades,
            "total_profit": f"{total_profit_abs:.2f} USDT",
            "open_trades_count": len(open_trades_list),
            "by_strategy": by_strategy
        },
        "market_sentiment": sentiment_data,
        "timestamp": datetime.now().isoformat()
    }

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def analyze_with_mistral(data):
    """Uses Mistral Free Tier API to analyze the data."""
    if not MISTRAL_API_KEY:
        return "Intelligence module deactivated (No API Key)."

    client = Mistral(api_key=MISTRAL_API_KEY, server_url="https://codestral.mistral.ai")
    
    prompt = f"""
    Act as the MasterBot Intelligence Layer. Analyze the following trading performance and sentiment data.
    
    Data:
    {json.dumps(data, indent=2)}
    
    Tasks:
    1. Identify the most profitable strategy.
    2. Suggest whether to increase or decrease risk based on sentiment.
    3. Provide a 'MasterBot Directives' section with 3 concise bullet points.
    
    Format: Markdown. Tone: Senior Quant.
    """
    
    chat_response = client.chat.complete(
        model="codestral-latest",
        messages=[{"role": "user", "content": prompt}]
    )
    return chat_response.choices[0].message.content

def notify(analysis, data):
    """Generates the Google Doc and sends Telegram notification."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"MasterBot Intelligence Report - {date_str}"
    
    # 1. Google Doc via qnt CLI
    report_content = f"# {title}\n\nGenerated at: {data['timestamp']}\n\n## Analysis\n{analysis}\n\n## Raw Stats Summary\n{json.dumps(data['summary'], indent=2)}"
    doc_prompt = f"Create a Google Doc in folder '{REPORTS_FOLDER_ID}' with title '{title}' and this content: {report_content}. Then email a link to this doc to {DEST_EMAIL}."
    
    print("Syncing with Google Workspace...")
    try:
        subprocess.run(['qnt', '-p', doc_prompt], check=True)
    except:
        print("Google Workspace sync failed. Proceeding with Telegram.")

    # 2. Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        short_analysis = analysis[:3500] # Telegram limit is 4096
        msg = f"🧠 *MasterBot Intelligence Brief - {date_str}*\n\n{short_analysis}\n\n_Full report synced to MasterBot_Vault_"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'})

if __name__ == "__main__":
    print("MasterBot Intelligent Reporter starting...")
    data = gather_data()
    print("Data gathered. Requesting intelligence from Mistral...")
    analysis = analyze_with_mistral(data)
    print("Analysis complete. Dispatching notifications...")
    notify(analysis, data)
    print("Done.")
