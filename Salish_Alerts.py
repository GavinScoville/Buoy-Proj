import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import math
import os

from _fetch_buoy_functions import fetch_and_clean_buoy_data, predict_currents,predict_tides
from _geodesy import arclength, azimuth
from _plot_conditions_functions import plot_waves, plot_wind, plot_neah_waves, plot_tide_currents
from _map_conditions import map_pacific
from _report_funcitons import  wave_summary, current_report, tide_report, wind_report, setstatus
from _salish_website import render_salish_report

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
PacificTime = ZoneInfo("America/Los_Angeles")

######################################################################
'''Pull that data!'''
######################################################################
#naming based on latitiude
waves145 = fetch_and_clean_buoy_data(Ocean_Papa) #returns a datafeame of the last 45 days of data
#add northwest seattle in here when wifi
waves124 = fetch_and_clean_buoy_data(Neah_Bay)
waves123pa = fetch_and_clean_buoy_data(Port_Angelis)
waves123nd= fetch_and_clean_buoy_data(New_Dungeness)

#Get those tides and currents: 
currents124 = predict_currents(Neah_Bay_Current,today_str,tomorrow_str, interval="h")
currents123 = predict_currents(New_Dungeness_Current,today_str,tomorrow_str, interval="h")
tides124 = predict_tides(Neah_Bay_Tide,today_str,tomorrow_str, interval="h")
tides123 = predict_tides(Port_Townsend,today_str,tomorrow_str, interval="h")

######################################################################
'''Make a report!'''
######################################################################

wave145 = wave_summary(waves145, "Ocean Papa", PacificTime) # wave summary returns a dataframe with the latest data and calculated energy etc.
wave124 = wave_summary(waves124, "Neah Bay", PacificTime)
wave123pa = wave_summary(waves123pa, "Port Angelis", PacificTime)
wave123nd = wave_summary(waves123nd, "New Dungeness", PacificTime)

time124 = wave124["datetime"]  #get the time of the latest wave data 
time123 = wave123nd["datetime"]
                  
current124=current_report(currents124, time124, PacificTime)
current123=current_report(currents123, time123, PacificTime)

tide124 = tide_report(tides124, time124, PacificTime)
tide123 = tide_report(tides123, time123, PacificTime)

######################################################################
'''Plot that data'''
######################################################################
plot_waves(waves145, station_name="Ocean_Papa", timezone="America/Los_Angeles")
plot_neah_waves(waves124, timezone="America/Los_Angeles")
plot_waves(waves123pa, station_name="Port_Angelis", timezone="America/Los_Angeles")
plot_waves(waves123nd, station_name="New_Dungeness", timezone="America/Los_Angeles")

plot_wind(waves124,station_name="Neah_Bay", timezone="America/Los_Angeles")
plot_wind(waves123nd,station_name="New_Dungeness", timezone="America/Los_Angeles")

plot_tide_currents(tides124,currents124,wave124["datetime"],PacificTime,"Neah_Bay")
plot_tide_currents(tides123,currents123,wave123nd["datetime"],PacificTime,"New_Dungeness")

map_pacific(wave145,wave124,wave123pa,wave123nd)

######################################################################
'''Decide if it might be firing'''
######################################################################
#THis is for Ocean Papa:
#can replace this with a stochastic model later:
if abs(wave145["MWD"]-180-azimuth(49.903, 145.246, 48.493, 124.727)) >10: #if wave direction is within 10 degrees of path to neah bay 
    print("ocean waves are not aligned with path to neah bay")
    wave145["status"]= 0 #set status to zero (normal)
elif wave145["WVHT"] <5: 
    print("ocean waves are less then 5m high at ocean papa")
    wave145["status"]= 0
elif wave145["DPD"] <12:
    print("ocean waves have a period under 12s at ocean papa")
    wave145["status"] = 0
else:
    print("Swell is on path to Neah bay and is large enough to surf")
    wave145["status"]= 1  #set status to 1 (watch)
#update status file
change145 = setstatus(wave145, "ocean_papa")
if change145.loc[1]["status"]-change145.loc[0]["status"]>0: #if the status goes up, send email:
    send_ocean_email = "T" 
else:
    send_ocean_email = "F"



#Neah Bay Forcast:

azimuth(48.493, 124.727, 48.173, 123.607)-azimuth(48.493, 124.727,48.332, 123.179)#14 deg window:

if abs(wave124["MWD"]-180)> azimuth(48.493, 124.727, 48.173, 123.607) or abs(wave124["MWD"]-180)< azimuth(48.493, 124.727, 48.173, 123.607) : #if wave direction is within 10 degrees of path to neah bay 
    print("swell is not headed down the strait")
    wave124["status"]= 0
elif wave124["WVHT"] <3: 
    print("ocean waves are less then 3m high at Neah")
    wave124["status"]= 0
elif wave124["DPD"] <10:
    print("ocean waves have a period under 10s at ocean papa")
    wave124["status"]= 0
else:
    print("Swell is going down the strait and is big enough to surf")
    wave124["status"]= 1  #set status to 1 (watch)
#update status file

change124 = setstatus(wave124, "Neah_Bay")
if change124.loc[1]["status"]-change124.loc[0]["status"]>0: #if the status goes up, send email:
    send_strait_email = "T" 
else:
    send_strait_email = "F"


#P/A Forcast:
if wave123pa["WVHT"] <1.2: 
    print("ocean waves are less then 1.2m high at PA")
    wave123pa["status"]= 0
elif wave123pa["DPD"] < 8:
    print("Ocean waves have a period under 8 seconds at PA")
    wave123pa["status"]= 0
else:
    print("Swell is big enough tto surf at PA")
    wave123pa["status"]= 1  #set status to 1 (watch)

change123pa = setstatus(wave124, "Port Angelis")#setting status

if change123pa.loc[1]["status"]-change123pa.loc[0]["status"]>0: #if the status goes up, send email:
    send_PA_email = "T" 
else:
    send_PA_email = "F"

    #Dungeness Forcast:
if wave123nd["WVHT"] <1: 
    print("ocean waves are less then 1m high at ND")
    wave123nd["status"]= 0
elif wave123nd["DPD"] <8:
    print("Ocean waves have a period under 8 seconds at ND")
    wave123nd["status"]= 0
else:
    print("Swell is big enough to surf at ND")
    wave123nd["status"]= 1  #set status to 1 (watch)

change123nd = setstatus(wave124, "New Dungeness")#setting status
    
if change123nd.loc[1]["status"]-change123nd.loc[0]["status"]>0: #if the status goes up, send email:
    send_ND_email = "T" 
else:
    send_ND_email = "F"

#email list: 

######################################################################
'''Send The Emails!'''
###################################################################### 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
import os
# Load environment variables from .env file
load_dotenv()
# Retrieve them
sender_email = os.getenv("EMAIL_USER")
password = os.getenv("EMAIL_PASS")
receiver_email = "gavin.scoville@gmail.com" 

######################################################################
'''Send Ocean Papa'''
###################################################################### 
if send_ocean_email == "T":
    local_time = wave145['datetime'].astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    distance = arclength(49.903, 145.246,48.321, 122.831)
    wavelength = (9.81*wave145["DPD"]**2)/(2*math.pi) #L = gT2/2π
    speed = (9.81/(2*math.pi)*wave145["DPD"])
    traveltime = distance/(speed*60**2) # hours from Ocean Papa to Neah Bay (deepwater waves)
    landfall = (wave145['datetime'] + timedelta(hours = traveltime)).astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    azy = azimuth(49.903, 145.246, 48.493, 124.727)
    missshot = -(wave145["MWD"]-azimuth(49.903, 145.246, 48.493, 124.727)-180) #to Ebbyazimuth(49.903, 145.246, 48.493, 124.727) 
# --- create the email ---
    message = MIMEMultipart("alternative")
    message["Subject"] = "🌊 Ocean Papa Detects Waves"
    message["From"] = sender_email
    message["To"] = receiver_email

    # --- body text ---
    text = f"""\
    
Summary from Ocean Papa Buoy at {wave145['datetime'].astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")}:

  - Wave height: {wave145['WVHT']} m
  - Dominant period: {wave145['DPD']} s
  - Estimated wave energy: {wave145['wave_energy']:.2f} kJ/m²
  - Wave bearing: {wave145['wave_bearing']:.2f}°, 
  - The waves are propogating {missshot:.2f}° north of the {azy:.2f}° azimuth to Neah Bay
  - First waves landfall in {traveltime:.2f} hours at {landfall}

"""
    message.attach(MIMEText(text, "plain"))

    # --- send email securely ---
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.send_message(message)

    print("Ocean Papa alert sent successfully!")

######################################################################
'''Send Strait Email'''
###################################################################### 
if send_strait_email == "T":
    local_time = wave124['datetime'].astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    distance = arclength(48.493, 124.727,48.2248207, 122.7701732)
    wavelength = (9.81*wave124["DPD"]**2)/(2*math.pi) #L = gT2/2π
    celarity = math.sqrt((9.81*wavelength)/(2*math.pi)*math.tanh(2*math.pi*100/wavelength)) #C = sqrt(gλ/2π * tanh(2πd/λ)) #average depth of 100 m 
    speed = celarity+current124[" Velocity_Major"]/100
    traveltime = distance/(speed*60**2) # hours from Ocean Papa to Neah Bay (deepwater waves)
    landfall = (wave124['datetime'] + timedelta(hours = traveltime)).astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
 #set current status
    if current124[" Velocity_Major"]> 10:
        current_status = "FLOODING"
    elif current124[" Velocity_Major"]< -10:
        current_status = "EBBING"
    else:
        current_status = "SLACK"

#Getting tide conditions
    tides124['time_diff'] = abs(pd.to_datetime(tides124['datetime'], utc=True) - pd.to_datetime(wave124['datetime'],utc=True))
    closest_row = tides124.loc[tides124['time_diff'].idxmin()]# Get the row closest to the specified time
    idx = tides124['time_diff'].idxmin()
    row_after = tides124.loc[idx +1 ] if idx +1 < len(tides124) else None
    tide_change = row_after["v"]-closest_row["v"]
    if tide_change >.2:
        tide_status = "RISING"
    elif tide_change <-.2:
        tide_status = "FALLING"
    else:
        tide_status = "SLACK"
#determining wind conditions
    if wave124["GST"]<2:
        wind_status = "SLACK"
    elif abs(wave124["WDIR"]- wave124["MWD"]) > 135:
        wind_status = "OFFSHORE"
    elif abs(wave124["WDIR"]- wave124["MWD"]) > 45:
        wind_status = "ONSHORE"
    else:
        wind_status = "CROSS"
        
    azy = azimuth(48.493, 124.727,48.2248207, 122.7701732)
    missshot = wave124["MWD"]-azimuth(48.493, 124.727,48.2248207, 122.7701732)-180 #to Ebby

# --- create the email ---
    message = MIMEMultipart("alternative")
    message["Subject"] = "🌊 Waves are Moving down the Strait"
    message["From"] = sender_email
    message["To"] = receiver_email

    # --- body text ---
    text = f"""\
    
Summary from Neah Bay Bouy at {local_time}:

  - Wave height: {wave124['WVHT']} m
  - Dominant period: {wave124['DPD']} s
  - Estimated wave energy: {wave124['wave_energy']:.2f} kJ/m²
  - Wave bearing: {wave124['wave_bearing']:.2f}°

  - Tide is {closest_row['v']:.2f}m and {tide_status}, expected to change by {tide_change:.2f}m in the next hour 
  - Current is {current_status}, and moving at {current124[" Velocity_Major"]:.2f} cm/s
  - Wind at Neah Bay is currenly {wind_status} at {wave124["WSPD"]} m/s, from {wave124["WDIR"]}° EoN. 

  photos available at https://www.ndbc.noaa.gov/station_page.php?station=46087 
"""
    message.attach(MIMEText(text, "plain"))

    # --- send email securely ---
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.send_message(message)

    print("Strait of Juan de Fuca Alert sent successfully!")


######################################################################
'''Send PA Email!!'''
###################################################################### 

if send_PA_email == "T":
    local_time = wave123pa['datetime'].astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    wavelength = (9.81*wave123pa["DPD"]**2)/(2*math.pi) #L = gT2/2π

    # Get the row closest to the specified time
    tides123['time_diff'] = abs(pd.to_datetime(tides123['datetime'], utc=True) - pd.to_datetime(wave123nd['datetime'],utc=True))
    closest_row = tides123.loc[tides123['time_diff'].idxmin()]
    idx = tides123['time_diff'].idxmin()
    row_after = tides123.loc[idx +1 ] if idx +1 < len(tides123) else None
    tide_change = row_after["v"]-closest_row["v"] #hoe much it is going to change in an hour 
    if tide_change >.2:
        tide_status = "RISING"
    elif tide_change <-.2:
        tide_status = "FALLING"
    else:
        tide_status = "SLACK"
        
    azy = azimuth(48.2248207, 122.7701732, 48.493, 124.727)+180 #to Ebby 


# --- create the email ---
    message = MIMEMultipart("alternative")
    message["Subject"] = "🌊 Port Angelis has Waves"
    message["From"] = sender_email
    message["To"] = receiver_email

    # --- body text ---
    text = f"""\
    
Summary from Port Angelis at {local_time}:

  - Wave height: {wave123pa['WVHT']} m
  - Dominant period: {wave123pa['DPD']} s
  - Average period: {wave123pa['APD']} s
  - Estimated wave energy: {wave123pa['wave_energy']:.2f} kJ/m²
  - Wave bearing: {wave123pa['wave_bearing']:.2f}°
  - Ebey needs waves from {azy:.2f}° EoN

  - Tide is {closest_row['v']:.2f}m and {tide_status}, expected to change by {tide_change:.2f}m in the next hour 


"""
    message.attach(MIMEText(text, "plain"))

    # --- send email securely ---
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.send_message(message)

    print("PA alert sent successfully!")
######################################################################
'''Send ND Email!!'''
###################################################################### 

if send_ND_email == "T":
    local_time = wave123nd['datetime'].astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    wavelength = (9.81*wave123nd["DPD"]**2)/(2*math.pi) #L = gT2/2π
 #set current status
    if current123[" Velocity_Major"]> 10:
        current_status = "FLOODING"
    elif current123[" Velocity_Major"]< -10:
        current_status = "EBBING"
    else:
        current_status = "SLACK"

    # Using the Port Townsand Tides: 
    tides123['time_diff'] = abs(pd.to_datetime(tides123['datetime'], utc=True) - pd.to_datetime(wave123nd['datetime'],utc=True))
    closest_row = tides123.loc[tides123['time_diff'].idxmin()]
    idx = tides123['time_diff'].idxmin()
    row_after = tides123.loc[idx +1 ] if idx +1 < len(tides123) else None
    tide_change = row_after["v"]-closest_row["v"] #hoe much it is going to change in an hour 
    if tide_change >.2:
        tide_status = "RISING"
    elif tide_change <-.2:
        tide_status = "FALLING"
    else:
        tide_status = "SLACK"
#determining wind conditions
    if wave123nd["GST"]<2:
        wind_status = "SLACK"
    elif abs(wave123nd["WDIR"]- wave123nd["MWD"]) > 135:
        wind_status = "OFFSHORE"
    elif abs(wave123nd["WDIR"]- wave123nd["MWD"]) > 45:
        wind_status = "ONSHORE"
    else:
        wind_status = "CROSS"
        
    azy = azimuth(48.2248207, 122.7701732, 48.493, 124.727)+180 #to Ebby 

# --- create the email ---
    message = MIMEMultipart("alternative")
    message["Subject"] = "🌊 New Dungeness has Waves"
    message["From"] = sender_email
    message["To"] = receiver_email

    # --- body text ---
    text = f"""\
    
Summary from New Dungeness Bouy at {local_time}:

  - Wave height: {wave123nd['WVHT']} m
  - Dominant period: {wave123nd['DPD']} s
  - Average period: {wave123nd['APD']} s
  - Estimated wave energy: {wave123nd['wave_energy']:.2f} kJ/m²
  - Wave bearing: {wave123nd['wave_bearing']:.2f}° EoN
  - Ebey needs waves from {azy:.2f}° EoN


  - Tide is {closest_row['v']:.2f}m and {tide_status}, expected to change by {tide_change:.2f}m in the next hour 
  - Current at PT is {current_status}, and moving at {current123[" Velocity_Major"]:.2f} cm/s
  - Wind is currenly {wind_status} at {wave123nd["WSPD"]} m/s, from {wave123nd["WDIR"]}° E of N. 

  -  photos available at https://www.ndbc.noaa.gov/station_page.php?station=46088
"""
    message.attach(MIMEText(text, "plain"))

    # --- send email securely ---
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.send_message(message)

    print("New Dungeness Alert sent successfully!")

######################################################################
'''Render the Report!'''
###################################################################### 
print("now to render the report:")
#map_salish_sea(wave145,wave124,wave123pa,wave123nd)
map_pacific(wave145, wave124,wave123pa, wave123nd)
render_salish_report(wave145, wave124, wave123pa, wave123nd)