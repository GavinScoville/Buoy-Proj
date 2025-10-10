#here we have our prediciton functions so we can updat them easily
import pandas as pd
import os

# Create prediction folder if it doesn't exist

def prediction_update(new_row, prediction_path):
    os.makedirs("data/predicted", exist_ok=True)
    # Load existing predictions (or create empty DF if not present)
    try:
        pred_df = pd.read_csv(prediction_path, parse_dates=['datetime'])
    except FileNotFoundError:
       pred_df = pd.DataFrame(columns=list(new_row.keys()))

    # Create a one-row DataFrame and concat
    new_df = pd.DataFrame([new_row])
    combined = pd.concat([pred_df, new_df], ignore_index=True)

    # Ensure datetime dtype
    combined['datetime'] = pd.to_datetime(combined['datetime'])

    # Remove exact duplicate rows (all columns must match) and keep the last occurrence (the new row)
    combined = combined.drop_duplicates(keep='last')

    # Sort by datetime (optional) and reset index
    combined = combined.sort_values('datetime').reset_index(drop=True)

    # Save back to CSV
    combined.to_csv(prediction_path, index=False)
    print(f"Saved prediction to {prediction_path} (rows now: {len(combined)})")
