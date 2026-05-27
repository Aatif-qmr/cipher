# qnt/thesis/cli_caller.py
import json
import re
import subprocess
from typing import Optional


def extract_json(text: str) -> dict:
    """Extract first JSON object from CLI output text."""
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}', text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in output: {text[:300]}")
    return json.loads(match.group())


def call_cli(cli_name, prompt: str, timeout: int = 60) -> Optional[dict]:
    """
    Call claude or gemini CLI with -p flag.
    Returns parsed JSON dict or None on failure/timeout.
    """
    try:
        cmd = (cli_name if isinstance(cli_name, list) else [cli_name]) + ["-p", prompt]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip()
        if not output:
            print(f"[cli_caller] {cli_name} returned empty output (stderr: {result.stderr[:200]})")
            return None
        return extract_json(output)
    except subprocess.TimeoutExpired:
        print(f"[cli_caller] {cli_name} timed out after {timeout}s")
        return None
    except json.JSONDecodeError as e:
        print(f"[cli_caller] JSON parse error from {cli_name}: {e}")
        return None
    except Exception as e:
        print(f"[cli_caller] Unexpected error calling {cli_name}: {e}")
        return None
