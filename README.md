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

Historical weather, AQI, and UV data for 2023-2025 have been downloaded and checked for coverage. The aligned dataset contains 26,304 hourly records with no missing values. EDA covers distributions, seasonal and daily patterns, rain events, wind direction, correlations, and unusual observations. Models and the dashboard have not been built yet.

- [EDA notebook with plots and explanations](notebooks/01_faisalabad_eda.ipynb)
- [Findings and data decisions](docs/EDA.md)
- [Dataset sources](docs/DATASET.md) and [coverage audit](docs/HISTORICAL_AUDIT.md)
- [Project requirements](docs/REQUIREMENTS.md)

## Collect a sample

Requires Python 3.11 or later. No additional packages or API key are needed.

```powershell
python scripts/collect_sample.py --start 2025-01-01 --end 2025-01-07
```

The script saves raw responses, hourly CSV files, and coverage summaries under `data/samples/`. Downloaded data stays out of Git.

## Check the historical dataset

```powershell
python scripts/audit_history.py --download
python -m unittest discover -s tests -p "test_audit_history.py" -v
```

The download resumes from validated monthly files in `data/historical/`. It writes an aligned table to `data/processed/` and audit summaries to `docs/audit_2023_2025/`. Run without `--download` to audit local files without network requests. The audit does not fill gaps or remove outliers. Its exit status reports coverage, not readiness for model training.

## Run the EDA

After downloading the history:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-eda.txt
python scripts/check_warming_source.py
.\.venv\Scripts\python.exe scripts/eda_faisalabad.py
.\.venv\Scripts\python.exe scripts/build_eda_notebook.py --execute
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The source comparison downloads one day of ERA5-Land data for diagnosis. It does not replace the ERA5 training candidate. Figures and tables are saved under `docs/eda/`. The EDA preserves source values and records unresolved questions rather than deleting unusual weather.
