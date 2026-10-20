"""Canonical filesystem locations for the project.

Every module resolves its inputs and outputs through these constants rather
than using paths relative to the current working directory, so the pipeline
behaves the same whether it is launched from the repo root, from cron, or
from GitHub Actions.
"""

from pathlib import Path

# salish/paths.py -> salish/ -> repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA = PROJECT_ROOT / "data"
ARTIFACTS = PROJECT_ROOT / "artifacts"

# Inputs
BATHYMETRY = DATA / "bathymetry_file"
HISTORIC = DATA / "historic"
STATUS = DATA / "status"
STATIONS_YAML = DATA / "stations.yaml"

# Derived / fetched data
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
PREDICTED = DATA / "predicted"
AIRYWAVES = DATA / "airywaves"
BUOY_ARCHIVE = DATA / "buoy_archive"

# Deliverables
PLOTS = ARTIFACTS / "plots"
FRAMES = ARTIFACTS / "frames"


def ensure_dirs() -> None:
    """Create the directories the pipeline writes into."""
    for d in (RAW, PROCESSED, PREDICTED, STATUS, HISTORIC,
              PLOTS, PLOTS / "waves", PLOTS / "wind",
              PLOTS / "tidecurrent", PLOTS / "maps"):
        d.mkdir(parents=True, exist_ok=True)
