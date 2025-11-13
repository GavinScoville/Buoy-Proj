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
    md = f"""
---

# Salish Sea Surf Report
**Updated:** {timestamp}

---
![Wave Map](/plots/maps/pacific.png)

1,600 km off the coast, Ocean Papa bouy picks up wave data. 
Using this data we can infer the trajectory of waves as they move across our spherical earth. 
Right now this map uses spherical geometry to calculate the azimuth and trajectory of each wave,  
but it does not account for the coreolis effect. Comming soon... 

![Wave Map](/plots/maps/Strait.png)

At the mouth of the Salish Sea, a Neah Bay bouy gives us monocromatic directional wave data. 
No other surf models have yet to understand how these directional waves refract across the Strait.
This ray-tracing diagram is a heuristic model to show how the coastline will bend and refract waves at different 
wavelengths and directions. Right now there is a cheesy algorythm to predict wave height by holding energy flux
between the rays constant. 


![Wave Map](/plots/maps/Island.png)

The rays in the wave map are linear interpolation of the waves from the Port Angelis Bouy to the New Dungeness Bouy.
They pass over many underwater obsticles, but will only register friction when the depth is less then half the wavelength. 


## Ocean Papa Wave Report:  
{arclength(49.903, 145.246, 48.2248207, 122.7701732)/1000:.0f}km to Fort Ebey

- **Wave height:** {wave145['WVHT']*3.28084:.1f}ft
- **Dominant period:** {wave145['DPD']} s
- **Wave energy:** {wave145['wave_energy']:.0f} kJ/m of crest
- **Wave bearing:** {wave145['wave_bearing']:.0f}°

A meter of wave crest has the same amount of kinetic energy as a prius driving {math.sqrt(wave145['wave_energy']*2/1350)*2.23694:.1f}mph 
![Wave Plot](/plots/waves/Ocean_Papa.png) 

- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46246)
---

## Neah Bay Wave Report:  
{arclength(48.493, 124.727, 48.2248207, 122.7701732)/1000:.0f}km to Fort Ebey

- **Wave height:** {wave124['WVHT']*3.28084:.1f}ft
- **Dominant period:** {wave124['DPD']} s
- **Wave energy:** {wave124['wave_energy']:.0f} kJ/m of crest
- **Wave bearing:** {wave124['wave_bearing']:.0f}°
- **Wind speed:** {wave124.get('WSPD', 'N/A')} m/s 

A meter wide of wave crest has the same amount of kinetic energy as a prius driving {math.sqrt(wave124['wave_energy']*2/1350)*2.23694:.1f}mph

![Wave Plot](/plots/waves/Neah_Bay.png)

![Wind Plot](/plots/wind/Neah_Bay.png) 

![Tideplot](/plots/tidecurrent/Neah_Bay.png) 

- [See Photos](https://www.ndbc.noaa.gov/station_page.php?station=46087)


## Port Angeles Wave Report: 
{arclength(48.173, 123.607, 48.2248207, 122.7701732)/1000:.0f}km to Fort Ebey 
- **Wave height:** {wave123pa['WVHT']*3.28084:.1f}ft
- **Dominant period:** {wave123pa.get('DPD', 'N/A')} s  
- **Mean direction:** {wave123pa.get('MWD', 'N/A')}°  
- **Energy:** {wave123pa.get('wave_energy', 0):.2f} kJ/m  

![Wave Plot](/plots/waves/Port_Angelis.png)


## New Dungeness Wave Report: 
{arclength(48.332, 123.179,48.2248207, 122.7701732)/1000:.0f} km to Fort Ebey 
- **Wave height:** {wave123nd['WVHT']*3.28084:.1f}ft
- **Dominant period:** {wave123nd.get('DPD', 'N/A')} s  
- **Mean direction:** {wave123nd.get('MWD', 'N/A')}°  
- **Wind speed:** {wave123nd.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave123nd.get('WDIR', 'N/A')}°  
- **Energy:** {wave123nd.get('wave_energy', 0):.2f} kJ/m  

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

    print(f"Markdown report updated: {outpath}")