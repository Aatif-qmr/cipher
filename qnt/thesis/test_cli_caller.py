# qnt/thesis/test_cli_caller.py
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class TestCliCaller(unittest.TestCase):

    def test_extract_json_from_plain_output(self):
        from qnt.thesis.cli_caller import extract_json
        output = 'Some preamble text\n{"bias": "BUY", "confidence": 0.8}\ntrailing text'
        result = extract_json(output)
        self.assertEqual(result["bias"], "BUY")
        self.assertAlmostEqual(result["confidence"], 0.8)

    def test_extract_json_raises_on_no_json(self):
        from qnt.thesis.cli_caller import extract_json
        with self.assertRaises(ValueError):
            extract_json("This output has no JSON in it at all")

    def test_call_cli_timeout_returns_none(self):
        from qnt.thesis.cli_caller import call_cli
        result = call_cli("sleep", "5", timeout=1)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
