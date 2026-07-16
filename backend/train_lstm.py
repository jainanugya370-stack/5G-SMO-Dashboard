import pandas as pd
import numpy as np
import os
import pickle
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input

def train():
    # Ensure model directory exists
    os.makedirs("backend/model", exist_ok=True)

    print("Loading 5G_KPI_Dataset_Grafana.csv...")
    df = pd.read_csv("5G_KPI_Dataset_Grafana.csv")
    
    # Extract downlink and uplink bitrates
    data = df[["dl_bitrate_mbps", "ul_bitrate_mbps"]].values
    print(f"Total dataset records: {len(data)}")

    # Fit MinMaxScaler
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data)

    # Create sequences: lookback = 20 (past 100 seconds), horizon = 5 (next 25 seconds)
    X, y = [], []
    lookback = 20
    horizon = 5

    for i in range(len(data_scaled) - lookback - horizon + 1):
        X.append(data_scaled[i : i + lookback])
        # Flatten the next 5 timesteps (5, 2) -> (10,)
        y.append(data_scaled[i + lookback : i + lookback + horizon].flatten())

    X = np.array(X)
    y = np.array(y)

    print(f"X shape: {X.shape}, y shape: {y.shape}")

    # Train/Validation Split (80/20)
    split = int(0.8 * len(X))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"Train size: {len(X_train)}, Val size: {len(X_val)}")

    # Build LSTM Model
    model = Sequential([
        Input(shape=(lookback, 2)),
        LSTM(32, activation="tanh", return_sequences=False),
        Dense(16, activation="relu"),
        Dense(horizon * 2)  # 10 outputs (5 for dl, 5 for ul)
    ])

    model.compile(optimizer="adam", loss="mse")
    model.summary()

    # Train model
    print("Starting training...")
    history = model.fit(
        X_train, y_train,
        epochs=30,
        batch_size=16,
        validation_data=(X_val, y_val),
        verbose=1
    )

    # Save trained model weights and scaler
    model_path = "backend/model/lstm_weights.h5"
    scaler_path = "backend/model/scaler.pkl"
    
    model.save_weights(model_path)
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    print(f"Model saved successfully to {model_path}")
    print(f"Scaler saved successfully to {scaler_path}")
    print(f"Final Train Loss: {history.history['loss'][-1]:.6f}")
    print(f"Final Val Loss: {history.history['val_loss'][-1]:.6f}")

if __name__ == "__main__":
    train()
