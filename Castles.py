from _fetch_buoy_functions import fetch_and_clean_buoy_data, predict_tides, plot_tides, predict_currents
from _report_funcitons import wave_summary
from datetime import date, timedelta

# today
today = date.today()
today_str = today.strftime("%Y%m%d")

# tomorrow
tomorrow = today + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y%m%d")


Mokapu_Point = '51202'# Off shore from Castles 
Mokuoloe = '1612480' # Example: Mokuoloe (Kaneohe Bay, HI — station 1612480)

waves = fetch_and_clean_buoy_data(Mokapu_Point)
if waves is not None:
    wave_summary(waves, Mokapu_Point)

tides = predict_tides( Mokuoloe, today_str, tomorrow_str, interval="h")
print(tides["t"].max)
 
plot_tides(tides, "Mokuoloe (Kaneohe Bay, HI)")

