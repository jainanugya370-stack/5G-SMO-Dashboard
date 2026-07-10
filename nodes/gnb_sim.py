"""
gnb_sim.py — Simulated gNB (DU/CU aggregation) node
Exposes live RAN-layer KPIs: RRC/handover success rates, latency, UE throughput.

Run:  python nodes/gnb_sim.py            (defaults to port 6002)
"""
from flask import Flask, jsonify, request
import random, threading, time, argparse

app = Flask(__name__)

state = {
    "rrc_success_rate":      99.2,
    "handover_success_rate": 98.5,
    "latency_ms":             12.0,
    "ue_throughput_mbps":    180.0,
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
                state["rrc_success_rate"]      = clamp(state["rrc_success_rate"] - random.uniform(2, 8), 50, 100)
                state["handover_success_rate"] = clamp(state["handover_success_rate"] - random.uniform(2, 10), 50, 100)
                state["latency_ms"]            = clamp(state["latency_ms"] + random.uniform(10, 40), 5, 200)
                state["ue_throughput_mbps"]    = clamp(state["ue_throughput_mbps"] - random.uniform(20, 60), 10, 300)
            else:
                state["rrc_success_rate"]      = clamp(state["rrc_success_rate"] + random.uniform(-0.3, 0.3), 96, 100)
                state["handover_success_rate"] = clamp(state["handover_success_rate"] + random.uniform(-0.4, 0.4), 94, 100)
                state["latency_ms"]            = clamp(state["latency_ms"] + random.uniform(-1, 1), 5, 25)
                state["ue_throughput_mbps"]    = clamp(state["ue_throughput_mbps"] + random.uniform(-10, 10), 100, 250)

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
    return jsonify({"status": "ok", "service": "gNB simulator"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6002)
    args = parser.parse_args()
    threading.Thread(target=drift, daemon=True).start()
    app.run(host="0.0.0.0", port=args.port, debug=False)