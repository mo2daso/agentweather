"""Checks for time-boundary and aggregation mistakes that can mislead EDA."""

from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import eda_faisalabad as eda


class EdaTests(unittest.TestCase):
    def test_runs_include_first_and_last_observation(self):
        index = pd.date_range("2024-01-01", periods=6, freq="h", tz="Asia/Karachi")
        result = eda.runs(pd.Series([1, 1, 2, 3, 3, 3], index=index))
        self.assertEqual([item["hours"] for item in result], [2, 1, 3])
        self.assertEqual(result[-1]["end"], index[-1].isoformat())
        self.assertEqual(result[-1]["value"], 3)

    def test_constant_series_is_one_run(self):
        index = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
        self.assertEqual(eda.runs(pd.Series([0, 0, 0], index=index))[0]["hours"], 3)

    def test_daily_sum_excludes_partial_local_days_and_direction_mean(self):
        index = pd.date_range("2023-01-01", periods=48, freq="h", tz="UTC").tz_convert("Asia/Karachi")
        frame = pd.DataFrame({field: 1.0 for field in eda.FIELDS}, index=index)
        frame["temperature_2m"] = 20.0
        before = frame.copy(deep=True)
        result = eda.local_day_summary(frame)
        self.assertEqual(len(result), 1)
        self.assertEqual(str(result.index[0].date()), "2023-01-02")
        self.assertEqual(result.iloc[0]["precipitation"], 24.0)
        self.assertEqual(result.iloc[0]["temperature_2m"], 20.0)
        self.assertNotIn("wind_direction_10m", result.columns)
        pd.testing.assert_frame_equal(frame, before)


if __name__ == "__main__":
    unittest.main()
