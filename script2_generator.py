"""
script2_generator.py
Reads inventory.json for topology
Reads 5G_KPI_Dataset_Grafana.csv for KPI values (row by row, loops forever)
POSTs combined payload to Flask every 5 seconds
"""
import json, time, random, os, requests
import pandas as pd
from datetime import datetime

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "backend", "data")
INV_FILE  = os.path.join(DATA_DIR, "inventory.json")
KPI_FILE  = os.path.join(DATA_DIR, "kpis.json")
CSV_FILE  = os.path.join(BASE_DIR, "5G_KPI_Dataset_Grafana.csv")
FLASK_URL = "http://localhost:5000/api/update"   # ← localhost only
INTERVAL  = 5

# Load CSV once at startup
df         = pd.read_csv(CSV_FILE)
csv_index  = 0
total_rows = len(df)
print(f"[Generator] Loaded CSV: {total_rows} rows")

def load_inventory():
    with open(INV_FILE) as f:
        return json.load(f)

def random_status():
    return random.choices(["active", "inactive"], weights=[85, 15])[0]

def generate_payload(inventory):
    global csv_index

    n_gnb = inventory["num_gnbs"]
    n_ue  = inventory["num_ues"]

    # ── Nodes with live status ────────────────────────────────────────────
    nodes = []
    for node in inventory["nodes"]:
        status = random_status() if node["type"] in ["gnb", "ims"] else "active"
        nodes.append({
            "id":     node["id"],
            "label":  node["label"],
            "type":   node["type"],
            "status": status
        })

    # ── Build edges dynamically ───────────────────────────────────────────
    edges    = []
    core_ids = [n["id"] for n in nodes if n["type"] == "core"]
    gnb_ids  = [n["id"] for n in nodes if n["type"] == "gnb"]
    ue_ids   = [n["id"] for n in nodes if n["type"] == "ue"]

    # core → ims
    for c in core_ids:
        edges.append({"source": c, "target": "ims"})

    # core → each gnb
    for c in core_ids:
        for g in gnb_ids:
            edges.append({"source": c, "target": g})

    # gnb → ue (round-robin distribution)
    for ui, u in enumerate(ue_ids):
        parent_gnb = gnb_ids[ui % len(gnb_ids)] if gnb_ids else None
        if parent_gnb:
            edges.append({"source": parent_gnb, "target": u})

    active_gnbs = sum(1 for n in nodes if n["type"] == "gnb" and n["status"] == "active")

    # ── KPIs from CSV row ─────────────────────────────────────────────────
    row       = df.iloc[csv_index]
    csv_index = (csv_index + 1) % total_rows

    payload = {
        "timestamp": datetime.now().astimezone().isoformat(),

        # Topology
        "nodes":       nodes,
        "edges":       edges,
        "active_gnbs": active_gnbs,
        "total_gnbs":  n_gnb,

        # Core KPIs from CSV
        "active_subscribers":  int(row["active_subscribers"]),
        "active_sessions":     int(row["active_sessions"]),
        "downlink_bitrate":    round(float(row["dl_bitrate_mbps"]),      1),
        "uplink_bitrate":      round(float(row["ul_bitrate_mbps"]),      1),
        "traffic_utilization": round(float(row["prb_utilization_pct"]),  1),

        # Additional 3GPP KPIs
        "rrc_success_rate":              round(float(row["rrc_success_rate"]),              2),
        "session_success_rate":          round(float(row["session_success_rate"]),          2),
        "handover_success_rate":         round(float(row["handover_success_rate"]),         2),
        "latency_ms":                    round(float(row["latency_ms"]),                    1),
        "packet_loss_pct":               round(float(row["packet_loss_pct"]),               2),
        "bler_pct":                      round(float(row["bler_pct"]),                      2),
        "core_resource_utilization_pct": round(float(row["core_resource_utilization_pct"]), 1),
        "ue_throughput_mbps":            round(float(row["ue_throughput_mbps"]),            2),
    }

    return payload

def main():
    print("[Generator] Starting...")
    while True:
        try:
            inventory = load_inventory()
            payload   = generate_payload(inventory)

            with open(KPI_FILE, "w") as f:
                json.dump(payload, f, indent=2)

            try:
                requests.post(FLASK_URL, json=payload, timeout=2)
                print(
                    f"[Generator] Row {csv_index}/{total_rows} | "
                    f"gNBs:{payload['active_gnbs']}/{payload['total_gnbs']} | "
                    f"DL:{payload['downlink_bitrate']} UL:{payload['uplink_bitrate']} | "
                    f"Subs:{payload['active_subscribers']}"
                )
            except Exception as e:
                print(f"[Generator] POST failed: {e}")

        except FileNotFoundError as e:
            print(f"[Generator] File not found: {e}")

        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()