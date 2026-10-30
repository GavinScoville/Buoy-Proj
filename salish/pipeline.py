"""
The scheduled run: python -m salish.pipeline

  1. ingest   - pull NOAA buoys, tide and current predictions
  2. process  - summarise each buoy's latest reading
  3. alerts   - decide watch/normal per spot and email when a spot goes up
  4. plots    - per-station wave, wind and tide/current charts
  5. models   - WAVEWATCH III forecast, ray tracing (Pacific, Strait,
                Islands), spectral (mild-slope), finite-difference
  6. website  - render artifacts/site/Salish-Surf-Report.md

Alerts go out before the models run so a slow or broken model never delays
them. Each model runs as an isolated stage: if it fails or its inputs are
missing, the run carries on and the website notes it.

Everything configurable lives in config/pipeline.yaml.
"""

import argparse
from datetime import timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import salish
from salish.core.config import load_pipeline_config
from salish.core.stages import Skip, run_stage
from salish.ingest.noaa import fetch_and_clean_buoy_data, predictions_with_fallback
from salish.notify.alerts import compose
from salish.notify.mail import deliver
from salish.paths import BATHYMETRY, ensure_dirs
from salish.processing import alerts
from salish.processing.conditions import wave_summary
from salish.viz.plot_conditions import plot_tide_currents, plot_waves, plot_wind
from salish.web.website import plot_name, render_site

MODEL_STAGES = ("wavewatch", "pacific_rays", "spectral", "finite_difference") #"ray_tracing", add ray tracing if you ant but its pretty lame 


# ---------------------------------------------------------------------------
# 1-2. Ingest and process
# ---------------------------------------------------------------------------
def fetch_buoys(cfg, tz):
    """buoy id -> (full recent DataFrame, latest summarised observation)."""
    buoys = {}
    for buoy_id in cfg["buoys"]:
        df = fetch_and_clean_buoy_data(buoy_id)
        latest = wave_summary(df, buoy_id, tz) if df is not None else None
        if latest is None:
            print(f"[warning] no usable data from buoy {buoy_id}")
        buoys[buoy_id] = (df, latest)
    return buoys


def fetch_tides_and_currents(cfg, tz):
    """station id -> hourly predictions for today and tomorrow."""
    today = pd.Timestamp.now(tz).normalize()
    begin = today.strftime("%Y%m%d")
    end = (today + timedelta(days=1)).strftime("%Y%m%d")
    tides, currents = {}, {}
    for spot in cfg["spots"]:
        if "tide_station" in spot and spot["tide_station"] not in tides:
            tides[spot["tide_station"]] = predictions_with_fallback(
                "tide", spot["tide_station"], begin, end, today, tz)
        if "current_station" in spot and spot["current_station"] not in currents:
            currents[spot["current_station"]] = predictions_with_fallback(
                "current", spot["current_station"], begin, end, today, tz)
    return tides, currents


# ---------------------------------------------------------------------------
# 3. Alerts
# ---------------------------------------------------------------------------
def run_alerts(cfg, obs, tides, currents, tz):
    """Update every spot's status; email those that went up. Returns spot key -> (status, reason)."""
    decisions = {}
    for spot in cfg["spots"]:
        latest = obs.get(spot["buoy"])
        if "alert" not in spot or latest is None:
            continue
        status, reason = alerts.evaluate(cfg, spot, latest)
        decisions[spot["key"]] = (status, reason)
        print(f"{spot['name']}: {'WATCH' if status else 'normal'} - {reason}")
        if alerts.update_status(spot, latest, status):
            message = compose(cfg, spot, latest,
                              tides.get(spot.get("tide_station")),
                              currents.get(spot.get("current_station")), tz)
            deliver(message, spot["name"], cfg["email"]["recipients"])
    return decisions


# ---------------------------------------------------------------------------
# 4. Station plots
# ---------------------------------------------------------------------------
def plot_stations(cfg, buoys, tides, currents, tz):
    for spot in cfg["spots"]:
        df, latest = buoys[spot["buoy"]]
        if latest is None:
            continue
        name = plot_name(spot)
        plots = spot.get("plots", [])
        if "waves" in plots:
            plot_waves(df, station_name=name, timezone=cfg["timezone"])
        if "wind" in plots:
            plot_wind(df, station_name=name, timezone=cfg["timezone"])
        if "tidecurrent" in plots:
            plot_tide_currents(tides[spot["tide_station"]], currents[spot["current_station"]],
                               latest["datetime"], tz, name)


# ---------------------------------------------------------------------------
# 5. Models, in website order
# ---------------------------------------------------------------------------
def _need(obs, *buoy_ids):
    missing = [b for b in buoy_ids if obs.get(b) is None]
    if missing:
        raise Skip(f"no data from buoy {', '.join(missing)}")


def _need_grids(*names):
    missing = [n for n in names if not (BATHYMETRY / n).exists()]
    if missing:
        raise Skip(f"bathymetry grid not found: {', '.join(missing)} "
                   f"(build it with python -m salish.processing.bathymetry)")


def model_wavewatch(mcfg, obs, buoys):
    from salish.ingest.wavewatch import make_forecast_charts
    return make_forecast_charts(mcfg["station"])


def model_pacific_rays(mcfg, obs, buoys):
    from salish.models.wavepath import predict_pacific_wavepath
    from salish.viz.map_conditions import map_pacific
    _need(obs, mcfg["source_buoy"])
    pacific_waves = predict_pacific_wavepath(buoys[mcfg["source_buoy"]][0])
    others = (obs[b] if obs.get(b) is not None else pd.Series(dtype=float) for b in mcfg["map_buoys"])
    map_pacific(pacific_waves, *others)


def model_ray_tracing(mcfg, obs, buoys):
    from salish.models.ray_tracing import run_ray_tracing
    i = mcfg["islands"]
    _need(obs, mcfg["strait"]["buoy"], i["south"]["buoy"], i["north"]["buoy"])
    return run_ray_tracing(mcfg, obs)


def current_tide(station, tz):
    """Predicted tide height (m above MLLW) for the hour nearest now, or 0.0
    when neither the API nor the archive has anything."""
    now = pd.Timestamp.now(tz)
    day = now.normalize()
    df = predictions_with_fallback("tide", station, day.strftime("%Y%m%d"),
                                   (day + timedelta(days=1)).strftime("%Y%m%d"), day, tz)
    if df.empty:
        print(f"no tide predictions for {station}; running at MLLW")
        return 0.0
    t = pd.to_datetime(df["datetime"])
    t = t.dt.tz_localize("UTC") if t.dt.tz is None else t  # the API returns naive GMT
    return float(df["v"].iloc[(t - now).abs().argmin()])


def model_spectral(mcfg, obs, buoys):
    from salish.models.mild_slope_simulation import run_spectral_model
    _need(obs, mcfg["buoy"])
    _need_grids(mcfg["bathymetry"])
    o = obs[mcfg["buoy"]]
    cfg = load_pipeline_config()
    tide = current_tide(mcfg["tide_station"], ZoneInfo(cfg["timezone"]))
    return run_spectral_model(o["WVHT"], o["DPD"], o["MWD"], BATHYMETRY / mcfg["bathymetry"],
                              grid_spacing_m=mcfg["grid_spacing_m"],
                              subsample=mcfg["subsample"], components=mcfg["components"],
                              spread_s=mcfg["spread_s"], cap=mcfg["cap"],
                              buoy_label=mcfg["buoy"], breaks=cfg.get("breaks"),
                              grid_origin=mcfg.get("grid_origin"),
                              grid_mean_lat=mcfg.get("grid_mean_lat"),
                              window_arcsec=mcfg["window_arcsec"],
                              depth_band=mcfg["depth_band_m"],
                              search_m=mcfg["break_search_m"],
                              water_level_m=tide,
                              datum_above_mllw_m=mcfg["datum_above_mllw_m"])


def model_finite_difference(mcfg, obs, buoys):
    locations = [loc for loc in mcfg["locations"]
                 if (BATHYMETRY / loc["bathymetry"]).exists() and obs.get(loc["buoy"]) is not None]
    if not locations:
        _need_grids(*(loc["bathymetry"] for loc in mcfg["locations"]))
        raise Skip("no buoy data for any location")
    from salish.models.run_all_simulations import run_all_simulations
    params = {b: {"h": float(o["WVHT"]), "T": float(o["DPD"]), "direction": float(o["MWD"])}
              for b, o in obs.items() if o is not None}
    return run_all_simulations(use_warm_start=mcfg["warm_start"], locations=locations,
                               buoy_params=params, short_run=False, create_3d=True)


MODELS = {
    "wavewatch": model_wavewatch,
    "pacific_rays": model_pacific_rays,
    #"ray_tracing": model_ray_tracing,
    "spectral": model_spectral,
    "finite_difference": model_finite_difference,
}


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Salish Sea surf pipeline")
    ap.add_argument("--skip", nargs="*", default=[], choices=MODEL_STAGES, metavar="MODEL",
                    help=f"models to leave out this run: {', '.join(MODEL_STAGES)}")
    args = ap.parse_args(argv)

    cfg = load_pipeline_config()
    tz = ZoneInfo(cfg["timezone"])
    ensure_dirs()

    buoys = fetch_buoys(cfg, tz)
    obs = {b: latest for b, (_, latest) in buoys.items()}
    tides, currents = fetch_tides_and_currents(cfg, tz)

    decisions = run_alerts(cfg, obs, tides, currents, tz)
    # Station plots are off until they're replaced with better ones
    stages = {"station_plots": run_stage("station plots", False, plot_stations,
                                         cfg, buoys, tides, currents, tz)}

    for name in MODEL_STAGES:
        mcfg = cfg["models"][name]
        enabled = mcfg.get("enabled", True) and name not in args.skip
        stages[name] = run_stage(name, enabled, MODELS[name], mcfg, obs, buoys)

    render_site(cfg, obs, decisions, stages, tz)

    print("\n=== summary ===")
    for name, r in stages.items():
        print(f"  {name:<18} {r.status:<9} {r.seconds:6.0f}s  {r.note}")


if __name__ == "__main__":
    main()
