"""Reproduce Faisalabad EDA figures and tables without modifying source data."""

import hashlib
import json
import os
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DATA = ROOT / "data/processed/faisalabad_2023_2025_unimputed.csv"
OUT = ROOT / "docs/eda"
FIELDS = {
    "temperature_2m": "Temperature (C)", "relative_humidity_2m": "Humidity (%)",
    "precipitation": "Hourly precipitation (mm)", "wind_speed_10m": "Wind speed (m/s)",
    "wind_direction_10m": "Wind direction (degrees)", "us_aqi": "US AQI",
    "pm2_5": "PM2.5 (micrograms/m3)", "pm10": "PM10 (micrograms/m3)",
    "uv_index": "UV Index",
}
CORE = ["temperature_2m", "us_aqi", "relative_humidity_2m", "uv_index", "wind_speed_10m", "precipitation"]
COLORS = ["#176B87", "#B14C32", "#4F7961", "#8058A5", "#B38322", "#377EB8"]


def load_data(path=DATA, verify_hash=True):
    path = Path(path)
    if verify_hash:
        audit = json.loads((ROOT / "docs/audit_2023_2025/summary.json").read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != audit["joined_dataset_sha256"]:
            raise ValueError("Dataset fingerprint differs from the audited version; rerun the audit first")
    frame = pd.read_csv(path)
    expected = {"city", "timestamp_utc", *FIELDS}
    if set(frame.columns) != expected or set(frame["city"]) != {"Faisalabad"}:
        raise ValueError("Unexpected schema or city")
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    expected_hours = pd.date_range("2023-01-01", "2025-12-31 23:00", freq="h", tz="UTC")
    actual_hours = pd.DatetimeIndex(frame["timestamp_utc"]).as_unit("ns")
    if not actual_hours.equals(expected_hours.as_unit("ns")):
        raise ValueError("Dataset must contain the exact complete audited UTC hourly grid")
    frame = frame.set_index("timestamp_utc")
    values = frame[list(FIELDS)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("EDA expects the audited finite numeric dataset")
    frame.index = frame.index.tz_convert("Asia/Karachi")
    frame.index.name = "time_pakistan"
    return frame


def runs(series):
    """Consecutive identical-value runs; lengths count hourly observations."""
    boundaries = np.flatnonzero(np.r_[True, series.to_numpy()[1:] != series.to_numpy()[:-1], True])
    return [{"start": series.index[a].isoformat(), "end": series.index[b-1].isoformat(),
             "hours": int(b-a), "value": float(series.iloc[a])}
            for a, b in zip(boundaries[:-1], boundaries[1:])]


def full_local_days(frame):
    """Exclude partial local days introduced by converting a UTC-bounded dataset."""
    counts = frame.groupby(frame.index.normalize()).size()
    return counts.index[counts == 24]


def local_day_summary(frame):
    daily = frame[list(FIELDS)].resample("D").mean()
    daily["precipitation"] = frame["precipitation"].resample("D").sum(min_count=24)
    # Do not publish arithmetic direction means.
    daily = daily.drop(columns="wind_direction_10m")
    return daily.loc[full_local_days(frame)]


def time_axes(ax):
    span_days = ax.get_xlim()[1] - ax.get_xlim()[0]
    if span_days > 365:
        locator = mdates.MonthLocator(bymonth=[1, 7], tz="Asia/Karachi")
        pattern = "%b\n%Y"
    elif span_days > 40:
        locator = mdates.MonthLocator(tz="Asia/Karachi")
        pattern = "%b\n%Y"
    else:
        locator = mdates.HourLocator(interval=6, tz="Asia/Karachi")
        pattern = "%d %b\n%H:%M"
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter(pattern, tz="Asia/Karachi"))


def save(fig, name, title, subtitle):
    height = fig.get_figheight()
    fig.suptitle(title, fontsize=17, x=0.055, y=1-0.15/height, va="top", ha="left", fontweight="bold")
    fig.text(0.055, 1-0.57/height, subtitle, fontsize=10, color="#505965", va="top")
    fig.text(0.055, 0.012, "Faisalabad | 2023-2025 UTC coverage | Open-Meteo / ECMWF ERA5 / CAMS | Modelled data", fontsize=8, color="#616977")
    fig.tight_layout(rect=(0.025, 0.045, 0.99, 1-0.95/height), h_pad=2.0)
    fig.savefig(OUT / "figures" / name, dpi=145, facecolor="white")
    plt.close(fig)


def event_plot(frame, center, filename, title):
    center = pd.Timestamp(center).tz_convert("Asia/Karachi")
    window = frame.loc[center-pd.Timedelta(hours=12):center+pd.Timedelta(hours=12)]
    fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
    fields = ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"]
    for ax, field, color in zip(axes, fields, COLORS):
        if field == "precipitation":
            ax.bar(window.index, window[field], width=0.032, color=color)
            ax.set_ylim(bottom=0)
            if window[field].max() == 0:
                ax.set_ylim(0, 1)
                ax.text(0.98, 0.8, "No rainfall in this window", ha="right", transform=ax.transAxes, color="#505965")
        else:
            ax.plot(window.index, window[field], "o-", color=color, markersize=3)
        ax.axvline(center, color="#333333", linestyle="--", alpha=0.7)
        ax.set_ylabel(FIELDS[field], fontsize=9)
        time_axes(ax)
    axes[-1].set_xlabel("Pakistan time (UTC+5); dashed line marks the flagged hour")
    save(fig, filename, title, "Read the same hour across all four panels; these are aligned model/reanalysis series.")
    window.to_csv(OUT / "tables" / filename.replace(".png", ".csv"))
    previous = frame.loc[center-pd.Timedelta(hours=1)]
    current = frame.loc[center]
    return {"time_pakistan": center.isoformat(), "previous": {k: float(previous[k]) for k in fields},
            "current": {k: float(current[k]) for k in fields}}


def build_eda(frame):
    for directory in (OUT / "figures", OUT / "tables"):
        directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.18,
                         "axes.axisbelow": True, "font.size": 10})
    description = frame[list(FIELDS)].describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
    description.loc["wind_direction_10m", ["mean", "std", "1%", "25%", "50%", "75%", "99%"]] = np.nan
    description.to_csv(OUT / "tables/description.csv")

    # 1. Histograms: use the same count interpretation in each separate unit.
    distribution_fields = [field for field in FIELDS if field != "wind_direction_10m"]
    fig, axes = plt.subplots(4, 2, figsize=(12, 12))
    for ax, field in zip(axes.flat, distribution_fields):
        ax.hist(frame[field], bins=40, color="#176B87", edgecolor="white", linewidth=0.3)
        ax.axvline(frame[field].mean(), color="#B14C32", linestyle="--", label="Mean")
        ax.axvline(frame[field].median(), color="#222222", linestyle=":", label="Median")
        ax.set_xlabel(FIELDS[field]); ax.set_ylabel("Hourly records")
    axes[0, 0].legend(fontsize=8)
    save(fig, "01_distributions.png", "1. Which values are common?", "A histogram groups values into bins; tall bars mean more hours in that range. Direction is analysed separately.")

    # 2. Time series: daily means, except rain totals; retain raw hourly data.
    daily = local_day_summary(frame)
    daily.to_csv(OUT / "tables/daily.csv")
    fig, axes = plt.subplots(6, 1, figsize=(12, 13), sharex=True)
    for ax, field, color in zip(axes, CORE, COLORS):
        ax.plot(daily.index, daily[field], color=color, linewidth=0.7)
        ax.set_ylabel("Rain (mm/day)" if field == "precipitation" else FIELDS[field], fontsize=9)
        time_axes(ax)
    save(fig, "02_daily_series.png", "2. How do conditions change over time?", "Daily averages smooth hourly noise; precipitation is summed. Incomplete boundary days are excluded.")

    # 3. Calendar-month distributions: full local months only for totals.
    monthly = frame[list(FIELDS)].groupby(frame.index.month).agg(["mean", "median", "min", "max"])
    monthly.to_csv(OUT / "tables/calendar_month.csv")
    fig, axes = plt.subplots(3, 2, figsize=(12, 11))
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for ax, field in zip(axes.flat, CORE):
        groups = [frame.loc[frame.index.month == month, field].to_numpy() for month in range(1, 13)]
        if field == "precipitation":
            totals = frame["precipitation"].resample("MS").sum()
            counts = frame["precipitation"].resample("MS").count()
            totals = totals[counts == totals.index.days_in_month*24]
            for year in (2023, 2024, 2025):
                selected = totals[totals.index.year == year]
                ax.plot(selected.index.month, selected, "o-", label=str(year))
            ax.set_xticks(range(1, 13), month_names, rotation=45)
            ax.set_ylabel("Rain total (mm/month)"); ax.legend(fontsize=8)
        else:
            ax.boxplot(groups, tick_labels=month_names, showfliers=False, widths=0.55,
                       medianprops={"color": "#B14C32"}, patch_artist=True,
                       boxprops={"facecolor": "#C9E1EA"})
            ax.tick_params(axis="x", rotation=45)
            ax.set_ylabel(FIELDS[field])
    save(fig, "03_monthly_patterns.png", "3. Look for seasonal patterns", "Boxes show the middle 50%, with a median line. Fliers are hidden only in the plot; no observations are removed.")

    # 4. Daily cycle in local time, stratified by broad meteorological seasons.
    season_map = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
                  6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}
    seasons = pd.Series(frame.index.month, index=frame.index).map(season_map)
    fig, axes = plt.subplots(3, 2, figsize=(12, 10))
    hourly = frame[list(FIELDS)].groupby(frame.index.hour).mean().drop(columns="wind_direction_10m")
    hourly.to_csv(OUT / "tables/local_hour_means.csv")
    for ax, field in zip(axes.flat, CORE):
        for season, color in zip(["DJF", "MAM", "JJA", "SON"], COLORS):
            selected = frame.loc[seasons == season, field]
            if field == "precipitation":
                selected = selected.gt(0.1).astype(float) * 100
            profile = selected.groupby(selected.index.hour).mean()
            ax.plot(profile.index, profile, color=color, label=season)
        ax.set_xticks([0, 4, 8, 12, 16, 20, 23]); ax.set_xlabel("Hour in Pakistan")
        ax.set_ylabel("Hours with rain >0.1 mm (%)" if field == "precipitation" else FIELDS[field])
    axes[0, 0].legend(fontsize=8, ncol=2)
    save(fig, "04_daily_cycles.png", "4. What repeats within a day?", "DJF=Dec-Feb, MAM=Mar-May, JJA=Jun-Aug, SON=Sep-Nov. Lines are averages, not forecasts or uncertainty bands.")

    # 5. Rain: separate occurrence from amount and test threshold sensitivity.
    rain = frame["precipitation"]
    rain_thresholds = pd.DataFrame([
        {"definition": label, "wet_hours": int(mask.sum()), "share_percent": float(mask.mean()*100)}
        for label, mask in [("amount > 0 mm", rain.gt(0)), ("amount > 0.1 mm", rain.gt(0.1)), ("amount >= 1 mm", rain.ge(1))]
    ])
    rain_thresholds.to_csv(OUT / "tables/rain_thresholds.csv", index=False)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    counts = [rain.eq(0).sum(), (rain.gt(0) & rain.le(0.1)).sum(), rain.gt(0.1).sum()]
    bars = axes[0].bar(["Zero", ">0 to 0.1", ">0.1"], counts, color=["#AEBBC2", "#7CB3C7", "#176B87"])
    axes[0].bar_label(bars, fontsize=9); axes[0].set_ylabel("Hourly records"); axes[0].set_xlabel("Rain amount (mm)")
    axes[1].hist(rain[rain > 0], bins=35, color="#176B87"); axes[1].set_yscale("log")
    axes[1].set_xlabel("Positive rain amount (mm)"); axes[1].set_ylabel("Count (log scale)")
    bars = axes[2].bar([">0", ">0.1", ">=1"], rain_thresholds["share_percent"], color="#377EB8")
    axes[2].bar_label(bars, fmt="%.2f%%", fontsize=9); axes[2].set_ylabel("Hours labelled wet (%)")
    axes[2].set_xlabel("Candidate threshold (mm)")
    save(fig, "05_rain_occurrence.png", "5. Rain amount and rain occurrence are different tasks", "The event threshold changes the positive class. These are exploratory definitions, not a finalized target or probability forecast.")

    # 6. Circular direction: north at top and clockwise; ignore calm direction.
    calm = frame["wind_speed_10m"] < 0.5
    direction = frame.loc[~calm, "wind_direction_10m"].mod(360).to_numpy()
    centers = np.arange(16)*22.5
    bins = np.floor(((direction + 11.25) % 360)/22.5).astype(int)
    counts = np.bincount(bins, minlength=16)
    shares = counts/counts.sum()*100
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(121, projection="polar")
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
    ax.bar(np.deg2rad(centers), shares, width=np.deg2rad(20), color="#176B87", alpha=0.85)
    ax.set_title("Direction the wind comes FROM\nRadial axis: % of non-calm hours", fontsize=10, pad=18)
    ax = fig.add_subplot(122)
    ax.hist(frame["wind_speed_10m"], bins=40, color="#176B87")
    ax.axvline(0.5, color="#B14C32", linestyle="--", label="Exploratory calm cutoff")
    ax.set_xlabel("Wind speed (m/s)"); ax.set_ylabel("Hourly records"); ax.legend(fontsize=8)
    save(fig, "06_wind_direction.png", "6. Wind direction wraps around a circle", "359 degrees and 1 degree are close. Direction frequency excludes speed <0.5 m/s; this cutoff is provisional.")
    pd.DataFrame({"sector_center_degrees": centers, "hours": counts, "share_noncalm_percent": shares}).to_csv(OUT / "tables/wind_sectors.csv", index=False)

    # 7. Correlation: exclude circular degrees; keep all paired hours.
    corr_fields = [field for field in FIELDS if field != "wind_direction_10m"]
    correlation = frame[corr_fields].corr(method="pearson")
    correlation.to_csv(OUT / "tables/correlations.csv")
    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(correlation, cmap="RdBu_r", vmin=-1, vmax=1)
    labels = ["Temp", "Humidity", "Rain", "Wind speed", "AQI", "PM2.5", "PM10", "UV"]
    ax.set_xticks(range(8), labels, rotation=40, ha="right"); ax.set_yticks(range(8), labels)
    for i in range(8):
        for j in range(8):
            value = correlation.iloc[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", color="white" if abs(value)>0.6 else "#222222", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Pearson correlation")
    ax.grid(False)
    save(fig, "07_correlations.png", "7. Which variables move together?", "Correlation describes linear association, not causation or forecasting skill. AQI is derived from pollutant series.")

    # 8. Autocorrelation on the hourly series, not on the smoothed daily chart.
    lags = np.arange(1, 73)
    autocorr = pd.DataFrame({field: [frame[field].autocorr(int(lag)) for lag in lags] for field in CORE}, index=lags)
    autocorr.index.name = "lag_hours"; autocorr.to_csv(OUT / "tables/autocorrelation.csv")
    fig, axes = plt.subplots(3, 2, figsize=(12, 10))
    for ax, field, color in zip(axes.flat, CORE, COLORS):
        ax.plot(lags, autocorr[field], color=color)
        ax.axhline(0, color="gray", linewidth=0.5)
        for lag in (24, 48, 72): ax.axvline(lag, color="gray", linestyle=":", linewidth=0.7)
        ax.set_ylim(-1, 1.02); ax.set_xticks([1, 12, 24, 48, 72])
        ax.set_xlabel("Lag (hours earlier)"); ax.set_ylabel("Correlation"); ax.set_title(FIELDS[field], fontsize=10)
    save(fig, "08_autocorrelation.png", "8. Does the past resemble the present?", "Lag 24 compares each value with the value 24 hours earlier. Persistence and seasonality can inflate correlation.")

    # 9-10. Investigate sharp changes using their surrounding variables.
    cooling = event_plot(frame, "2024-06-05T12:00Z", "09_cooling_event.png", "9. Investigate the largest temperature drop")
    warming = event_plot(frame, "2025-01-26T05:00Z", "10_warming_event.png", "10. Investigate a sharp winter warming")

    # 11. Longest AQI plateau: compare independent columns in the same source.
    plateau = max(runs(frame["us_aqi"]), key=lambda item: item["hours"])
    a, b = pd.Timestamp(plateau["start"]), pd.Timestamp(plateau["end"])
    window = frame.loc[a-pd.Timedelta(hours=12):b+pd.Timedelta(hours=12)]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    for ax, field, color in zip(axes, ["us_aqi", "pm2_5", "pm10"], COLORS):
        ax.plot(window.index, window[field], "o-", markersize=3, color=color)
        ax.axvspan(a, b+pd.Timedelta(hours=1), color="#E8D8A0", alpha=0.4)
        ax.set_ylabel(FIELDS[field]); time_axes(ax)
    axes[-1].set_xlabel("Pakistan time; shading covers the 21 hourly observations")
    save(fig, "11_aqi_plateau.png", "11. A constant AQI does not mean every input was constant", "Compare AQI with PM2.5 and PM10. Averaging windows and rounding are hypotheses, not a verified cause.")
    plateau_window = frame.loc[a:b]
    plateau["pm2_5_range"] = [float(plateau_window["pm2_5"].min()), float(plateau_window["pm2_5"].max())]
    plateau["pm10_range"] = [float(plateau_window["pm10"].min()), float(plateau_window["pm10"].max())]
    plateau["distinct_full_rows"] = int(plateau_window[list(FIELDS)].drop_duplicates().shape[0])
    window.to_csv(OUT / "tables/aqi_plateau_window.csv")

    # 12. Dry run context and UV clock-hour check.
    dry = max((item for item in runs(rain) if item["value"] == 0), key=lambda item: item["hours"])
    a, b = pd.Timestamp(dry["start"]), pd.Timestamp(dry["end"])
    window = frame.loc[a-pd.Timedelta(days=7):b+pd.Timedelta(days=7)]
    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    total = window["precipitation"].resample("D").sum()
    axes[0].bar(total.index, total, color="#377EB8", width=0.8)
    axes[0].axvspan(a, b+pd.Timedelta(hours=1), color="#E8D8A0", alpha=0.4)
    axes[0].set_ylabel("Daily rain (mm)"); time_axes(axes[0])
    zero_uv = frame["uv_index"].eq(0).groupby(frame.index.hour).mean()*100
    axes[1].bar(zero_uv.index, zero_uv, color="#8058A5")
    axes[1].set_xlabel("Hour in Pakistan"); axes[1].set_ylabel("Hours with UV = 0 (%)")
    axes[1].set_xticks(range(0, 24, 2)); axes[1].set_ylim(0, 105)
    save(fig, "12_zero_values.png", "12. Zero is a value, not a missing observation", "Top: longest dry run with surrounding rainfall. Bottom: UV zeros by local hour; no solar-position model is used.")

    # 13. Check whether large changes cluster at one clock hour, rather than
    # attributing a single selected event to a weather mechanism.
    delta = frame["temperature_2m"].diff()
    jump_counts = delta.abs().ge(6).groupby(frame.index.hour).sum()
    typical_change = delta.abs().groupby(frame.index.hour).median()
    pd.DataFrame({"large_changes_abs_ge_6_C": jump_counts,
                  "median_absolute_change_C": typical_change}).to_csv(OUT / "tables/temperature_changes_by_hour.csv")
    diagnostic = ROOT / "data/diagnostics/era5_land_2025_01_26.json"
    comparison_metadata = None
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    axes[0].bar(typical_change.index, typical_change, color="#176B87")
    axes[0].set_ylabel("Median absolute change (C)")
    axes[1].bar(jump_counts.index, jump_counts, color="#B14C32")
    axes[1].set_ylabel("Changes >=6 C (count)")
    for ax in axes[:2]:
        ax.set_xlabel("Hour in Pakistan"); ax.set_xticks(range(0, 24, 2))
    if diagnostic.exists():
        record = json.loads(diagnostic.read_text(encoding="utf-8"))
        canonical = json.dumps(record["response"], sort_keys=True, allow_nan=False).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != record["response_sha256"]:
            raise ValueError("ERA5-Land diagnostic fingerprint mismatch")
        hourly = record["response"]["hourly"]
        index = pd.to_datetime(hourly["time"], utc=True).tz_convert("Asia/Karachi")
        comparison = pd.DataFrame({"era5_land_temperature_C": hourly["temperature_2m"]}, index=index)
        comparison["era5_temperature_C"] = frame.loc[index, "temperature_2m"]
        comparison.to_csv(OUT / "tables/warming_source_comparison.csv", index_label="time_pakistan")
        for field, color in zip(comparison.columns, COLORS):
            axes[2].plot(comparison.index, comparison[field], "o-", label=field.replace("_temperature_C", ""), color=color, markersize=3)
        axes[2].set_ylabel("Temperature (C)"); axes[2].legend(); time_axes(axes[2])
        axes[2].set_xlabel("26 January 2025, Pakistan time; related reanalysis products")
        comparison_metadata = {key: value for key, value in record.items() if key != "response"}
        (OUT / "warming_source_manifest.json").write_text(json.dumps(comparison_metadata, indent=2) + "\n", encoding="utf-8")
    else:
        for stale in (OUT / "tables/warming_source_comparison.csv", OUT / "warming_source_manifest.json"):
            if stale.exists():
                stale.unlink()
        axes[2].text(0.5, 0.5, "Optional source comparison not downloaded.\nRun python scripts/check_warming_source.py, then rerun EDA.", ha="center", va="center", transform=axes[2].transAxes)
        axes[2].set_axis_off()
    save(fig, "13_temperature_timing.png", "13. Is the sharp warming an isolated event?", "A repeated clock-hour pattern needs source investigation. ERA5-Land is related to ERA5, not independent station truth.")

    # Save facts used in the narrative; never modify the input table.
    night = frame.index.hour <= 3
    season_stats = frame[CORE].groupby(seasons).mean().drop(columns="precipitation")
    season_stats.to_csv(OUT / "tables/season_means.csv")
    largest_temp = frame["temperature_2m"].diff().abs().nlargest(10)
    largest_temp.to_csv(OUT / "tables/largest_temperature_changes.csv", header=["absolute_change_C"])
    facts = {
        "dataset_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
        "rows": len(frame), "local_start": frame.index[0].isoformat(), "local_end": frame.index[-1].isoformat(),
        "complete_local_days": len(daily), "temperature_cooling": cooling, "temperature_warming": warming,
        "aqi_plateau": plateau, "longest_dry_run": dry,
        "rain_zero_hours": int(rain.eq(0).sum()), "rain_positive_hours": int(rain.gt(0).sum()),
        "rain_zero_percent": float(rain.eq(0).mean()*100),
        "rain_thresholds": rain_thresholds.to_dict(orient="records"),
        "uv_zero_percent": float(frame["uv_index"].eq(0).mean()*100),
        "uv_core_night_hours": int(night.sum()),
        "uv_positive_core_night_hours": int(frame.loc[night, "uv_index"].gt(0).sum()),
        "wind_calm_hours_below_0_5": int(calm.sum()), "wind_dominant_sector_center": float(centers[np.argmax(counts)]),
        "pm10_below_pm2_5_hours": int(frame["pm10"].lt(frame["pm2_5"]).sum()),
        "temperature_changes_ge_6_C_by_local_hour": {str(key): int(value) for key, value in jump_counts.items()},
        "warming_source_comparison": comparison_metadata,
        "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
    }
    (OUT / "findings.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(facts, indent=2))
    return facts


if __name__ == "__main__":
    build_eda(load_data())
