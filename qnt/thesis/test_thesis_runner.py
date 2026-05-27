# qnt/thesis/test_thesis_runner.py
import unittest
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

MOCK_BULL = {"case": "Strong RSI divergence", "key_signals": ["RSI", "volume", "funding"], "confidence": 0.8}
MOCK_BEAR = {"case": "OI too high risk", "key_signals": ["OI spike", "fear", "macro"], "confidence": 0.4}
MOCK_SYNTHESIS = {"bias": "BUY", "confidence": 0.75, "reasoning": "Bull wins", "stake_modifier": 1.0, "key_risks": ["macro"]}

class TestThesisRunner(unittest.TestCase):

    def test_run_thesis_writes_valid_json(self):
        from qnt.thesis.thesis_runner import run_thesis
        with patch("qnt.thesis.thesis_runner.build_context", return_value="mock context"), \
             patch("qnt.thesis.thesis_runner.call_cli", side_effect=[MOCK_BULL, MOCK_BEAR, MOCK_SYNTHESIS]), \
             tempfile.TemporaryDirectory() as tmpdir:
            thesis = run_thesis("BTC/USDT", output_dir=Path(tmpdir))

        self.assertEqual(thesis["bias"], "BUY")
        self.assertEqual(thesis["pair"], "BTC/USDT")
        self.assertIn("generated_at", thesis)
        self.assertIn("valid_until", thesis)
        self.assertIn("context_snapshot", thesis)

    def test_run_thesis_falls_back_on_cli_failure(self):
        from qnt.thesis.thesis_runner import run_thesis
        with patch("qnt.thesis.thesis_runner.build_context", return_value="ctx"), \
             patch("qnt.thesis.thesis_runner.call_cli", return_value=None), \
             tempfile.TemporaryDirectory() as tmpdir:
            thesis = run_thesis("ETH/USDT", output_dir=Path(tmpdir))

        self.assertIn(thesis["bias"], ("BUY", "HOLD", "SELL"))
        self.assertLess(thesis["confidence"], 0.5)

    def test_run_thesis_writes_file(self):
        from qnt.thesis.thesis_runner import run_thesis
        with patch("qnt.thesis.thesis_runner.build_context", return_value="ctx"), \
             patch("qnt.thesis.thesis_runner.call_cli", side_effect=[MOCK_BULL, MOCK_BEAR, MOCK_SYNTHESIS]), \
             tempfile.TemporaryDirectory() as tmpdir:
            run_thesis("SOL/USDT", output_dir=Path(tmpdir))
            out_file = Path(tmpdir) / "SOL_USDT.json"
            self.assertTrue(out_file.exists())
            data = json.loads(out_file.read_text())
            self.assertEqual(data["pair"], "SOL/USDT")

if __name__ == "__main__":
    unittest.main()
