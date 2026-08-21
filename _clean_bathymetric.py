#Subsetting the data: 
import xarray as xr
import math
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import os 
import rasterio
import rioxarray as rxr

#Here we take the bathymetric data subset from _bathymetry.py and turn it into grids of squares for FDM:
# The tricky bit is that downloaded data can come in all types, especailly .tiff(a 1d raster immge)
# and .nc which is more like a scientific dataset.  

subset = xr.open_dataset("data/gebco_strait_subset.nc") #bringing in my bathymetric dataset
grid_size=10 # this seems to be a decent size for anything 7 seconds and up 


# Choose zoom area (in degrees)
lat_min, lat_max = 48.00208333 , 48.74791667 
lon_min, lon_max = -124.99791667, -122.00208333
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

grid_height = int((lat_max-lat_min)*lat_m/grid_size) #how many cells tall
grid_width = int((lon_max-lon_min)*long_m/grid_size) # how many cells wide

lon_grid =  lon_min + np.arange(grid_width) * (grid_size/long_m) 
lat_grid = lat_min + np.arange(grid_height) * (grid_size / lat_m)

#making an array to store bahtmetric data:
bathymetry_grid = zoom.sel(
    lon=xr.DataArray(lon_grid, dims="lon"),
    lat=xr.DataArray(lat_grid, dims="lat"),
    method="nearest"
)

np.save("data/salish_sea_bathymetry_grid.npy", bathymetry_grid.elevation)
depth = np.load("data/salish_sea_bathymetry_grid.npy")
print(f"Bathymetry grid shape: {depth.shape}")

