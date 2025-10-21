import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import math
import os

from _fetch_buoy_functions import fetch_and_clean_buoy_data,  predict_currents, predict_tides, plot_currents
from _report_funcitons import  wave_summary, current_report, tide_report, wind_report, setstatus
from _geodesy import arclength, azimuth

######################################################################
'''Make a website!'''
######################################################################

def render_salish_report(wave124, wave145, wave123pa, wave123nd):
    PacificTime = ZoneInfo("America/Los_Angeles")
    timestamp = datetime.now(PacificTime).strftime("%Y-%m-%d %H:%M %Z")
    date = datetime.today().strftime("%Y-%m-%d")




    # Build the Markdown content
    md = f"""---
layout: single
title: "Fort Ebey Surf Report"
categories: [portfolio]
date: {date}
---

# 🌊 Fort Ebey Surf Report
**Updated:** {timestamp}

---

## Neah Bay (46087)
- **Wave height:** {wave124.get('WVHT', 'N/A')} m  
- **Dominant period:** {wave124.get('DPD', 'N/A')} s  
- **Mean direction:** {wave124.get('MWD', 'N/A')}°  
- **Wind speed:** {wave124.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave124.get('WDIR', 'N/A')}°  
- **Energy:** {wave124.get('wave_energy', 0):.2f} kJ/m²  
- **Status:** {wave124.get('status', 'Unknown')}  
- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46087)

---

## New Dungeness (46088)
- **Wave height:** {wave123nd.get('WVHT', 'N/A')} m  
- **Dominant period:** {wave123nd.get('DPD', 'N/A')} s  
- **Mean direction:** {wave123nd.get('MWD', 'N/A')}°  
- **Wind speed:** {wave123nd.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave123nd.get('WDIR', 'N/A')}°  
- **Energy:** {wave123nd.get('wave_energy', 0):.2f} kJ/m²  
- **Status:** {wave123nd.get('status', 'Unknown')}  
- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46088)

---

## Port Angeles (46267)
- **Wave height:** {wave123pa.get('WVHT', 'N/A')} m  
- **Dominant period:** {wave123pa.get('DPD', 'N/A')} s  
- **Mean direction:** {wave123pa.get('MWD', 'N/A')}°  
- **Wind speed:** {wave123pa.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave123pa.get('WDIR', 'N/A')}°  
- **Energy:** {wave123pa.get('wave_energy', 0):.2f} kJ/m²  
- **Status:** {wave123pa.get('status', 'Unknown')}  
- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46267)

---

## Ocean Papa (46246)
- **Wave height:** {wave145.get('WVHT', 'N/A')} m  
- **Dominant period:** {wave145.get('DPD', 'N/A')} s  
- **Mean direction:** {wave145.get('MWD', 'N/A')}°  
- **Wind speed:** {wave145.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave145.get('WDIR', 'N/A')}°  
- **Energy:** {wave145.get('wave_energy', 0):.2f} kJ/m²  
- **Status:** {wave145.get('status', 'Unknown')}  
- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46246)

---

*Report auto-generated from live NOAA buoy data.*
"""

   #change this to whatever repo I want updated regualrily 
    outpath = "Salish-Surf-Report.md"

    # Ensure the folder exists
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    # Write (overwrite) the file
    with open(outpath, "w") as f:
        f.write(md)

    print(f"✅ Markdown report updated: {outpath}")
