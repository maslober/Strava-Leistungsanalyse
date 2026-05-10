from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fitparse import FitFile


RECORD_FIELDS = {
    "timestamp",
    "distance",
    "heart_rate",
    "power",
    "cadence",
    "altitude",
    "speed",
    "temperature",
    "position_lat",
    "position_long",
    "enhanced_speed",
    "enhanced_altitude",
    "grade",
}


SESSION_FIELDS = {
    "total_timer_time",
    "total_elapsed_time",
    "total_distance",
    "total_ascent",
    "total_descent",
    "avg_speed",
    "max_speed",
    "avg_heart_rate",
    "max_heart_rate",
    "avg_power",
    "max_power",
    "avg_cadence",
    "max_temperature",
    "avg_temperature",
    "sport",
    "sub_sport",
}


def _safe_value(value: Any) -> Any:
    return value if value is not None else None


def load_fit_records(file_path: str | Path) -> pd.DataFrame:
    """Liest Record-Messages aus einer FIT-Datei und gibt ein DataFrame zurück."""
    file_path = Path(file_path)
    fitfile = FitFile(str(Path(file_path).resolve()))

    rows: list[dict[str, Any]] = []
    for record in fitfile.get_messages("record"):
        row: dict[str, Any] = {}
        for field in record:
            if field.name in RECORD_FIELDS:
                row[field.name] = _safe_value(field.value)
        if row:
            rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp").reset_index(drop=True)
        df["elapsed_seconds"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()

    if "distance" in df.columns:
        df["distance_km"] = df["distance"] / 1000.0

    speed_source = None
    if "enhanced_speed" in df.columns:
        speed_source = "enhanced_speed"
    elif "speed" in df.columns:
        speed_source = "speed"

    if speed_source is not None:
        df["speed_m_s"] = df[speed_source]
        df["speed_kmh"] = df["speed_m_s"] * 3.6

    altitude_source = None
    if "enhanced_altitude" in df.columns:
        altitude_source = "enhanced_altitude"
    elif "altitude" in df.columns:
        altitude_source = "altitude"

    if altitude_source is not None:
        df["altitude_m"] = df[altitude_source]

    return df


def load_fit_session_summary(file_path: str | Path) -> dict[str, Any]:
    """Liest Session-Metadaten aus einer FIT-Datei."""
    file_path = Path(file_path)
    fitfile = FitFile(file_path)

    summary: dict[str, Any] = {}
    for session in fitfile.get_messages("session"):
        for field in session:
            if field.name in SESSION_FIELDS:
                summary[field.name] = _safe_value(field.value)
        break

    if "total_distance" in summary and summary["total_distance"] is not None:
        summary["total_distance_km"] = summary["total_distance"] / 1000.0

    if "avg_speed" in summary and summary["avg_speed"] is not None:
        summary["avg_speed_kmh"] = summary["avg_speed"] * 3.6

    if "max_speed" in summary and summary["max_speed"] is not None:
        summary["max_speed_kmh"] = summary["max_speed"] * 3.6

    return summary


def find_first_fit_file(data_dir: str | Path = "data/raw") -> Path:
    data_dir = Path(data_dir)
    files = sorted(data_dir.glob("*.fit"))
    if not files:
        raise FileNotFoundError(
            f"Keine .fit-Datei in '{data_dir}' gefunden. Bitte lege eine FIT-Datei in diesen Ordner."
        )
    return files[0]
