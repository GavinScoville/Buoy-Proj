# The goal of this program is to investigate how waves propogate through the salish sea. It may be useful for informing surfing conditions.

## Project structure

The repo follows the pipeline: pull NOAA data → process it → run models →
plot and report → send alerts → render the website.

```
config/                 hand-edited settings
  stations.yaml         buoy IDs, coordinates and plotting hints

salish/                 the Python package (all code lives here)
  paths.py              every input/output location; nothing else hardcodes paths
  pipeline.py           the scheduled run: python -m salish.pipeline
  core/                 shared helpers: geodesy, station config loading
  ingest/               pulling data: NOAA buoys/tides/currents, WAVEWATCH III GRIBs, archiving
  processing/           cleaning and summarising: buoy summaries + alert status, bathymetry grids
  models/               ray tracing, Pacific wave paths, mild-slope and Airy-wave simulations
  viz/                  plots and maps
  notify/               email delivery
  web/                  renders the surf report website

data/
  raw/                  exactly as downloaded; gitignored, safe to delete and refetch
    ndbc/               latest NDBC buoy pulls
    gfs_wave/           WAVEWATCH III GRIB cache (Herbie)
    bathymetry/         source GEBCO / 10-30m TIFF rasters
    cartopy/            Natural Earth shapefiles
  processed/            cleaned and derived data
    buoys/              cleaned latest buoy data (gitignored)
    historic/           monthly Parquet archive per station (tracked, CI commits it)
    bathymetry/         gebco_strait_subset.nc (tracked) + .npy model grids (gitignored)
    predictions/        model predictions (gitignored)
    buoy_archive/       long-term buoy timeseries (gitignored)
  state/
    alerts/             last alert status per spot; drives email dedup (tracked)

artifacts/              deliverables
  plots/                PNGs used by the website
  site/                 the rendered surf report
  simulations/          heavy simulation output (results.md tracked, the rest gitignored)
```

The Python package is called `salish` rather than `code` because a top-level
`code` package would shadow Python's built-in `code` module.

## Running the pipeline

From the repo root:

```bash
python -m salish.pipeline
```

Each run:

1. fetches every buoy listed in `config/pipeline.yaml`, plus tide and current predictions
2. summarises each buoy's latest reading
3. checks each spot's alert rules and emails any spot whose status went from normal to watch
4. draws the per-station wave, wind and tide/current plots
5. runs the models in this order: WAVEWATCH III forecast, ray tracing (Pacific,
   Strait, Islands), the spectral mild-slope model, then the finite-difference model
6. renders `artifacts/site/Salish-Surf-Report.md`, with the model sections in that same order

Alerts go out before the models run, so a slow or broken model can't delay them.
Each model is isolated: if it fails, or its input files are missing, the run
carries on. The website then says it wasn't updated and keeps the last figure.

Station lists, alert thresholds, email recipients and model settings all live in
`config/pipeline.yaml`. To leave models out of a run:

```bash
python -m salish.pipeline --skip spectral finite_difference
```

The spectral and finite-difference models need the `.npy` bathymetry grids, which
are gitignored, so they skip themselves in GitHub Actions and only run on a
machine that has the grids.

Set `SALISH_NO_EMAIL=1` to run everything (fetch, modelling, plots, report)
without delivering the surf alerts:

```bash
SALISH_NO_EMAIL=1 python -m salish.pipeline
```

Email delivery needs `EMAIL_USER` and `EMAIL_PASS`, read from `.env` locally
and from repository secrets in CI.

Other entry points:

```bash
python -m salish.ingest.archive               # archive buoy history
python -m salish.ingest.wavewatch             # WAVEWATCH III swell forecast charts
python -m salish.processing.bathymetry        # rebuild .npy grids from raw rasters
python -m salish.models.mild_slope_simulation
python -m salish.models.run_all_simulations
python -m salish.web.export_html              # Markdown report -> HTML
```

### Reading the report as HTML

`artifacts/site/Salish-Surf-Report.md` embeds a still of each 3D wave surface,
because no Markdown viewer can render the interactive PyVista scenes. To see
those scenes live instead, export the report and serve it:

```bash
python -m salish.web.export_html --serve
```

That writes `artifacts/site/Salish-Surf-Report.html`, with each scene in an
iframe, and opens it. It is served over HTTP rather than opened straight from
disk because browsers disagree about whether a `file://` page may frame another
local file. Pass `--no-3d` to keep the scenes as links, which makes the page
safe to open from disk.

### Large data files

The bathymetry rasters under `data/raw/bathymetry/` and the `.npy` grids
derived from them are gitignored because of their size. Regenerate the grids
from the rasters with `python -m salish.processing.bathymetry`. The one
exception is `data/processed/bathymetry/gebco_strait_subset.nc`, which is
small and tracked because the pipeline needs it.

## Download NOAA data (waves and tides)
Every 15 minutes I retrieve new infomration from NOAA on the waves, tides, current, and wind. See salish/ingest/noaa.py to see the functions that call on the NOAA API. This data is collected by NOAA bouys such as the[New Dungeness Buoy](https://www.ndbc.noaa.gov/station_page.php?station=46088).

 Description of on NOAA bouy measurments is [available here](https://www.ndbc.noaa.gov/faq/measdes.shtml)
