"""
Daily swell-vector forecast chart from NOAA WAVEWATCH III (GFS-Wave) via Herbie.

For each forecast day a small compass panel is drawn. Swells 1-3 and the wind
wave are plotted as vectors from the origin pointing in their direction of
TRAVEL. Vector length = significant height (m), vector colour = period (s).
The daily chart samples one hour per day; the hourly chart covers the next
48 hours. Below each panel the partitions are listed as  height(m) @ period(s) @ direction(°),
where direction is the conventional "coming from" bearing (as buoys/surf reports use).
"""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from herbie import Herbie, HerbieLatest

from _station_metadata import get_station

warnings.filterwarnings("ignore", category=FutureWarning)

STATION_ID = "46087"
PRODUCT = "wcoast.0p16"      # West Coast regional grid - small files
N_DAYS = 7
VALID_HOUR = 12              # UTC hour of day to sample (12Z = 5am PDT)
# Only the partition fields we need -> small byte-range downloads
SEARCH = ":(WVHGT|WVPER|WVDIR|SWELL|SWPER|SWDIR):"
# SWDIR swell 3 is the last GRIB message (open-ended byte range) and Herbie drops it
# from multi-field subsets, so it is fetched on its own.
SEARCH_LAST = ":SWDIR:3 in sequence:"
OUT_PATH = "plots/swell_forecast.png"
HOURLY_HOURS = 48
HOURLY_COLS = 8              # panels per row in the hourly chart
HOURLY_OUT_PATH = "plots/swell_forecast_hourly.png"
LOCAL_TZ = "America/Los_Angeles"

PARTITIONS = ["Swell 1", "Swell 2", "Swell 3", "Wind wave"]
MARKERS = {"Swell 1": "1", "Swell 2": "2", "Swell 3": "3", "Wind wave": "W"}


def nearest_ocean_index(ds, var, lat, lon):
    """Index of the grid cell nearest (lat, lon) that has data (coastal cells are masked)."""
    field = ds[var]
    if "orderedSequenceData" in field.dims:
        field = field.isel(orderedSequenceData=0)
    lats, lons = np.meshgrid(ds.latitude.values, ds.longitude.values, indexing="ij")
    dist = (lats - lat) ** 2 + ((lons - lon) * np.cos(np.radians(lat))) ** 2
    dist[np.isnan(field.values)] = np.inf
    return np.unravel_index(np.argmin(dist), dist.shape)


def extract_point(ds_list, lat, lon):
    """Pull swell 1-3 + wind wave (height, period, direction) at a point."""
    ds_list = ds_list if isinstance(ds_list, list) else [ds_list]
    if float(ds_list[0].longitude.max()) > 180:
        lon = lon % 360

    # cfgrib may split the fields over several datasets; gather point values by name
    ref = next(d for d in ds_list if "shts" in d)
    iy, ix = nearest_ocean_index(ref, "shts", lat, lon)
    values = {}
    for d in ds_list:
        pt = d.isel(latitude=iy, longitude=ix)
        for var in pt.data_vars:
            if "orderedSequenceData" in pt[var].dims:
                for seq in pt.orderedSequenceData.values:
                    values[(var, int(seq))] = float(pt[var].sel(orderedSequenceData=seq))
            elif "orderedSequenceData" in pt.coords:       # single swell partition
                values[(var, int(pt.orderedSequenceData))] = float(pt[var])
            else:
                values[(var, 0)] = float(pt[var])

    rows = []
    for i in (1, 2, 3):
        rows.append((f"Swell {i}", values.get(("shts", i), np.nan),
                     values.get(("mpts", i), np.nan), values.get(("swdir", i), np.nan)))
    rows.append(("Wind wave", values.get(("shww", 0), np.nan),
                 values.get(("mpww", 0), np.nan), values.get(("wvdir", 0), np.nan)))
    grid_pt = (float(ref.latitude[iy]), float(ref.longitude[ix]))
    return rows, grid_pt


def latest_run():
    latest = HerbieLatest(model="gfs_wave", product=PRODUCT, verbose=False)
    run = pd.Timestamp(latest.date)
    print(f"Using GFS-Wave run {run:%Y-%m-%d %HZ}")
    return run


def daily_times(run, n_days=N_DAYS, valid_hour=VALID_HOUR):
    """valid_hour UTC on each of the next n_days, starting at/after the run."""
    first = run.normalize() + pd.Timedelta(hours=valid_hour)
    if first < run:
        first += pd.Timedelta(days=1)
    return [first + pd.Timedelta(days=d) for d in range(n_days)]


def hourly_times(run, n_hours=HOURLY_HOURS):
    """Every hour for the next n_hours from now (the GFS-Wave output is hourly to f120)."""
    now = pd.Timestamp.now(tz="UTC").tz_localize(None).ceil("h")
    start = max(now, run)
    return [start + pd.Timedelta(hours=h) for h in range(n_hours)]


def fetch_forecast(lat, lon, run, times):
    """One record per partition per valid time, all from the same model run."""
    records, grid_pt = [], None
    for valid in times:
        fxx = int((valid - run) / pd.Timedelta(hours=1))
        try:
            H = Herbie(run, model="gfs_wave", product=PRODUCT, fxx=fxx, verbose=False)
            ds_list = H.xarray(SEARCH, remove_grib=False)
            ds_list = ds_list if isinstance(ds_list, list) else [ds_list]
            ds_list.append(H.xarray(SEARCH_LAST, remove_grib=False))
            rows, grid_pt = extract_point(ds_list, lat, lon)
        except Exception as e:
            print(f"  skipping {valid:%Y-%m-%d %HZ} (f{fxx:03d}): {e}")
            continue
        for name, hgt, per, direc in rows:
            records.append(dict(valid=valid, partition=name,
                                height=hgt, period=per, direction=direc))
        print(f"  {valid:%a %m-%d %HZ} (f{fxx:03d}) ok")
    return pd.DataFrame(records), grid_pt


def plot_forecast(df, station, run, grid_pt, out_path=OUT_PATH, ncols=None,
                  title_fmt=lambda t: t.strftime("%a %b %d"), cadence=f"{VALID_HOUR:02d}Z daily",
                  title="Swell forecast"):
    """Grid of compass panels, one per valid time, with the partition text below each."""
    df = df.dropna(subset=["height", "period", "direction"])
    df = df[df.height > 0.05]                       # drop negligible partitions
    times = sorted(df.valid.unique())
    n = len(times)
    ncols = ncols or n
    nrows = int(np.ceil(n / ncols))

    # common scale across all panels so lengths are comparable
    rmax = max(1.0, np.ceil(df.height.max() * 2) / 2)
    ring = 0.5 if rmax <= 3 else 1.0
    # plasma without its pale-yellow end, which vanishes on a white background
    cmap = plt.matplotlib.colors.ListedColormap(plt.get_cmap("plasma")(np.linspace(0, 0.85, 256)))
    norm = plt.Normalize(vmin=min(4, df.period.min()), vmax=max(16, df.period.max()))

    fig = plt.figure(figsize=(3.0 * ncols + 1.2, 5.4 * nrows))
    height_in = fig.get_figheight()
    # fixed-inch top margin so the header hugs the grid regardless of row count
    gs = fig.add_gridspec(2 * nrows, ncols + 1, height_ratios=[1, 0.62] * nrows,
                          width_ratios=[1] * ncols + [0.08], hspace=0.05, wspace=0.3,
                          top=1 - 0.6 / height_in, bottom=0.2 / height_in)

    for j, t in enumerate(times):
        row, col = divmod(j, ncols)
        ax = fig.add_subplot(gs[2 * row, col], projection="polar")
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)                  # compass: clockwise from north
        ax.set_ylim(0, rmax)
        ax.set_yticks(np.arange(ring, rmax + 0.01, ring))
        ax.set_yticklabels([])
        ax.set_xticks(np.radians([0, 90, 180, 270]))
        ax.set_xticklabels(["N", "E", "S", "W"], fontsize=8, color="0.4")
        ax.tick_params(pad=-2)
        ax.grid(color="0.85", lw=0.6)
        ax.spines["polar"].set_color("0.7")
        ax.set_title(title_fmt(pd.Timestamp(t)), fontsize=11, fontweight="bold", pad=10)

        lines = []
        day_df = df[df.valid == t].copy()
        day_df["order"] = day_df.partition.map(PARTITIONS.index)
        day_df = day_df.sort_values("order")
        for _, r in day_df.iterrows():
            travel = np.radians((r.direction + 180) % 360)   # WW3 dir is "from"
            color = cmap(norm(r.period))
            ax.annotate("", xy=(travel, r.height), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>,head_width=0.22,head_length=0.45",
                                        color=color, lw=2.0, shrinkA=0, shrinkB=0))
            ax.text(travel, r.height + rmax * 0.1, MARKERS[r.partition],
                    ha="center", va="center", fontsize=8, fontweight="bold", color="0.25")
            lines.append((r.partition, f"{r.height:.1f}m @ {r.period:.0f}s @ {r.direction:.0f}°", color))

        # text block under the compass
        tax = fig.add_subplot(gs[2 * row + 1, col])
        tax.axis("off")
        for k, (name, txt, color) in enumerate(lines):
            y = 0.92 - k * 0.2
            tax.plot(0.02, y, "s", color=color, ms=7, transform=tax.transAxes)
            tax.text(0.09, y, f"{MARKERS[name]}", fontsize=8.5, fontweight="bold",
                     va="center", transform=tax.transAxes)
            tax.text(0.17, y, txt, fontsize=8.5, va="center", family="monospace",
                     transform=tax.transAxes)

    cax = fig.add_subplot(gs[0, ncols])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
    cb.set_label("Period (s)")

    # header placed in inches from the top so it sits the same on 1-row and 6-row figures
    fig.suptitle(f"{title} — {station['name']} ({STATION_ID})", fontsize=14,
                 fontweight="bold", y=1 + 0.05 / height_in, va="bottom")
    fig.text(0.5, 1 - 0.05 / height_in,
             f"GFS-Wave (WW3) {run:%Y-%m-%d %HZ} run · {cadence} · "
             f"grid pt {grid_pt[0]:.2f}°N {grid_pt[1] - 360 if grid_pt[1] > 180 else grid_pt[1]:.2f}°E · "
             f"arrows point in direction of travel, length = height (rings every "
             f"{ring:g} m) · text: height @ period @ direction-from · "
             f"1-3 = swells, W = wind wave",
             ha="center", va="bottom", fontsize=8, color="0.4")

    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Saved {out_path}")
    return fig


def to_local(t):
    return t.tz_localize("UTC").tz_convert(LOCAL_TZ)


if __name__ == "__main__":
    station = get_station(STATION_ID)
    lat, lon = station["lat"], station["lon"]
    run = latest_run()

    # daily chart
    df, grid_pt = fetch_forecast(lat, lon, run, daily_times(run))
    print(df.to_string(index=False))
    plot_forecast(df, station, run, grid_pt)

    # hourly chart, next 48 h, titled in local time
    df_h, grid_pt = fetch_forecast(lat, lon, run, hourly_times(run))
    plot_forecast(df_h, station, run, grid_pt, out_path=HOURLY_OUT_PATH, ncols=HOURLY_COLS,
                  title_fmt=lambda t: to_local(t).strftime("%a %-I%p %Z"),
                  cadence="hourly, next 48 h", title="Hourly swell forecast")
