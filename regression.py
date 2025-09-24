#lets try and predict waves in PA using waves in NeahBay
#Options: lets go for a 
import pandas as pd
import numpy as np
import sklearn
import keras
from keras import models
from keras import layers 
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split 
from sklearn import preprocessing 

#Import Data:
Neah_Bay = '46087' #Neah Bay bouy
Port_Angelis = '46267' #PA bouy

independant_bouy = Neah_Bay
dependant_bouy = Port_Angelis

historic_path = f"data/historic/buoy_{independant_bouy}_historic.csv"
df_independant = pd.read_csv(historic_path, parse_dates=["datetime"])

historic_path = f"data/historic/buoy_{dependant_bouy}_historic.csv"
df_dependant = pd.read_csv(historic_path, parse_dates=["datetime"])

# Just keep datetime and WVHT (Wave Height)
df1 = df_independant[["datetime", "WVHT"]].rename(columns={"WVHT": "WVHT_Indep"})
#need to improve to include wave angle
df2 = df_dependant[["datetime", "WVHT"]].rename(columns={"WVHT": "WVHT_Dep"})

# Merge on datetime
df_merged = pd.merge(df1, df2, on="datetime")
df_merged["WVHT_Indep_lag1"] df_merged.info()= df_merged["WVHT_Indep"].shift(1)#this needs to be improved to be a length of time
df_merged = df_merged.dropna()
features = df_merged[["WVHT_Indep", "WVHT_Indep_lag1"]].values
target = df_merged["WVHT_Dep"].values


from sklearn.model_selection import train_test_split

#divide into training ans test sets 
X_train, X_test, y_train, y_test = train_test_split(
    features, target, test_size=0.3, shuffle=False  # no shuffling for time series
)

 #start neural network 
network = models.Sequential()
network.add(layers.Dense(units=32, activation="relu", input_shape=(X_train.shape[1],)))
network.add(layers.Dense(units=16, activation="relu"))
network.add(layers.Dense(units=1))  # output layer

network.compile(optimizer="adam", loss="mse")

history = network.fit(X_train, y_train, epochs=50, batch_size=16, validation_split=0.2)

import matplotlib.pyplot as plt

# Predict and plot
y_pred = network.predict(X_test)

plt.figure(figsize=(12, 4))
plt.plot(df_merged["datetime"].iloc[-len(y_test):], y_test, label="True")
plt.plot(df_merged["datetime"].iloc[-len(y_test):], y_pred.flatten(), label="Predicted")
plt.legend()
plt.title("Wave Height Prediction (PA using Neah Bay)")
plt.xlabel("Date")
plt.ylabel("Wave Height (m)")
plt.grid()
plt.show()
