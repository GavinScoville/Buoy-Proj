import pandas as pd
import matplotlib.pyplot as plt
import math


def wave_summary(df, buoy_id):
    # Ensure necessary columns are present
    required = ['WVHT', 'DPD', 'MWD', 'datetime']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Missing required wave data columns: {missing}")
        return

    # Convert columns to numeric (in case of strings) and drop fully NaN rows
    for col in required:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['datetime'])

    # Forward-fill all columns to deal with random gaps
    df = df.sort_values('datetime').bfill()

    # Drop rows that still have missing required values after filling
    df = df.dropna(subset=['WVHT', 'DPD', 'MWD'])

    if df.empty:
        print("No usable data available after cleaning.")
        return

    # Calculate wave length and energy
    df['wave_length'] = 9.81 * (df['DPD'] ** 2) / (2 * math.pi)
    df['wave_energy'] = 1.025 * 9.81 * ((df['WVHT']) ** 2) * df['wave_length'] / 8

    # Get the most recent row
    latest = df.iloc[-1]

    print(f"\n🌊 Summary for Buoy {buoy_id} (most recent):")
    print(f"  - Wave Height (WVHT): {latest['WVHT']} m")
    print(f"  - Dominant Period (DPD): {latest['DPD']} s")
    print(f"  - Estimated Wavelength: {latest['wave_length']:.2f} m")
    print(f"  - Estimated Wave Energy: {latest['wave_energy']:.2f} kJ/m²")
    print(f"  - Wave Direction : {latest['MWD']:.2f} deg")





def plot_wave_height(df1, buoy_id1, df2, buoy_id2):
    # Check if required columns are present
    if 'WVHT' not in df1.columns or 'WVHT' not in df2.columns:
        print("Wave height (WVHT) column not found in one of the DataFrames.")
        return

    # Drop rows with missing values
    df1 = df1.dropna(subset=['datetime', 'WVHT'])
    df2 = df2.dropna(subset=['datetime', 'WVHT'])

    # Plot
    plt.figure(figsize=(10, 5))
    plt.plot(df1['datetime'], df1['WVHT'], label=f"Buoy {buoy_id1}", color='red')
    plt.plot(df2['datetime'], df2['WVHT'], label=f"Buoy {buoy_id2}", color='blue')
    
    plt.title(f"Wave Height: Buoys {buoy_id1} and {buoy_id2}")
    plt.xlabel("Date")
    plt.ylabel("Wave Height (m)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()



