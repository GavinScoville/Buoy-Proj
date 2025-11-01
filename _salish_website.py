import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import math
from _geodesy import arclength, azimuth

######################################################################
'''Make a website!'''
######################################################################
#this needs graphs and more facotrs but I am getting tired now 
def render_salish_report(wave145, wave124, wave123pa, wave123nd):
    PacificTime = ZoneInfo("America/Los_Angeles")
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
- **Wave height: {wave145['WVHT']*3.28084:.1f}ft
- **Dominant period: {wave145['DPD']} s
- **Wave energy: {wave145['wave_energy']:.0f} kJ/m pr. crest
A meter of wave has the same amount of kinetic energy as a prius driving {math.sqrt(wave145['wave_energy']*2/1350)*2.23694:.1f}mph
- **Wave bearing: {wave145['wave_bearing']:.0f}°

![Wave Plot](/plots/waves/Ocean_Papa.png) 

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

![Wind Plot](/plots/wind/Neah_Bay.png) 

![Tideplot](/plots/tidecurrent/Neah_Bay.png) 

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

![Wave Plot](/plots/waves/Port_Angelis.png)



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

![Wave Plot](/plots/waves/New_Dungeness.png)

![Wind Plot](/plots/wind/New_Dungeness.png)

![Tideplot](/plots/tidecurrent/New_Dungeness.png)

---


*Report auto-generated from live NOAA buoy data.*
"""


    outpath = "Salish-Surf-Report.md"

    # Write (overwrite) the file
    with open(outpath, "w") as f:
        f.write(md)

    print(f"✅ Markdown report updated: {outpath}")