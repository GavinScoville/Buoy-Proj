"""Decide whether a spot is on watch, from the rules in config/pipeline.yaml."""

import pandas as pd

from salish.core.config import place
from salish.core.geodesy import angle_diff, bearing
from salish.processing.conditions import setstatus


def travel_bearing(obs):
    """Direction the waves are travelling TOWARD (MWD is where they come from)."""
    return (obs["MWD"] + 180) % 360


def evaluate(cfg, spot, obs):
    """
    Return (status, reason): status 1 (watch) when every rule in the spot's
    `alert` block passes, else 0 with the first rule that failed.
    """
    rules = spot["alert"]
    missing = [k for k in ("WVHT", "DPD", "MWD") if pd.isna(obs.get(k))]
    if missing:
        return 0, f"buoy is not reporting {', '.join(missing)}"
    origin = place(cfg, spot["buoy"])
    travel = travel_bearing(obs)

    if "aimed_at" in rules:
        target = rules["aimed_at"]["place"]
        off = angle_diff(travel, bearing(origin, place(cfg, target)))
        if abs(off) > rules["aimed_at"]["tolerance_deg"]:
            return 0, f"waves travelling {travel:.0f}° are {off:+.0f}° off the path to {target.replace('_', ' ')}"

    if "heading_between" in rules:
        a, b = (bearing(origin, place(cfg, p)) for p in rules["heading_between"])
        mid = a + angle_diff(b, a) / 2
        if abs(angle_diff(travel, mid)) > abs(angle_diff(b, a)) / 2:
            return 0, f"waves travelling {travel:.0f}° are outside the {min(a, b):.0f}-{max(a, b):.0f}° window"

    if obs["WVHT"] < rules["min_height_m"]:
        return 0, f"waves are {obs['WVHT']} m, under {rules['min_height_m']} m"
    if obs["DPD"] < rules["min_period_s"]:
        return 0, f"period is {obs['DPD']} s, under {rules['min_period_s']} s"
    return 1, "swell is big enough and heading the right way"


def update_status(spot, obs, status):
    """Record the new status; True when it went up since the last run."""
    obs = obs.copy()
    obs["status"] = status
    history = setstatus(obs, spot["status_file"])
    return history.loc[1, "status"] > history.loc[0, "status"]
