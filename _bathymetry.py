
#Subsetting thr data: 
import xarray as xr
import math
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import os 

subset = xr.open_dataset("data/gebco_strait_subset.nc")

# Choose your zoom area (in degrees)
lat_min, lat_max = 48.1, 48.45
lon_min, lon_max = -123.75, -122.5

# Subset to the fort ebey area: 
zoom = subset.sel(
    lat=slice(lat_min, lat_max),
    lon=slice(lon_min, lon_max)
)


'''
# Plot it
zoom_elev.plot(
    cmap="terrain",
    figsize=(6, 5),
    cbar_kwargs={"label": "Depth (m)"}
)
plt.title("Zoomed Subset of GEBCO Bathymetry")
plt.show()



subset_elev.plot(
    cmap="terrain",           # land+sea style
    figsize=(6, 5),
    cbar_kwargs={"label": "Elevation (m)"}
)
plt.show()
#Ok, now to find the gradient: 
'''

lat = subset["lat"].values
lon = subset["lon"].values

dlat_deg = np.abs(np.mean(np.diff(lat)))
dlon_deg = np.abs(np.mean(np.diff(lon)))

lat_m = 111_320
mean_lat = np.mean(lat)

long_m = lat_m * np.cos(np.radians(mean_lat))

dlat_m = dlat_deg * lat_m
dlon_m = dlon_deg * lat_m * np.cos(np.radians(mean_lat))

dz_dlat, dz_dlon = np.gradient(subset["elevation"], dlat_m, dlon_m)
#and for the zoomed in version: 
dz_dlatz, dz_dlonz = np.gradient(zoom["elevation"], dlat_m, dlon_m)

def find_depth(target_lat=48.493, target_lon=-124.727, dataset=subset):
    # Select the nearest elevation point
    pt = subset["elevation"].sel(
        lat=target_lat,
        lon=target_lon,
        method="nearest"
    )
    # Convert elevation (negative = below sea level) to positive depth
    depth = -pt.values if pt.values < 0 else 0

    return depth

dz_subset = np.arctan2(dz_dlon,dz_dlat) #this gives us the direction fo the gradeint relative to north. 
dz_subset= np.mod(dz_subset, 2*math.pi)
#wrapping into an Xarray: 
dz_subset = subset["elevation"].copy(data=dz_subset)
dz_subset.name = "slope_direction"

def find_slope_azy(target_lat=48.493, target_lon=-124.727, dataset=dz_subset):
    """
    Returns the local slope direction (° clockwise from north)
    at the nearest grid point to the specified latitude/longitude.
    """
    # Select nearest point
    slopeazy = dataset.sel(
        lat=target_lat,
        lon=target_lon,
        method="nearest"
    )

    # Extract scalar direction (already in degrees if you followed prior steps)
    direction = slopeazy.values.item()
    return direction

def step_ray(lat, lon, azy, L, c, H, T, dt):
    """
    Single ray step.
    lat, lon: current position (deg)
    azy: current azimuth (rad, from north, clockwise)
    L: current wavelength (m)
    H: current wave height (m) - held constant in your first version
    T: period (s)
    dt: timestep (s)
    Returns: new_lat, new_lon, new_azi, new_L, new_speed
    """
    g = 9.8
    if c <= .1:
        return lat, lon, azy, L, 0

    # 1) Local depth at current position
    depth = find_depth(lat, lon)

    
    # 2) Current speed (given L and depth -> dispersion approx)
    # For now, deep-water approx unless flagged shallow below

    # 3) Move forward along current direction
    ds = c * dt  # distance traveled this step (m)

    # Components (north, east) in meters
    dy = ds * math.cos(azy)  # toward north
    dx = ds * math.sin(azy)  # toward east

    # Convert to navigational degrees
    dlat = dy / lat_m
    lon_m = lat_m * math.cos(math.radians(lat))
    dlon = dx / lon_m if lon_m != 0 else 0.0

    lat_new = lat + dlat
    lon_new = lon + dlon

    # 4) New depth at the new position
    depth_new = find_depth(lat_new, lon_new)

    # 5) Decide deep vs shallow vs intermediate
    # Use L as current wavelength; thresholds are heuristic
    deep = depth_new > L / 2
    shallow = depth_new < L / 20

    # Initialize new speed / azymuth / wavelength
    L_new = L
    c_new = c
    azy_new = azy

    if deep:
        # No refraction, keep everything the same (for now)
        pass

    elif shallow:
        # Breaking check
        if H > 1.3 * depth_new:
            return lat_new, lon_new, azy, L, 0.0  # speed zero

        # Shallow-water speed
        c_new = math.sqrt(g * depth_new)

        # Bottom slope direction (° from north) -> radians
        slope_rad  = find_slope_azy(lat_new, lon_new)
        slope_v =[math.sin(slope_rad), math.cos(slope_rad)]
        azy_v = [math.sin(azy),math.cos(azy)]
        cross = np.cross(np.append(slope_v, 0), np.append(azy_v, 0))[2]
        theta_i = math.atan2(cross,np.dot(slope_v,azy_v)) #so no we know which way it rotated
        sin_theta_i = cross
        sin_theta_r = (c_new / c) * cross
        #clamping to maintain numerical stability. most a ray can turn is 90* 
        sin_theta_r = max(-1.0, min(1.0, sin_theta_r))

        cos_theta_r = math.copysign(math.sqrt(1-sin_theta_r**2),np.dot(slope_v,azy_v))
        theta_r=math.atan2(sin_theta_r,cos_theta_r)

        azy_new = (slope_rad - theta_r)%(math.pi*2)
        # New wavelength proportional to depth: 
        L_new = math.sqrt(g*depth_new)*T
        

    else:
        # Intermediate depth: dispersion correction
        # (simple 1-step iteration using old L)
        k = 2 * math.pi / L
        kh = k * depth_new
        tanh_kh = math.tanh(kh)
        c_new = math.sqrt((g / k) * tanh_kh)  # phase speed

        slope_rad  = find_slope_azy(lat_new, lon_new)
        slope_v =[math.sin(slope_rad), math.cos(slope_rad)]
        azy_v = [math.sin(azy),math.cos(azy)]
        cross = np.cross(np.append(slope_v, 0), np.append(azy_v, 0))[2]
        theta_i = math.atan2(cross,np.dot(slope_v,azy_v)) #so no we know which way it rotated
        sin_theta_i = cross
        sin_theta_r = (c_new / c) * cross
        #clamping to maintain numerical stability. most a ray can turn is 90* 
        sin_theta_r = max(-1.0, min(1.0, sin_theta_r))

        cos_theta_r = math.copysign(math.sqrt(1-sin_theta_r**2),np.dot(slope_v,azy_v))
        theta_r=math.atan2(sin_theta_r,cos_theta_r)

        azy_new = (slope_rad - theta_r)%(math.pi*2)

        L_new = L * (c_new / c)

    return lat_new, lon_new, azy_new, L_new, c_new

def trace_ray(lat0, lon0, T, H, azys, n_steps=1000, dt=5.0):
    """
    Marches a single wave ray across the bathymetry.

    Parameters
    ----------
    lat0, lon0 : float
        Starting latitude and longitude (deg)
    T : float
        Wave period (s)
    H : float
        Wave height (m)
    MWD_deg : float
        Mean wave direction *from which* the wave is coming (rad, clockwise from north)
    n_steps : int
        Number of timesteps to march
    dt : float
        Duration of each timestep (s)
    
    Returns
    -------
    pandas.DataFrame
        Columns: ['step', 'lat', 'lon', 'azi', 'L', 'c', 'depth']
    """
    g = 9.81
    
    # Initialize wavelength and deep-water speed
    L = g * T**2 / (2 * math.pi)
    c = g * T / (2 * math.pi)

    # Initialize starting values
    lat=lat0
    lon= lon0

    # Set up storage for results
    records = []
    
    for step in range(n_steps):
        depth = find_depth(lat, lon)

        # Save current state
        records.append({
            "step": step,
            "lat": lat,
            "lon": lon,
            "azy": azy,  # stored as degrees for readability
            "L": L,
            "c": c,
            "depth": depth
        })

        # Break if wave has stopped (breaking or zero velocity)
        if c <= 0:
            print(f"Stopped at step {step}: wave broke or stalled.")
            break
        
        # Take a step
        lat, lon, azy, L, c = step_ray(lat, lon, azy, L, c, H, T, dt)
    
    # Convert to DataFrame
    ray_df = pd.DataFrame(records)
    return ray_df
# ---------------------------------------
# INITIALIZE RAY STARTS
# ---------------------------------------
def intialise_ray_starts(P1,n_rays,front_width, mean_wave_direction, T, H):

    '''
        P1 = (48.5, -124.8)   # center of wave front (lat, lon)
        n_rays = 30                  # number of rays
        front_width_m = 20000        # total wave front width (m)
        mean_wave_direction = direciton waves are coming from: 
    '''
    wave_front_orientation = (np.radians(mean_wave_direction) - math.pi / 2) % (2 * math.pi)  # perpendicular
    azy = (np.radians(mean_wave_direction)+np.pi)%(np.pi*2)
    spacing_m = front_width / n_rays

    # conversion factors (approx)
    lat_m = 111_000
    lon_m = lat_m * math.cos(math.radians(P1[0]))

    # create starting points evenly spaced along wave front
    ray_starts = np.empty((n_rays, 5))  # (lat, lon, azy, T, H)
    for i in range(n_rays):
        offset = (i - n_rays / 2) * spacing_m  # meters offset from center
        dlat = (offset * math.cos(wave_front_orientation)) / lat_m
        dlon = (offset * math.sin(wave_front_orientation)) / lon_m
        ray_starts[i] = [P1[0] + dlat, P1[1] + dlon, azy, T, H]
    
    return(ray_starts)

# ---------------------------------------
# TRACE MULTIPLE RAYS
# ---------------------------------------

def trace_rays(ray_starts, n_steps=100, dt=20):
    """
    March multiple wave rays across the bathymetry simultaneously.

    Parameters
    ----------
    ray_starts : array of shape (n_rays, 2)
        Starting positions (lat, lon) for each ray.
    T : float
        Wave period (s)
    H : float
        Initial wave height (m)
    azy : float or array-like
        Initial azimuth (radians, from north, clockwise)
    n_steps : int
        Number of time steps
    dt : float
        Time step (s)
    """
    g = 9.81
    n_rays = len(ray_starts)
    #group velocity: 
        #k=2*math.pi/L
        #energy flux is related to croup velocity: 
        #C_g=1/2*c*(1+(1*k*depth)/math.sinh(2*k*depth))
        #but we are assuming a monocromatic ocean (stupid) but its our heuristic first step
    # --- ensure azimuths are an array (if scalar, repeat for all rays)
    # --- initialize state variables per ray

    lats = ray_starts[:, 0].copy()
    lons = ray_starts[:, 1].copy()
    azys = ray_starts[:, 2].copy()
    Ts = ray_starts[:, 3].copy()
    Hs = ray_starts[:, 4].copy()
    H0 = Hs
    

    Ls = np.full(n_rays, g * Ts**2 / (2 * math.pi), dtype=float)  # wavelength
    L0 = Ls
    cs = np.full(n_rays, g * Ts / (2 * math.pi), dtype=float)     # phase speed
                      # wave height (can evolve later)

    #for conversion between spherical and plane coords. 
    lat_m = 111_000
    lon_m = lat_m * np.cos(np.radians(lats.mean()))
    difx = np.diff(lons) * lon_m
    dify = np.diff(lats) * lat_m
    spacing0 = np.sqrt(difx**2 + dify**2)

    # --- storage
    records = [[] for _ in range(n_rays)]

    # --- time stepping loop
    for step in range(n_steps):
        # Record current state for each ray
        for i in range(n_rays):
            depth = find_depth(lats[i], lons[i])  # user-defined function
            records[i].append({
                "step": step,
                "lat": lats[i],
                "lon": lons[i],
                "azy": azys[i],
                "L": Ls[i],
                "c": cs[i],
                "H": Hs[i],
                "depth": depth,
            })
            '''
            # trying the jacobain: 
            x0, y0 = lon[i,   step],   lat[i,   step]
            x1, y1 = lon[i+1, step],   lat[i+1, step]   # neighbor in "u" direction (across rays)
            x2, y2 = lon[i,   step+1], lat[i,   step+1] # neighbor in "v" direction (along ray)

            dx_du = (x1 - x0) * lon_m
            dy_du = (y1 - y0) * lat_m

            dx_dv = (x2 - x0) * lon_m
            dy_dv = (y2 - y0) * lat_m

            J_area = abs(dx_du * dy_dv - dx_dv * dy_du)   # |det 2x2|
            '''
            #this isint actually the jacobian becasue I am only scaling a line length 
            difx = np.diff(lons) * lon_m
            dify = np.diff(lats) * lat_m
            spacing = np.sqrt(difx**2 + dify**2)
            J = np.ones(n_rays)
            if len(spacing) > 1:
                J[1:-1] = spacing[1:] / spacing0[1:]
                J[0] = J[1]
                J[-1] = J[-2]

            # Take a physical step
            lats[i], lons[i], azys[i], L_new, c_new = step_ray(
                lats[i], lons[i], azys[i], Ls[i], cs[i], Hs[i], Ts[i], dt
            )

            # Update L and c
            Ls[i] = L_new
            cs[i] = c_new

            val = L0[i]/Ls[i]/J[i]
            val = max(val, 0)#clamp for num. stability
            # Recalculate new height using flux conservation and divergence
            Hs[i] =  min(H0[i] * np.sqrt(val), 2*H0[i]) #but also clamp to never be more then 2* the OG amplitude
            #ending simulation when they stop: c
        if np.all(cs <= 0):
            print(f"All waves stopped at step {step}. Ending simulation.")
            break
        #flux = 1.025*9.8*H**2*(g * T**2 / (2 * math.pi))/8
        #computing the new height given how the rest of the wave's properties have changed 
        # When I do group velocity, and energy flux, I will use the jacobian, and measure the stretching of the vector veild at every step: 
    # Convert to DataFrames
    ray_dfs = [pd.DataFrame(rec) for rec in records]
    return ray_dfs


import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np


def plot_ray_tracing(ray_dfs, subset, name):

    """
    Visualize multiple ray paths over bathymetry with dual colorbars.
    
    Left: Depth (m) — vertical bar
    Bottom: Wave height (m) — horizontal bar
    """

    # --- Create figure & axis
    fig, ax = plt.subplots(figsize=(10, 8))
    

    # --- Bathymetry base layer
    bathy = subset["elevation"]
    bathy_cmap = cm.get_cmap("gray")  # white=shallow, black=deep
    vmin_bathy, vmax_bathy = -100, 0

    bathy_plot = bathy.plot(
        ax=ax,
        cmap=bathy_cmap,
        vmin=vmin_bathy,
        vmax=vmax_bathy,
        add_colorbar=False,  # we'll add our own
        alpha=1,
    )

    # Maintain geographic aspect ratio
    lat0 = float(bathy["lat"].mean())
    ax.set_aspect(1 / np.cos(np.radians(lat0)))

    # --- Colormap setup for wave height
    wave_cmap = cm.viridis
    min_wave = 0
    max_wave_start = max([df["H"].iloc[1] for df in ray_dfs])
    max_wave = 2*max_wave_start

    wave_norm = mcolors.Normalize(vmin=min_wave, vmax=max_wave)

    # --- Plot rays colored by wave height
    for df in ray_dfs:
        sc = ax.scatter(
            df["lon"], df["lat"],
            c=df["H"],
            cmap=wave_cmap,
            norm=wave_norm,
            s=5,
            alpha=0.8,
            edgecolor="none",
            zorder=3
        )
        # Mark the end of each ray in the correct color
        H_end = df["H"].iloc[-1]
        end_color = wave_cmap(wave_norm(H_end))
        ax.scatter(df["lon"].iloc[-1], df["lat"].iloc[-1],
                   color=end_color, s=30, zorder=4)

    # --- Add colorbars ---
    ## Horizontal colorbar for wave height
    sm_wave = cm.ScalarMappable(norm=wave_norm, cmap=wave_cmap)
    cbar_wave = fig.colorbar(sm_wave, ax=ax, orientation="horizontal",
                         pad=0.10, fraction=0.04, aspect=30)
    cbar_wave.set_label("Wave Height (m)", fontsize=11)

    ## Horizontal colorbar for bathymetry
    sm_bathy = cm.ScalarMappable(norm=mcolors.Normalize(vmin=vmin_bathy, vmax=vmax_bathy),
                                 cmap=bathy_cmap)
    cbar_bathy = fig.colorbar(
        sm_bathy, ax=ax,
        orientation="horizontal",
        pad=0.10, fraction=0.04, aspect=30
    )
    cbar_bathy.set_label("Depth (m)", fontsize=11)
    cbar_bathy.ax.invert_yaxis()  # optional: deeper = lower

    # --- Final polish
    ax.set_title(f"Wave Refraction over Salish Sea {name} Bathymetry", fontsize=14, fontweight="bold")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.grid(alpha=0.3)
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.show()

    # --- Save
    os.makedirs("plots/maps", exist_ok=True)
    fig.savefig(f"plots/maps/{name}.png", bbox_inches="tight", dpi=200)


"""
ray_starts = intialise_ray_starts(P1 = (48.5, -124.8),n_rays = 40,front_width = 20_000, mean_wave_direction = wave124["MWD"], T= wave124["DPD"], H = wave124["WVHT"])
rayz_startz1 = intialise_ray_starts(P1 = (48.173, -123.607), n_rays = 10,front_width = 6000, mean_wave_direction = wave123pa["MWD"], T= wave123pa["DPD"], H = wave123pa["WVHT"])
rayz_startz2 = intialise_ray_starts(P1 = (48.332, -123.179), n_rays = 20,front_width = 10000, mean_wave_direction = wave123nd["MWD"], T= wave123nd["DPD"], H = wave123nd["WVHT"])

puget_rays = trace_rays(ray_starts,
                        n_steps=2000, 
                        dt=5)

Island_rays1 = trace_rays(rayz_startz1,
                        n_steps=2000, 
                        dt=5)
Island_rays2 = trace_rays(rayz_startz2,
                        n_steps=2000, 
                        dt=5)
Island_rayz = Island_rays1 + Island_rays2


plot_ray_tracing(puget_rays, subset, "Puget Sound") #nice 

plot_ray_tracing(Island_rayz, zoom, "Inner Puget Sound")
"""