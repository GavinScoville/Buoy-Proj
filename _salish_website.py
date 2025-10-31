import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import math
import os

from _fetch_buoy_functions import fetch_and_clean_buoy_data, predict_currents, predict_tides
from _geodesy import arclength, azimuth
from _plot_conditions_functions import plot_waves, plot_wind, plot_neah_waves, plot_tide_currents
from _report_funcitons import  wave_summary, current_report, tide_report, wind_report, setstatus
from _map_conditions import map_pacific

######################################################################
'''Make a website!'''
######################################################################
#this needs graphs and more facotrs but I am getting tired now 
def render_salish_report(wave145, wave124, wave123pa, wave123nd):
    PacificTime = ZoneInfo("America/Los_Ansgeles")
    timestamp = datetime.now(PacificTime).strftime("%Y-%m-%d %H:%M %Z")
    date = datetime.today().strftime("%Y-%m-%d")

    md = f"""---
layout: single
title: "Fort Ebey Surf Report"
categories: [portfolio]
date: {date}
---

# Fort Ebey Surf Report
**Updated:** {timestamp}

---
![Wave Map](/plots/maps/pacific.png)

## Ocean Papa 
{arclength(49.903, 145.246, 48.2248207, 122.7701732)/1000:.2f}km {azimuth(49.903, 145.246, 48.2248207, 122.7701732):.2f}° to Fort Ebey
- **Wave height:** {wave145.get('WVHT', 'N/A')} m  
- **Dominant period:** {wave145.get('DPD', 'N/A')} s  
- **Mean direction:** {wave145.get('MWD', 'N/A')}°  
- **Wind speed:** {wave145.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave145.get('WDIR', 'N/A')}°  
- **Energy:** {wave145.get('wave_energy', 0):.2f} kJ/m  
- **Status:** {wave145.get('status', 'Unknown')}  
![Wave Plot](/plots/waves/Ocean Papa.png)
- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46246)
---

## Neah Bay 
{arclength(48.493, 124.727, 48.2248207, 122.7701732)/1000:.2f}km {azimuth(48.493, 124.727,48.2248207, 122.7701732):.2f}° to Fort Ebey

- **Wave height:** {wave124.get('WVHT', 'N/A')} m  
- **Dominant period:** {wave124.get('DPD', 'N/A')} s  
- **Mean bearing:** {wave124.get('wave_bearing', 'N/A')}°  
- **Wind speed:** {wave124.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave124.get('WDIR', 'N/A')}°  
- **Energy:** {wave124.get('wave_energy', 0):.2f} kJ/m 
- **Status:** {wave124.get('status', 'Unknown')}  

![Wave Plot](/plots/waves/Neah_Bay.png)
![Wind Plot](/plots/wind/Neah Bay.png)
![Tideplot](/plots/tidecurrent/Neah Bay.png)
- (https://www.ndbc.noaa.gov/station_page.php?station=46087)



## Port Angeles 
{arclength(48.173, 123.607, 48.2248207, 122.7701732)/1000:.2f}km {azimuth(48.173, 123.607,48.2248207, 122.7701732 ):.2f}° to Fort Ebey 
- **Dominant period:** {wave123pa.get('DPD', 'N/A')} s  
- **Mean direction:** {wave123pa.get('MWD', 'N/A')}°  
- **Wind speed:** {wave123pa.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave123pa.get('WDIR', 'N/A')}°  
- **Energy:** {wave123pa.get('wave_energy', 0):.2f} kJ/m  
- **Status:** {wave123pa.get('status', 'Unknown')}  
- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46267)
![Wave Plot](/plots/waves/Port Angelis.png)


## New Dungeness 
{arclength(48.332, 123.179,48.2248207, 122.7701732)/1000:.2f} km {azimuth(48.332,  123.179,48.2248207, 122.7701732):.2f}° to Fort Ebey 

- **Wave height:** {wave123nd.get('WVHT', 'N/A')} m  
- **Dominant period:** {wave123nd.get('DPD', 'N/A')} s  
- **Mean direction:** {wave123nd.get('MWD', 'N/A')}°  
- **Wind speed:** {wave123nd.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave123nd.get('WDIR', 'N/A')}°  
- **Energy:** {wave123nd.get('wave_energy', 0):.2f} kJ/m  
- **Status:** {wave123nd.get('status', 'Unknown')}  
- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46088)
![Wave Plot](/plots/waves/New Dungeness.png)
![Wind Plot](/plots/wind/New Dungeness.png)
![Tideplot](/plots/tidecurrent/New Dungeness.png)
---


*Report auto-generated from live NOAA buoy data.*
"""


    outpath = "Salish-Surf-Report.md"

    # Write (overwrite) the file
    with open(outpath, "w") as f:
        f.write(md)

    print(f"✅ Markdown report updated: {outpath}")