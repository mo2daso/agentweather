"""Fetch a one-day ERA5-Land diagnostic; it does not replace training data."""

from datetime import date, datetime, timezone
import hashlib
import json
from urllib.parse import urlencode

from collect_sample import ROOT, LATITUDE, LONGITUDE, fetch_json, validate_hourly


def main():
    params = {
        "latitude": LATITUDE, "longitude": LONGITUDE,
        "start_date": "2025-01-26", "end_date": "2025-01-26",
        "hourly": "temperature_2m,relative_humidity_2m", "timezone": "UTC", "models": "era5_land",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
    payload = fetch_json(url)
    validate_hourly(payload, ["temperature_2m", "relative_humidity_2m"], date(2025, 1, 26), date(2025, 1, 26))
    canonical = json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
    record = {"request_url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
              "response_sha256": hashlib.sha256(canonical).hexdigest(), "response": payload}
    target = ROOT / "data/diagnostics/era5_land_2025_01_26.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("Saved one-day ERA5-Land comparison:", target)


if __name__ == "__main__":
    main()
