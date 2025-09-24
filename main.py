
import pandas as pd
import matplotlib.pyplot as plt
import math

#North Hawaii: 51101

# Run the pipeline
Neah_Bay = '46087' #Neah Bay bouy
Port_Angelis = '46267' #PA bouy
West_Port_1 = '46100' #Off West Port Coast #46.851 N 124.964 W
West_Port_2 = '46099' #Closer to West POrt #46.988 N 124.567 W
West_Port_3 = '46211' #In West Port Channel #46.857 N 124.243 W
North_Hawaii= '51101'


from fetch_buoy import fetch_and_clean_buoy_data
from analyze_buoy import wave_summary
from analyze_buoy import plot_wave_height

df = fetch_and_clean_buoy_data(North_Hawaii)
if df is not None:
    wave_summary(df, North_Hawaii)

df1 = fetch_and_clean_buoy_data(Neah_Bay)
df2 = fetch_and_clean_buoy_data(Port_Angelis)
plot_wave_height(df1,Neah_Bay,df2,Port_Angelis)




buoy_id = '46087'
df = fetch_and_clean_buoy_data(buoy_id)
if df is not None:
    wave_summary(df, buoy_id)



