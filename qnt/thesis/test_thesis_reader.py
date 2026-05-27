# qnt/thesis/test_thesis_reader.py
import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def _write_thesis(tmpdir: Path, pair: str, bias: str, confidence: float, minutes_old: int = 30) -> Path:
    slug = pair.replace("/", "_")
    now = datetime.now(timezone.utc)
    thesis = {
        "pair": pair, "bias": bias, "confidence": confidence,
        "stake_modifier": 1.0, "reasoning": "test",
        "key_risks": [], "bull_confidence": 0.7, "bear_confidence": 0.3,
        "valid_until": (now + timedelta(hours=4)).isoformat(),
        "generated_at": (now - timedelta(minutes=minutes_old)).isoformat(),
        "context_snapshot": {"shield_status": "GREEN"},
    }
    path = tmpdir / f"{slug}.json"
    path.write_text(json.dumps(thesis))
    return path

class TestThesisReader(unittest.TestCase):

    def test_read_valid_thesis(self):
        from qnt.thesis.thesis_reader import read_thesis
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_thesis(Path(tmpdir), "BTC/USDT", "BUY", 0.8)
            result = read_thesis("BTC/USDT", thesis_dir=Path(tmpdir))
        self.assertEqual(result["bias"], "BUY")
        self.assertAlmostEqual(result["confidence"], 0.8)

    def test_read_missing_returns_hold(self):
        from qnt.thesis.thesis_reader import read_thesis
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_thesis("XRP/USDT", thesis_dir=Path(tmpdir))
        self.assertEqual(result["bias"], "HOLD")
        self.assertLess(result["confidence"], 0.5)

    def test_read_stale_returns_hold(self):
        from qnt.thesis.thesis_reader import read_thesis
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_thesis(Path(tmpdir), "ETH/USDT", "BUY", 0.9, minutes_old=400)
            result = read_thesis("ETH/USDT", thesis_dir=Path(tmpdir))
        self.assertEqual(result["bias"], "HOLD")

    def test_low_confidence_returns_hold(self):
        from qnt.thesis.thesis_reader import read_thesis
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_thesis(Path(tmpdir), "SOL/USDT", "BUY", 0.3)
            result = read_thesis("SOL/USDT", thesis_dir=Path(tmpdir))
        self.assertEqual(result["bias"], "HOLD")

if __name__ == "__main__":
    unittest.main()
