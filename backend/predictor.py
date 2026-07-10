"""
predictor.py
Lightweight anomaly detection + short-horizon forecasting over the KPI
history already maintained by app.py. No GPU/torch/sklearn required, so
it runs in the same Flask process as the rest of the backend.

Approach:
  - EWMA (exponentially weighted moving average) as a rolling baseline per KPI
  - z-score of the latest value against a rolling std to flag anomalies
  - simple least-squares linear trend over recent points for forecasting

This is intentionally simple. Swap in an LSTM/autoencoder later using the
same `history` in / JSON out contract if you want a heavier model — the
Flask routes and Grafana panels that consume this won't need to change.
"""
import numpy as np

MONITORED_FIELDS = [
    "downlink_bitrate", "uplink_bitrate", "traffic_utilization",
    "rrc_success_rate", "session_success_rate", "handover_success_rate",
    "latency_ms", "packet_loss_pct", "bler_pct",
    "core_resource_utilization_pct", "ue_throughput_mbps",
]

EWMA_ALPHA  = 0.3    # weight on newest sample when building the baseline
Z_THRESHOLD = 2.5    # |z-score| above this is flagged as an anomaly
MIN_POINTS  = 10      # need at least this many history points to judge anomalies


def _series(history, field):
    return np.array([row.get(field, 0.0) for row in history], dtype=float)


def detect_anomalies(history):
    """Returns {field: {value, baseline, std, z_score, is_anomaly}} for each monitored field."""
    if len(history) < MIN_POINTS:
        return {"status": "warming_up", "points": len(history), "needed": MIN_POINTS}

    result = {}
    for field in MONITORED_FIELDS:
        vals = _series(history, field)

        baseline_vals = vals[:-1]
        ewma = baseline_vals[0]
        for v in baseline_vals[1:]:
            ewma = EWMA_ALPHA * v + (1 - EWMA_ALPHA) * ewma

        std    = float(np.std(baseline_vals)) if len(baseline_vals) > 1 else 0.0
        latest = float(vals[-1])
        z      = 0.0 if std == 0 else (latest - ewma) / std

        result[field] = {
            "value":      round(latest, 3),
            "baseline":   round(float(ewma), 3),
            "std":        round(std, 3),
            "z_score":    round(float(z), 2),
            "is_anomaly": bool(abs(z) > Z_THRESHOLD),
        }
    return result


def forecast(history, field, horizon=6, step_seconds=5):
    """Simple linear (least-squares) short-horizon forecast for one field."""
    if field not in MONITORED_FIELDS:
        return {"status": "error", "message": f"'{field}' is not a monitored field"}

    vals = _series(history, field)
    if len(vals) < MIN_POINTS:
        return {"status": "warming_up", "points": len(vals), "needed": MIN_POINTS}

    n = len(vals)
    x = np.arange(n)
    slope, intercept = np.polyfit(x, vals, 1)

    last_ts   = history[-1]["timestamp"]
    future_x  = np.arange(n, n + horizon)
    predicted = (slope * future_x + intercept).tolist()
    future_ts = [last_ts + (i + 1) * step_seconds * 1000 for i in range(horizon)]

    return {
        "field": field,
        "trend_per_step": round(float(slope), 4),
        "timestamps": future_ts,
        "predicted": [round(v, 3) for v in predicted],
    }