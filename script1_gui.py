import tkinter as tk
from tkinter import messagebox
import json, os, subprocess, sys

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "backend", "data")
INV_FILE   = os.path.join(DATA_DIR, "inventory.json")
GEN_SCRIPT = os.path.join(BASE_DIR, "script2_generator.py")
os.makedirs(DATA_DIR, exist_ok=True)

gen_process = None

def save_and_start():
    global gen_process
    try:
        n_gnb  = int(entry_gnb.get())
        n_core = int(entry_core.get())
        n_ue   = int(entry_ue.get())
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid integers.")
        return
    if n_gnb < 1 or n_core < 1 or n_ue < 1:
        messagebox.showerror("Input Error", "All values must be >= 1.")
        return

    nodes = []
    edges = []

    # Core nodes
    for i in range(n_core):
        nodes.append({
            "id":     f"core{i+1}",
            "label":  f"5G CORE{'-'+str(i+1) if n_core>1 else ''}",
            "type":   "core",
            "status": "active"
        })

    # IMS
    nodes.append({"id":"ims","label":"IMS","type":"ims","status":"active"})

    # gNB nodes
    for i in range(n_gnb):
        nodes.append({
            "id":     f"gnb{i+1}",
            "label":  f"gNB-001:01:{hex(i+1)[2:].zfill(7)}",
            "type":   "gnb",
            "status": "active"
        })

    # UE nodes
    for i in range(n_ue):
        nodes.append({
            "id":     f"ue{i+1}",
            "label":  f"UE-{str(i+1).zfill(3)}",
            "type":   "ue",
            "status": "active"
        })

    # Edges: core → ims
    for i in range(n_core):
        edges.append({"source": f"core{i+1}", "target": "ims"})

    # Edges: core → gnb
    for i in range(n_core):
        for j in range(n_gnb):
            edges.append({"source": f"core{i+1}", "target": f"gnb{j+1}"})

    # Edges: gnb → ue (round-robin)
    for i in range(n_ue):
        edges.append({"source": f"gnb{(i % n_gnb) + 1}", "target": f"ue{i+1}"})

    inventory = {
        "num_gnbs":  n_gnb,
        "num_cores": n_core,
        "num_ues":   n_ue,
        "nodes":     nodes,
        "edges":     edges
    }

    with open(INV_FILE, "w") as f:
        json.dump(inventory, f, indent=2)

    status_label.config(
        text=f"✅ Generator running | {n_core} Core · {n_gnb} gNBs · {n_ue} UEs",
        fg="lightgreen")

    if gen_process and gen_process.poll() is None:
        gen_process.terminate()
    gen_process = subprocess.Popen([sys.executable, GEN_SCRIPT])

def stop_generator():
    global gen_process
    if gen_process and gen_process.poll() is None:
        gen_process.terminate()
        status_label.config(text="⛔ Generator stopped", fg="salmon")
    else:
        status_label.config(text="ℹ️  Generator is not running", fg="yellow")

# ── GUI ────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("5G SMO — Inventory Generator")
root.geometry("420x340")
root.configure(bg="#0a0f1e")
root.resizable(False, False)

FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_LABEL = ("Segoe UI", 11)
FONT_BTN   = ("Segoe UI", 10, "bold")
COLOR_BG   = "#0a0f1e"
COLOR_CARD = "#18243a"
COLOR_CYAN = "#63d6ff"

tk.Label(root, text="5G SMO Inventory Generator",
         font=FONT_TITLE, fg=COLOR_CYAN, bg=COLOR_BG).pack(pady=(18,10))

card = tk.Frame(root, bg=COLOR_CARD, padx=20, pady=16)
card.pack(padx=30, fill="x")

def make_row(parent, label_text, default, row):
    tk.Label(parent, text=label_text, font=FONT_LABEL,
             fg="white", bg=COLOR_CARD, anchor="w").grid(row=row, column=0, sticky="w", pady=6)
    var = tk.StringVar(value=str(default))
    e = tk.Entry(parent, textvariable=var, font=FONT_LABEL,
                 bg="#0d1b3e", fg=COLOR_CYAN, insertbackground="white",
                 width=8, relief="flat", bd=4)
    e.grid(row=row, column=1, padx=(20,0), pady=6)
    return var

entry_core = make_row(card, "Number of Core Nodes:", 1, 0)
entry_gnb  = make_row(card, "Number of gNBs:",       4, 1)
entry_ue   = make_row(card, "Number of UEs:",         4, 2)

btn_frame = tk.Frame(root, bg=COLOR_BG)
btn_frame.pack(pady=14)

tk.Button(btn_frame, text="▶  Generate & Start",
          font=FONT_BTN, bg="#00ff88", fg="#0a0f1e",
          padx=16, pady=6, relief="flat", cursor="hand2",
          command=save_and_start).pack(side="left", padx=8)

tk.Button(btn_frame, text="⛔  Stop",
          font=FONT_BTN, bg="#ff4d4d", fg="white",
          padx=16, pady=6, relief="flat", cursor="hand2",
          command=stop_generator).pack(side="left", padx=8)

status_label = tk.Label(root, text="ℹ️  Set values and click Generate",
                         font=("Segoe UI", 9), fg="gray", bg=COLOR_BG)
status_label.pack()

root.mainloop()

# Terminal 1 — Flask Backend
# cd D:\IITD\5G-SMO-Dashboard
# python backend/app.py
#
# Terminal 2 — HTTP Server for Topology
# cd D:\IITD\5G-SMO-Dashboard\topology
# python -m http.server 8000
#
# Terminal 3 — GUI + Generator
# cd D:\IITD\5G-SMO-Dashboard
# python script1_gui.py
# GUI window opens → set your values → click Generate & Start