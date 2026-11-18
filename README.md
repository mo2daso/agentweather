# AgentWeather

Weather and air-quality forecasting for Faisalabad, Pakistan.

The project will use historical weather and air-quality data to train models and produce forecasts for the next 24 hours.

## Forecast outputs

- Air Quality Index (AQI)
- Temperature (degrees Celsius)
- Precipitation amount and rain probability
- Relative humidity
- UV Index
- Wind speed and direction

## Current status

A sample collector checks historical weather, AQI, and UV data for Faisalabad. Initial checks cover three weeks; the full training dataset has not been selected yet. See [dataset investigation](docs/DATASET.md) for sources and results.

## Collect a sample

Requires Python 3.11 or later. No additional packages or API key are needed.

```powershell
python scripts/collect_sample.py --start 2025-01-01 --end 2025-01-07
```

The script saves raw responses, hourly CSV files, and coverage summaries under `data/samples/`. Downloaded data stays out of Git.
