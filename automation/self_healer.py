import os
import subprocess
import time
import glob
from pathlib import Path

# --- CONFIGURATION ---
LOG_DIR = "/Users/aatifquamre/masterbot/logs"
QNT_BIN = "/Users/aatifquamre/.nvm/versions/node/v20.20.2/bin/qnt"
WORKSPACE = "/Users/aatifquamre/masterbot"
ERROR_KEYWORDS = ["Traceback", "ERROR", "CRITICAL", "NameError", "ValueError", "TypeError"]

def get_error_context():
    """Scans all log files and returns a summary of recent errors."""
    error_summary = []
    
    # Scan all log files
    log_files = glob.glob(os.path.join(LOG_DIR, "*.log*"))
    
    for log_path in log_files:
        try:
            with open(log_path, 'r') as f:
                # Read last 50 lines to catch recent issues
                lines = f.readlines()[-50:]
                content = "".join(lines)
                
                # Check for keywords
                if any(keyword in content for keyword in ERROR_KEYWORDS):
                    error_summary.append(f"--- FILE: {os.path.basename(log_path)} ---\n{content}")
        except Exception:
            continue
            
    return "\n\n".join(error_summary)

def run_self_healing():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting self-healing scan...")
    
    context = get_error_context()
    
    if not context:
        print("✅ No errors found in logs. System healthy.")
        return

    print("⚠️ Errors detected! Invoking QNT CLI to fix...")
    
    # Construct the prompt for QNT CLI
    healing_prompt = f"""
I am the MasterBot Self-Healer. I have detected the following errors in the system logs.
Your task:
1. Analyze the errors below.
2. Identify the source files causing these issues.
3. Apply targeted, surgical fixes to resolve them.
4. Verify the fix by checking if the project still compiles or by running a relevant check.

ERRORS FROM LOGS:
{context}

Proceed in YOLO mode to apply the fixes immediately.
"""

    try:
        # Invoke QNT in headless YOLO mode
        # -p: prompt, -y: automatically accept actions, --skip-trust: avoid interactive prompts
        cmd = [
            QNT_BIN, 
            "-p", healing_prompt, 
            "-y", 
            "--skip-trust",
            "--approval-mode", "yolo"
        ]
        
        # Run and wait for it to finish
        result = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True)
        
        # Log the healer's output
        with open(os.path.join(LOG_DIR, "self_healer_run.log"), "a") as f:
            f.write(f"\n\n=== RUN AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\nERRORS:\n" + result.stderr)
                
        print("✅ Healing session complete. Results logged to logs/self_healer_run.log")
        
    except Exception as e:
        print(f"❌ Failed to invoke QNT CLI: {e}")

if __name__ == "__main__":
    run_self_healing()
