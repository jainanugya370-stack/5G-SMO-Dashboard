import os
import pickle
import numpy as np
import tensorflow as tf

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_PATH = os.path.join(MODEL_DIR, "model", "lstm_weights.h5")
SCALER_PATH = os.path.join(MODEL_DIR, "model", "scaler.pkl")

# Global variables to store loaded models and cached predictions
model = None
scaler = None

# Cache structure to avoid duplicate joint inference runs
# Format: { "last_history_timestamp": ts, "dl_predictions": [...], "ul_predictions": [...] }
inference_cache = {
    "last_history_timestamp": None,
    "dl_predictions": None,
    "ul_predictions": None
}

def init_lstm_predictor():
    """Load the LSTM model weights and scaler once on Flask app startup."""
    global model, scaler
    
    # Suppress TensorFlow logs in container
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    
    if not os.path.exists(WEIGHTS_PATH) or not os.path.exists(SCALER_PATH):
        print(f"[LSTM] Error: Weights or scaler files not found at {WEIGHTS_PATH} / {SCALER_PATH}")
        return False
        
    try:
        # Reconstruct the model structure exactly as it was trained
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Input
        
        model = Sequential([
            Input(shape=(20, 2)),
            LSTM(32, activation="tanh", return_sequences=False),
            Dense(16, activation="relu"),
            Dense(10)  # 5 steps * 2 fields
        ])
        
        # Load weights into the constructed model
        model.load_weights(WEIGHTS_PATH)
        
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)
            
        print("[LSTM] Model weights and scaler loaded successfully!")
        return True
    except Exception as e:
        print(f"[LSTM] Failed to load model/scaler: {e}")
        return False

def predict_lstm(history, field, horizon=5, step_seconds=5):
    """
    Run joint LSTM forecasting. Automatically caches inference if multiple 
    endpoints request predictions for the same history timestamp.
    """
    global model, scaler, inference_cache
    
    if model is None or scaler is None:
        return {"status": "error", "message": "LSTM model not initialized"}

    if len(history) < 20:
        return {"status": "warming_up", "points": len(history), "needed": 20}

    last_entry = history[-1]
    last_ts = last_entry["timestamp"]

    # If the cache is valid, retrieve from cache instead of running model again
    if inference_cache["last_history_timestamp"] == last_ts:
        if field == "downlink_bitrate":
            return {
                "field": field,
                "model": "lstm",
                "timestamps": [last_ts + (i + 1) * step_seconds * 1000 for i in range(horizon)],
                "predicted": inference_cache["dl_predictions"]
            }
        elif field == "uplink_bitrate":
            return {
                "field": field,
                "model": "lstm",
                "timestamps": [last_ts + (i + 1) * step_seconds * 1000 for i in range(horizon)],
                "predicted": inference_cache["ul_predictions"]
            }
        else:
            return {"status": "error", "message": f"Unsupported field '{field}'"}

    # Cache is invalid or empty, perform model inference
    try:
        # Extract last 20 timesteps of downlink_bitrate and uplink_bitrate
        lookback_data = []
        for row in history[-20:]:
            dl = float(row.get("downlink_bitrate", 0.0))
            ul = float(row.get("uplink_bitrate", 0.0))
            lookback_data.append([dl, ul])
            
        lookback_data = np.array(lookback_data, dtype=float)  # shape: (20, 2)
        
        # Scale input
        scaled_lookback = scaler.transform(lookback_data)
        
        # Reshape to (1, 20, 2)
        input_tensor = np.expand_dims(scaled_lookback, axis=0)
        
        # Run inference
        pred_scaled = model.predict(input_tensor, verbose=0)  # shape: (1, 10)
        
        # Reshape flat predictions back to (5, 2) for inverse scaling
        pred_scaled_reshaped = pred_scaled.reshape(horizon, 2)
        
        # Inverse scale predictions
        pred_unscaled = scaler.inverse_transform(pred_scaled_reshaped)  # shape: (5, 2)
        
        # Extract individual forecasts and round values
        dl_preds = [round(float(v), 3) for v in pred_unscaled[:, 0]]
        ul_preds = [round(float(v), 3) for v in pred_unscaled[:, 1]]
        
        # Update cache
        inference_cache["last_history_timestamp"] = last_ts
        inference_cache["dl_predictions"] = dl_preds
        inference_cache["ul_predictions"] = ul_preds
        
        # Return result for the requested field
        target_preds = dl_preds if field == "downlink_bitrate" else ul_preds
        
        return {
            "field": field,
            "model": "lstm",
            "timestamps": [last_ts + (i + 1) * step_seconds * 1000 for i in range(horizon)],
            "predicted": target_preds
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Inference failure: {str(e)}"}
