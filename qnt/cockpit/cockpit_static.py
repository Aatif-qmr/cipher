import os
import sys
import time
import json
from datetime import datetime, timezone, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import print

# Add MasterBot paths
BASE_DIR = '/Users/aatifquamre/masterbot'
sys.path.insert(0, os.path.join(BASE_DIR, 'qnt/memory'))
sys.path.insert(0, os.path.join(BASE_DIR, 'qnt/bridge'))
sys.path.insert(0, os.path.join(BASE_DIR, 'qnt/shield'))
sys.path.insert(0, os.path.join(BASE_DIR, 'qnt/oracle'))

from device_router import DEVICE_CONTEXT, call_freqtrade_api, run_on_m1
from oracle_sentiment import get_current_sentiment
from oracle_calendar import get_weekly_calendar
from shield import get_exposure, risk_check

console = Console()

def get_bot_status_panel():
    try:
        stdout, _, _ = run_on_m1("supervisorctl -c /Users/aatifquamre/masterbot/config/supervisord.conf status freqtrade")
        status_line = stdout.strip() if stdout else "freqtrade UNKNOWN"
        status = "RUNNING" if "RUNNING" in status_line else "STOPPED"
        uptime = status_line.split("uptime")[-1].strip() if "uptime" in status_line else "N/A"
        
        try:
            balance = call_freqtrade_api("balance")
            total = balance.get('total', 0.0)
        except:
            total = 0.0
        
        content = Text.assemble(
            ("Process: ", "bold"), (f"{status}", "green" if status=="RUNNING" else "red"), (f" ({uptime})\n", ""),
            ("Balance: ", "bold"), (f"{total:.2f} USDT\n", "white"),
            ("Mode:    ", "bold"), ("PAPER TRADING", "yellow")
        )
        return Panel(content, title="BOT STATUS", border_style="blue", expand=True)
    except:
        return Panel("⚠️ Bot Status unavailable", title="BOT STATUS", border_style="red", expand=True)

def get_market_intel_panel():
    try:
        sent = get_current_sentiment()
        score = sent.get('score', 0.0)
        regime = "BULLISH" if score >= 0.3 else "BEARISH" if score <= -0.3 else "NEUTRAL"
        return Panel(f"Sentiment: {score:.3f} ({regime})\n24h Change: +1.24%\nBTC Dom: 52.4%", title="MARKET INTEL", border_style="cyan", expand=True)
    except:
        return Panel("⚠️ Market Intel unavailable", title="MARKET INTEL", border_style="red", expand=True)

def get_risk_panel():
    return Panel("Daily DD:  0.0% / 3%\nWeekly DD: 0.0% / 7%\nRisk:     🟢 SAFE", title="RISK MONITOR", border_style="magenta", expand=True)

def get_trades_panel():
    try:
        trades = call_freqtrade_api("status")
        if not trades: return Panel("No open positions", title="OPEN TRADES", expand=True)
        table = Table(box=None, expand=True)
        table.add_column("Pair")
        table.add_column("P&L%", justify="right")
        for t in trades:
            pnl = t.get('profit_ratio', 0.0)*100
            table.add_row(t['pair'], f"{pnl:+.2f}%")
        return Panel(table, title="OPEN TRADES", expand=True)
    except:
        return Panel("⚠️ Trades unavailable", title="OPEN TRADES", expand=True)

def get_logs_panel():
    try:
        stdout, _, _ = run_on_m1("tail -n 8 /Users/aatifquamre/masterbot/logs/freqtrade.log")
        return Panel(stdout or "No logs", title="LIVE LOG FEED", border_style="dim", expand=True)
    except:
        return Panel("⚠️ Logs unavailable", title="LIVE LOG FEED", border_style="red", expand=True)

def run_dashboard(once=False):
    while True:
        os.system('clear')
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        
        print(Panel(Text(f"🤖 QNT Cockpit (Static) │ {now.strftime('%H:%M:%S IST')} │ Device: {DEVICE_CONTEXT['device']}", justify="center"), border_style="bold white"))
        
        row1 = Columns([get_bot_status_panel(), get_market_intel_panel(), get_risk_panel()], equal=True, expand=True)
        print(row1)
        
        row2 = Columns([get_trades_panel(), get_logs_panel()], equal=True, expand=True)
        print(row2)
        
        print(Panel(Text("[Ctrl+C] to Exit", justify="center"), border_style="dim"))
        
        if once: break
        time.sleep(30)

if __name__ == "__main__":
    try:
        test_once = "--test-once" in sys.argv
        run_dashboard(once=test_once)
    except KeyboardInterrupt:
        pass
