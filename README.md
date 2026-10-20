# The goal of this program is to investigate how waves propogate through the salish sea. It may be useful for informing surfing conditions.

## the project has the following strucutre:

### salish/
The code that pulls data, runs it through numerical models. It will output reports and visualisations

This is also the code that sends out alerts

Hardcoded buoy tags and coordinates live in `data/stations.yaml`; all input and
output locations are defined in `salish/paths.py`.

### Data:
The home for bathymetric data and bouy data

### Artifacts:
The home for deliverables: plots, forcasts, and tables

## Running the pipeline

From the repo root:

```bash
python -m salish.pipeline
```

Set `SALISH_NO_EMAIL=1` to run everything (fetch, modelling, plots, report)
without delivering the surf alerts:

```bash
SALISH_NO_EMAIL=1 python -m salish.pipeline
```

Email delivery needs `EMAIL_USER` and `EMAIL_PASS`, read from `.env` locally
and from repository secrets in CI.

### Large data files

The bathymetry rasters under `data/bathymetry_file/` and the `.npy` grids
derived from them are gitignored because of their size. Regenerate the grids
from the rasters with `python -m salish.clean_bathymetry`. The one exception is
`data/bathymetry_file/gebco_strait_subset.nc`, which is small and tracked
because the pipeline needs it.

## Download NOAA data (waves and tides)
Every 15 minutes I retrieve new infomration from NOAA on the waves, tides, current, and wind. See salish/fetch_buoy.py to see the functions that call on the NOAA API. This data is collected by NOAA bouys such as the[New Dungeness Buoy](https://www.ndbc.noaa.gov/station_page.php?station=46088).

 Description of on NOAA bouy measurments is [available here](https://www.ndbc.noaa.gov/faq/measdes.shtml)
