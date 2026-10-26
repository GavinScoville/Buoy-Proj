import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from herbie import Herbie
from datetime import datetime, timedelta
from salish.core.stations import get_station
from salish.paths import GRIB_CACHE, PLOTS

# Get station coordinates
s = get_station("46087")
lat, lon = s["lat"], s["lon"]

# Define dates to fetch
start_date = datetime(2026, 9, 20)
num_days = 5
dates = [start_date + timedelta(days=i) for i in range(num_days)]

# Collect data for multiple days
swell_data = []
wind_data = []
date_labels = []

for date in dates:
    print(f"Fetching data for {date.strftime('%Y-%m-%d')}...")

    try:
        H = Herbie(
            date.strftime("%Y-%m-%d 12:00"),
            model="gfs_wave",
            product="wcoast.0p16",
            fxx=0,
            save_dir=GRIB_CACHE,
        )
        ds_list = H.xarray()
        myFile = H.download(verbose=False)

        # Get swell data (first dataset)
        ds_swell = ds_list[0]

        # Get wind wave data (second dataset)
        ds_wind = ds_list[1]

        # Adjust longitude if needed
        if float(ds_swell.longitude.max()) > 180:
            lon_adj = lon % 360
        else:
            lon_adj = lon

        # Select nearest point for swells
        neah_swell = ds_swell.sel(latitude=lat, longitude=lon_adj, method="nearest")
        neah_wind = ds_wind.sel(latitude=lat, longitude=lon_adj, method="nearest")

        # Extract swell parameters (orderedSequenceData: 1.0=swell1, 2.0=swell2, 3.0=swell3)
        for i in range(3):
            swell_idx = float(i + 1)
            swell_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'swell_num': i + 1,
                'direction': float(neah_swell['swdir'].sel(orderedSequenceData=swell_idx).values),
                'height': float(neah_swell['shts'].sel(orderedSequenceData=swell_idx).values),
                'period': float(neah_swell['mpts'].sel(orderedSequenceData=swell_idx).values),
            })

        # Extract wind wave parameters (handle NaN values)
        try:
            wind_dir = float(neah_wind['wvdir'].values) if not np.isnan(float(neah_wind['wvdir'].values)) else float(neah_wind['dirpw'].values)
            wind_ht = float(neah_wind['shww'].values) if not np.isnan(float(neah_wind['shww'].values)) else float(neah_wind['perpw'].values) * 0.5
            wind_per = float(neah_wind['mpww'].values) if not np.isnan(float(neah_wind['mpww'].values)) else float(neah_wind['perpw'].values)
        except:
            wind_dir = float(neah_wind['dirpw'].values)
            wind_ht = float(neah_wind['perpw'].values) * 0.5
            wind_per = float(neah_wind['perpw'].values)

        wind_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'direction': wind_dir,
            'height': wind_ht,
            'period': wind_per,
        })

        date_labels.append(date.strftime('%m-%d'))

    except Exception as e:
        print(f"Error fetching data for {date.strftime('%Y-%m-%d')}: {e}")
        continue

# Convert to DataFrames
swell_df = pd.DataFrame(swell_data)
wind_df = pd.DataFrame(wind_data)

print("\nSwell Data:")
print(swell_df)
print("\nWind Wave Data:")
print(wind_df)

# Create quiver plot
fig, ax = plt.subplots(figsize=(14, 8))

# Function to convert direction and magnitude to components
def dir_to_components(direction, magnitude):
    """Convert direction (degrees from North) and magnitude to u, v components"""
    rad = np.radians(direction)
    u = magnitude * np.sin(rad)  # eastward component
    v = magnitude * np.cos(rad)  # northward component
    return u, v

# Plot configuration
num_unique_dates = len(date_labels)
y_positions = {
    'swell1': 3,
    'swell2': 2,
    'swell3': 1,
    'windwave': 0,
}

# Collect arrows for colorbar
all_periods = []
all_colors = []

# Plot wind waves
for idx, (date, row) in enumerate(wind_df.iterrows()):
    u, v = dir_to_components(row['direction'], row['height'])
    color_val = row['period']
    ax.quiver(idx, y_positions['windwave'], u, v, color_val, cmap='viridis', alpha=0.7,
             scale=5, scale_units='xy', width=0.006)
    all_periods.append(color_val)

# Plot swells
swell_colors = ['red', 'blue', 'green']
for swell_num in [1, 2, 3]:
    swell_subset = swell_df[swell_df['swell_num'] == swell_num]
    for idx, (date_idx, row) in enumerate(swell_subset.iterrows()):
        # Skip NaN values
        if np.isnan(row['period']):
            continue

        # Find the position in the date sequence
        date_pos = list(swell_df['date'].unique()).index(row['date'])

        u, v = dir_to_components(row['direction'], row['height'])
        period = row['period']

        # Use period for color intensity
        ax.quiver(date_pos, y_positions[f'swell{swell_num}'], u, v, period,
                 cmap='viridis', alpha=0.8,
                 scale=5, scale_units='xy', width=0.006)
        all_periods.append(period)

# Create custom colorbar
sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(vmin=min(all_periods), vmax=max(all_periods)))
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax, label='Period (seconds)', pad=0.02)

# Formatting
ax.set_xlim(-0.5, num_unique_dates - 0.5)
ax.set_ylim(-0.5, 3.5)
ax.set_xticks(range(num_unique_dates))
ax.set_xticklabels(date_labels, rotation=45)
ax.set_yticks(list(y_positions.values()))
ax.set_yticklabels(list(y_positions.keys()), rotation=0)
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Wave Type', fontsize=12)
ax.set_title(f'Swell and Wind Wave Vectors at Station {s["name"]} (Lat: {lat}, Lon: {lon})\nArrow Length = Height, Color = Period',
            fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)

# Add legend
from matplotlib.patches import FancyArrowPatch
swell_handles = [plt.Line2D([0], [0], color=swell_colors[i], marker='>', markersize=8, label=f'Swell {i+1}', linestyle='None')
                 for i in range(3)]
wind_handle = plt.Line2D([0], [0], color='purple', marker='>', markersize=8, label='Wind Wave', linestyle='None')
ax.legend(handles=swell_handles + [wind_handle], loc='upper left', fontsize=10)

plt.tight_layout()
plt.savefig(PLOTS / "swell_arrow_plot.png", dpi=300, bbox_inches='tight')
print("\nPlot saved to plots/swell_arrow_plot.png")
plt.show()
