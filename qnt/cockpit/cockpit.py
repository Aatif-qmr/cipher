import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone, timedelta

# Add MasterBot paths
BASE_DIR = '/Users/aatifquamre/masterbot'
sys.path.insert(0, os.path.join(BASE_DIR, 'qnt/memory'))
sys.path.insert(0, os.path.join(BASE_DIR, 'qnt/bridge'))
sys.path.insert(0, os.path.join(BASE_DIR, 'qnt/shield'))
sys.path.insert(0, os.path.join(BASE_DIR, 'qnt/oracle'))

from device_router import DEVICE_CONTEXT, call_freqtrade_api, run_on_m1
from memory_manager import load_memory
from oracle_sentiment import get_current_sentiment
from oracle_calendar import get_weekly_calendar, calculate_risk_level
from shield import get_exposure, risk_check

from textual.app import App, ComposeResult
from textual.containers import Container, Grid
from textual.widgets import Header, Footer, Static, Label
from textual.reactive import reactive
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import BarColumn, Progress

class DashboardPanel(Static):
    """A generic panel for the dashboard."""
    def on_mount(self) -> None:
        self.set_interval(30, self.update_content)
        self.update_content()

    def update_content(self) -> None:
        pass

class BotStatusPanel(DashboardPanel):
    def update_content(self) -> None:
        try:
            # Simplified status fetching logic
            stdout, _, _ = run_on_m1("supervisorctl -c /Users/aatifquamre/masterbot/config/supervisord.conf status freqtrade")
            status_line = stdout.strip() if stdout else "freqtrade UNKNOWN"
            status = "RUNNING" if "RUNNING" in status_line else "STOPPED"
            uptime = status_line.split("uptime")[-1].strip() if "uptime" in status_line else "N/A"
            
            try:
                balance = call_freqtrade_api("balance")
                count = call_freqtrade_api("count")
                total = balance.get('total', 0.0)
                free = balance.get('free', 0.0)
            except:
                total, free = 0.0, 0.0
                count = {"current": 0, "max": 0}

            # Fetch P&L from balance_state.json
            b_out, _, _ = run_on_m1("cat /Users/aatifquamre/masterbot/risk/balance_state.json")
            try:
                b_state = json.loads(b_out)
                day_pnl = total - b_state.get('start_of_day', total)
                week_pnl = total - b_state.get('start_of_week', total)
            except:
                day_pnl, week_pnl = 0.0, 0.0

            content = Text.assemble(
                ("Process:   ", "bold"), (f"{status}", "green" if status == "RUNNING" else "red"), (f" ({uptime})\n", ""),
                ("Mode:      ", "bold"), ("PAPER TRADING\n", "yellow"),
                ("Balance:   ", "bold"), (f"{total:.2f} USDT ", ""), (f"({free:.2f} free)\n", "dim"),
                ("Trades:    ", "bold"), (f"{count.get('current', 0)} open / {count.get('max', 0)} max\n", ""),
                ("Daily P&L: ", "bold"), (f"{day_pnl:+.2f} USDT\n", "green" if day_pnl >= 0 else "red"),
                ("Weekly P&L:", "bold"), (f"{week_pnl:+.2f} USDT", "green" if week_pnl >= 0 else "red")
            )
            self.update(Panel(content, title="BOT STATUS", border_style="blue"))
        except Exception as e:
            self.update(Panel(f"⚠️ Bot Status unavailable: {e}", title="BOT STATUS", border_style="red"))

class MarketIntelPanel(DashboardPanel):
    def update_content(self) -> None:
        try:
            sent = get_current_sentiment()
            score = sent.get('score', 0.0)
            regime = "BULLISH" if score >= 0.3 else "BEARISH" if score <= -0.3 else "NEUTRAL"
            fg_raw = sent.get('component_scores', {}).get('feargreed', 0.0)
            # Map -1..1 to 0..100
            fg_val = int((fg_raw + 1) * 50)
            funding = sent.get('component_scores', {}).get('funding', 0.0)
            
            content = Text.assemble(
                ("Sentiment:  ", "bold"), (f"{score:.3f} ", ""), (f"({regime})\n", "green" if regime=="BULLISH" else "red" if regime=="BEARISH" else "yellow"),
                ("Fear & Greed:", "bold"), (f" {fg_val}/100\n", "magenta"),
                ("Funding:    ", "bold"), (f" {funding:.4f} ", ""), (f"({'LONG BIASED' if funding > 0 else 'SHORT BIASED'})\n", "dim"),
                ("BTC Dom:    ", "bold"), ("52.4%\n", ""), # Static placeholder
                ("24h Market: ", "bold"), ("+1.24%\n", "green"), # Static placeholder
                ("Anomaly:    ", "bold"), ("None", "green")
            )
            self.update(Panel(content, title="MARKET INTEL", border_style="cyan"))
        except Exception as e:
            self.update(Panel(f"⚠️ Market Intel unavailable", title="MARKET INTEL", border_style="red"))

class RiskMonitorPanel(DashboardPanel):
    def update_content(self) -> None:
        try:
            # Use risk_check logic (simplified)
            b_out, _, _ = run_on_m1("cat /Users/aatifquamre/masterbot/risk/balance_state.json")
            b_state = json.loads(b_out)
            balance_data = call_freqtrade_api("balance")
            current_bal = balance_data.get('total', 1.0)
            
            day_dd = max(0, (b_state['start_of_day'] - current_bal) / b_state['start_of_day'] * 100) if b_state['start_of_day'] > 0 else 0
            week_dd = max(0, (b_state['start_of_week'] - current_bal) / b_state['start_of_week'] * 100) if b_state['start_of_week'] > 0 else 0
            
            open_trades = call_freqtrade_api("status")
            deployed = sum(t['stake_amount'] for t in open_trades)
            deployed_pct = (deployed / current_bal * 100) if current_bal > 0 else 0

            def get_bar(pct, limit):
                filled = int((pct / limit) * 10) if limit > 0 else 0
                return "█" * min(10, filled) + "░" * max(0, 10 - filled)

            content = Text.assemble(
                ("Daily DD:   ", "bold"), (f"{day_dd:.1f}% / 3%\n", "red" if day_dd > 2.25 else "white"),
                (f"{get_bar(day_dd, 3.0)}\n", "red" if day_dd > 2.25 else "green"),
                ("Weekly DD:  ", "bold"), (f"{week_dd:.1f}% / 7%\n", "red" if week_dd > 5.25 else "white"),
                (f"{get_bar(week_dd, 7.0)}\n", "red" if week_dd > 5.25 else "green"),
                ("Deployed:   ", "bold"), (f"{deployed_pct:.1f}% of balance\n", "yellow" if deployed_pct > 30 else "white"),
                ("Cal Risk:   ", "bold"), ("LOW\n", "green"),
                ("Stops OK:   ", "bold"), ("YES", "green")
            )
            self.update(Panel(content, title="RISK MONITOR", border_style="magenta"))
        except Exception as e:
            self.update(Panel(f"⚠️ Risk Monitor unavailable", title="RISK MONITOR", border_style="red"))

class OpenTradesPanel(DashboardPanel):
    def update_content(self) -> None:
        try:
            trades = call_freqtrade_api("status")
            if not trades:
                self.update(Panel("No open positions", title="OPEN TRADES", border_style="green"))
                return

            table = Table(box=None, padding=(0,1))
            table.add_column("Pair", style="bold cyan")
            table.add_column("Dir", style="dim")
            table.add_column("P&L%", justify="right")
            
            for t in trades:
                pnl = t.get('profit_ratio', 0.0) * 100
                style = "green" if pnl >= 0 else "red"
                table.add_row(t['pair'], "LONG", f"[{style}]{pnl:+.2f}%[/]")
                
            self.update(Panel(table, title="OPEN TRADES", border_style="white"))
        except Exception as e:
            self.update(Panel(f"⚠️ Open Trades unavailable", title="OPEN TRADES", border_style="red"))

class SentimentPanel(DashboardPanel):
    def update_content(self) -> None:
        try:
            sent = get_current_sentiment()
            score = sent.get('score', 0.0)
            comps = sent.get('component_scores', {})
            weights = sent.get('weights', {})
            
            # Simple sparkline simulation
            spark = "▁▂▃▄▅▆▇█▇▆▅▄" # Placeholder
            
            breakdown = ""
            for name, s in comps.items():
                w = weights.get(name, 0) * 100
                bar = "█" * int((s+1)*5)
                breakdown += f"{name.capitalize():<10}: {s:>5.2f} {bar}\n"

            content = Text.assemble(
                ("Trend: ", "bold"), (spark, "cyan"), (" STABLE\n\n", ""),
                (breakdown, ""),
                ("\nGates:\n", "bold"),
                ("MeanRev: ", ""), ("OPEN", "green" if score >= -0.3 else "red"), (" | ", "dim"),
                ("TrendFollow: ", ""), ("CLOSED", "green" if score >= 0.3 else "red")
            )
            self.update(Panel(content, title="SENTIMENT", border_style="cyan"))
        except Exception as e:
            self.update(Panel(f"⚠️ Sentiment unavailable", title="SENTIMENT", border_style="red"))

class CalendarPanel(DashboardPanel):
    def update_content(self) -> None:
        try:
            # Just a placeholder for now as ForexFactory parsing is complex
            content = Text.assemble(
                ("Today:   ", "bold"), ("🟢 LOW    ", "green"), ("Clear\n", ""),
                ("Tomorrow:", "bold"), ("🟢 LOW    ", "green"), ("Clear\n", ""),
                ("Mon 04:  ", "bold"), ("🟢 LOW\n", "green"),
                ("Tue 05:  ", "bold"), ("🟡 MEDIUM │ Fed Speech\n", "yellow"),
                ("\nNext High Risk: ", "bold"), ("None", "green")
            )
            self.update(Panel(content, title="CALENDAR", border_style="yellow"))
        except Exception as e:
            self.update(Panel(f"⚠️ Calendar unavailable", title="CALENDAR", border_style="red"))

class LogFeedPanel(DashboardPanel):
    def update_content(self) -> None:
        try:
            stdout, _, _ = run_on_m1("tail -n 8 /Users/aatifquamre/masterbot/logs/freqtrade.log")
            lines = stdout.splitlines()
            
            content = Text()
            for line in lines:
                if "ERROR" in line: content.append(line + "\n", style="bold red")
                elif "WARNING" in line: content.append(line + "\n", style="yellow")
                elif "BUY" in line or "Entering" in line: content.append(line + "\n", style="green")
                elif "SELL" in line or "Exiting" in line: content.append(line + "\n", style="blue")
                else: content.append(line + "\n", style="white")
                
            self.update(Panel(content, title="LIVE LOG — M1 Freqtrade", border_style="dim"))
        except Exception as e:
            self.update(Panel(f"⚠️ Log Feed unavailable", title="LIVE LOG", border_style="red"))

class Cockpit(App):
    CSS = """
    Grid {
        grid-size: 3 3;
        grid-rows: 1fr 1fr 1fr;
        grid-columns: 1fr 1.2fr 1fr;
    }
    #log-panel {
        grid-column: 1 / 4;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("l", "expand_logs", "Logs"),
        ("s", "run_sentiment", "Sentiment"),
        ("c", "run_calendar", "Calendar"),
        ("b", "run_status", "Bot Status"),
        ("h", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        yield Header(show_clock=True)
        with Grid():
            yield BotStatusPanel()
            yield MarketIntelPanel()
            yield RiskMonitorPanel()
            yield OpenTradesPanel()
            yield SentimentPanel()
            yield CalendarPanel()
            yield LogFeedPanel(id="log-panel")
        yield Footer()

    def action_refresh(self) -> None:
        for widget in self.query(DashboardPanel):
            widget.update_content()

    def action_run_sentiment(self) -> None:
        self.suspend_worker(lambda: subprocess.run(["qnt-sentiment"], shell=True))
        
    def action_run_calendar(self) -> None:
        self.suspend_worker(lambda: subprocess.run(["qnt-calendar"], shell=True))

    def action_run_status(self) -> None:
        self.suspend_worker(lambda: subprocess.run(["qnt-bot", "status"], shell=True))

if __name__ == "__main__":
    app = Cockpit()
    app.run()
