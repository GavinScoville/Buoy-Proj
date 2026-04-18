
#Subsetting the data: 
import xarray as xr
import math
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import os 

subset = xr.open_dataset("data/gebco_strait_subset.nc") #bringing in my bathymetric dataset

# Choose zoom area (in degrees)
lat_min, lat_max = 48.1, 48.45
lon_min, lon_max = -123.75, -122.5

# Subset: 
zoom = subset.sel(
    lat=slice(lat_min, lat_max),
    lon=slice(lon_min, lon_max)
)


lat = subset["lat"].values
lon = subset["lon"].values

dlat_deg = np.abs(np.mean(np.diff(lat)))
dlon_deg = np.abs(np.mean(np.diff(lon)))

lat_m = 111_320
mean_lat = np.mean(lat)

long_m = lat_m * np.cos(np.radians(mean_lat))

dlat_m = dlat_deg * lat_m
dlon_m = dlon_deg * lat_m * np.cos(np.radians(mean_lat))
print((lat[0]-lat[-1])*lat_m)
print((lon[0]-lon[-1])*long_m)
print(len(lat))
print(len(lon))