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
    "start_time",
    "timestamp",
}


def _safe_value(value: Any) -> Any:
    return value if value is not None else None


def _open_fit_file(file_path: str | Path) -> FitFile:
    file_path = Path(file_path)
    return FitFile(str(file_path.resolve()))


def load_fit_records(file_path: str | Path) -> pd.DataFrame:
    """Liest Record-Messages aus einer FIT-Datei und gibt ein DataFrame zurück."""
    file_path = Path(file_path)
    fitfile = _open_fit_file(file_path)

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
        df["distance_km"] = pd.to_numeric(df["distance"], errors="coerce") / 1000.0

    speed_source = None
    if "enhanced_speed" in df.columns:
        speed_source = "enhanced_speed"
    elif "speed" in df.columns:
        speed_source = "speed"

    if speed_source is not None:
        df["speed_m_s"] = pd.to_numeric(df[speed_source], errors="coerce")
        df["speed_kmh"] = df["speed_m_s"] * 3.6

    altitude_source = None
    if "enhanced_altitude" in df.columns:
        altitude_source = "enhanced_altitude"
    elif "altitude" in df.columns:
        altitude_source = "altitude"

    if altitude_source is not None:
        df["altitude_m"] = pd.to_numeric(df[altitude_source], errors="coerce")

    for col in ["heart_rate", "power", "cadence", "temperature", "grade"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["source_file"] = file_path.name
    return df


def load_fit_session_summary(file_path: str | Path) -> dict[str, Any]:
    """Liest Session-Metadaten aus einer FIT-Datei."""
    file_path = Path(file_path)
    fitfile = _open_fit_file(file_path)

    summary: dict[str, Any] = {"file_name": file_path.name}
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


def find_fit_files(data_dir: str | Path = "data/raw") -> list[Path]:
    data_dir = Path(data_dir)
    files = sorted(data_dir.glob("*.fit"))
    if not files:
        raise FileNotFoundError(
            f"Keine .fit-Datei in '{data_dir}' gefunden. Bitte lege mindestens eine FIT-Datei in diesen Ordner."
        )
    return files


def find_first_fit_file(data_dir: str | Path = "data/raw") -> Path:
    return find_fit_files(data_dir)[0]


def find_latest_fit_file(data_dir: str | Path = "data/raw") -> Path:
    files = find_fit_files(data_dir)
    return max(files, key=lambda p: p.stat().st_mtime)


def load_multiple_fit_activities(data_dir: str | Path = "data/raw") -> dict[str, pd.DataFrame]:
    activities: dict[str, pd.DataFrame] = {}
    for fit_file in find_fit_files(data_dir):
        activities[fit_file.name] = load_fit_records(fit_file)
    return activities
