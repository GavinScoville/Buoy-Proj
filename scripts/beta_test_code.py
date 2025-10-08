
import pandas as pd
import matplotlib.pyplot as plt
import math

#North Hawaii: 51101

# Run the pipeline
Mokapu_Point = '51202'# Off shore from Castles 


from fetch_buoy import fetch_and_clean_buoy_data
from wave_functions import wave_summary
from wave_functions import plot_wave_height

df = fetch_and_clean_buoy_data(Mokapu_Point)
if df is not None:
    wave_summary(df, Mokapu_Point)

df1 = fetch_and_clean_buoy_data(Mokapu_Point)



