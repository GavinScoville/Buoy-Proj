"""
Plot buoy stations on top of simulation results.

Shows station locations, names, and optionally recent conditions (Hs, wind)
overlaid on bathymetry or wave field maps.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import pandas as pd

from _station_metadata import get_station_dataframe, load_buoy_timeseries


def plot_stations_on_domain(depth, dx, dy, stations_df=None, ax=None,
                            show_names=True, show_conditions=False):
    """
    Overlay station markers on a bathymetry/domain plot.

    Args:
        depth: 2-D array (y, x) with bathymetry, negative = water
        dx, dy: grid spacing (m)
        stations_df: DataFrame from get_station_dataframe(), or None to load default
        ax: matplotlib axis to draw on (default: create new fig)
        show_names: label stations with their names
        show_conditions: include recent Hs / wind in labels

    Returns:
        ax (axis object)
    """
    if stations_df is None:
        stations_df = get_station_dataframe()

    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 8))

    # Assume domain spans -125° to -123° longitude, 48° to 49° latitude
    # (adjust these bounds to your actual domain if different)
    lon_min, lon_max = -125.0, -123.0
    lat_min, lat_max = 48.0, 50.0

    # Convert lat/lon to grid indices
    ny, nx = depth.shape
    x_grid = np.linspace(lon_min, lon_max, nx)
    y_grid = np.linspace(lat_min, lat_max, ny)

    for _, station in stations_df.iterrows():
        lon, lat = station["lon"], station["lat"]

        # Check if station is within domain bounds
        if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
            continue

        # Map lat/lon to grid indices
        j = np.argmin(np.abs(x_grid - lon))
        i = np.argmin(np.abs(y_grid - lat))

        # Plot station marker
        ax.plot(lon, lat, "r*", markersize=16, label=station["name"] if _ == 0 else "")

        # Add circle around it for visibility
        circle = Circle((lon, lat), 0.05, fill=False, edgecolor="red", linewidth=1)
        ax.add_patch(circle)

        # Add label if requested
        if show_names:
            label = station["name"]

            if show_conditions:
                # Optionally load recent data
                ts = load_buoy_timeseries(station["station_id"])
                if not ts.empty:
                    latest = ts.iloc[-1]
                    if pd.notna(latest.get("WVHT")):
                        label += f"\nHs={latest['WVHT']:.1f}m"
                    if pd.notna(latest.get("WSPD")):
                        label += f" W={latest['WSPD']:.1f}m/s"

            ax.text(
                lon + 0.05,
                lat,
                label,
                fontsize=9,
                ha="left",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
            )

    ax.set_xlabel("Longitude (°W)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title("Station Locations")
    ax.grid(True, alpha=0.3)

    return ax


def plot_stations_with_timeseries(station_ids=None, hours_back=72, ncols=2):
    """
    Quick multi-panel plot: one panel per station showing recent wind/wave.

    Args:
        station_ids: list of station IDs, or None for all
        hours_back: how far back to plot
        ncols: number of columns in subplot grid
    """
    if station_ids is None:
        from _station_metadata import STATION_IDS
        station_ids = STATION_IDS

    nrows = (len(station_ids) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3 * nrows))
    axes = np.atleast_1d(axes).reshape(-1)

    for i, sid in enumerate(station_ids):
        ax = axes[i]
        ts = load_buoy_timeseries(sid)

        if ts.empty:
            ax.text(0.5, 0.5, f"No data\nfor {sid}", ha="center", va="center")
            ax.set_title(f"Station {sid}")
            continue

        # Filter to recent
        ts["datetime"] = pd.to_datetime(ts["datetime"])
        cutoff = ts["datetime"].max() - pd.Timedelta(hours=hours_back)
        ts = ts[ts["datetime"] >= cutoff]

        # Twin axis: wave height and wind speed
        ax2 = ax.twinx()

        # Plot Hs
        valid_hs = ts[ts["WVHT"].notna()]
        if not valid_hs.empty:
            ax.plot(valid_hs["datetime"], valid_hs["WVHT"], "b-", linewidth=2, label="Hs")
            ax.set_ylabel("Wave Height (m)", color="b")
            ax.tick_params(axis="y", labelcolor="b")

        # Plot wind speed
        valid_wind = ts[ts["WSPD"].notna()]
        if not valid_wind.empty:
            ax2.plot(valid_wind["datetime"], valid_wind["WSPD"], "g-", linewidth=2, label="Wind")
            ax2.set_ylabel("Wind Speed (m/s)", color="g")
            ax2.tick_params(axis="y", labelcolor="g")

        ax.set_xlabel("Time")
        ax.set_title(f"Station {sid}")
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=45)

    # Hide unused subplots
    for j in range(len(station_ids), len(axes)):
        axes[j].axis("off")

    fig.tight_layout()
    return fig


if __name__ == "__main__":
    # Example: plot recent conditions for key stations
    import matplotlib.dates as mdates

    fig = plot_stations_with_timeseries(["46087", "46267", "46088"], hours_back=168)
    fig.savefig("plots/station_timeseries.png", dpi=100, bbox_inches="tight")
    print("Saved plots/station_timeseries.png")
