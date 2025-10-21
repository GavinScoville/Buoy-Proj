"""Predict WVHT at buoy_46087 using lagged features from buoy_46246.

Creates a time-aware train/test split, trains a Ridge regression with TimeSeriesSplit
hyperparameter search, prints RMSE on the holdout set, and saves the trained model
and metadata to models/.

Usage: python3 scripts/predict_buoy_wvht.py

Files (relative to repo root):
 - data/processed/buoy_46246_processed.csv  (features source)
 - data/processed/buoy_46087_processed.csv  (target WVHT)

Produces:
 - models/buoy_wvht_ridge.joblib
 - models/buoy_wvht_meta.json

This script is conservative: resamples to hourly, uses lags of 72/96/120 hours
(3-5 days), imputes missing values by linear interpolation, and standard-scales
features before regression.
"""

import os
import json
from pathlib import Path
import sys

# Helpful import wrapper: catch common binary import issues (numpy/scipy/sklearn)
try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    import joblib
except Exception as e:
    msg = f"""
Failed to import required scientific packages (numpy/pandas/scikit-learn).
This commonly happens on macOS when binary wheels are for a different CPU architecture
(e.g. x86_64 vs arm64). Error:


Suggested fixes (choose one):

1) Create and use a fresh venv and reinstall packages:
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install --upgrade --force-reinstall numpy pandas scikit-learn joblib

2) Use conda/miniforge (recommended on macOS Apple Silicon):
   # install miniforge if needed, then:
   conda create -n buoy python=3.11 numpy pandas scikit-learn joblib -c conda-forge
   conda activate buoy
   python scripts/predict_buoy_wvht.py

3) Quick check of installed numpy details:
   python -c "import numpy; print(numpy.__version__, numpy.__file__)"

After fixing your environment, rerun this script. Exiting now.
"""
    print(msg, file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'processed'
MODEL_DIR = ROOT / 'models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)

SRC_FILE = DATA_DIR / 'buoy_46246_processed.csv'
TGT_FILE = DATA_DIR / 'buoy_46087_processed.csv'

# Parameters
RESAMPLE_FREQ = '1H'  # resample both time series to hourly
LAG_HOURS = [72, 96, 120]  # 3, 4, 5 days
FEATURE_VARS = ['WVHT', 'DPD', 'MWD']
TARGET_VAR = 'WVHT'


def load_and_prepare(path, resample_freq='1H'):
    df = pd.read_csv(path)
    # Ensure datetime column exists
    if 'datetime' not in df.columns:
        raise ValueError(f"No 'datetime' column in {path}")
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime').sort_index()
    # Convert numeric columns to floats
    df = df.apply(pd.to_numeric, errors='coerce')
    # Resample to common frequency using mean and then interpolate
    df_rs = df.resample(resample_freq).mean()
    # Interpolate linearly to fill small gaps; leave large gaps as NaN
    df_rs = df_rs.interpolate(method='time', limit=6)
    return df_rs


def build_lagged_features(src_df, feature_vars, lags_hours):
    """Return a DataFrame of lagged features indexed by the reference time t where
    features are from t - lag.
    """
    X = pd.DataFrame(index=src_df.index)
    for var in feature_vars:
        if var not in src_df.columns:
            X[var] = np.nan
            continue
        for lag in lags_hours:
            X[f'{var}_lag{lag}h'] = src_df[var].shift(lag)
    return X


def main():
    print('Loading source and target data...')
    src = load_and_prepare(SRC_FILE, RESAMPLE_FREQ)
    tgt = load_and_prepare(TGT_FILE, RESAMPLE_FREQ)

    print('Building lagged features from source...')
    X = build_lagged_features(src, FEATURE_VARS, LAG_HOURS)

    print('Preparing target series...')
    y = tgt[TARGET_VAR].rename('target')

    print('Merging features and target on time index...')
    df = pd.concat([X, y], axis=1)

    print(f'Initial rows: {len(df)}')
    # Drop rows where target is missing
    df = df[~df['target'].isna()]
    # Drop rows where all features are NaN
    df = df.dropna(subset=[c for c in df.columns if c != 'target'], how='all')

    # For modeling we'll drop any remaining rows with NaNs (or could impute)
    # But we'll keep rows where at least some features exist and then impute numeric missing values.
    feature_cols = [c for c in df.columns if c != 'target']

    # Simple time-based split: train on first 80% of time, test on last 20%
    split_idx = int(0.8 * len(df))
    # Ensure split respects time order
    df_train = df.iloc[:split_idx]
    df_test = df.iloc[split_idx:]

    print(f'Train rows: {len(df_train)}, Test rows: {len(df_test)}')

    # Pipeline: impute -> scale -> random forest
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor(random_state=1, n_jobs=-1))
    ])

    # Small grid for RF; increase for more thorough search
    param_grid = {
        'model__n_estimators': [50, 100],
        'model__max_depth': [5, 10, None],
        'model__min_samples_split': [2, 5]
    }

    tscv = TimeSeriesSplit(n_splits=5)

    X_train = df_train[feature_cols].values
    y_train = df_train['target'].values
    X_test = df_test[feature_cols].values
    y_test = df_test['target'].values

    print('Running time-series cross-validated grid search for alpha...')
    gcv = GridSearchCV(pipeline, param_grid, cv=tscv, scoring='neg_root_mean_squared_error', n_jobs=-1)
    gcv.fit(X_train, y_train)

    print('Best params:', gcv.best_params_)
    best_model = gcv.best_estimator_

    # Evaluate on test set
    y_pred = best_model.predict(X_test)
    rmse = mean_squared_error(y_test, y_pred, squared=False)
    mae = mean_absolute_error(y_test, y_pred)
    print(f'Test RMSE: {rmse:.4f} m, MAE: {mae:.4f} m')

    # Save model and metadata
    model_path = MODEL_DIR / 'buoy_wvht_ridge.joblib'
    meta_path = MODEL_DIR / 'buoy_wvht_meta.json'

    joblib.dump(best_model, model_path)
    meta = {
        'source_file': str(SRC_FILE),
        'target_file': str(TGT_FILE),
        'resample_freq': RESAMPLE_FREQ,
        'lags_hours': LAG_HOURS,
        'feature_vars': FEATURE_VARS,
        'feature_columns': feature_cols,
        'model_path': str(model_path)
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    print('Model and metadata saved to', model_path, meta_path)


if __name__ == '__main__':
    main()
