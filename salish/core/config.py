"""Load config/pipeline.yaml and resolve the names it refers to."""

import yaml

from salish.core.stations import get_station
from salish.paths import PIPELINE_YAML


def load_pipeline_config(path=PIPELINE_YAML):
    with open(path) as f:
        return yaml.safe_load(f)


def place(cfg, name):
    """(lat, lon) of a named place in config, or of a buoy if given its id."""
    if name in cfg["places"]:
        lat, lon = cfg["places"][name]
        return lat, lon
    station = get_station(str(name))
    return station["lat"], station["lon"]
