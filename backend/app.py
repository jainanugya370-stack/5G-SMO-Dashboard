from flask import Flask, jsonify, request
from flask_cors import CORS
import json, os
from collections import deque
from datetime import datetime
from predictor import detect_anomalies, forecast
from lstm_predictor import init_lstm_predictor, predict_lstm

# Initialize LSTM predictor at module load time
init_lstm_predictor()

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
KPI_FILE = os.path.join(DATA_DIR, "kpis.json")
os.makedirs(DATA_DIR, exist_ok=True)

HISTORY_SIZE = 100
history = deque(maxlen=HISTORY_SIZE)
latest  = {}

@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"]        = "no-cache"
    response.headers["Expires"]       = "0"
    return response

def clean_kpis(data, ts_ms=None):
    if ts_ms is None:
        ts_ms = int(datetime.now().timestamp() * 1000)
    return {
        "timestamp":                     ts_ms,
        "active_gnbs":                   float(data.get("active_gnbs", 0)),
        "total_gnbs":                    float(data.get("total_gnbs", 0)),
        "active_subscribers":            float(data.get("active_subscribers", 0)),
        "active_sessions":               float(data.get("active_sessions", 0)),
        "downlink_bitrate":              float(data.get("downlink_bitrate", 0)),
        "uplink_bitrate":                float(data.get("uplink_bitrate", 0)),
        "traffic_utilization":           float(data.get("traffic_utilization", 0)),
        "rrc_success_rate":              float(data.get("rrc_success_rate", 0)),
        "session_success_rate":          float(data.get("session_success_rate", 0)),
        "handover_success_rate":         float(data.get("handover_success_rate", 0)),
        "latency_ms":                    float(data.get("latency_ms", 0)),
        "packet_loss_pct":               float(data.get("packet_loss_pct", 0)),
        "bler_pct":                      float(data.get("bler_pct", 0)),
        "core_resource_utilization_pct": float(data.get("core_resource_utilization_pct", 0)),
        "ue_throughput_mbps":            float(data.get("ue_throughput_mbps", 0)),
    }

if os.path.exists(KPI_FILE):
    try:
        with open(KPI_FILE) as f:
            _seed = json.load(f)
        latest = _seed
        now_ms = int(datetime.now().timestamp() * 1000)
        for i in range(30):
            history.append(clean_kpis(_seed, ts_ms=now_ms - (30 - i) * 5000))
        print("[Flask] Seeded 30 history points")
    except Exception as e:
        print(f"[Flask] Seed error: {e}")

@app.route("/")
def root():
    return jsonify({"status": "ok", "service": "5G SMO API"})

@app.route("/api/update", methods=["POST"])
def update():
    global latest
    latest = request.get_json()
    history.append(clean_kpis(latest, ts_ms=int(datetime.now().timestamp() * 1000)))
    return jsonify({"status": "ok"})

@app.route("/api/kpis")
def kpis():
    if latest:
        return jsonify(clean_kpis(latest))
    if os.path.exists(KPI_FILE):
        with open(KPI_FILE) as f:
            return jsonify(clean_kpis(json.load(f)))
    return jsonify({})

@app.route("/api/history")
def kpis_history():
    return jsonify(list(history))

def make_series(*fields):
    """
    Returns a flat object where every array has EXACTLY the same length.
    {timestamps:[t1,t2,...], field1:[v1,v2,...], field2:[v1,v2,...]}
    Equal-length arrays are required for marcusolsson-json-datasource
    to build a valid multi-field time-series frame from one query.
    """
    h = list(history)
    n = len(h)
    result = {"timestamps": [row["timestamp"] for row in h]}
    for f in fields:
        vals = [row.get(f, 0) for row in h]
        # safety: force exact same length as timestamps
        vals = vals[:n] + [0] * (n - len(vals))
        result[f] = vals
    return result

@app.route("/api/series/traffic")
def series_traffic():
    return jsonify(make_series("downlink_bitrate", "uplink_bitrate"))

@app.route("/api/series/ran")
def series_ran():
    return jsonify(make_series("active_gnbs", "rrc_success_rate"))

@app.route("/api/series/cluster")
def series_cluster():
    return jsonify(make_series("active_subscribers", "active_sessions"))

@app.route("/api/series/core")
def series_core():
    return jsonify(make_series("core_resource_utilization_pct"))

@app.route("/api/series/ue")
def series_ue():
    return jsonify(make_series("ue_throughput_mbps"))

@app.route("/api/topology")
def topology():
    if latest:
        return jsonify({"nodes": latest.get("nodes", []), "edges": latest.get("edges", [])})
    if os.path.exists(KPI_FILE):
        with open(KPI_FILE) as f:
            d = json.load(f)
        return jsonify({"nodes": d.get("nodes",[]), "edges": d.get("edges",[])})
    return jsonify({"nodes":[], "edges":[]})

@app.route("/topology")
def topology_legacy():
    return topology()

@app.route("/api/predict/anomaly")
@app.route("/api/predict/anomaly/")
@app.route("/api/anomaly")
@app.route("/api/anomaly/")
def predict_anomaly():
    """Per-KPI EWMA baseline, z-score, and anomaly flag over current history."""
    return jsonify(detect_anomalies(list(history)))

@app.route("/api/predict/anomaly/table")
@app.route("/api/predict/anomaly/table/")
def predict_anomaly_table():
    """Flat array of anomaly records for Grafana Table/Stat visualizations."""
    raw_anomalies = detect_anomalies(list(history))
    if isinstance(raw_anomalies, dict) and raw_anomalies.get("status") == "warming_up":
        return jsonify([])
    flat_records = []
    for field, metrics in raw_anomalies.items():
        record = {
            "field": field,
            "value": metrics.get("value"),
            "baseline": metrics.get("baseline"),
            "std": metrics.get("std"),
            "z_score": metrics.get("z_score"),
            "is_anomaly": metrics.get("is_anomaly")
        }
        flat_records.append(record)
    return jsonify(flat_records)

@app.route("/api/predict/forecast/<field>")
def predict_forecast(field):
    """Short-horizon linear forecast for one KPI field, e.g. /api/predict/forecast/latency_ms"""
    horizon = int(request.args.get("horizon", 6))
    return jsonify(forecast(list(history), field, horizon=horizon))

@app.route("/api/predict/lstm/<field>")
def predict_lstm_route(field):
    """LSTM model forecast for one KPI field (downlink_bitrate or uplink_bitrate)."""
    horizon = int(request.args.get("horizon", 5))
    field_map = {
        "downlink_bitrate": "downlink_bitrate",
        "uplink_bitrate": "uplink_bitrate",
        "dl_bitrate_mbps": "downlink_bitrate",
        "ul_bitrate_mbps": "uplink_bitrate"
    }
    target_field = field_map.get(field)
    if not target_field:
        return jsonify({"status": "error", "message": f"Unsupported LSTM prediction field: '{field}'"}), 400
        
    return jsonify(predict_lstm(list(history), target_field, horizon=horizon))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)