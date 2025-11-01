import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime 
from zoneinfo import ZoneInfo
import math
import os

def move_wave(North=49.903, East=-145.246, azy=88, dist=1000000):
    P1=(math.radians(North),math.radians(East))
    azy1=math.radians(azy)

    #this gives us the node, or azy of the great circle as it take off from the equator towards point1
    node= math.atan2((math.sin(azy1)*math.cos(P1[0])),(math.sqrt(math.cos(azy1)**2+math.sin(azy1)**2*math.sin(P1[0])**2)))
    #this gives us the ang. dist fomr the node to P1:
    angd1 = math.atan2(math.tan(P1[0]),math.cos(azy1))
    #and the node longitude:
    node_long = P1[1]-math.atan2(math.sin(node)*math.sin(angd1),math.cos(angd1))
    #this is the angular distance to an arbatrary point farther along the path:
    angx = dist/6371000 #arclength/radius of earth 
    angd2 = angd1 + angx
    P2lat = math.degrees(math.atan2((math.cos(node)*math.sin(angd2)),math.sqrt(math.cos(angd2)**2+math.sin(node)**2+math.cos(angd2)**2)))
    P2long = math.degrees(math.atan2(math.sin(node)*math.sin(angd2),math.cos(angd2))+node_long)
    P2azy = math.degrees(math.atan2(math.tan(node),math.cos(angd2)))
    return(P2lat,P2long,P2azy) 
    
#https://en.wikipedia.org/wiki/Great-circle_navigation 
def predict_wavepath(waves145):
    """
    Predicts where Ocean PAPA waves are now located based on
    their period and mean direction over the past 24 hours.
    """
    # Convert and subset last 24 hours
    waves145["datetime"] = pd.to_datetime(waves145["datetime"], utc=True)
    cutoff_time = waves145["datetime"].iloc[0] - timedelta(hours=24)
    pacific_waves = waves145[waves145["datetime"] >= cutoff_time].copy()

    # Compute phase speed (deep-water approx)
    pacific_waves["speed"] = 9.81 * pacific_waves["DPD"] / (2 * math.pi)  # m/s

    # Compute distance traveled since the earliest timestamp
    pacific_waves["elapsed_s"] = (pacific_waves["datetime"].iloc[0] - pacific_waves["datetime"]).dt.total_seconds()

    pacific_waves["dist"] = pacific_waves["speed"] * pacific_waves["elapsed_s"]#m

    # Compute propagation azimuth 
    pacific_waves["azy"] = (pacific_waves["MWD"] - 180) % 360

    # Initialize new columns
    pacific_waves["newnorth"] = np.nan
    pacific_waves["neweast"] = np.nan
    pacific_waves["newazy"] = np.nan

    # Iterate row-by-row 
    for i, row in pacific_waves.iterrows():
        lat2, lon2, azy2 = move_wave(
            North=49.903, East=-145.246,
            azy=row["azy"], dist=row["dist"]
        )
        pacific_waves.at[i, "newnorth"] = lat2
        pacific_waves.at[i, "neweast"] = lon2
        pacific_waves.at[i, "newazy"] = azy2

    return pacific_waves

move_wave(North=49.903, East=-145.246, azy=84, dist=1000000)
'''
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

wave133 = fetch_and_clean_buoy_data(South_Nomad)
if wave133 is not None:
    wave_summary(wave133, South_Nomad)
#these are missing MWD data 

#from La Persouse Bank:
wave126 = fetch_and_clean_buoy_data(La_Persouse_Bank)
if wave126 is not None:
    wave_summary(wave126, La_Persouse_Bank)

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
'''