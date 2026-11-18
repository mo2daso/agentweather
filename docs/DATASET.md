# Dataset investigation

## Current decision

Faisalabad remains the selected city for investigation. The full 2023-2025 UTC history from Open-Meteo contains all requested weather variables, US AQI, and UV Index with no missing hours or values. It passes coverage and basic bounds checks. [EDA](EDA.md) is complete for this candidate dataset, with source-comparability questions and unusual temperature timing still open. See the [full audit](HISTORICAL_AUDIT.md).

The mentor allows any dataset with enough complete data for a Pakistani city, provided the chosen dataset and its processing are documented.

## Location and sources

Requested location: Faisalabad, Punjab, Pakistan, latitude **31.41554**, longitude **73.08969**. Coordinates were checked using the [Open-Meteo geocoding API](https://geocoding-api.open-meteo.com/v1/search?name=Faisalabad&count=1&language=en&format=json).

| Candidate source | Fields requested | What the data represents |
| --- | --- | --- |
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), with `models=era5` | Temperature, relative humidity, precipitation, wind speed, wind direction | ERA5 reanalysis: reconstructed historical weather, not direct measurements from a Faisalabad station |
| [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) | US AQI, PM2.5, PM10, UV Index | Archived CAMS model output, not independent ground-truth sensor readings |

The returned grid locations differ: the weather samples use approximately 31.5, 73.0, while the air-quality samples return approximately 31.400002, 73.100006. These are estimates for grid cells near the requested city, not identical monitoring locations. API coordinates do not establish the native resolution of the underlying model.

Open-Meteo documents the global CAMS atmospheric forecast at roughly 45 km spatial resolution and three-hourly native output. An hourly response is not evidence of hourly independent station measurements. Model and processing changes over the archive also need investigation.

## Sample checks

Checked on 18 November 2026. All periods below are inclusive and requested in UTC.

| Period | Weather rows | Air-quality/UV rows | Missing requested values |
| --- | --- | --- | --- |
| 1-7 January 2023 | 168 | 168 | 0 |
| 1-7 January 2025 | 168 | 168 | 0 |
| 1-7 July 2025 | 168 | 168 | 0 |

This covers **504 distinct hourly timestamps per source**, spread across three weeks. It is a coverage sample, not a training dataset or a complete seasonal audit. The sample tables remain separate. The later full-history audit aligns both sources into one local table without imputation.

The collector checks the complete requested hourly grid, UTC offset, column lengths, unit metadata, and numeric values. Missing values remain missing. Five automated checks cover duplicate timestamps, misaligned columns, unexpected timezone offsets, invalid numbers, and preservation of missing values.

Per-variable counts and ranges are in [sample_coverage.csv](sample_coverage.csv). Local downloads retain the original response, a CSV table, and a summary with the request URL, retrieval time, units, and returned coordinates. `sample_manifest.json` records those summaries and SHA-256 fingerprints of the saved responses.

The API uses an empty unit string for dimensionless UV Index. The collector accepts this metadata and preserves it; it does not treat it as missing data.

## Units and definitions

| Field | Meaning | Unit |
| --- | --- | --- |
| `temperature_2m` | Temperature at 2 metres | Celsius |
| `relative_humidity_2m` | Relative humidity at 2 metres | Percent |
| `precipitation` | Precipitation over the preceding hour | Millimetres |
| `wind_speed_10m` | Wind speed at 10 metres | Metres per second |
| `wind_direction_10m` | Direction the wind comes from | Degrees |
| `us_aqi` | Provider's consolidated US AQI | Index |
| `pm2_5`, `pm10` | Modelled particulate concentrations | Micrograms per cubic metre |
| `uv_index` | UV Index | Dimensionless index |

Rain probability is not an observed historical probability column in the weather sample. A later modelling step can define a rain event from precipitation amount and estimate its probability. The event definition, threshold, and evaluation must be documented. A provider's old rain-probability forecast must not be presented as observed truth.

## Processing completed

- Requested explicit UTC timestamps and wind speed in metres per second.
- Saved source responses without changing their values.
- Exported hourly tables with city and explicit UTC timestamps.
- Calculated missing-value counts and value ranges.

The later full-history audit also aligns the two source tables by timestamp. No imputation, outlier removal, scaling, target creation, or model training has been performed. Zero rain and nighttime zero UV values were retained. Complete model output is not proof of measurement accuracy.

## Training dataset acceptance checks

1. Completed: downloaded the continuous UTC period 1 January 2023 to 31 December 2025, with 26,304 hourly timestamps including the 2024 leap day.
2. Completed: counted missing values and duplicate hours, checked monthly coverage, ranges, constant runs, hourly changes, and seasonal/daily plots. All requested values are present.
3. Completed exploratory review: physical/broad bounds checks passed; statistical flags and selected extreme events were examined in [EDA](EDA.md). The repeated temperature-jump timing and exact AQI plateau cause remain unresolved source questions. No extremes were deleted.
4. Check continuity across changes in the underlying air-quality model or AQI calculation.
5. Establish suitable live inputs. Historical reanalysis can be revised and is not available immediately; archived model outputs must not be assumed to have been available at their valid time. Forecast features need a documented availability rule.
6. Decide whether independent station observations are available for validation. If models are trained and tested against CAMS output, describe the results as forecasting that modelled series, not validated local sensor accuracy.
7. Record the final date range, dataset version, exclusions, imputation rules, transformations, and chronological train/validation/test periods.

If Faisalabad cannot meet these needs, compare Lahore, Karachi, and Islamabad using the same checks. No city change is needed based on the current samples alone.

## Reproduce a sample

Python 3.11 or later is sufficient; the collector uses the standard library and does not need an API key.

```powershell
python scripts/collect_sample.py --start 2025-01-01 --end 2025-01-07
python -m unittest discover -s tests -p "test_collect_sample.py" -v
```

Downloads are stored under `data/samples/` and excluded from Git. Repeating the same request replaces that local sample, so preserve a copy before comparing provider revisions. Requests are limited to 31 days per invocation at this stage.

## Attribution and access

Weather data: [Open-Meteo](https://open-meteo.com/) and ECMWF/Copernicus ERA5. Air-quality data: Open-Meteo and the Copernicus Atmosphere Monitoring Service (CAMS).

Open-Meteo provides API data under [CC BY 4.0](https://open-meteo.com/en/licence), requiring attribution and disclosure of changes. The [free API tier](https://open-meteo.com/en/pricing) has usage limits and excludes commercial use. Data licensing and hosted API access conditions are separate considerations. The final report and dashboard must include source credits.

The final report will use this record to explain dataset selection, cleaning decisions, exclusions, and limitations. It must describe the processing actually performed.
