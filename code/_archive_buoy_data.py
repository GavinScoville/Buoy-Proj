"""
Fetch recent buoy data from NOAA and archive to parquet.

This script is meant to run periodically (cron, or manually before plotting).
It pulls the last N hours of data for each station and appends to the archive,
deduplicating on datetime.
"""

import argparse
import sys
from datetime import datetime, timedelta

import pandas as pd

from _fetch_buoy_functions import fetch_and_clean_buoy_data
from _station_metadata import STATION_IDS, save_buoy_timeseries, get_station


def archive_station(station_id, hours_back=72, verbose=True):
    """
    Fetch recent data for one station and add it to the archive.

    Args:
        station_id: NDBC buoy ID (e.g., "46087")
        hours_back: how far back to try to fetch (actual NOAA limit is ~30 days)
        verbose: print status messages

    Returns:
        (success: bool, message: str)
    """
    try:
        # The existing fetch function already handles NOAA download + cleanup
        df = fetch_and_clean_buoy_data(station_id)

        if df is None or df.empty:
            msg = f"  {station_id}: no data returned"
            if verbose:
                print(msg)
            return False, msg

        # Archive it
        save_buoy_timeseries(df, station_id)

        nrows = len(df)
        date_range = f"{df['datetime'].min()} to {df['datetime'].max()}"
        msg = f"  {station_id}: archived {nrows} rows ({date_range})"
        if verbose:
            print(msg)
        return True, msg

    except Exception as e:
        msg = f"  {station_id}: ERROR - {e}"
        if verbose:
            print(msg, file=sys.stderr)
        return False, msg


def main():
    ap = argparse.ArgumentParser(
        description="Fetch and archive NOAA buoy data to parquet"
    )
    ap.add_argument(
        "--stations",
        nargs="+",
        default=None,
        help="station IDs to archive (default: all known stations)",
    )
    ap.add_argument(
        "--hours", type=int, default=72, help="hours back to fetch (default: 72)"
    )
    ap.add_argument(
        "-q", "--quiet", action="store_true", help="suppress output"
    )
    args = ap.parse_args()

    stations = args.stations if args.stations else STATION_IDS
    verbose = not args.quiet

    if verbose:
        print(f"Archiving {len(stations)} station(s) to data/buoy_archive/")
        print()

    success_count = 0
    for sid in stations:
        ok, msg = archive_station(sid, hours_back=args.hours, verbose=verbose)
        if ok:
            success_count += 1

    if verbose:
        print()
        print(f"Success: {success_count}/{len(stations)} stations")

    return 0 if success_count == len(stations) else 1


if __name__ == "__main__":
    sys.exit(main())
