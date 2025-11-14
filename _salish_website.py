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

## Pacific Wave Propagation
![Wave Map](/plots/maps/pacific.png)

1,600 km off the coast, the Ocean Papa buoy collects wave data.  
Using this information, we can infer the trajectory of waves as they travel across the Pacific.  
This map uses spherical trigonometry to calculate the azimuth and great-circle path of each wave.  
It does not yet include the Coriolis effect — coming soon.

---

## Strait of Juan de Fuca Refraction
![Wave Map](/plots/maps/Strait.png)

At the entrance of the Salish Sea, the Neah Bay buoy provides us basic wave data.  
No other surf models currently incorporate how these waves refract across the Strait.  

This ray-tracing diagram illustrates how the coastline bends and redirects incoming wave energy.  
A simple algorithm currently predicts wave height by holding energy flux constant.

---

## Islands Region Refraction
![Wave Map](/plots/maps/Island.png)

This map uses the same model. The rays linearly interpolate between the Port Angeles Buoy  
and the New Dungeness Buoy. Waves pass over many underwater features but only experience  
friction and thus refraction when the depth is less than half the wavelength.

---

# Wave Reports

## Ocean Papa Wave Report  
Distance: {arclength(49.903, 145.246, 48.2248207, 122.7701732)/1000:.0f} km to Fort Ebey

- **Wave height:** {wave145['WVHT']*3.28084:.1f} ft  
- **Dominant period:** {wave145['DPD']} s  
- **Wave energy:** {wave145['wave_energy']:.0f} kJ/m of crest  
- **Wave bearing:** {wave145['wave_bearing']:.0f}°

A meter of wave crest has the kinetic energy of a Prius traveling  
**{math.sqrt(wave145['wave_energy']*2/1350)*2.23694:.1f} mph.**

<details>
<summary><strong>Click to show Ocean Papa plots</strong></summary>

![Wave Plot](/plots/waves/Ocean_Papa.png)

</details>

- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46246)

---

## Neah Bay Wave Report  
Distance: {arclength(48.493, 124.727, 48.2248207, 122.7701732)/1000:.0f} km to Fort Ebey

- **Wave height:** {wave124['WVHT']*3.28084:.1f} ft  
- **Dominant period:** {wave124['DPD']} s  
- **Wave energy:** {wave124['wave_energy']:.0f} kJ/m of crest  
- **Wave bearing:** {wave124['wave_bearing']:.0f}°  
- **Wind speed:** {wave124.get('WSPD', 'N/A')} m/s

A meter of wave crest has the kinetic energy of a Prius traveling  
**{math.sqrt(wave124['wave_energy']*2/1350)*2.23694:.1f} mph.**

<details>
<summary><strong>Click to show Neah Bay plots</strong></summary>

![Wave Plot](/plots/waves/Neah_Bay.png)  
![Wind Plot](/plots/wind/Neah_Bay.png)  
![Tide Plot](/plots/tidecurrent/Neah_Bay.png)

</details>

- [See Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46087)

---

## Port Angeles Wave Report  
Distance: {arclength(48.173, 123.607, 48.2248207, 122.7701732)/1000:.0f} km to Fort Ebey

- **Wave height:** {wave123pa['WVHT']*3.28084:.1f} ft  
- **Dominant period:** {wave123pa.get('DPD', 'N/A')} s  
- **Wave bearing:** {wave123pa.get('wave_bearing', 'N/A'):.0f}°  
- **Energy:** {wave123pa.get('wave_energy', 0):.2f} kJ/m  

<details>
<summary><strong>Click to show Port Angeles plot</strong></summary>

![Wave Plot](/plots/waves/Port_Angelis.png)

</details>

---

## New Dungeness Wave Report  
Distance: {arclength(48.332, 123.179, 48.2248207, 122.7701732)/1000:.0f} km to Fort Ebey

- **Wave height:** {wave123nd['WVHT']*3.28084:.1f} ft  
- **Dominant period:** {wave123nd.get('DPD', 'N/A')} s  
- **Wave bearing:** {wave123nd.get('wave_bearing', 'N/A'):.0f}°  
- **Wind speed:** {wave123nd.get('WSPD', 'N/A')} m/s  
- **Wind direction:** {wave123nd.get('WDIR', 'N/A')}°  
- **Energy:** {wave123nd.get('wave_energy', 0):.2f} kJ/m  

<details>
<summary><strong>Click to show New Dungeness plots</strong></summary>

![Wave Plot](/plots/waves/New_Dungeness.png)  
![Wind Plot](/plots/wind/New_Dungeness.png)  
![Tide Plot](/plots/tidecurrent/New_Dungeness.png)

</details>

---

*Report auto-generated from live NOAA buoy data.*


"""

    outpath = "Salish-Surf-Report.md"

    # Write (overwrite) the file
    with open(outpath, "w") as f:
        f.write(md)

    print(f"Markdown report updated: {outpath}")