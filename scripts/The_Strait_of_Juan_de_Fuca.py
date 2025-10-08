import pandas as pd
import numpy as np
from datetime import date, timedelta

from fetch_buoy import fetch_and_clean_buoy_data
from wave_functions import wave_summary
from tide_functions import predict_tides
from current_functions import predict_currents
from tide_functions import plot_tides



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


wave145 = fetch_and_clean_buoy_data(Ocean_Papa)
if wave145 is not None:
    wave_summary(wave145, Ocean_Papa)

wave145.iloc[-1]["WVHT"]#most recent entry, waveheight 
wave145.iloc[-1]["DPD"]#most recent entry, period
wave145.iloc[-1]["MWD"]#most rencent entry, direction








'''
tides = predict_tides( Neah_Bay_Tide, today_str, tomorrow_str, interval="h")
print(tides)

currents = predict_currents(New_Dungeness_Current, today_str, tomorrow_str, interval="h")
print(currents)

 
plot_tides(tides, "Neah Bay")

#deepwater 
https://en.wikipedia.org/wiki/Dispersion_(water_waves)

wavelength= g/2pi* period**2
wavespeed= g/2pi* Period
'''