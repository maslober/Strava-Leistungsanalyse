from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


METRIC_LABELS = {
    "power": "Leistung (W)",
    "heart_rate": "Herzfrequenz (bpm)",
    "cadence": "Kadenz (rpm)",
    "speed_kmh": "Geschwindigkeit (km/h)",
    "altitude_m": "Höhe (m)",
    "temperature": "Temperatur (°C)",
}


def _duration_series_seconds(df: pd.DataFrame) -> pd.Series:
    if "elapsed_seconds" not in df.columns or df.empty:
        return pd.Series([1.0] * len(df), index=df.index, dtype=float)

    deltas = pd.to_numeric(df["elapsed_seconds"], errors="coerce").diff().fillna(0)
    positive = deltas[deltas > 0]
    default_step = float(positive.median()) if not positive.empty else 1.0
    deltas = deltas.where(deltas > 0, default_step)
    return deltas.astype(float)


def summarize_activity(df: pd.DataFrame, session_summary: dict | None = None) -> pd.DataFrame:
    session_summary = session_summary or {}

    metrics: list[tuple[str, object]] = []
    file_name = session_summary.get("file_name") or df.get("source_file", pd.Series([None])).iloc[0]
    if file_name is not None:
        metrics.append(("Datei", file_name))

    if not df.empty:
        duration_seconds = None
        if "elapsed_seconds" in df.columns:
            duration_seconds = float(pd.to_numeric(df["elapsed_seconds"], errors="coerce").max())
        elif "timestamp" in df.columns:
            duration_seconds = float((df["timestamp"].max() - df["timestamp"].min()).total_seconds())

        if duration_seconds is not None and not np.isnan(duration_seconds):
            metrics.append(("Dauer (min)", round(duration_seconds / 60, 2)))

        if "distance_km" in df.columns and df["distance_km"].notna().any():
            metrics.append(("Distanz (km)", round(float(df["distance_km"].max()), 2)))

        if "altitude_m" in df.columns and df["altitude_m"].notna().any():
            altitude_gain = float(pd.to_numeric(df["altitude_m"], errors="coerce").diff().clip(lower=0).sum())
            metrics.append(("Höhenmeter positiv (m)", round(altitude_gain, 0)))

        for col, label in [
            ("speed_kmh", "Ø Geschwindigkeit (km/h)"),
            ("heart_rate", "Ø Herzfrequenz (bpm)"),
            ("power", "Ø Leistung (W)"),
            ("cadence", "Ø Kadenz (rpm)"),
        ]:
            if col in df.columns and df[col].notna().any():
                metrics.append((label, round(float(pd.to_numeric(df[col], errors="coerce").mean()), 2)))

        for col, label in [
            ("speed_kmh", "Max Geschwindigkeit (km/h)"),
            ("heart_rate", "Max Herzfrequenz (bpm)"),
            ("power", "Max Leistung (W)"),
        ]:
            if col in df.columns and df[col].notna().any():
                metrics.append((label, round(float(pd.to_numeric(df[col], errors="coerce").max()), 2)))

    for key, label in [
        ("sport", "Sportart"),
        ("sub_sport", "Unterkategorie"),
    ]:
        value = session_summary.get(key)
        if value is not None:
            metrics.append((label, value))

    return pd.DataFrame(metrics, columns=["Kennzahl", "Wert"])


def rolling_best_efforts(
    df: pd.DataFrame,
    column: str = "power",
    windows: Iterable[int] = (5, 30, 60, 300, 1200),
) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=["Fenster (s)", "Bestwert"])

    work = df[[column]].copy()
    work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna()
    if work.empty:
        return pd.DataFrame(columns=["Fenster (s)", "Bestwert"])

    values = []
    for window in windows:
        if len(work) >= window:
            best = work[column].rolling(window=window, min_periods=window).mean().max()
            values.append({"Fenster (s)": window, "Bestwert": round(float(best), 2)})
    return pd.DataFrame(values)


def add_time_bins(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "elapsed_seconds" in out.columns:
        out["elapsed_minutes"] = out["elapsed_seconds"] / 60.0
        out["elapsed_hours"] = out["elapsed_seconds"] / 3600.0
    return out


def available_metrics(df: pd.DataFrame) -> list[str]:
    return [metric for metric in METRIC_LABELS if metric in df.columns and df[metric].notna().any()]


def correlation_matrix(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return pd.DataFrame()
    return df[cols].apply(pd.to_numeric, errors="coerce").corr(numeric_only=True)


def heart_rate_zones(df: pd.DataFrame, hr_max: int = 190) -> pd.DataFrame:
    if "heart_rate" not in df.columns:
        return pd.DataFrame(columns=["Zone", "Bereich", "Dauer (min)", "Anteil (%)"])

    hr = pd.to_numeric(df["heart_rate"], errors="coerce")
    duration = _duration_series_seconds(df)
    valid = hr.notna()
    if not valid.any():
        return pd.DataFrame(columns=["Zone", "Bereich", "Dauer (min)", "Anteil (%)"])

    hr = hr[valid]
    duration = duration[valid]

    zones = [
        ("Z1", 0.00, 0.60),
        ("Z2", 0.60, 0.70),
        ("Z3", 0.70, 0.80),
        ("Z4", 0.80, 0.90),
        ("Z5", 0.90, 1.01),
    ]

    total_seconds = float(duration.sum()) if len(duration) else 0.0
    rows = []
    for name, lower, upper in zones:
        lower_val = hr_max * lower
        upper_val = hr_max * upper
        if upper >= 1.0:
            mask = hr >= lower_val
            range_label = f">= {lower_val:.0f} bpm"
        else:
            mask = (hr >= lower_val) & (hr < upper_val)
            range_label = f"{lower_val:.0f} - {upper_val:.0f} bpm"
        zone_seconds = float(duration[mask].sum())
        rows.append(
            {
                "Zone": name,
                "Bereich": range_label,
                "Dauer (min)": round(zone_seconds / 60.0, 2),
                "Anteil (%)": round((zone_seconds / total_seconds * 100.0) if total_seconds else 0.0, 2),
            }
        )

    return pd.DataFrame(rows)


def estimate_ftp(df: pd.DataFrame, default_window_seconds: int = 1200) -> dict[str, float | int | None]:
    if "power" not in df.columns:
        return {
            "ftp_estimated": None,
            "best_20min_power": None,
            "window_seconds": default_window_seconds,
            "method": "Keine Leistungsdaten verfügbar",
        }

    power = pd.to_numeric(df["power"], errors="coerce").dropna()
    if len(power) < default_window_seconds:
        return {
            "ftp_estimated": None,
            "best_20min_power": None,
            "window_seconds": default_window_seconds,
            "method": "Zu wenig Daten für 20-Minuten-Schätzung",
        }

    best_20min = float(power.rolling(window=default_window_seconds, min_periods=default_window_seconds).mean().max())
    ftp_estimated = round(best_20min * 0.95, 2)
    return {
        "ftp_estimated": ftp_estimated,
        "best_20min_power": round(best_20min, 2),
        "window_seconds": default_window_seconds,
        "method": "FTP-Schätzung = 95% der besten 20-Minuten-Leistung",
    }


def power_zones(df: pd.DataFrame, ftp: float | None = None) -> pd.DataFrame:
    if "power" not in df.columns:
        return pd.DataFrame(columns=["Zone", "Bereich", "Dauer (min)", "Anteil (%)"])

    if ftp is None or ftp <= 0:
        ftp_info = estimate_ftp(df)
        ftp = ftp_info.get("ftp_estimated")

    if ftp is None or ftp <= 0:
        return pd.DataFrame(columns=["Zone", "Bereich", "Dauer (min)", "Anteil (%)"])

    power = pd.to_numeric(df["power"], errors="coerce")
    duration = _duration_series_seconds(df)
    valid = power.notna()
    if not valid.any():
        return pd.DataFrame(columns=["Zone", "Bereich", "Dauer (min)", "Anteil (%)"])

    power = power[valid]
    duration = duration[valid]

    zones = [
        ("Z1", 0.00, 0.55, "Aktive Erholung"),
        ("Z2", 0.55, 0.75, "Grundlage"),
        ("Z3", 0.75, 0.90, "Tempo"),
        ("Z4", 0.90, 1.05, "Schwelle"),
        ("Z5", 1.05, 1.20, "VO2max"),
        ("Z6", 1.20, 1.50, "Anaerob"),
        ("Z7", 1.50, np.inf, "Neuromuskulär"),
    ]

    total_seconds = float(duration.sum()) if len(duration) else 0.0
    rows = []
    for zone_name, lower, upper, label in zones:
        lower_val = ftp * lower
        upper_val = ftp * upper if np.isfinite(upper) else np.inf
        if np.isfinite(upper_val):
            mask = (power >= lower_val) & (power < upper_val)
            range_label = f"{lower_val:.0f} - {upper_val:.0f} W ({label})"
        else:
            mask = power >= lower_val
            range_label = f">= {lower_val:.0f} W ({label})"

        zone_seconds = float(duration[mask].sum())
        rows.append(
            {
                "Zone": zone_name,
                "Bereich": range_label,
                "Dauer (min)": round(zone_seconds / 60.0, 2),
                "Anteil (%)": round((zone_seconds / total_seconds * 100.0) if total_seconds else 0.0, 2),
            }
        )

    return pd.DataFrame(rows)


def compare_activities(activity_map: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for file_name, df in activity_map.items():
        row: dict[str, object] = {"Datei": file_name}
        if df.empty:
            rows.append(row)
            continue

        if "timestamp" in df.columns and df["timestamp"].notna().any():
            start_time = df["timestamp"].min()
            row["Datum"] = pd.to_datetime(start_time).strftime("%Y-%m-%d %H:%M")

        if "elapsed_seconds" in df.columns and df["elapsed_seconds"].notna().any():
            row["Dauer (min)"] = round(float(df["elapsed_seconds"].max()) / 60.0, 2)

        if "distance_km" in df.columns and df["distance_km"].notna().any():
            row["Distanz (km)"] = round(float(df["distance_km"].max()), 2)

        if "speed_kmh" in df.columns and df["speed_kmh"].notna().any():
            row["Ø Geschwindigkeit (km/h)"] = round(float(df["speed_kmh"].mean()), 2)
            row["Max Geschwindigkeit (km/h)"] = round(float(df["speed_kmh"].max()), 2)

        if "heart_rate" in df.columns and df["heart_rate"].notna().any():
            row["Ø Herzfrequenz (bpm)"] = round(float(df["heart_rate"].mean()), 2)
            row["Max Herzfrequenz (bpm)"] = round(float(df["heart_rate"].max()), 2)

        if "power" in df.columns and df["power"].notna().any():
            row["Ø Leistung (W)"] = round(float(df["power"].mean()), 2)
            row["Max Leistung (W)"] = round(float(df["power"].max()), 2)
            ftp_info = estimate_ftp(df)
            row["FTP geschätzt (W)"] = ftp_info.get("ftp_estimated")

        if "altitude_m" in df.columns and df["altitude_m"].notna().any():
            row["Höhenmeter positiv (m)"] = round(float(df["altitude_m"].diff().clip(lower=0).sum()), 0)

        rows.append(row)

    compare_df = pd.DataFrame(rows)
    preferred_cols = [
        "Datei",
        "Datum",
        "Dauer (min)",
        "Distanz (km)",
        "Höhenmeter positiv (m)",
        "Ø Geschwindigkeit (km/h)",
        "Max Geschwindigkeit (km/h)",
        "Ø Herzfrequenz (bpm)",
        "Max Herzfrequenz (bpm)",
        "Ø Leistung (W)",
        "Max Leistung (W)",
        "FTP geschätzt (W)",
    ]
    existing_cols = [c for c in preferred_cols if c in compare_df.columns]
    other_cols = [c for c in compare_df.columns if c not in existing_cols]
    return compare_df[existing_cols + other_cols].sort_values(by="Datum", ascending=False, na_position="last")
