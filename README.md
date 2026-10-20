# The goal of this program is to investigate how waves propogate through the salish sea. It may be useful for informing surfing conditions. 

## the project has the following strucutre:

### Config: 
- Hardcoded bouy tags and coordinates 
- Webpage design scripts 
- emails to alert if the waves look good for surfing

### Code:
The code that pulls data, runs it through numerical models. It will output reports and visualisations 

This is also the code that sends out alerts 

### Data: 
The home for bathymetric data and bouy data 

### Artifacts:
The home for deliverables: plots, forcasts, and tables 





## Download NOAA data (waves and tides) 
Every 15 minutes I retrieve new infomration from NOAA on the waves, tides, current, and wind. See fetch_bouy_funcitons.py to see the functions that call on the NOAA API. This data is collected by NOAA bouys such as the[New Dungeness Buoy](https://www.ndbc.noaa.gov/station_page.php?station=46088). 

 Description of on NOAA bouy measurments is [available here](https://www.ndbc.noaa.gov/faq/measdes.shtml) 
