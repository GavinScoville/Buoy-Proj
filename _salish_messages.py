
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import math
import os

from _fetch_buoy_functions import fetch_and_clean_buoy_data,  predict_currents, predict_tides, plot_currents
from _report_funcitons import  wave_summary, current_report, tide_report, wind_report, setstatus
from _geodesy import arclength, azimuth
from _salish_website import render_salish_report

from dotenv import load_dotenv
import os
# Load environment variables from .env file
load_dotenv()
# Retrieve them
sender_email = os.getenv("EMAIL_USER")
password = os.getenv("EMAIL_PASS")
receiver_email = "gavin.scoville@gmail.com" 

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


current124=current_report(currents124, time124, PacificTime)

######################################################################
'''Send Ocean Papa'''
###################################################################### 
def send_ocean_email(waves145, sender_email,password,receiver_email, PacificTime):
    df = wave_summary(waves145, "Ocean Papa", PacificTime)
    local_time = df["datetime"].astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    distance = arclength(49.903, 145.246,48.321, 122.831)
    speed = (9.81/(2*math.pi)*waves145.loc[waves145.index[-1],"DPD"])
    traveltime = distance/(speed*60**2) # hours from Ocean Papa to Neah Bay (deepwater waves)
    landfall = (df['datetime'] + timedelta(hours = traveltime)).astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    azy = azimuth(49.903, 145.246, 48.493, 124.727)
    missshot = -(waves145.loc[waves145.index[-1],"MWD"]-azimuth(49.903, 145.246, 48.493, 124.727)-180) #to Ebbyazimuth(49.903, 145.246, 48.493, 124.727) 
# --- create the email ---
    message = MIMEMultipart("alternative")
    message["Subject"] = f"🌊 Ocean Papa Detects {df['WVHT']*3.28084:.0f} foot Waves"
    message["From"] = sender_email
    message["To"] = receiver_email

    # --- body text ---
    text = f"""\
{local_time}

Ocean Papa Bouy has detected {df['WVHT']*3.28084:.0f}ft swell {distance*0.000621371 :.0f} miles offshore 

- Wave height: {df['WVHT']*3.28084:.1f}ft
- Dominant period: {df['DPD']} s
- Average wave energy: {df['wave_energy']:.2f} kJ/m²
- Wave bearing: {df['wave_bearing']:.0f}°
- The waves are propogating {missshot:.0f}° north of the {azy:.0f}° direction to Neah Bay
- Waves will reach Neah in {traveltime:.0f} hours at {landfall}

Salish Sea Surf Report: https://github.com/GavinScoville/Buoy-Proj/blob/main/Salish-Surf-Report.md 
Ocean Papa Bouy: https://www.ndbc.noaa.gov/station_page.php?station=46246 

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
def send_straight_email(waves124,currents124,tides124,sender_email, password,receiver_email, PacificTime):
    df = wave_summary(waves124, "Neah Bay", PacificTime)
    local_time = df['datetime'].astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    distance = arclength(48.493, 124.727,48.2248207, 122.7701732)
    wavelength = (9.81*df["DPD"]**2)/(2*math.pi) #L = gT2/2π
    celarity = math.sqrt((9.81*wavelength)/(2*math.pi)*math.tanh(2*math.pi*100/wavelength)) #C = sqrt(gλ/2π * tanh(2πd/λ)) #average depth of 100 m 
    speed = celarity+current124[" Velocity_Major"]/100
    traveltime = distance/(speed*60**2) # hours from Ocean Papa to Neah Bay (deepwater waves)
    landfall = (df['datetime'] + timedelta(hours = traveltime)).astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")
    tides124['time_diff'] = abs(pd.to_datetime(df['datetime'], utc=True) - pd.to_datetime(tides124['datetime'],utc=True))
    closest_row = tides124.loc[tides124['time_diff'].idxmin()]# Get the row closest to the specified time
    idx = tides124['time_diff'].idxmin()
 #set current status
    if current124[" Velocity_Major"]> 10:
        current_status = "FLOODING"
    elif current124[" Velocity_Major"]< -10:
        current_status = "EBBING"
    else:
        current_status = "SLACK"

#Getting tide conditions
    tides124['time_diff'] = abs(pd.to_datetime(df['datetime'], utc=True) - pd.to_datetime(tides124['datetime'],utc=True))
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
    if df["GST"]<2:
        wind_status = "SLACK"
    elif abs(df["WDIR"]- df[")MWD"]) > 135:
        wind_status = "OFFSHORE"
    elif abs(df["WDIR"]- df["MWD"]) > 45:
        wind_status = "ONSHORE"
    else:
        wind_status = "CROSS"
        
    azy = azimuth(48.493, 124.727,48.2248207, 122.7701732)
    missshot = df["MWD"]-azimuth(48.493, 124.727,48.2248207, 122.7701732)-180 #to Ebby

# --- create the email ---
    message = MIMEMultipart("alternative")
    message["Subject"] = "🌊 Waves are Moving down the Strait"
    message["From"] = sender_email
    message["To"] = receiver_email

    # --- body text ---
    text = f"""\
    
Summary from Neah Bay Bouy at {local_time}:
Neah Bay Bouy has detected {df['WVHT']*3.28084:.0f}ft swell headed into the Strait

  - Wave height: {df['WVHT']} m
  - Dominant period: {df['DPD']} s
  - Estimated wave energy: {df['wave_energy']:.2f} kJ/m²
  - Wave bearing: {df['wave_bearing']:.2f}°

  - Tide is {closest_row['v']:.2f}m and {tide_status}, expected to change by {tide_change:.2f}m in the next hour 
  - Current is {current_status}, and moving at {current124[" Velocity_Major"]:.2f} cm/s
  - Wind at Neah Bay is currenly {wind_status} at {df["WSPD"]} m/s, from {df["WDIR"]}° EoN. 

  photos available at https://www.ndbc.noaa.gov/station_page.php?station=46087 
  Salish Sea Surf Report: https://github.com/GavinScoville/Buoy-Proj/blob/main/Salish-Surf-Report.md 
"""
    message.attach(MIMEText(text, "plain"))

    # --- send email securely ---
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.send_message(message)

    print("Strait of Juan de Fuca Alert sent successfully!")

send_straight_email(waves124,currents124,tides124,sender_email, password,receiver_email, PacificTime)