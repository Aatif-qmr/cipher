#!/usr/bin/env python3
"""
Real-Time Order Flow Engine (M2)
Streams Binance AggTrades via WebSockets and publishes CVD to NATS.
"""
import asyncio
import json
import os
import sys
import websockets
import nats
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from qnt.nats_subjects import SUBJECTS

# Load environment
load_dotenv(BASE_DIR / ".env")

NATS_URL = os.getenv('NATS_URL', 'nats://localhost:4222')
BINANCE_WS_URL = "wss://fstream.binance.com/ws/btcusdt@aggTrade"

class OrderFlowEngine:
    def __init__(self):
        self.nc = None
        self.js = None
        self.cvd = 0.0
        self.last_publish_time = 0
        self.batch_delta = 0.0
        self.batch_volume = 0.0

    async def connect_nats(self):
        self.nc = await nats.connect(NATS_URL)
        self.js = self.nc.jetstream()
        print(f"Connected to NATS: {NATS_URL}")

    async def stream_binance(self):
        print(f"Starting Binance WebSocket stream: {BINANCE_WS_URL}")
        async for websocket in websockets.connect(BINANCE_WS_URL):
            try:
                async for message in websocket:
                    data = json.loads(message)
                    
                    # AggTrade format:
                    # "q": quantity, "p": price, "m": is the buyer the market maker?
                    # If "m" is True, it's a SELL (taker sell). If False, it's a BUY (taker buy).
                    quantity = float(data['q'])
                    price = float(data['p'])
                    is_taker_sell = data['m']
                    
                    delta = -quantity if is_taker_sell else quantity
                    self.cvd += delta
                    self.batch_delta += delta
                    self.batch_volume += quantity
                    
                    # Throttle NATS publishing to max 5Hz (every 200ms) to avoid saturating M1
                    now = datetime.now(timezone.utc).timestamp()
                    if now - self.last_publish_time >= 0.2:
                        await self.publish_update()
                        self.last_publish_time = now
                        self.batch_delta = 0.0
                        self.batch_volume = 0.0
                        
            except websockets.ConnectionClosed:
                print("WebSocket connection lost. Reconnecting...")
                continue
            except Exception as e:
                print(f"Stream error: {e}")
                await asyncio.sleep(5)

    async def publish_update(self):
        if not self.js:
            return
            
        payload = {
            "symbol": "BTC/USDT",
            "cvd": self.cvd,
            "delta": self.batch_delta,
            "volume": self.batch_volume,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }
        
        try:
            # We use publish instead of js.publish for ultra-high frequency 
            # to avoid the overhead of acknowledgement wait if not needed.
            # But since we want stability, js.publish with a small timeout is better.
            await self.js.publish(SUBJECTS['ORDERFLOW_LIVE'], json.dumps(payload).encode())
        except Exception as e:
            print(f"NATS publish error: {e}")

async def main():
    engine = OrderFlowEngine()
    await engine.connect_nats()
    await engine.stream_binance()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
