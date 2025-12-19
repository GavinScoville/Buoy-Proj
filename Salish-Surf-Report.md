
---

# Salish Sea Surf Report
**Updated:** 2025-12-18 20:49 PST

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
Distance: 1642 km to Fort Ebey

- **Wave height:** 14.4 ft  
- **Dominant period:** 11.0 s  
- **Wave energy:** 4597 kJ/m of crest  
- **Wave bearing:** 140°

A meter of wave crest has the kinetic energy of a Prius traveling  
**5.8 mph.**

<details>
<summary><strong>Click to show Ocean Papa plots</strong></summary>

![Wave Plot](/plots/waves/Ocean_Papa.png)

</details>

- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46246)

---

## Neah Bay Wave Report  
Distance: 148 km to Fort Ebey

- **Wave height:** 15.7 ft  
- **Dominant period:** 11.0 s  
- **Wave energy:** 5471 kJ/m of crest  
- **Wave bearing:** 68°  
- **Wind speed:** 12.0 m/s

A meter of wave crest has the kinetic energy of a Prius traveling  
**6.4 mph.**

<details>
<summary><strong>Click to show Neah Bay plots</strong></summary>

![Wave Plot](/plots/waves/Neah_Bay.png)  
![Wind Plot](/plots/wind/Neah_Bay.png)  
![Tide Plot](/plots/tidecurrent/Neah_Bay.png)

</details>

- [See Station Page →](https://www.ndbc.noaa.gov/station_page.php?station=46087)

---

## Port Angeles Wave Report  
Distance: 62 km to Fort Ebey

- **Wave height:** 5.6 ft  
- **Dominant period:** 6.0 s  
- **Wave bearing:** 115°  
- **Energy:** 204.17 kJ/m  

<details>
<summary><strong>Click to show Port Angeles plot</strong></summary>

![Wave Plot](/plots/waves/Port_Angelis.png)

</details>

---

## New Dungeness Wave Report  
Distance: 33 km to Fort Ebey

- **Wave height:** 5.6 ft  
- **Dominant period:** 7.0 s  
- **Wave bearing:** 76°  
- **Wind speed:** 13.0 m/s  
- **Wind direction:** 250.0°  
- **Energy:** 277.90 kJ/m  

<details>
<summary><strong>Click to show New Dungeness plots</strong></summary>

![Wave Plot](/plots/waves/New_Dungeness.png)  
![Wind Plot](/plots/wind/New_Dungeness.png)  
![Tide Plot](/plots/tidecurrent/New_Dungeness.png)

</details>

---

*Report auto-generated from live NOAA buoy data.*


