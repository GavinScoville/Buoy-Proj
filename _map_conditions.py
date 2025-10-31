import os
import numpy as np
import pandas as pd
import requests
import zipfile
from pyproj import Geod
from zoneinfo import ZoneInfo

from _fetch_buoy_functions import fetch_and_clean_buoy_data, predict_currents,predict_tides
from _geodesy import arclength, azimuth
from _report_funcitons import  wave_summary, current_report, tide_report, wind_report, setstatus
PacificTime = ZoneInfo("America/Los_Angeles")
Ocean_Papa = "46246"
South_Nomad = "46036"
Northwest_Seattle = "46419"
La_Persouse_Bank = '46204' #Off Vancouver Island
Neah_Bay = '46087' #Neah Bay bouy
Port_Angelis = '46267' #PA bouy
New_Dungeness = '46088' #Off shore fort Ebey 

#Funcitons for the map:
waves145 = fetch_and_clean_buoy_data(Ocean_Papa) #returns a datafeame of the last 45 days of data
waves124 = fetch_and_clean_buoy_data(Neah_Bay)
waves123pa = fetch_and_clean_buoy_data(Port_Angelis)
waves123nd= fetch_and_clean_buoy_data(New_Dungeness)
wave145 = wave_summary(waves145, "Ocean Papa", PacificTime) # wave summary returns a dataframe with the latest data and calculated energy etc.
wave124 = wave_summary(waves124, "Neah Bay", PacificTime)
wave123pa = wave_summary(waves123pa, "Port Angelis", PacificTime)
wave123nd = wave_summary(waves123nd, "New Dungeness", PacificTime)

def add_scalebar(ax, proj, length, location=(0.5, 0.1), linewidth=2, color='black', units='km'):
    """
    Adds a scale bar to a Cartopy map.
    length: length of the scale bar in km
    location: (x, y) in axes fraction coordinates (0 to 1)
    """
    # get map extent
    lon_min, lon_max, lat_min, lat_max = ax.get_extent(crs=proj)
    lon_center = (lon_min + lon_max) / 2
    lat = lat_min + (lat_max - lat_min) * location[1]
    
    # find how many degrees of longitude correspond to 'length' km at that latitude
    geod = Geod(ellps='WGS84')
    lon2, lat2, _ = geod.fwd(lon_center, lat, 90, length * 1000)
    dx = lon2 - lon_center
    
    # compute start and end positions for bar
    x0 = lon_center - dx / 2
    x1 = lon_center + dx / 2
    y = lat

    # draw bar
    ax.plot([x0, x1], [y, y], transform=proj, color=color, linewidth=linewidth)
    ax.text(lon_center, y - (lat_max - lat_min) * 0.02,
            f'{length} {units}', transform=proj,
            horizontalalignment='center', verticalalignment='top', fontsize=9, color=color)
    
def add_north_arrow(ax, location=(0.95, 0.1), width=0.03, height=0.1, pad=0.02, color='black'):
    """
    Adds a north arrow to the map.
    location: (x, y) in axis fraction coordinates (0–1)
    width, height: size of arrow in axis fraction
    """
    x, y = location
    ax.annotate('N',
                xy=(x, y + height / 2), xytext=(x, y - height / 2),
                arrowprops=dict(facecolor=color, width=5, headwidth=5),
                ha='center', va='center', fontsize=10,
                xycoords=ax.transAxes)



def map_pacific(wave145, wave124, wave123pa, wave123nd):

    # Find the base directory (works in scripts & notebooks)
    try:
        base_dir = os.path.dirname(__file__)
    except NameError:
        base_dir = os.getcwd()

    # Create a local Cartopy data folder inside your project
    data_dir = os.path.join(base_dir, "cartopy_data")
    os.makedirs(os.path.join(data_dir, "shapefiles", "natural_earth", "physical"), exist_ok=True)
    import cartopy
    # Tell Cartopy to use it
    cartopy.config['data_dir'] = data_dir

    # File to ensure
    fname = "ne_10m_land.zip"
    local_path = os.path.join(data_dir, "shapefiles", "natural_earth", "physical", fname)
    url = f"https://naturalearth.s3.amazonaws.com/10m_physical/{fname}"


    if not os.path.exists(local_path):
        print(f"Downloading {url} ...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(r.content)
        print("Download complete.")
    else:
        print("Natural Earth shapefile already present.")

    print("Cartopy data dir:", cartopy.config["data_dir"])

    # Ensure the nested folder exists
    shp_dir = os.path.join(data_dir, "shapefiles", "natural_earth", "physical")
    os.makedirs(shp_dir, exist_ok=True)

    # Path to the zip file and extracted .shp
    zip_path = os.path.join(shp_dir, "ne_10m_land.zip")
    shp_path = os.path.join(shp_dir, "ne_10m_land.shp")

    # If the shapefile doesn’t exist but the zip does → unzip it automatically
    if os.path.exists(zip_path) and not os.path.exists(shp_path):
        print("Extracting Natural Earth shapefile ...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(shp_dir)
        print("Extraction complete.")
    elif not os.path.exists(zip_path):
        print("⚠️ Missing ne_10m_land.zip — please run your downloader once.")
    else:
        print("Natural Earth shapefile already present.")


    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    print("Cartopy data dir:", cartopy.config["data_dir"])
    land = cfeature.NaturalEarthFeature('physical', 'land', '10m')
    print(land)
    print(land.category, land.name, land.scale)

    # ---------------------------------------------------------------------
    # STEP 2 — Define Station Metadata Table
    # ---------------------------------------------------------------------

    prestations = pd.DataFrame({
        "name": ["Ocean Papa", "Neah Bay", "Port Angeles", "New Dungeness"],
        "station_id": ["46246", "46087", "46267", "46088"],
        "lat": [49.903, 48.493, 48.173, 48.332],
        "lon": [-145.246, -124.727, -123.607, -123.179],
        "depth_m": [4252, 259, 75, 115],
        "notes": [
            "",
            "",
            "",
            ""
        ]
    })

    wave_data = pd.DataFrame({
        "Ocean PAPA": wave145,
        "Neah Bay": wave124,
        "Port Angeles": wave123pa,
        "New Dungeness": wave123nd
    }).T
    stations = pd.concat([prestations.reset_index(drop=True), wave_data.reset_index(drop=True)], axis=1)
    # Load the status CSVs: 
    ocean_papa = pd.read_csv("data/status/ocean_papa.csv")
    ocean_papa_status = ocean_papa["status"].iloc[-1]

    neah_bay = pd.read_csv("data/status/Neah_Bay.csv")
    neah_bay_status = neah_bay["status"].iloc[-1]

    port_angelis = pd.read_csv("data/status/Port Angelis.csv")
    pa_status = port_angelis["status"].iloc[-1]

    new_dungeness = pd.read_csv("data/status/New Dungeness.csv")
    nd_status = new_dungeness["status"].iloc[-1]

    stations["status"] = [ocean_papa_status, neah_bay_status, pa_status, nd_status]

    radians = np.radians(stations["wave_bearing"].astype(float))
# Compute unit vector components (u = east-west, v = north-south)

    stations["u"] = np.sin(radians)
    stations["v"] = np.cos(radians)

    stations["vadjust"] = [.2,0,-1.6,-.4]
    stations["hadjust"] = [.5,-1,-1,.5]

    # ---------------------------------------------------------------------
    # STEP 4-- MAP: 
    # ---------------------------------------------------------------------
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(8, 6))

    ax = plt.axes(projection=proj)
    ax.set_extent([-146, -120, 44, 54], crs=proj)
    ax.add_feature(land)

    add_scalebar(ax,proj, length=100)  # 100 km scale bar
    add_north_arrow(ax) #north arow

    # Plot stations
    for _, row in stations.iterrows():
        ax.plot(row["lon"], row["lat"],
                marker="o", 
                color="green" if row["status"] == 1 else "red", markersize=8,
                transform=proj,
                label=f'{row["name"]} ({row["station_id"]})')
        ax.text(row["lon"] + row["hadjust"], row["lat"] + row["vadjust"],
            f'{row["name"]}\n{row["notes"]}',
            transform=proj, fontsize=9, verticalalignment="bottom")
    
    ax.quiver(
        stations["lon"], stations["lat"], stations["u"], stations["v"],
        transform=proj,
        color="navy",
        scale=15,   # arrows shrink for smaller waves
        width=0.004,
        zorder=5 
    )    
    


    # Title
    plt.title("NOAA Wave Monitoring Stations — Northeast Pacific", fontsize=14, fontweight="bold")
    os.makedirs("plots/maps", exist_ok=True)
    fig.savefig(f"plots/maps/pacific.png", bbox_inches="tight", dpi=150)

map_pacific(wave145, wave124, wave123pa, wave123nd)