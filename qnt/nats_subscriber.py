import asyncio
import json
import os
import sys
import nats
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
# Script is at masterbot/qnt/nats_subscriber.py
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load .env from project root
load_dotenv(BASE_DIR / '.env')

NATS_URL = os.getenv('NATS_URL')
SCORES_PATH = BASE_DIR / 'sentiment/scores/current_score.json'
MACRO_PATH = BASE_DIR / 'risk/macro_state.json'
REGIME_PATH = BASE_DIR / 'qnt/oracle/current_regime.json'
ORDERFLOW_PATH = BASE_DIR / 'qnt/oracle/order_flow_live.json'

async def handle_sentiment(msg):
    """Instantly write new sentiment to disk."""
    data = json.loads(msg.data.decode())
    with open(SCORES_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[NATS] Sentiment updated: {data.get('score', '?'):.3f}")

async def handle_macro(msg):
    """Instantly write macro state to disk."""
    data = json.loads(msg.data.decode())
    with open(MACRO_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[NATS] Macro updated: DXY={data.get('dxy_24h_change','?')}")

async def handle_regime(msg):
    """Instantly write HMM regime to disk."""
    data = json.loads(msg.data.decode())
    # Save as simple JSON
    with open(REGIME_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[NATS] Regime updated: {data.get('regime','?')}")

async def handle_orderflow_live(msg):
    """Instantly update live order flow (CVD) data."""
    data = json.loads(msg.data.decode())
    with open(ORDERFLOW_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    # Silent for high-frequency updates

async def handle_anomaly(msg):
    """Forward anomaly alerts immediately."""
    data = json.loads(msg.data.decode())
    print(f"[NATS] ANOMALY: {data.get('type','?')}")
    try:
        sys.path.insert(0, str(BASE_DIR / 'qnt/memory'))
        from qnt_notifier import send_notify
        send_notify(f"Anomaly: {data.get('type','')}", data.get('description',''), 'WARN')
    except Exception as e:
        print(f"Notification error: {e}")

async def subscribe_all():
    """Subscribe to all M2 intelligence subjects."""
    if not NATS_URL:
        print("Error: NATS_URL not found in environment.")
        return

    from nats_subjects import SUBJECTS
    
    print(f"Connecting to NATS at {NATS_URL}...")
    nc = await nats.connect(servers=[NATS_URL])
    js = nc.jetstream()

    # Create durable subscriptions
    subscriptions = [
        (SUBJECTS['SENTIMENT'], handle_sentiment, 'm1_sentiment'),
        (SUBJECTS['MACRO'], handle_macro, 'm1_macro'),
        (SUBJECTS['HMM'], handle_regime, 'm1_regime'),
        (SUBJECTS['ANOMALY'], handle_anomaly, 'm1_anomaly'),
        (SUBJECTS['ORDERFLOW_LIVE'], handle_orderflow_live, 'm1_orderflow_live')
    ]

    for subject, callback, durable in subscriptions:
        try:
            await js.subscribe(
                subject,
                cb=callback,
                durable=durable,
                stream='qnt'
            )
            print(f"[NATS] Subscribed to {subject}")
        except Exception as e:
            print(f"[NATS] Subscription error for {subject}: {e}")

    print("[NATS] Waiting for real-time updates...")

    # Keep running forever
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(subscribe_all())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}")
