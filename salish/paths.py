"""Canonical filesystem locations for the project.

Every module resolves its inputs and outputs through these constants rather
than using paths relative to the current working directory, so the pipeline
behaves the same whether it is launched from the repo root, from cron, or
from GitHub Actions.

Layout:
    config/            hand-edited settings (station list, ...)
    data/raw/          data exactly as downloaded; safe to delete and refetch
    data/processed/    cleaned data and model outputs derived from raw/
    data/state/        small cross-run state the pipeline reads back next run
    artifacts/         deliverables: plots, the website, simulation output
"""

from pathlib import Path

# salish/paths.py -> salish/ -> repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG = PROJECT_ROOT / "config"
DATA = PROJECT_ROOT / "data"
ARTIFACTS = PROJECT_ROOT / "artifacts"

# Configuration
STATIONS_YAML = CONFIG / "stations.yaml"
PIPELINE_YAML = CONFIG / "pipeline.yaml"

# Raw: downloaded as-is
RAW = DATA / "raw"
RAW_BUOYS = RAW / "ndbc"
RAW_BATHYMETRY = RAW / "bathymetry"
GRIB_CACHE = RAW  # Herbie appends <model>/<YYYYMMDD>/ itself
CARTOPY_CACHE = RAW / "cartopy"

# Processed: cleaned and derived
PROCESSED = DATA / "processed"
PROCESSED_BUOYS = PROCESSED / "buoys"
HISTORIC = PROCESSED / "historic"
BUOY_ARCHIVE = PROCESSED / "buoy_archive"
BATHYMETRY = PROCESSED / "bathymetry"
PREDICTIONS = PROCESSED / "predictions"
AIRYWAVES = PROCESSED / "airywaves"

# State carried between runs (alert dedup)
STATE = DATA / "state"
ALERT_STATUS = STATE / "alerts"

# Deliverables
PLOTS = ARTIFACTS / "plots"
SITE = ARTIFACTS / "site"
SIMULATIONS = ARTIFACTS / "simulations"
FRAMES = SIMULATIONS / "frames"


def ensure_dirs() -> None:
    """Create the directories the pipeline writes into."""
    for d in (RAW_BUOYS, PROCESSED_BUOYS, HISTORIC, PREDICTIONS, ALERT_STATUS,
              SITE, PLOTS, PLOTS / "waves", PLOTS / "wind",
              PLOTS / "tidecurrent", PLOTS / "maps"):
        d.mkdir(parents=True, exist_ok=True)
