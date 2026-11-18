"""Download a small historical data sample for Faisalabad using Python 3.11+."""

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LATITUDE = 31.41554
LONGITUDE = 73.08969
SOURCES = {
    "weather": {
        "url": "https://archive-api.open-meteo.com/v1/archive",
        "kind": "ERA5 reanalysis (not a local station observation)",
        "variables": [
            "temperature_2m", "relative_humidity_2m", "precipitation",
            "wind_speed_10m", "wind_direction_10m",
        ],
        "options": {"models": "era5", "wind_speed_unit": "ms"},
    },
    "air_quality": {
        "url": "https://air-quality-api.open-meteo.com/v1/air-quality",
        "kind": "CAMS archived model output (not a local station observation)",
        "variables": ["us_aqi", "pm2_5", "pm10", "uv_index"],
        "options": {},
    },
}


def fetch_json(url):
    """Retry temporary server and connection errors; report other errors clearly."""
    request = Request(url, headers={"User-Agent": "AgentWeather/0.1"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                detail = error.read().decode("utf-8", errors="replace")[:500]
                raise ValueError(f"HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError) as error:
            if attempt == 2:
                raise ValueError(f"Could not reach data source: {error}") from error
        time.sleep(2 ** attempt)


def validate_hourly(payload, variables, start, end):
    """Require the requested UTC hourly grid, while preserving missing values."""
    if payload.get("error"):
        raise ValueError(payload.get("reason", "API returned an error"))
    hourly = payload.get("hourly", {})
    timestamps = hourly.get("time", [])
    expected_count = ((end - start).days + 1) * 24
    first = datetime.combine(start, datetime.min.time())
    expected_times = [
        (first + timedelta(hours=i)).isoformat(timespec="minutes")
        for i in range(expected_count)
    ]
    if payload.get("utc_offset_seconds") != 0:
        raise ValueError("Expected UTC timestamps")
    if timestamps != expected_times:
        raise ValueError("Response does not contain the complete requested hourly grid")
    for variable in variables:
        values = hourly.get(variable)
        if not isinstance(values, list) or len(values) != expected_count:
            raise ValueError(f"Missing or misaligned column: {variable}")
        if variable not in payload.get("hourly_units", {}):
            raise ValueError(f"Missing unit for {variable}")
        if any(value is not None and (isinstance(value, bool) or
               not isinstance(value, (int, float)) or not math.isfinite(value))
               for value in values):
            raise ValueError(f"Unexpected non-numeric value in {variable}")
    return hourly


def collect(source_name, start, end, output):
    source = SOURCES[source_name]
    params = {
        "latitude": LATITUDE, "longitude": LONGITUDE,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "hourly": ",".join(source["variables"]), "timezone": "UTC",
        **source["options"],
    }
    url = source["url"] + "?" + urlencode(params)
    payload = fetch_json(url)
    hourly = validate_hourly(payload, source["variables"], start, end)
    folder = output / f"{start}_{end}" / source_name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "response.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8"
    )
    with (folder / "hourly.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["city", "timestamp_utc", *source["variables"]])
        for i, timestamp in enumerate(hourly["time"]):
            writer.writerow([
                "Faisalabad", timestamp + "Z",
                *(hourly[variable][i] for variable in source["variables"]),
            ])
    coverage = {}
    for variable in source["variables"]:
        values = [value for value in hourly[variable] if value is not None]
        coverage[variable] = {
            "unit": payload["hourly_units"][variable],
            "available": len(values), "missing": len(hourly["time"]) - len(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    summary = {
        "city": "Faisalabad", "source": source_name, "data_kind": source["kind"],
        "request_url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_coordinates": {"latitude": LATITUDE, "longitude": LONGITUDE},
        "returned_coordinates": {
            "latitude": payload.get("latitude"), "longitude": payload.get("longitude"),
        },
        "timezone": "UTC", "row_count": len(hourly["time"]),
        "start": hourly["time"][0] + "Z", "end": hourly["time"][-1] + "Z",
        "coverage": coverage,
    }
    (folder / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(f"{source_name}: saved {summary['row_count']} rows to {folder}")
    for variable, stats in coverage.items():
        print(f"  {variable}: {stats['available']} available, {stats['missing']} missing")
    return all(stats["available"] > 0 for stats in coverage.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["all", *SOURCES], default="all")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 1, 7))
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "samples")
    args = parser.parse_args()
    if not 0 <= (args.end - args.start).days < 31:
        parser.error("Choose a sample interval of 1 to 31 days, inclusive")
    if args.end >= datetime.now(timezone.utc).date():
        parser.error("Historical samples must end before today (UTC)")
    failed = False
    selected = SOURCES if args.source == "all" else [args.source]
    for source_name in selected:
        try:
            if not collect(source_name, args.start, args.end, args.output):
                print(f"WARNING: {source_name} has an entirely missing column", file=sys.stderr)
                failed = True
        except (ValueError, OSError) as error:
            print(f"ERROR [{source_name}]: {error}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
