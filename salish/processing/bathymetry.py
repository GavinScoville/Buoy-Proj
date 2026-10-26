"""
Convert bathymetric data (TIFF or NetCDF) to gridded .npy format for FDM simulations.
Supports both NOAA GEBCO .nc files and 30m resolution TIFF grids.
"""

import xarray as xr
import numpy as np
import os
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS
from salish.paths import BATHYMETRY, RAW_BATHYMETRY


#A good place to get data: https://www.ncei.noaa.gov/maps/bathymetry/?demFootprintsVisible=true&demShadedReliefVisible=true&xmax=-122.473&xmin=-123.231&ymax=48.347&ymin=48.060

# Ensure script runs from project root regardless of VS Code working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print(f"Working directory: {os.getcwd()}\n")


def load_bathymetry_file(input_file):
    """
    Load bathymetry data from TIFF or NetCDF file.

    Returns:
        data: 2D elevation array (positive = land, negative = water)
        lat: 1D latitude coordinates
        lon: 1D longitude coordinates
        crs: Coordinate reference system (for TIFF)
    """

    file_ext = os.path.splitext(input_file)[1].lower()

    print(f"Loading bathymetry from {input_file}")
    print(f"File type: {file_ext}\n")

    if file_ext == '.tif' or file_ext == '.tiff':
        return load_tiff(input_file)
    elif file_ext == '.nc' or file_ext == '.netcdf':
        return load_netcdf(input_file)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}. Use .tif, .tiff, .nc, or .netcdf")


def load_tiff(tiff_file):
    """Load TIFF bathymetry file using rasterio."""

    with rasterio.open(tiff_file) as src:
        # Read the data (band 1 for single-band TIFF)
        data = src.read(1)

        # Get transform to convert pixel coordinates to lat/lon
        transform = src.transform
        crs = src.crs

        print(f"✓ Loaded TIFF")
        print(f"  Shape: {data.shape}")
        print(f"  Data type: {data.dtype}")
        print(f"  CRS: {crs}")

        # Generate lat/lon coordinates from geotransform
        # TIFF coordinates: top-left corner is (0, 0)
        # Affine transform: (x, y) = (c, f) + row * (e, h) + col * (a, b)
        # where a, b = pixel width, rotation; c, d = upper-left x; e, f = rotation, pixel height

        height, width = data.shape
        cols = np.arange(width)
        rows = np.arange(height)

        # Convert pixel coordinates to geographic coordinates
        xs = transform.a * cols + transform.c  # longitude
        ys = transform.e * rows + transform.f  # latitude

        # Create 1D coordinate arrays (assume uniform grid)
        lon = xs
        lat = ys

        print(f"  Lat range: {lat.min():.4f} to {lat.max():.4f}")
        print(f"  Lon range: {lon.min():.4f} to {lon.max():.4f}")
        print(f"  Elevation range: {data.min():.1f} to {data.max():.1f}\n")

        return data, lat, lon, crs


def load_netcdf(nc_file):
    """Load NetCDF bathymetry file using xarray."""

    dataset = xr.open_dataset(nc_file)

    print(f"✓ Loaded NetCDF")
    print(f"  Dimensions: {dataset.dims}")
    print(f"  Variables: {list(dataset.data_vars)}\n")

    # Try to find elevation variable (common names: elevation, z, depth, band_data)
    elevation_var = None
    for var_name in ['elevation', 'z', 'depth', 'band_data', 'data']:
        if var_name in dataset.data_vars:
            elevation_var = var_name
            break

    if elevation_var is None:
        raise ValueError(f"Could not find elevation variable. Available: {list(dataset.data_vars)}")

    data = dataset[elevation_var].values
    lat = dataset['lat'].values if 'lat' in dataset.coords else dataset['y'].values
    lon = dataset['lon'].values if 'lon' in dataset.coords else dataset['x'].values
    crs = None  # NetCDF typically doesn't have CRS info

    print(f"  Variable: {elevation_var}")
    print(f"  Shape: {data.shape}")
    print(f"  Lat range: {lat.min():.4f} to {lat.max():.4f}")
    print(f"  Lon range: {lon.min():.4f} to {lon.max():.4f}")
    print(f"  Elevation range: {data.min():.1f} to {data.max():.1f}\n")

    return data, lat, lon, crs


def grid_bathymetry(data, lat, lon, lat_min, lat_max, lon_min, lon_max, grid_size=10.0):
    """
    Resample bathymetry data to uniform grid for FDM.

    Parameters:
    -----------
    data : 2D array
        Raw elevation data
    lat, lon : 1D arrays
        Coordinate arrays
    lat_min, lat_max, lon_min, lon_max : float
        Geographic bounds (degrees)
    grid_size : float
        Target grid spacing in meters

    Returns:
    --------
    grid_array : 2D array
        Gridded bathymetry
    """

    print(f"Creating uniform grid with {grid_size}m spacing...\n")

    # Constants for geographic to metric conversion
    lat_m = 111_320  # meters per degree latitude
    mean_lat = (lat_min + lat_max) / 2
    lon_m = lat_m * np.cos(np.radians(mean_lat))  # varies with latitude

    # Calculate grid dimensions
    grid_height = int((lat_max - lat_min) * lat_m / grid_size)
    grid_width = int((lon_max - lon_min) * lon_m / grid_size)

    print(f"Grid dimensions: {grid_height} × {grid_width} ({grid_height * grid_width:,} cells)")
    print(f"Geographic bounds:")
    print(f"  Latitude:  {lat_min:.4f}° to {lat_max:.4f}° ({(lat_max-lat_min)*lat_m/1000:.1f} km)")
    print(f"  Longitude: {lon_min:.4f}° to {lon_max:.4f}° ({(lon_max-lon_min)*lon_m/1000:.1f} km)\n")

    # Create regular grid
    lon_grid = lon_min + np.arange(grid_width) * (grid_size / lon_m)
    lat_grid = lat_min + np.arange(grid_height) * (grid_size / lat_m)

    # Interpolate data to regular grid using nearest-neighbor
    # Create meshgrid for interpolation
    lon_2d, lat_2d = np.meshgrid(lon, lat)

    # Create target grid
    lon_grid_2d, lat_grid_2d = np.meshgrid(lon_grid, lat_grid)

    # Nearest-neighbor interpolation (fast, preserves data)
    from scipy.interpolate import griddata
    print(f"Interpolating to regular grid (this may take a moment)...")

    grid_array = griddata(
        (lon_2d.ravel(), lat_2d.ravel()),
        data.ravel(),
        (lon_grid_2d, lat_grid_2d),
        method='nearest'
    )

    print(f"✓ Grid created: {grid_array.shape}")
    print(f"  Elevation range: {np.nanmin(grid_array):.1f} to {np.nanmax(grid_array):.1f}m\n")

    return grid_array


# ============================================================================
# CONFIGURATION
# ============================================================================

# Define your locations and their parameters
locations = {
    'Fort_Ebey': {
        'input_file': RAW_BATHYMETRY / "fort_ebey_10m.tiff",  # Update with your 30m TIFF
        'output_file': BATHYMETRY / "fort_ebey.npy",
        'lat_min': 48.15920, 'lat_max': 48.29917,
        'lon_min': -122.91132, 'lon_max': -122.71666,
        'grid_size': 10.0,  # meters
        'description': 'Northern Olympic Peninsula'
    },
    'The_Dump': {
        'input_file': RAW_BATHYMETRY / "the_dump_10m.tiff",  # Update with your 10m TIFF
        'output_file': BATHYMETRY / "the_dump.npy",
        'lat_min': 48.34, 'lat_max': 48.43,
        'lon_min': -124.75, 'lon_max': -124.57,
        'grid_size': 10.0,  # Use 30m grid for coarse locations
        'description': 'The Headlands of the Peninsula'
    },
    #'Port_Angelis': {
     #   'input_file': RAW_BATHYMETRY / "PA_30m.tiff",  # Update with your 30m TIFF
      #  'output_file': BATHYMETRY / "pa_grid.npy",
       # 'lat_min': 48.08, 'lat_max': 48.32,
        #'lon_min': -123.62, 'lon_max': -122.70,
     #   'grid_size': 10.0,  # Use 30m grid for coarse locations
      #  'description': 'Strait of Juan de Fuca'
   # }
}


# ============================================================================
# PROCESS LOCATION
# ============================================================================

def process_location(location_name, config):
    """Process a single location."""

    print("=" * 70)
    print(f"Processing: {location_name}")
    print(f"Description: {config['description']}")
    print("=" * 70 + "\n")

    try:
        # Check if input file exists
        if not os.path.exists(config['input_file']):
            raise FileNotFoundError(f"Input file not found: {config['input_file']}")

        # Load bathymetry
        data, lat, lon, crs = load_bathymetry_file(config['input_file'])

        # Grid the data
        grid_array = grid_bathymetry(
            data, lat, lon,
            config['lat_min'], config['lat_max'],
            config['lon_min'], config['lon_max'],
            grid_size=config['grid_size']
        )

        # Save to .npy
        output_file = config['output_file']
        print(f"Saving to {output_file}...")
        np.save(output_file, grid_array.astype(np.float32))
        file_size_mb = os.path.getsize(output_file) / 1e6
        print(f"✓ Saved {file_size_mb:.1f} MB\n")

        # Verify
        print("Verifying file...")
        loaded = np.load(output_file)
        print(f"✓ Verified shape: {loaded.shape}")
        print(f"✓ Verified range: {loaded.min():.1f}m to {loaded.max():.1f}m")
        print(f"✓ Data type: {loaded.dtype}\n")

        print(f"✓✓✓ {location_name} completed successfully!\n")
        return True

    except Exception as e:
        print(f"❌ ERROR processing {location_name}: {e}\n")
        import traceback
        traceback.print_exc()
        print()
        return False


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys

    print("\n" + "=" * 70)
    print("BATHYMETRY GRID GENERATOR")
    print("Converts TIFF and NetCDF to .npy for wave simulations")
    print("=" * 70 + "\n")

    # Process all locations or specific ones
    if len(sys.argv) > 1:
        locations_to_process = sys.argv[1:]
    else:
        locations_to_process = list(locations.keys())

    results = {}
    for location_name in locations_to_process:
        if location_name in locations:
            results[location_name] = process_location(location_name, locations[location_name])
        else:
            print(f"⚠️  Location not found: {location_name}")
            print(f"   Available locations: {', '.join(locations.keys())}\n")

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    successful = sum(1 for v in results.values() if v)
    print(f"Successfully processed: {successful}/{len(results)}")

    for location_name, success in results.items():
        symbol = "✓" if success else "✗"
        print(f"  {symbol} {location_name}")

    print("=" * 70 + "\n")

    if successful == len(results):
        print("💡 All grids ready for wave simulations!")
        print("   Update run_all_simulations.py with new bathymetry_file paths\n")

"""    'Flat_Island': {
        'input_file': RAW_BATHYMETRY / "flat_is.tiff",  # NetCDF example
        'output_file': BATHYMETRY / "flat_is_grid.npy",
        'lat_min': 21.3685, 'lat_max': 21.4783,
        'lon_min': -157.7533, 'lon_max': -157.6807,
        'grid_size': 10.0,
        'description': 'Central Pacific'
    }"""