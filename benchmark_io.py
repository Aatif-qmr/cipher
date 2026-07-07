import asyncio
import json
import time
import os

class Msg:
    def __init__(self):
        self.data = b'{"cvd": 123.45, "volume": 9876.5}'

path = "test_benchmark.json"

async def handle_sync(msg):
    data = json.loads(msg.data.decode())
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def _write_sync(msg_data, p):
    data = json.loads(msg_data.decode())
    with open(p, "w") as f:
        json.dump(data, f, indent=2)

async def handle_thread(msg):
    await asyncio.to_thread(_write_sync, msg.data, path)

async def measure_event_loop_lag(func, msg, n=1000):
    # We want to measure the maximum lag of the event loop
    max_lag = 0
    running = True

    async def monitor():
        nonlocal max_lag
        while running:
            start = time.perf_counter()
            await asyncio.sleep(0.001)
            lag = time.perf_counter() - start - 0.001
            if lag > max_lag:
                max_lag = lag

    monitor_task = asyncio.create_task(monitor())

    start_time = time.perf_counter()
    # Create tasks
    tasks = [asyncio.create_task(func(msg)) for _ in range(n)]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start_time

    running = False
    await monitor_task

    return total_time, max_lag

async def main():
    msg = Msg()
    print("Running Sync Benchmark...")
    sync_total, sync_lag = await measure_event_loop_lag(handle_sync, msg, 2000)
    print(f"Sync - Total time: {sync_total:.4f}s, Max Event Loop Lag: {sync_lag:.4f}s")

    print("Running Thread Benchmark...")
    thread_total, thread_lag = await measure_event_loop_lag(handle_thread, msg, 2000)
    print(f"Thread - Total time: {thread_total:.4f}s, Max Event Loop Lag: {thread_lag:.4f}s")

    if os.path.exists(path):
        os.remove(path)

if __name__ == "__main__":
    asyncio.run(main())
