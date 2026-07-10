"""
collector.py
Replaces script2_generator.py (CSV replay). Polls the LIVE simulated
RU / gNB / Core node services and forwards a unified payload to the
existing Flask backend — same schema as before, so app.py and every
Grafana panel keep working unchanged.

Run order:
  1) python nodes/ru_sim.py
  2) python nodes/gnb_sim.py
  3) python nodes/core_sim.py
  4) python backend/app.py
  5) python script1_gui.py          (creates inventory.json — click Generate & Start,
                                      but you can just leave the OLD generator OFF)
  6) python collector.py
"""
import json, time, random, os, requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
INV_FILE = os.path.join(DATA_DIR, "inventory.json")
KPI_FILE = os.path.join(DATA_DIR, "kpis.json")

import os

FLASK_URL = os.environ.get("FLASK_URL", "http://localhost:5000/api/update")
RU_URL    = os.environ.get("RU_URL", "http://localhost:6001/api/metrics")
GNB_URL   = os.environ.get("GNB_URL", "http://localhost:6002/api/metrics")
CORE_URL  = os.environ.get("CORE_URL", "http://localhost:6003/api/metrics")

INTERVAL = 5
TIMEOUT  = 2


def load_inventory():
    with open(INV_FILE) as f:
        return json.load(f)


def random_status():
    return random.choices(["active", "inactive"], weights=[85, 15])[0]


def fetch(url, label):
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Collector] {label} unreachable ({e}) — using defaults for this tick")
        return {}


def build_topology(inventory):
    """Same cosmetic topology-flicker logic as the old script2_generator.py."""
    nodes = []
    for node in inventory["nodes"]:
        status = random_status() if node["type"] in ["gnb", "ims"] else "active"
        nodes.append({"id": node["id"], "label": node["label"], "type": node["type"], "status": status})

    edges = []
    core_ids = [n["id"] for n in nodes if n["type"] == "core"]
    gnb_ids  = [n["id"] for n in nodes if n["type"] == "gnb"]
    ue_ids   = [n["id"] for n in nodes if n["type"] == "ue"]

    for c in core_ids:
        edges.append({"source": c, "target": "ims"})
    for c in core_ids:
        for g in gnb_ids:
            edges.append({"source": c, "target": g})
    for i, u in enumerate(ue_ids):
        if gnb_ids:
            edges.append({"source": gnb_ids[i % len(gnb_ids)], "target": u})

    active_gnbs = sum(1 for n in nodes if n["type"] == "gnb" and n["status"] == "active")
    return nodes, edges, active_gnbs, inventory["num_gnbs"]


def build_payload(inventory):
    nodes, edges, active_gnbs, total_gnbs = build_topology(inventory)

    ru   = fetch(RU_URL,   "RU sim")
    gnb  = fetch(GNB_URL,  "gNB sim")
    core = fetch(CORE_URL, "Core sim")

    return {
        "timestamp": datetime.now().astimezone().isoformat(),

        # Topology (cosmetic, same as before)
        "nodes": nodes,
        "edges": edges,
        "active_gnbs": active_gnbs,
        "total_gnbs": total_gnbs,

        # From RU (PHY layer)
        "downlink_bitrate":    round(ru.get("dl_bitrate_mbps", 0), 1),
        "uplink_bitrate":      round(ru.get("ul_bitrate_mbps", 0), 1),
        "traffic_utilization": round(ru.get("prb_utilization_pct", 0), 1),
        "bler_pct":            round(ru.get("bler_pct", 0), 2),

        # From gNB (RAN layer)
        "rrc_success_rate":      round(gnb.get("rrc_success_rate", 0), 2),
        "handover_success_rate": round(gnb.get("handover_success_rate", 0), 2),
        "latency_ms":            round(gnb.get("latency_ms", 0), 1),
        "ue_throughput_mbps":    round(gnb.get("ue_throughput_mbps", 0), 2),

        # From Core
        "active_subscribers":            int(core.get("active_subscribers", 0)),
        "active_sessions":               int(core.get("active_sessions", 0)),
        "session_success_rate":          round(core.get("session_success_rate", 0), 2),
        "packet_loss_pct":               round(core.get("packet_loss_pct", 0), 2),
        "core_resource_utilization_pct": round(core.get("core_resource_utilization_pct", 0), 1),
    }


def main():
    print("[Collector] Starting live collection loop...")
    while True:
        try:
            inventory = load_inventory()
            payload   = build_payload(inventory)

            with open(KPI_FILE, "w") as f:
                json.dump(payload, f, indent=2)

            try:
                requests.post(FLASK_URL, json=payload, timeout=TIMEOUT)
                print(
                    f"[Collector] Sent | DL:{payload['downlink_bitrate']} UL:{payload['uplink_bitrate']} "
                    f"| Lat:{payload['latency_ms']}ms | Subs:{payload['active_subscribers']}"
                )
            except Exception as e:
                print(f"[Collector] POST to Flask failed: {e}")

        except FileNotFoundError as e:
            print(f"[Collector] inventory.json not found — run script1_gui.py once first ({e})")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()