import pandas as pd
import numpy as np
from datetime import date, timedelta
import os 
import math

from fetch_buoy_functions import fetch_and_clean_buoy_data, wave_summary, predict_currents, plot_currents
from predict_functions import prediction_update
from geodesy import arclength, azimuth

#for waves: 
Ocean_Papa = "46246"
South_Nomad = "46036"
La_Persouse_Bank = '46204' #Off Vancouver Island
Neah_Bay = '46087' #Neah Bay bouy
Port_Angelis = '46267' #PA bouy
New_Dungeness = '46088' #Off shore fort Ebey 
#Map: https://www.ndbc.noaa.gov/ 

#For Tides: 
Neah_Bay_Tide = "9443090"
Port_Townsend = "9444900"

#For currens: 
Neah_Bay_Current = "9443090" #PUG1642
New_Dungeness_Current = "PUG1635"

# today
today = date.today()
today_str = today.strftime("%Y%m%d")

# tomorrow
tomorrow = today + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y%m%d")

#from Ocean Papa: 

wave145 = fetch_and_clean_buoy_data(Ocean_Papa)
if wave145 is not None:
    wave_summary(wave145, Ocean_Papa)

#Can replace this with a stochastic model later: 
if abs(wave145.iloc[-1]["MWD"]-azimuth(49.903, 145.246, 48.493, 124.727)) <15: #if wave direction is within 15 degrees of path to neah bay 
    print("waves are aligned with path to neah bay")

    distance = arclength(49.903, 145.246, 48.493, 124.727)
    speed = math.sqrt(9.81/(2* math.pi)*wave145.iloc[-1]["DPD"])  #wavespeed= sqrt(g/2pi* Period) 
    traveltime = distance/(speed*60**2) # hours from Ocean Papa to Neah Bay (deepwater waves)
    traveltime = int(traveltime*4)/4 #round to nearest 15 min
    print(f"predicted travel time to Neah Bay is {traveltime:.2f} hours")

    # Building the new prediction row
    new_row = {
        'datetime': pd.to_datetime(wave145.iloc[-1]['datetime']) + pd.Timedelta(hours=traveltime),
        'WVHT': wave145.iloc[-1]['WVHT'],
        'DPD':  wave145.iloc[-1]['DPD'],
        'MWD':  wave145.iloc[-1]['MWD'],  # make sure this is MWD (not WMD)
    }
    prediction_update(new_row, "data/predicted/neah.csv")
else:
    print("waves are NOT on path to neah bay, no update made")

#from South Nomad:
wave133 = fetch_and_clean_buoy_data(South_Nomad)
if wave133 is not None:
    wave_summary(wave133, South_Nomad)
#these are missing MWD data 

#from La Persouse Bank:
wave126 = fetch_and_clean_buoy_data(La_Persouse_Bank)
if wave126 is not None:
    wave_summary(wave126, La_Persouse_Bank)
#these are missing MWD data 

#from Neah Bay to Fort Ebey: #48.2248207°N 122.7701732°W
wave124 = fetch_and_clean_buoy_data(Neah_Bay) #48.493 N 124.727 W
if wave124 is not None:
    wave_summary(wave124, Neah_Bay)

#currents at Neah Bay
current124 = predict_currents("PUG1642", today_str, tomorrow_str, interval="h")


#Can replace this with a stochastic model later: 
if abs(wave124.iloc[-1]["MWD"]-azimuth(48.493, 124.727, 48.2248207, 122.7701732)) <15: #if wave direction is within 15 degrees 
    print("waves are on path to Fort Ebey") 

    distance = arclength(48.493, 124.727, 48.2248207, 122.7701732)
    wavelength = (9.81*wave145.iloc[-1]["DPD"]**2)/(2*math.pi) #L = gT2/2π
    celarity = math.sqrt((9.81*wavelength)/(2*math.pi)*math.tanh(2*math.pi*150/wavelength)) #C = sqrt(gλ/2π * tanh(2πd/λ)) #average depth of 100 m 
    speed= celarity # going to add current to this later 
    traveltime = distance/(speed*60**2) # hours from Ocean Papa to Neah Bay
    traveltime = int(traveltime*4)/4 #round to nearest 15 min
    print(f"predicted travel time to Fort Ebey is {traveltime:.2f} hours")

    # Building the new prediction row
    new_row = {
        'datetime': pd.to_datetime(wave124.iloc[-1]['datetime']) + pd.Timedelta(hours=traveltime),
        'WVHT': wave124.iloc[-1]['WVHT'],
        'DPD':  wave124.iloc[-1]['DPD'],
        'MWD':  wave124.iloc[-1]['MWD'],  # make sure this is MWD (not WMD)
    }
    prediction_update(new_row, "data/predicted/ebey.csv")
else:
    print("waves are NOT on path to ebey bay, no update made")


#Can replace this with a stochastic model later: 
if abs(wave124.iloc[-1]["MWD"]-azimuth(48.493, 124.727, 48.2248207, 122.7701732)) <15: #if wave direction is within 15 degrees 
    print("waves are on path to Fort Ebey") 

    distance = arclength(48.493, 124.727, 48.2248207, 122.7701732)
    wavelength = (9.81*wave145.iloc[-1]["DPD"]**2)/(2*math.pi) #L = gT2/2π
    celarity = math.sqrt((9.81*wavelength)/(2*math.pi)*math.tanh(2*math.pi*150/wavelength)) #C = sqrt(gλ/2π * tanh(2πd/λ)) #average depth of 100 m 
    speed= celarity # going to add current to this later 
    traveltime = distance/(speed*60**2) # hours from Ocean Papa to Neah Bay
    traveltime = int(traveltime*4)/4 #round to nearest 15 min
    print(f"predicted travel time to Fort Ebey is {traveltime:.2f} hours")

    # Building the new prediction row
    new_row = {
        'datetime': pd.to_datetime(wave124.iloc[-1]['datetime']) + pd.Timedelta(hours=traveltime),
        'WVHT': wave124.iloc[-1]['WVHT'],
        'DPD':  wave124.iloc[-1]['DPD'],
        'MWD':  wave124.iloc[-1]['MWD'],  # make sure this is MWD (not WMD)
    }
    prediction_update(new_row, "data/predicted/ebey.csv")
else:
    print("waves are NOT on path to ebey bay, no update made")
