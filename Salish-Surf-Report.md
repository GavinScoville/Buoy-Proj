
---

# Salish Sea Surf Report
**Updated:** 2025-11-12 16:40 PST

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
1642km to Fort Ebey

- **Wave height:** 10.2ft
- **Dominant period:** 11.0 s
- **Wave energy:** 2282 kJ/m of crest
- **Wave bearing:** 104°

A meter of wave crest has the same amount of kinetic energy as a prius driving 4.1mph 
![Wave Plot](/plots/waves/Ocean_Papa.png) 

- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46246)
---

## Neah Bay Wave Report:  
148km to Fort Ebey

- **Wave height:** 6.2ft
- **Dominant period:** 12.0 s
- **Wave energy:** 1020 kJ/m of crest
- **Wave bearing:** 101°
- **Wind speed:** 9.0 m/s 

A meter wide of wave crest has the same amount of kinetic energy as a prius driving 2.8mph

![Wave Plot](/plots/waves/Neah_Bay.png)

![Wind Plot](/plots/wind/Neah_Bay.png) 

![Tideplot](/plots/tidecurrent/Neah_Bay.png) 

- [See Photos](https://www.ndbc.noaa.gov/station_page.php?station=46087)


## Port Angeles Wave Report: 
62km to Fort Ebey 
- **Wave height:** 1.3ft
- **Dominant period:** 13.0 s  
- **Mean direction:** 305.0°  
- **Energy:** 53.06 kJ/m  

![Wave Plot](/plots/waves/Port_Angelis.png)


## New Dungeness Wave Report: 
33 km to Fort Ebey 
- **Wave height:** 1.0ft
- **Dominant period:** 3.0 s  
- **Mean direction:** 263.0°  
- **Wind speed:** 3.0 m/s  
- **Wind direction:** 220.0°  
- **Energy:** 1.59 kJ/m  

- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46088)

![Wave Plot](/plots/waves/New_Dungeness.png)

![Wind Plot](/plots/wind/New_Dungeness.png)

![Tideplot](/plots/tidecurrent/New_Dungeness.png)

---
*Report auto-generated from live NOAA buoy data.*
