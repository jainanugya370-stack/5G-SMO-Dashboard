"""
ru_sim.py — Simulated Radio Unit (RU) node
Exposes live PHY-layer KPIs on its own Flask service so the collector can
poll it just like it would poll a real O-RU management interface.

Run:  python nodes/ru_sim.py            (defaults to port 6001)
      python nodes/ru_sim.py --port 6011  (run a second RU on another port)
"""
from flask import Flask, jsonify, request
import random, threading, time, argparse

app = Flask(__name__)

state = {
    "prb_utilization_pct": 45.0,
    "bler_pct":             1.2,
    "dl_bitrate_mbps":    850.0,
    "ul_bitrate_mbps":    120.0,
    "rssi_dbm":           -85.0,
}

ANOMALY_UNTIL = 0.0   # epoch time; while now < this, inject degraded radio conditions
LOCK = threading.Lock()


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def drift():
    """Background thread: random-walks the KPIs every second, with occasional
    self-triggered anomaly windows (simulating interference/congestion)."""
    global ANOMALY_UNTIL
    while True:
        with LOCK:
            now = time.time()
            anomaly = now < ANOMALY_UNTIL

            if anomaly:
                state["prb_utilization_pct"] = clamp(state["prb_utilization_pct"] + random.uniform(2, 6), 0, 100)
                state["bler_pct"]            = clamp(state["bler_pct"] + random.uniform(1, 4), 0, 30)
                state["dl_bitrate_mbps"]     = clamp(state["dl_bitrate_mbps"] - random.uniform(20, 60), 50, 1000)
                state["ul_bitrate_mbps"]     = clamp(state["ul_bitrate_mbps"] - random.uniform(5, 15), 10, 300)
                state["rssi_dbm"]            = clamp(state["rssi_dbm"] - random.uniform(1, 3), -110, -60)
            else:
                state["prb_utilization_pct"] = clamp(state["prb_utilization_pct"] + random.uniform(-2, 2), 20, 75)
                state["bler_pct"]            = clamp(state["bler_pct"] + random.uniform(-0.2, 0.2), 0.1, 3)
                state["dl_bitrate_mbps"]     = clamp(state["dl_bitrate_mbps"] + random.uniform(-15, 15), 400, 1000)
                state["ul_bitrate_mbps"]     = clamp(state["ul_bitrate_mbps"] + random.uniform(-5, 5), 60, 250)
                state["rssi_dbm"]            = clamp(state["rssi_dbm"] + random.uniform(-1, 1), -95, -70)

                # ~1% chance per second to self-trigger a degraded-radio window
                if random.random() < 0.01:
                    ANOMALY_UNTIL = now + random.uniform(15, 40)
        time.sleep(1)


@app.route("/api/metrics")
def metrics():
    with LOCK:
        return jsonify(dict(state))


@app.route("/api/inject_anomaly", methods=["POST"])
def inject_anomaly():
    """Manually trigger a degraded-radio window — handy for demoing the anomaly detector."""
    global ANOMALY_UNTIL
    duration = float(request.args.get("seconds", 20))
    with LOCK:
        ANOMALY_UNTIL = time.time() + duration
    return jsonify({"status": "anomaly injected", "duration_s": duration})


@app.route("/")
def root():
    return jsonify({"status": "ok", "service": "RU simulator"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6001)
    args = parser.parse_args()
    threading.Thread(target=drift, daemon=True).start()
    app.run(host="0.0.0.0", port=args.port, debug=False)