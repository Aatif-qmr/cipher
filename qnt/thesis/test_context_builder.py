# qnt/thesis/test_context_builder.py
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class TestContextBuilder(unittest.TestCase):

    def test_build_context_returns_string(self):
        from qnt.thesis.context_builder import build_context
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "score: 0.42"
            mock_run.return_value.returncode = 0
            ctx = build_context("BTC/USDT")
        self.assertIsInstance(ctx, str)
        self.assertIn("BTC/USDT", ctx)

    def test_build_context_includes_all_sections(self):
        from qnt.thesis.context_builder import build_context
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "mock output"
            mock_run.return_value.returncode = 0
            ctx = build_context("ETH/USDT")
        for section in ("Sentiment", "Shield", "Balance", "Anomaly", "Calendar"):
            self.assertIn(section, ctx)

    def test_build_context_handles_cli_failure_gracefully(self):
        from qnt.thesis.context_builder import build_context
        with patch("subprocess.run", side_effect=Exception("tool not found")):
            ctx = build_context("SOL/USDT")
        self.assertIsInstance(ctx, str)
        self.assertIn("unavailable", ctx)

if __name__ == "__main__":
    unittest.main()
