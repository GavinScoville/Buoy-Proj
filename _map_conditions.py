import os
import numpy as np
import pandas as pd
import requests
import zipfile
from pyproj import Geod
from zoneinfo import ZoneInfo


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

def download_map():
        # Find the base directory 
    try:
        base_dir = os.path.dirname(__file__)
    except NameError:
        base_dir = os.getcwd()

    # Create a local Cartopy data folder inside project
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
        print("Natural Earth data is already local")

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
        print("⚠️ Missing ne_10m_land.zip — please download")
    else:
        print("Natural Earth shapefile already present.")


    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors
    import cartopy.crs as ccrs

    print("Cartopy data dir:", cartopy.config["data_dir"])
    land = cfeature.NaturalEarthFeature('physical', 'land', '10m')
    print(land)
    print(land.category, land.name, land.scale)
    return

def map_pacific(pacific_waves,wave133,wave126,wave125, wave124, wave123pa, wave123nd):
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
        print("Natural Earth data is already local")

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
        print("⚠️ Missing ne_10m_land.zip — please download")
    else:
        print("Natural Earth shapefile already present.")


    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors
    import cartopy.crs as ccrs

    print("Cartopy data dir:", cartopy.config["data_dir"])
    land = cfeature.NaturalEarthFeature('physical', 'land', '10m')
    print(land)
    print(land.category, land.name, land.scale)
    # ---------------------------------------------------------------------
    # STEP 1 -- Build station metadata
    # ---------------------------------------------------------------------
    prestations = pd.DataFrame({
        "name": [
            "Ocean PAPA",
            "South Nomad",
            "La Perouse Bank",
            "Tillamook OR",
            "Neah Bay",
            "Port Angeles",
            "New Dungeness"
        ],
        "station_id": [
            "46246",
            "46036",
            "46206",
            "46089",
            "46087",
            "46267",
            "46088",
        ],
        "lat": [
            49.903,
            48.360,
            48.840,
            45.928,
            48.493,
            48.173,
            48.332
        ],
        "lon": [
            -145.246,
            -133.940,
            -126.000,
            -125.815,
            -124.727,
            -123.607,
            -123.179
        ],
        "depth_m": [
            4252,
            None,
            None,
            None,
            None,
            259,
            75
        ],
        "notes": [
            "Advanced wave data.",
            "Wind data only.",
            "No directional data.",
            "No directional data.",
            "",
            "",
            ""
        ]
    })


    # Combine latest buoy readings
    wave_data = pd.DataFrame({
        "Ocean Papa": pacific_waves["WVHT"].iloc[0] if "WVHT" in pacific_waves else np.nan,
        "South Nomad": wave133.get("WVHT", np.nan),
        "La Perouse Bank": wave126.get("WVHT", np.nan),
        "Tillamook OR": wave125.get("WVHT", np.nan),
        "Neah Bay": wave124.get("WVHT", np.nan),
        "Port Angeles": wave123pa.get("WVHT", np.nan),
        "New Dungeness": wave123nd.get("WVHT", np.nan)
    }, index=["WVHT"]).T.reset_index(drop=True)

    # Merge metadata + current wave height
    stations = pd.concat([prestations.reset_index(drop=True), wave_data], axis=1)

    # ---------------------------------------------------------------------
    # STEP 2 -- Load station status
    # ---------------------------------------------------------------------

    stations["vadjust"] = [0.2,0.2,.2,0, 0, -1, -0.4]
    stations["hadjust"] = [0.5,.5,-2,0, -1, -1, 0.5]

    # ---------------------------------------------------------------------
    # STEP 3 -- Prepare vector data for wave propagation
    # ---------------------------------------------------------------------
    pacific_waves["newlat"] = pd.to_numeric(pacific_waves.get("newnorth", np.nan), errors="coerce")
    pacific_waves["newlon"] = pd.to_numeric(pacific_waves.get("neweast", np.nan), errors="coerce")
    pacific_waves["newazy"] = pd.to_numeric(pacific_waves.get("newazy", np.nan), errors="coerce")
    pacific_waves["WVHT"] = pd.to_numeric(pacific_waves.get("WVHT", np.nan), errors="coerce")

    # Compute u,v components (for quiver arrows)
    radians = np.radians(pacific_waves["newazy"])
    pacific_waves["u"] = np.sin(radians)
    pacific_waves["v"] = np.cos(radians)

    # ---------------------------------------------------------------------
    # STEP 4 -- Plot map
    # ---------------------------------------------------------------------
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=proj)

    norm = mcolors.Normalize(vmin=0, vmax=10)
    cmap = cm.viridis
    bouycolor = cmap(norm(wave_data["WVHT"]))

    ax.set_facecolor("black")
    ax.set_extent([-146, -120, 44, 54], crs=proj)
    ax.add_feature(land, zorder=2, facecolor = "white")

    add_scalebar(ax, proj, length=100)
    add_north_arrow(ax)

    # Plot stations
    for idx, row in stations.iterrows():
        ax.plot(
            row["lon"], row["lat"],
            marker="o",
            color=bouycolor[idx],
            markersize=8,
            transform=proj,
            zorder=4
        )
        ax.text(
            row["lon"] + row["hadjust"],
            row["lat"] + row["vadjust"],
            f'{row["name"]}',
            transform=proj,
            fontsize=9,
            color = "grey",
            verticalalignment="bottom",
            zorder=6
        )

    # ---------------------------------------------------------------------
    # STEP 5 -- Plot quiver (wave direction arrows)
    # ---------------------------------------------------------------------
    # Handle invalid values
    colors = cmap(norm(pacific_waves["WVHT"]))

    q = ax.quiver(
        pacific_waves["newlon"], pacific_waves["newlat"],
        pacific_waves["u"], pacific_waves["v"],
        transform=proj,
        color=colors,
        scale=25,
        width=0.004,
        zorder=1
    )

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cbar = plt.colorbar(sm, ax=ax, shrink=0.4, pad=0.05)
    cbar.set_label("Wave Height (m)")

    plt.title("Known Waves in the Northeast Pacific", fontsize=14, fontweight="bold")
    os.makedirs("plots/maps", exist_ok=True)
    plt.tight_layout()

    fig.savefig("plots/maps/pacific.png", bbox_inches="tight", dpi=150)
