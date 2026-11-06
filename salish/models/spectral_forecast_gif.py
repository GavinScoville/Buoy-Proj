"""
Run the mild-slope spectral model over every WAVEWATCH III forecast time and
stitch the wave-height maps into an animated GIF.

    python -m salish.models.spectral_forecast_gif            # daily, ~1 frame/day
    python -m salish.models.spectral_forecast_gif --hourly   # next 48 h (slow)
    python -m salish.models.spectral_forecast_gif --max-frames 2   # quick test

Each frame uses the dominant swell partition (Swell 1) at the station in
config/pipeline.yaml and the predicted tide at that forecast time.
"""
import argparse
import shutil
from datetime import timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from salish.core.config import load_pipeline_config
from salish.core.stations import get_station
from salish.ingest.noaa import predictions_with_fallback
from salish.ingest.wavewatch import (STATION_ID, daily_times, fetch_forecast,
                                     hourly_times, latest_run)
from salish.models.mild_slope_simulation import run_spectral_model
from salish.paths import BATHYMETRY, PLOTS

FRAME_DIR = PLOTS / "spectral_forecast"
GIF_PATH = PLOTS / "mild_slope_forecast.gif"


def tide_lookup(station, times, tz):
    """Predicted tide (m MLLW) nearest each UTC time; 0.0 if none available."""
    start = pd.Timestamp(min(times)).tz_localize("UTC").tz_convert(tz).normalize()
    end = pd.Timestamp(max(times)).tz_localize("UTC").tz_convert(tz).normalize() + timedelta(days=1)
    df = predictions_with_fallback("tide", station, start.strftime("%Y%m%d"),
                                   end.strftime("%Y%m%d"), start, tz)
    if df.empty:
        print(f"no tide predictions for {station}; running at MLLW")
        return lambda t: 0.0
    tt = pd.to_datetime(df["datetime"])
    tt = tt.dt.tz_localize("UTC") if tt.dt.tz is None else tt.dt.tz_convert("UTC")
    v = df["v"].astype(float).to_numpy()
    return lambda t: float(v[(tt - pd.Timestamp(t).tz_localize("UTC")).abs().argmin()])


def run_frames(hourly=False, max_frames=None, partition="Swell 1"):
    cfg = load_pipeline_config()
    m = cfg["models"]["spectral"]
    tz = ZoneInfo(cfg["timezone"])
    st = get_station(STATION_ID)

    run = latest_run()
    times = hourly_times(run) if hourly else daily_times(run)
    df, _ = fetch_forecast(st["lat"], st["lon"], run, times)
    swell = df[df.partition == partition].dropna(subset=["height", "period", "direction"])
    if max_frames:
        swell = swell.head(max_frames)
    if swell.empty:
        raise RuntimeError("no forecast rows to run")
    tide = tide_lookup(m["tide_station"], list(swell.valid), tz)

    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for i, r in enumerate(swell.itertuples(), 1):
        level = tide(r.valid)
        print(f"\n### frame {i}/{len(swell)}: {r.valid:%Y-%m-%d %HZ}  "
              f"Hs={r.height:.2f} m T={r.period:.1f} s dir={r.direction:.0f}  tide={level:+.2f} m")
        out = run_spectral_model(r.height, r.period, r.direction, BATHYMETRY / m["bathymetry"],
                                 grid_spacing_m=m["grid_spacing_m"], subsample=m["subsample"],
                                 components=m["components"], spread_s=m["spread_s"], cap=m["cap"],
                                 buoy_label=m["buoy"], breaks=cfg.get("breaks"),
                                 grid_origin=m.get("grid_origin"),
                                 grid_mean_lat=m.get("grid_mean_lat"),
                                 window_arcsec=m["window_arcsec"],
                                 depth_band=m["depth_band_m"], search_m=m["break_search_m"],
                                 water_level_m=level,
                                 datum_above_mllw_m=m["datum_above_mllw_m"])
        # the model always writes the same PNG, so keep a copy per frame
        frame = FRAME_DIR / f"mild_slope_{r.valid:%Y%m%d_%H}Z.png"
        shutil.copy(out["plot"], frame)
        results.append({"valid": r.valid, "frame": frame,
                        **{k: v for k, v in out.items() if k not in ("plot", "breaks")}})
    return pd.DataFrame(results), tz


def make_gif(results, tz, out_path=GIF_PATH, seconds_per_frame=1.0, scale=0.5):
    frames = []
    font = ImageFont.load_default(size=28)
    for r in results.itertuples():
        img = Image.open(r.frame).convert("RGB")
        band = 50
        canvas = Image.new("RGB", (img.width, img.height + band), "white")
        canvas.paste(img, (0, band))
        local = pd.Timestamp(r.valid).tz_localize("UTC").tz_convert(tz)
        text = (f"{local:%a %b %-d, %-I %p %Z}    Hs {r.offshore_Hs:.1f} m   "
                f"T {r.T:.0f} s   from {r.mwd:.0f}°   tide {r.tide_m:+.1f} m")
        ImageDraw.Draw(canvas).text((20, 10), text, fill="black", font=font)
        frames.append(canvas)

    # bbox_inches="tight" can vary the size slightly; GIF frames must match
    w = int(max(f.width for f in frames) * scale)
    h = int(max(f.height for f in frames) * scale)
    frames = [f.resize((w, h), Image.LANCZOS) for f in frames]
    frames[0].save(out_path, save_all=True, append_images=frames[1:],
                   duration=int(seconds_per_frame * 1000), loop=0)
    print(f"\nsaved {out_path} ({len(frames)} frames)")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hourly", action="store_true", help="next 48 h hourly instead of daily")
    ap.add_argument("--max-frames", type=int, help="only run the first N forecast times")
    ap.add_argument("--partition", default="Swell 1",
                    help='"Swell 1", "Swell 2", "Swell 3" or "Wind wave"')
    ap.add_argument("--seconds-per-frame", type=float, default=1.0)
    ap.add_argument("--scale", type=float, default=0.5, help="GIF size relative to the PNGs")
    args = ap.parse_args()

    results, tz = run_frames(args.hourly, args.max_frames, args.partition)
    print(results.drop(columns="frame").to_string(index=False))
    make_gif(results, tz, seconds_per_frame=args.seconds_per_frame, scale=args.scale)


if __name__ == "__main__":
    main()
