"""
core_sim.py — Simulated 5G Core node
Exposes live core-network KPIs: subscriber/session counts, resource
utilization, session success rate, packet loss.

Run:  python nodes/core_sim.py            (defaults to port 6003)
"""
from flask import Flask, jsonify, request
import random, threading, time, argparse

app = Flask(__name__)

state = {
    "active_subscribers":            300.0,
    "active_sessions":                220.0,
    "session_success_rate":           99.0,
    "packet_loss_pct":                 0.3,
    "core_resource_utilization_pct":  40.0,
}

ANOMALY_UNTIL = 0.0
LOCK = threading.Lock()


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def drift():
    global ANOMALY_UNTIL
    while True:
        with LOCK:
            now = time.time()
            anomaly = now < ANOMALY_UNTIL

            if anomaly:
                state["active_subscribers"]           = clamp(state["active_subscribers"] + random.uniform(-30, 30), 50, 600)
                state["active_sessions"]               = clamp(state["active_sessions"] + random.uniform(-20, 20), 30, 500)
                state["session_success_rate"]          = clamp(state["session_success_rate"] - random.uniform(2, 10), 50, 100)
                state["packet_loss_pct"]               = clamp(state["packet_loss_pct"] + random.uniform(1, 5), 0, 20)
                state["core_resource_utilization_pct"] = clamp(state["core_resource_utilization_pct"] + random.uniform(10, 30), 0, 100)
            else:
                state["active_subscribers"]           = clamp(state["active_subscribers"] + random.uniform(-10, 10), 150, 450)
                state["active_sessions"]               = clamp(state["active_sessions"] + random.uniform(-8, 8), 100, 350)
                state["session_success_rate"]          = clamp(state["session_success_rate"] + random.uniform(-0.2, 0.2), 97, 100)
                state["packet_loss_pct"]               = clamp(state["packet_loss_pct"] + random.uniform(-0.05, 0.05), 0.05, 1)
                state["core_resource_utilization_pct"] = clamp(state["core_resource_utilization_pct"] + random.uniform(-3, 3), 25, 60)

                if random.random() < 0.01:
                    ANOMALY_UNTIL = now + random.uniform(15, 40)
        time.sleep(1)


@app.route("/api/metrics")
def metrics():
    with LOCK:
        return jsonify(dict(state))


@app.route("/api/inject_anomaly", methods=["POST"])
def inject_anomaly():
    global ANOMALY_UNTIL
    duration = float(request.args.get("seconds", 20))
    with LOCK:
        ANOMALY_UNTIL = time.time() + duration
    return jsonify({"status": "anomaly injected", "duration_s": duration})


@app.route("/")
def root():
    return jsonify({"status": "ok", "service": "Core simulator"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6003)
    args = parser.parse_args()
    threading.Thread(target=drift, daemon=True).start()
    app.run(host="0.0.0.0", port=args.port, debug=False)