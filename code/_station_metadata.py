"""
Station metadata management.

Loads buoy station definitions from YAML and provides a unified interface
to access location data, configuration, and historical timeseries.
"""

import os
import yaml
import pandas as pd
from pathlib import Path


def load_station_config(config_file="data/stations.yaml"):
    """
    Load station metadata from YAML.

    Returns:
        dict: {station_id: {name, description, lat, lon, depth_m, ...}}
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Station config not found: {config_file}")

    with open(config_file, "r") as f:
        data = yaml.safe_load(f)

    return data.get("stations", {})


def get_station(station_id, config_file="data/stations.yaml"):
    """
    Fetch metadata for a single station by ID.

    Args:
        station_id: NDBC buoy ID (e.g., "46087")
        config_file: path to stations.yaml

    Returns:
        dict with keys: name, description, lat, lon, depth_m, region, etc.
        Raises KeyError if station not found.
    """
    config = load_station_config(config_file)
    if station_id not in config:
        raise KeyError(f"Unknown station: {station_id}. Available: {list(config.keys())}")
    return config[station_id]


def load_buoy_timeseries(station_id, data_dir="data/buoy_archive"):
    """
    Load wind and wave timeseries for a station from parquet.

    Args:
        station_id: NDBC buoy ID
        data_dir: directory containing {station_id}/timeseries.parquet

    Returns:
        pd.DataFrame with columns: datetime, WDIR, WSPD, WVHT, DPD, MWD, etc.
        Returns empty DataFrame if file doesn't exist yet.
    """
    path = Path(data_dir) / station_id / "timeseries.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def save_buoy_timeseries(df, station_id, data_dir="data/buoy_archive"):
    """
    Save or append wind/wave timeseries to parquet.

    Args:
        df: DataFrame with datetime index (or datetime column) and columns
            like WDIR, WSPD, WVHT, DPD, MWD, etc.
        station_id: NDBC buoy ID
        data_dir: destination directory

    Ensures the directory exists and merges with any existing data,
    removing duplicates by datetime.
    """
    base = Path(data_dir) / station_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / "timeseries.parquet"

    # Ensure datetime is a column
    if df.index.name == "datetime" or isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()

    # Merge with existing data if present
    if path.exists():
        existing = pd.read_parquet(path)
        df = pd.concat([existing, df], ignore_index=True)

    # Deduplicate by datetime (keep first)
    if "datetime" in df.columns:
        df = df.drop_duplicates(subset=["datetime"])
        df = df.sort_values("datetime")

    df.to_parquet(path, index=False)


def get_all_stations(config_file="data/stations.yaml"):
    """
    Return all station IDs from the config.

    Returns:
        list of station ID strings
    """
    config = load_station_config(config_file)
    return list(config.keys())


def get_station_dataframe(config_file="data/stations.yaml"):
    """
    Build a DataFrame from station metadata for easy plotting/filtering.

    Returns:
        pd.DataFrame with one row per station, columns: station_id, name,
        lat, lon, depth_m, description, region, etc.
    """
    config = load_station_config(config_file)
    rows = []
    for sid, info in config.items():
        row = {"station_id": sid}
        row.update(info)
        rows.append(row)
    return pd.DataFrame(rows)


# Convenience: allow scripts to do `from _station_metadata import STATION_IDS`
CONFIG = load_station_config()
STATION_IDS = list(CONFIG.keys())

if __name__ == "__main__":
    # Quick test
    print("=== Loaded Stations ===")
    for sid in STATION_IDS:
        s = get_station(sid)
        print(f"  {sid}: {s['name']:20s} @ ({s['lat']:7.3f}°N, {s['lon']:8.3f}°W)")

    print("\n=== Station DataFrame ===")
    df = get_station_dataframe()
    print(df[["station_id", "name", "lat", "lon", "region"]])
