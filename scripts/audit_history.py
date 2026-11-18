"""Download and audit Faisalabad's 2023-2025 candidate datasets without imputation."""

import argparse
import calendar
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import csv
import hashlib
import json
from pathlib import Path
import statistics

from collect_sample import ROOT, SOURCES, collect, validate_hourly


START = date(2023, 1, 1)
END = date(2025, 12, 31)
RAW = ROOT / "data" / "historical"
REPORT = ROOT / "docs" / "audit_2023_2025"
# Hard bounds express impossible values for these variables. Broad review bounds
# are heuristics for inspection, not reasons to remove observations.
HARD_BOUNDS = {
    "relative_humidity_2m": (0, 100), "precipitation": (0, None),
    "wind_speed_10m": (0, None), "wind_direction_10m": (0, 360),
    "us_aqi": (0, None), "pm2_5": (0, None), "pm10": (0, None),
    "uv_index": (0, None),
}
REVIEW_BOUNDS = {
    "temperature_2m": (-20, 55), "precipitation": (0, 100),
    "wind_speed_10m": (0, 40), "us_aqi": (0, 500),
    "pm2_5": (0, 1000), "pm10": (0, 1500), "uv_index": (0, 20),
}


def months():
    for year in range(START.year, END.year + 1):
        for month in range(1, 13):
            yield date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def load_chunk(source, start, end):
    folder = RAW / f"{start}_{end}" / source
    payload = json.loads((folder / "response.json").read_text(encoding="utf-8"))
    hourly = validate_hourly(payload, SOURCES[source]["variables"], start, end)
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    if (summary.get("source") != source or
            summary.get("requested_coordinates") != {"latitude": 31.41554, "longitude": 73.08969} or
            summary.get("start") != f"{start}T00:00Z" or
            summary.get("end") != f"{end}T23:00Z"):
        raise ValueError("Cached summary does not match the requested source/location/period")
    if source == "weather" and "models=era5" not in summary.get("request_url", ""):
        raise ValueError("Cached weather is not the selected ERA5 source")
    return folder, payload, hourly, summary


def download_chunk(source, start, end):
    try:
        load_chunk(source, start, end)
        return f"cached {source} {start:%Y-%m}"
    except (OSError, ValueError, KeyError, TypeError):
        collect(source, start, end, RAW, verbose=False)
        load_chunk(source, start, end)
        return f"downloaded {source} {start:%Y-%m}"


def longest_run(values, predicate):
    longest = current = 0
    for value in values:
        current = current + 1 if predicate(value) else 0
        longest = max(longest, current)
    return longest


def outside(value, bounds):
    if value is None or bounds is None:
        return False
    low, high = bounds
    return (low is not None and value < low) or (high is not None and value > high)


def describe(values, variable):
    available = [value for value in values if value is not None]
    stats = {
        "rows": len(values), "available": len(available),
        "missing": len(values) - len(available),
        "longest_missing_hours": longest_run(values, lambda x: x is None),
        "zero_hours": sum(value == 0 for value in available),
        "longest_zero_hours": longest_run(values, lambda x: x == 0),
        "min": min(available) if available else None,
        "max": max(available) if available else None,
        # Arithmetic averages of degrees would misrepresent wind direction.
        "mean": statistics.mean(available) if available and variable != "wind_direction_10m" else None,
        "median": statistics.median(available) if available and variable != "wind_direction_10m" else None,
        "hard_bound_flags": sum(outside(value, HARD_BOUNDS.get(variable)) for value in available),
        "review_bound_flags": sum(outside(value, REVIEW_BOUNDS.get(variable)) for value in available),
    }
    longest = current = 0
    previous = None
    for value in values:
        current = current + 1 if value is not None and value == previous else (1 if value is not None else 0)
        longest = max(longest, current)
        previous = value
    stats["longest_constant_hours"] = longest
    changes = [
        abs(right - left) for left, right in zip(values, values[1:])
        if left is not None and right is not None
    ]
    if variable == "wind_direction_10m":
        changes = [min(change % 360, 360 - change % 360) for change in changes]
    stats["max_hourly_change"] = max(changes) if changes else None
    # Monthly IQR flags highlight unusual values without confusing winter with
    # summer. Zero-heavy precipitation/UV and circular direction are excluded.
    stats["q1"] = stats["q3"] = None
    stats["iqr_flags"] = None
    if len(available) >= 4 and variable not in ("precipitation", "uv_index", "wind_direction_10m"):
        q1, _, q3 = statistics.quantiles(available, n=4, method="inclusive")
        spread = q3 - q1
        stats["q1"], stats["q3"] = q1, q3
        stats["iqr_flags"] = sum(value < q1 - 1.5*spread or value > q3 + 1.5*spread for value in available)
    return stats


def write_csv(path, records):
    if not records:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def audit():
    REPORT.mkdir(parents=True, exist_ok=True)
    expected = [
        (datetime.combine(START, datetime.min.time()) + timedelta(hours=i)).isoformat(timespec="minutes")
        for i in range(((END - START).days + 1) * 24)
    ]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "city": "Faisalabad", "start": str(START), "end": str(END),
        "timezone": "UTC", "expected_hours": len(expected),
        "leap_day_expected_hours": 24, "sources": {}, "missing_chunks": [],
        "hard_bounds": HARD_BOUNDS, "review_bounds": REVIEW_BOUNDS,
        "interpretation": "Coverage audit of modelled/reanalysis series; not independent station validation.",
    }
    manifest, monthly, flags, variable_stats, largest_changes = [], [], [], [], []
    all_tables = {}
    for source, settings in SOURCES.items():
        table, timestamps, units = {}, [], None
        for start, end in months():
            try:
                folder, payload, hourly, metadata = load_chunk(source, start, end)
            except (OSError, ValueError, KeyError, TypeError) as error:
                summary["missing_chunks"].append({"source": source, "start": str(start), "error": str(error)})
                continue
            chunk_units = {variable: payload["hourly_units"][variable] for variable in settings["variables"]}
            if units is not None and units != chunk_units:
                raise ValueError(f"Unit change in {source} at {start}")
            units = chunk_units
            metadata["response_sha256"] = hashlib.sha256((folder / "response.json").read_bytes()).hexdigest()
            manifest.append(metadata)
            timestamps.extend(hourly["time"])
            for i, timestamp in enumerate(hourly["time"]):
                table[timestamp] = {variable: hourly[variable][i] for variable in settings["variables"]}
            for variable in settings["variables"]:
                monthly.append({"month": start.strftime("%Y-%m"), "source": source,
                                "variable": variable, "unit": units[variable],
                                **describe(hourly[variable], variable)})
        actual = set(timestamps)
        counts = Counter(timestamps)
        source_stats = {
            "rows": len(timestamps), "unique_hours": len(actual),
            "duplicate_hours": sum(count - 1 for count in counts.values()),
            "missing_hours": len(set(expected) - actual),
            "unexpected_hours": len(actual - set(expected)),
            "sorted": timestamps == sorted(timestamps),
            "leap_day_hours": sum(timestamp.startswith("2024-02-29") for timestamp in actual),
            "variables": {},
        }
        for variable in settings["variables"]:
            values = [table.get(timestamp, {}).get(variable) for timestamp in expected]
            stats = describe(values, variable)
            stats["unit"] = (units or {}).get(variable)
            source_stats["variables"][variable] = stats
            variable_stats.append({"source": source, "variable": variable, **stats})
            changes = []
            for i in range(1, len(values)):
                left, right = values[i-1], values[i]
                if left is None or right is None:
                    continue
                change = abs(right - left)
                if variable == "wind_direction_10m":
                    change = min(change % 360, 360 - change % 360)
                changes.append((change, expected[i], left, right))
            for change, timestamp, left, right in sorted(changes, reverse=True)[:5]:
                largest_changes.append({"source": source, "variable": variable,
                                        "timestamp_utc": timestamp + "Z", "previous": left,
                                        "value": right, "absolute_change": change})
            for timestamp, value in zip(expected, values):
                hard = outside(value, HARD_BOUNDS.get(variable))
                review = outside(value, REVIEW_BOUNDS.get(variable))
                if hard or review:
                    flags.append({"timestamp_utc": timestamp + "Z", "source": source,
                                  "variable": variable, "value": value,
                                  "flag": "hard_bound" if hard else "review_bound"})
        summary["sources"][source] = source_stats
        all_tables[source] = table

    variables = [variable for settings in SOURCES.values() for variable in settings["variables"]]
    # Align on the expected UTC grid. Empty cells remain missing; this is not imputation.
    dataset_path = ROOT / "data" / "processed" / "faisalabad_2023_2025_unimputed.csv"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    with dataset_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["city", "timestamp_utc", *variables])
        for timestamp in expected:
            writer.writerow(["Faisalabad", timestamp + "Z", *(
                all_tables[source].get(timestamp, {}).get(variable)
                for source, settings in SOURCES.items() for variable in settings["variables"]
            )])
    summary["joined_dataset_sha256"] = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    summary["joined_complete_rows"] = sum(
        all(all_tables[source].get(timestamp, {}).get(variable) is not None
            for source, settings in SOURCES.items() for variable in settings["variables"])
        for timestamp in expected
    )
    summary["coverage_complete"] = (
        not summary["missing_chunks"] and summary["joined_complete_rows"] == len(expected)
        and all(s["duplicate_hours"] == 0 and s["unexpected_hours"] == 0 for s in summary["sources"].values())
    )
    summary["monthly_iqr_flags"] = {
        variable: sum(row["iqr_flags"] or 0 for row in monthly if row["variable"] == variable)
        for variable in variables
        if any(row["variable"] == variable and row["iqr_flags"] is not None for row in monthly)
    }
    (REPORT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (REPORT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    write_csv(REPORT / "variables.csv", variable_stats)
    write_csv(REPORT / "monthly.csv", monthly)
    write_csv(REPORT / "largest_changes.csv", largest_changes)
    # Write a header even when there are no flags, so an old report cannot survive a rerun.
    with (REPORT / "flags.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp_utc", "source", "variable", "value", "flag"])
        writer.writeheader()
        writer.writerows(flags)
    print(json.dumps({"expected_hours": len(expected), "complete_joined_rows": summary["joined_complete_rows"],
                      "coverage_complete": summary["coverage_complete"], "bound_flags": len(flags),
                      "monthly_iqr_variable_flags": sum(summary["monthly_iqr_flags"].values()),
                      "missing_chunks": len(summary["missing_chunks"])}, indent=2), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download missing monthly chunks before auditing")
    args = parser.parse_args()
    if args.download:
        jobs = [(source, start, end) for start, end in months() for source in SOURCES]
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(download_chunk, *job): job for job in jobs}
            for index, future in enumerate(as_completed(futures), 1):
                try:
                    print(f"[{index}/{len(jobs)}] {future.result()}", flush=True)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    print(f"[{index}/{len(jobs)}] FAILED {futures[future]}: {error}", flush=True)
    result = audit()
    return 0 if result["coverage_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
