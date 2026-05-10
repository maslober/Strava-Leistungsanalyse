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


def summarize_activity(df: pd.DataFrame, session_summary: dict | None = None) -> pd.DataFrame:
    session_summary = session_summary or {}

    metrics: list[tuple[str, object]] = []

    if not df.empty:
        duration_seconds = None
        if "elapsed_seconds" in df.columns:
            duration_seconds = float(df["elapsed_seconds"].max())
        elif "timestamp" in df.columns:
            duration_seconds = float((df["timestamp"].max() - df["timestamp"].min()).total_seconds())

        if duration_seconds is not None:
            metrics.append(("Dauer (min)", round(duration_seconds / 60, 2)))

        if "distance_km" in df.columns:
            metrics.append(("Distanz (km)", round(float(df["distance_km"].max()), 2)))

        if "altitude_m" in df.columns:
            altitude_gain = float(df["altitude_m"].diff().clip(lower=0).sum())
            metrics.append(("Höhenmeter positiv (m)", round(altitude_gain, 0)))

        for col, label in [
            ("speed_kmh", "Ø Geschwindigkeit (km/h)"),
            ("heart_rate", "Ø Herzfrequenz (bpm)"),
            ("power", "Ø Leistung (W)"),
            ("cadence", "Ø Kadenz (rpm)"),
        ]:
            if col in df.columns and df[col].notna().any():
                metrics.append((label, round(float(df[col].mean()), 2)))

        for col, label in [
            ("speed_kmh", "Max Geschwindigkeit (km/h)"),
            ("heart_rate", "Max Herzfrequenz (bpm)"),
            ("power", "Max Leistung (W)"),
        ]:
            if col in df.columns and df[col].notna().any():
                metrics.append((label, round(float(df[col].max()), 2)))

    for key, label in [
        ("sport", "Sportart"),
        ("sub_sport", "Unterkategorie"),
    ]:
        value = session_summary.get(key)
        if value is not None:
            metrics.append((label, value))

    return pd.DataFrame(metrics, columns=["Kennzahl", "Wert"])


def rolling_best_efforts(df: pd.DataFrame, column: str = "power", windows: Iterable[int] = (5, 30, 60, 300, 1200)) -> pd.DataFrame:
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
        return pd.DataFrame(columns=["Zone", "Bereich", "Anteil (%)"])

    hr = pd.to_numeric(df["heart_rate"], errors="coerce").dropna()
    if hr.empty:
        return pd.DataFrame(columns=["Zone", "Bereich", "Anteil (%)"])

    zones = [
        ("Z1", 0.00, 0.60),
        ("Z2", 0.60, 0.70),
        ("Z3", 0.70, 0.80),
        ("Z4", 0.80, 0.90),
        ("Z5", 0.90, 1.01),
    ]

    rows = []
    total = len(hr)
    for name, lower, upper in zones:
        lower_val = hr_max * lower
        upper_val = hr_max * upper
        if upper >= 1.0:
            mask = hr >= lower_val
            range_label = f">= {lower_val:.0f}"
        else:
            mask = (hr >= lower_val) & (hr < upper_val)
            range_label = f"{lower_val:.0f} - {upper_val:.0f}"
        rows.append(
            {
                "Zone": name,
                "Bereich": range_label,
                "Anteil (%)": round(mask.sum() / total * 100, 2),
            }
        )

    return pd.DataFrame(rows)
