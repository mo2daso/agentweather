"""Checks for failures that could silently corrupt a training sample."""

from copy import deepcopy
from datetime import date, datetime, timedelta
import importlib.util
from pathlib import Path
import io
import ssl
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "collector", Path(__file__).resolve().parents[1] / "scripts" / "collect_sample.py"
)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class HourlyValidationTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2025, 1, 1)
        self.payload = {
            "utc_offset_seconds": 0,
            "hourly_units": {"uv_index": ""},
            "hourly": {
                "time": [
                    (datetime(2025, 1, 1) + timedelta(hours=i)).isoformat(timespec="minutes")
                    for i in range(24)
                ],
                "uv_index": [None] + [0.0] * 23,
            },
        }

    def validate(self, payload):
        return collector.validate_hourly(payload, ["uv_index"], self.day, self.day)

    def test_accepts_dimensionless_unit_and_preserves_missing_value(self):
        result = self.validate(self.payload)
        self.assertIsNone(result["uv_index"][0])

    def test_rejects_duplicate_timestamp(self):
        self.payload["hourly"]["time"][1] = self.payload["hourly"]["time"][0]
        with self.assertRaisesRegex(ValueError, "hourly grid"):
            self.validate(self.payload)

    def test_rejects_misaligned_values(self):
        self.payload["hourly"]["uv_index"].pop()
        with self.assertRaisesRegex(ValueError, "misaligned"):
            self.validate(self.payload)

    def test_rejects_non_utc_response(self):
        self.payload["utc_offset_seconds"] = 18000
        with self.assertRaisesRegex(ValueError, "UTC"):
            self.validate(self.payload)

    def test_rejects_invalid_numbers(self):
        for bad_value in ("unknown", True, float("nan"), float("inf")):
            with self.subTest(value=bad_value):
                payload = deepcopy(self.payload)
                payload["hourly"]["uv_index"][0] = bad_value
                with self.assertRaisesRegex(ValueError, "non-numeric"):
                    self.validate(payload)

    def test_retries_interrupted_ssl_transfer(self):
        with patch.object(collector, "urlopen", side_effect=[
            ssl.SSLError("interrupted transfer"), io.StringIO('{"ok": true}')
        ]) as request, patch.object(collector.time, "sleep"):
            self.assertEqual(collector.fetch_json("https://example.com"), {"ok": True})
            self.assertEqual(request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
