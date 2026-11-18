# Faisalabad historical data audit

The candidate dataset covers **1 January 2023 00:00 to 31 December 2025 23:00 UTC**. The full download and checks were completed on 18 November 2026. It contains modelled/reanalysis data, not independent Faisalabad station measurements.

## 1. Expected coverage

2023 and 2025 each have 8,760 hours. The leap year 2024 has 8,784. We therefore expect **26,304 hours per source**, including 24 hours on 29 February 2024.

The downloader makes one request per month for each of two sources: 36 weather requests and 36 air-quality/UV requests. It validates saved monthly files before reusing them. Eleven weather transfers failed during the first pass with an SSL transfer error; the resumed run fetched those months successfully. TLS verification remained enabled.

## 2. Actual coverage and time alignment

| Check | Weather | Air quality and UV |
| --- | ---: | ---: |
| Expected hours | 26,304 | 26,304 |
| Returned rows | 26,304 | 26,304 |
| Unique timestamps | 26,304 | 26,304 |
| Missing timestamps | 0 | 0 |
| Duplicate timestamps | 0 | 0 |
| Unexpected timestamps | 0 | 0 |
| Leap-day hours | 24 | 24 |
| Missing requested values | 0 | 0 |

All monthly timestamp sequences and column lengths matched the expected hourly UTC grid. Units were consistent between months for each source. UTC keeps joins unambiguous; the dashboard can convert timestamps to Pakistan time (UTC+5). This audit's calendar boundaries and monthly statistics are UTC, not local calendar boundaries.

Both sources were aligned by timestamp into **26,304 complete rows** with nine numeric fields, plus city and timestamp. Combining two tables does not double the number of examples: both describe the same hours.

The local table is `data/processed/faisalabad_2023_2025_unimputed.csv`. Raw monthly responses remain in `data/historical/`. These data files are excluded from Git; scripts, aggregate reports, request metadata, and file fingerprints are versioned.

## 3. Missing values and ranges

| Field | Minimum | Maximum | Missing values |
| --- | ---: | ---: | ---: |
| Temperature | 2.3 C | 45.4 C | 0 |
| Relative humidity | 9% | 100% | 0 |
| Precipitation | 0 mm | 17.8 mm | 0 |
| Wind speed | 0 m/s | 8.22 m/s | 0 |
| Wind direction | 1 degree | 360 degrees | 0 |
| US AQI | 66 | 437 | 0 |
| PM2.5 | 3.4 micrograms/m3 | 461.9 micrograms/m3 | 0 |
| PM10 | 3.4 micrograms/m3 | 741.3 micrograms/m3 | 0 |
| UV Index | 0 | 11.05 | 0 |

No values violated the implemented hard bounds: humidity outside 0-100, direction outside 0-360, or negative precipitation, speed, AQI, pollutant concentrations, or UV. No values crossed the additional broad review bounds listed in `summary.json`.

Those bounds are screening rules, not proof that every value is accurate. Historical model output is often complete by construction. Independent station agreement has not been checked.

## 4. Unusual values and repeated observations

The audit measures missing runs, zero runs, repeated values, and the largest hourly changes. Examples requiring context:

- Temperature falls from 36.9 C to 28.3 C at 12:00 UTC on 5 June 2024: an 8.6 C hourly change. Rain, humidity, wind, and surrounding hours should be examined before deciding whether this is a plausible weather event or a data issue.
- AQI has a longest identical-value run of 21 hours. Rounding, calculation windows, or model processing might contribute; its cause has not been established.
- Precipitation is exactly zero in 24,243 of 26,304 hours, about 92.2%. Its longest zero run is 2,051 hours. Dry periods can be real; a constant-value check must not automatically delete them.
- UV is zero in 13,692 hours, about 52.1%, with a longest zero run of 15 hours. This is consistent with expected day/night structure but does not independently validate every zero.
- Direction includes 360 degrees. A later transformation can represent it equivalently to 0 degrees. Raw values are retained. Direction is less informative in calm conditions.

The audit also counts values outside the monthly interquartile range (IQR) fences, `Q1 - 1.5*IQR` and `Q3 + 1.5*IQR`. Q1 and Q3 are the 25th and 75th percentiles. Comparing within each month reduces the risk of treating seasonal changes as errors.

| Field | Monthly IQR flags across 36 months |
| --- | ---: |
| Temperature | 28 |
| Humidity | 23 |
| Wind speed | 576 |
| AQI | 539 |
| PM2.5 | 497 |
| PM10 | 601 |

These **2,264 variable-level flags** can overlap in time. They are not 2,264 proven bad rows. Extremes are relevant to hazard forecasting and remain in the dataset. IQR screening is not applied to wind direction or zero-heavy precipitation and UV.

Monthly medians show different AQI levels across the year, but seasonality, weather, emissions, and model changes cannot be separated from this table alone. No formal change-point or drift conclusion has been drawn.

## 5. What was changed

- Requested ERA5 weather at a fixed location, UTC timestamps, and explicit metres/second for wind speed.
- Preserved each API response's values and source metadata.
- Exported tabular data and aligned sources on their shared UTC timestamps.
- Calculated quality statistics and flagged values for review.

**No imputation, interpolation by our code, clipping, outlier deletion, scaling, or target shifting was performed.** The provider may have interpolated the underlying model output. There were no gaps to fill in this historical download; that does not remove the requirement for a documented missing-data strategy in the live pipeline.

## 6. Decision and remaining work

The dataset passes coverage, numeric structure, and the implemented bounds checks. **Keep Faisalabad and proceed to EDA.** This is not final approval for an operational training dataset.

Before modelling:

1. Plot daily/seasonal distributions for all metric groups, inspect flagged extremes and surrounding weather, and review rain-event counts.
2. Review AQI definitions, archived CAMS model changes, and possible discontinuities. Verify suitable live sources and their relationship to the historical series.
3. Define the rain-event threshold used for probability modelling. Rain probability is an output to estimate, not an observed probability column in this dataset.
4. Define wind direction encoding and calm-wind handling.
5. Specify availability rules so reanalysis or archived forecasts unavailable at prediction time cannot leak future information into features.
6. Document missing-data rules for future outages, target exclusions, and chronological split boundaries. Fit learned transformations on training data only.
7. Establish whether independent station observations can validate the forecasts. Otherwise, state clearly that the reported AQI accuracy measures prediction of a modelled series.

## Evidence and reproduction

```powershell
python scripts/audit_history.py --download
python scripts/audit_history.py
python -m unittest discover -s tests -v
```

- [Machine-readable summary](audit_2023_2025/summary.json): coverage, units, bounds, and counts.
- [Variable statistics](audit_2023_2025/variables.csv): ranges, missingness, repetitions, and changes.
- [Monthly statistics](audit_2023_2025/monthly.csv): 36 months for every requested field.
- [Largest hourly changes](audit_2023_2025/largest_changes.csv): five changes per variable for inspection.
- [Bounds flags](audit_2023_2025/flags.csv): no flagged values in this run; header retained.
- [Download manifest](audit_2023_2025/manifest.json): exact requests, retrieval times, source locations, and response fingerprints.
- [Source definitions and attribution](DATASET.md).
- [Remaining project requirements](REQUIREMENTS.md).

Fourteen automated tests cover the collector and audit calculations. The full local audit is an additional integration check against the downloaded files.
