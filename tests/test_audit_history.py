"""Verify audit calculations using small examples with known answers."""

from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_history as audit


class AuditTests(unittest.TestCase):
    def test_months_include_leap_day_and_exact_year_boundaries(self):
        intervals = list(audit.months())
        self.assertEqual(len(intervals), 36)
        self.assertEqual(intervals[0][0], date(2023, 1, 1))
        self.assertEqual(intervals[-1][1], date(2025, 12, 31))
        self.assertIn((date(2024, 2, 1), date(2024, 2, 29)), intervals)
        self.assertEqual(sum(((end-start).days+1)*24 for start, end in intervals), 26304)

    def test_missing_values_are_counted_without_filling_or_bridging_gaps(self):
        result = audit.describe([1, None, None, 2, None], "temperature_2m")
        self.assertEqual(result["missing"], 3)
        self.assertEqual(result["longest_missing_hours"], 2)
        self.assertEqual(result["mean"], 1.5)
        self.assertIsNone(result["max_hourly_change"])

    def test_flags_are_separate_from_values(self):
        values = [-1, 0, 600]
        result = audit.describe(values, "us_aqi")
        self.assertEqual(result["available"], 3)
        self.assertEqual(result["hard_bound_flags"], 1)
        self.assertEqual(result["review_bound_flags"], 2)
        self.assertEqual(values, [-1, 0, 600])

    def test_missing_is_not_zero(self):
        result = audit.describe([0, 0, None, 0, 1, 1, 1], "precipitation")
        self.assertEqual(result["zero_hours"], 3)
        self.assertEqual(result["longest_zero_hours"], 2)
        self.assertEqual(result["longest_constant_hours"], 3)

    def test_direction_change_wraps_and_has_no_arithmetic_mean(self):
        result = audit.describe([359, 1], "wind_direction_10m")
        self.assertEqual(result["max_hourly_change"], 2)
        self.assertIsNone(result["mean"])
        self.assertIsNone(result["median"])

    def test_fully_missing_column_is_reported(self):
        result = audit.describe([None, None], "uv_index")
        self.assertEqual(result["available"], 0)
        self.assertEqual(result["missing"], 2)
        self.assertIsNone(result["min"])

    def test_iqr_marks_extreme_value_without_removing_it(self):
        result = audit.describe([1, 2, 3, 4, 100], "temperature_2m")
        self.assertEqual(result["iqr_flags"], 1)
        self.assertEqual(result["available"], 5)
        self.assertEqual(result["max"], 100)

    def test_iqr_not_applied_to_circular_or_zero_heavy_fields(self):
        for variable in ("precipitation", "uv_index", "wind_direction_10m"):
            with self.subTest(variable=variable):
                self.assertIsNone(audit.describe([0, 0, 0, 10], variable)["iqr_flags"])


if __name__ == "__main__":
    unittest.main()
