import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

key = os.getenv('BINANCE_API_KEY')
secret = os.getenv('BINANCE_SECRET')

print(f"Key found: {'Yes' if key else 'No'}")
print(f"Secret found: {'Yes' if secret else 'No'}")

if key and secret:
    exchange = ccxt.binance({
        'apiKey': key.strip(),
        'secret': secret.strip(),
        'enableRateLimit': True,
    })
    try:
        balance = exchange.fetch_balance()
        print(f"✅ Success: Connected to Binance.")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ Error: Missing API Key or Secret in .env")
