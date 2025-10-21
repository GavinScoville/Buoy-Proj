import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import pytz
import math

from _fetch_buoy_functions import fetch_and_clean_buoy_data,  predict_currents, predict_tides, plot_currents
from _report_funcitons import  wave_summary, current_report, tide_report
from _geodesy import arclength, azimuth

#for waves: 
Ocean_Papa = "46246"
South_Nomad = "46036"
Northwest_Seattle = "46419"
La_Persouse_Bank = '46204' #Off Vancouver Island
Neah_Bay = '46087' #Neah Bay bouy
Port_Angelis = '46267' #PA bouy
New_Dungeness = '46088' #Off shore fort Ebey 
#Map: https://www.ndbc.noaa.gov/ 

#For Tides: 
Neah_Bay_Tide = "9443090"
Port_Townsend = "9444900"
#For currens: 
Neah_Bay_Current = "PUG1642"
New_Dungeness_Current = "PUG1635"
# today
today = date.today()
today_str = today.strftime("%Y%m%d")
# tomorrow
tomorrow = today + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y%m%d")
#GMT to PT conversion:
pst_timezone = pytz.timezone('America/Los_Angeles')
current_time_pst = datetime.now(pst_timezone)
print(current_time_pst)
now = datetime.now()
print(now)
if today.month in [3,4,5,6,7,8,9,10,11]: #DST
    time_offset = -7
else:
    time_offset = -8 #PST 

######################################################################
'''Pull that data!'''
######################################################################
#naming based on latitiude
wave145 = fetch_and_clean_buoy_data(Ocean_Papa) #returns a datafeame of the last 45 days of data
wave133 = fetch_and_clean_buoy_data(South_Nomad)
wave126 = fetch_and_clean_buoy_data(La_Persouse_Bank)
#add northwest seattle in here when wifi
wave124 = fetch_and_clean_buoy_data(Neah_Bay)
wave123pa = fetch_and_clean_buoy_data(Port_Angelis)
wave123nd= fetch_and_clean_buoy_data(New_Dungeness)

#Get those tides and currents: 
current124 = predict_currents(Neah_Bay_Current,today_str,tomorrow_str, interval="h")
current123 = predict_currents(New_Dungeness_Current,today_str,tomorrow_str, interval="h")
tide124 = predict_tides(Neah_Bay_Tide,today_str,tomorrow_str, interval="h")
tide123 = predict_tides(Port_Townsend,today_str,tomorrow_str, interval="h")

######################################################################
'''Make a report!'''
######################################################################

sum145 = wave_summary(wave145, "Ocean Papa") # wave summary returns a dataframe with the latest data and calculated energy etc.
sum133 = wave_summary(wave133, "South Nomad") #this is in PST now
sum126 = wave_summary(wave126, "La Persouse Bank")
sum124 = wave_summary(wave124, "Neah Bay")
sum123pa = wave_summary(wave123pa, "Port Angelis")
sum123nd = wave_summary(wave123nd, "New Dungeness")

#now time for the logic that initiates setting the status of the waves to 1 or 0 based on conditions unique to that location.
time124 = sum124["datetime"]  #get the time of the latest wave data 
current_report(current124, time124)
time123nd = sum123nd["datetime"]  #get the time of the latest wave data 
current_report(current123, time123nd)


current124.info()





#Can replace this with a stochastic model later: 
if abs(wave145.iloc[-1]["MWD"]-180-azimuth(49.903, 145.246, 48.493, 124.727)) <15: #if wave direction is within 15 degrees of path to neah bay 
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
################################################################################################
#from South Nomad:
#these are missing MWD data
'''
wave133 = fetch_and_clean_buoy_data(South_Nomad)
if wave133 is not None:
    wave_summary(wave133, South_Nomad)
#these are missing MWD data 

#from La Persouse Bank:
wave126 = fetch_and_clean_buoy_data(La_Persouse_Bank)
if wave126 is not None:
    wave_summary(wave126, La_Persouse_Bank)
'''
################################################################################################
#from Neah Bay to Fort Ebey: #48.2248207°N 122.7701732°W
wave124 = fetch_and_clean_buoy_data(Neah_Bay) #48.493 N 124.727 W
if wave124 is not None:
    wave_summary(wave124, Neah_Bay)

#currents at Neah Bay
current124 = predict_currents("PUG1642", today_str, tomorrow_str, interval="h")
# ensure types
current124['datetime'] = pd.to_datetime(current124['datetime'])
target_dt = pd.to_datetime(wave124.iloc[-1]['datetime'])
target_dt = target_dt.round('H')  # round to nearest hour
# boolean mask and get value(s)
mask = current124['datetime'] == target_dt
if mask.any():
    # get the first matching value
    current_current = current124.loc[mask, 'Velocity_Major'].iloc[0]/100
else:
    current_current = 0  # not found


#Can replace this with a stochastic model later: 
if abs(wave124.iloc[-1]["MWD"]-180-azimuth(48.493, 124.727, 48.2248207, 122.7701732)) <15: #if wave direction is within 15 degrees 
    print("waves are on path to Fort Ebey") 

    distance = arclength(48.493, 124.727, 48.2248207, 122.7701732)
    wavelength = (9.81*wave145.iloc[-1]["DPD"]**2)/(2*math.pi) #L = gT2/2π
    celarity = math.sqrt((9.81*wavelength)/(2*math.pi)*math.tanh(2*math.pi*150/wavelength)) #C = sqrt(gλ/2π * tanh(2πd/λ)) #average depth of 100 m 
    speed= celarity+current_current # going to add current to the wave speed
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
    print("waves are NOT on path from Neah to Ebey, no update made")
################################################################################################

#from Port Angelis:
wave123 = fetch_and_clean_buoy_data(Port_Angelis) #48.173 N 123.607 W
if abs(wave123.iloc[-1]["MWD"]-180-azimuth(48.173, 123.607, 48.2248207, 122.7701732)) <30: #if wave direction is within 30 degrees 
    print("at PA are on path to Fort Ebey") 
    distance = arclength(48.173, 123.607, 48.2248207, 122.7701732)
    wavelength = (9.81*wave145.iloc[-1]["DPD"]**2)/(2*math.pi) #L = gT2/2π
    celarity = math.sqrt((9.81*wavelength)/(2*math.pi)*math.tanh(2*math.pi*150/wavelength)) #C = sqrt(gλ/2π * tanh(2πd/λ)) #average depth of 100 m 
    speed= celarity+current_current # going to add current to the wave speed
    traveltime = distance/(speed*60**2) # hours from Ocean Papa to Neah Bay
    traveltime = int(traveltime*4)/4 #round to nearest 15 min
    print(f"predicted travel time to Fort Ebey is {traveltime:.2f} hours")

    # Building the new prediction row
    new_row = {
        'datetime': pd.to_datetime(wave123.iloc[-1]['datetime']) + pd.Timedelta(hours=traveltime),
        'WVHT': wave123.iloc[-1]['WVHT'],
        'DPD':  wave123.iloc[-1]['DPD'],
        'MWD':  wave123.iloc[-1]['MWD'],  # make sure this is MWD (not WMD)
    }
    prediction_update(new_row, "data/predicted/ebey.csv")
else:
    print("waves are NOT on path from PA to Ebey, no update made")


