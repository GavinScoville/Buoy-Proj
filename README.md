# The goal of this program is to make you aware of the wave conditions in the Straight of Juan de Fuca

## Download NOAA data (waves and tides) 
Every 15 minutes I retrieve new infomration from NOAA on the waves, tides, current, and wind. See fetch_bouy_funcitons.py to see the functions that call on the NOAA API. This data is collected by NOAA bouys such as the[New Dungeness Buoy](https://www.ndbc.noaa.gov/station_page.php?station=46088). 

 Description of on NOAA bouy measurments is [available here](https://www.ndbc.noaa.gov/faq/measdes.shtml) 

### Wave Stations: 
    1 Ocean PAPA. 46246.[49.903 N 145.246 W]. -(water depth 4252m)-(advanced wave data).  

    2 Climate PAPA. 48400.[50.055 N 144.873 W]. -(wind data only). 

    3 South Nomad. 46036.[48.360 N 133.940 W]. -(no  directional data). 

    4 La Perouse Bank. 46206. [48.840 N 126.000 W]. (no direcitonal data).   
    
    5 Neah Bay. 46087. [48.493 N 124.727 W]. -(Depth 259 m) [photos available](https://www.ndbc.noaa.gov/station_page.php?station=46087).   

    6 Port Angles. 46267. [48.173 N 123.607 W]. -(Depth 75 m). 

    7 New Dungeness. 46088. [48.332 N 123.179 W]. -(Depth 115 m).    [photos available](https://www.ndbc.noaa.gov/station_page.php?station=46088).   

    8 Smith Island. SISW1. [48.321 N 122.831 W] (wind only).   

## Make predictions as to what windows conditions are good 
I am currently using a very simplistic newtonian model. 
This will hopefully will get updated with a stochastic model, which requres fewer violated assumtions. If I have free time I might look into numerical methods so I can include the coreolis effect, bathymetry, wind, tides, and currents in a deterministic model. 

### Process of Building Wave Report: 
Wave report is stored in Juan_de_Fuca.py 
#### Step 1: Predict Waves off Pacific Ocean and when they will reach Neah Bay 
These predictions are stored in data/predicted/Neah

#### Step 2: Predict which waves hitting Neah Bay will make it to Fort Ebey 
Azimuth from Neah Bay to Fort Ebey is about 100° E of N. A wave with an 11 second period traveling in 100m water moves about 17 meters/s. Tidal Currents can add +- 1.5 meters/s to this speed. 

#### Step 3: Identify when waves pass Port Angelis, and New Dungeness
Qualify that yes waves did make in into the straight. Ebey should be firing 

#### Step 4: Include Wind Waves genrated along Juan de Fuce fetch
Have not done this yet. Adding a wind report is defintly the next step for the wave forcaster. 


## Send out text updates if it looks like the waves are going to be really good 

### Possible Conditions: 

#### A. It is firing at Neah Bay and it looks like it might get good in Fort Ebey 
 If Neah Bay is >10 feet, and dominant wave bearing is within 10 degrees of 100° E of North. 

 Note: It takes about 2.5 hours for a wave with an 11 second period to make it from Neah Bay to fort Ebey on a slack current

 Report Wind at Neah Bay and New Dungeness also report tide
#### B. It is firing at Neah bay and Fort Ebay 

 If Neah Bay is >10 feet, and New Dungeness Bouy has >5 ft headed within 30° at Fort Ebey

#### C. It is just firing in Fort Ebey 

If New Dungeness Bouy has >5 ft, and bearing is within 30° of Fort Ebey

#### D. It is not firing anywhere 

Once the swell has passed, remove updates so that noone wastes thier time going out to check the surf



