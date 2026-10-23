"""
NetFailover - Advanced NOC GUI Dashboard
Computer Networks Fault Detection & Automatic Failover System

Features:
- Live Interactive Network Topology Diagram (Canvas-based)
- Dark-theme Datacenter/NOC visual aesthetics
- Live Latency Gauge & Heartbeat Miss step-indicators
- Real-time Failover Duration & Detection Timers
- Syntax-highlighted Scrolled Event Log
- Interactive Network Command Testing Panel
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from datetime import datetime

# Import the real NetFailover client engine and configuration
from client import NetFailoverClient, SERVER_IP, SERVER_PORT, BACKUP_SERVER_IP, BACKUP_SERVER_PORT

# Global client and widget references
client = None
root = None

# Statistics counters
stats = {
    "pings_sent": 0,
    "pongs_received": 0,
    "missed_count": 0,
    "total_failovers": 0
}

# UI Widget References
canvas_topo = None
lbl_active_pill = None
lbl_primary_pill = None
lbl_backup_pill = None
lbl_rtt_val = None
lbl_det_val = None
lbl_switch_val = None
lbl_hb_status = None
box_missed_1 = None
box_missed_2 = None
box_missed_3 = None
lbl_stat_pings = None
lbl_stat_pongs = None
lbl_stat_failovers = None
txt_event_log = None
btn_start = None
btn_stop = None
entry_message = None


def get_current_timestamp():
    """Returns formatted current timestamp string."""
    return datetime.now().strftime("%H:%M:%S")


def add_log(message, tag="INFO"):
    """
    Appends a timestamped, color-tagged message to the scrolling Event Log area.
    Thread-safe when called via root.after or on the main thread.
    """
    if txt_event_log is not None:
        timestamp = get_current_timestamp()
        log_entry = f"[{timestamp}] {message}\n"
        txt_event_log.configure(state="normal")
        txt_event_log.insert(tk.END, log_entry, tag)
        txt_event_log.see(tk.END)
        txt_event_log.configure(state="disabled")


def clear_log():
    """Clears all messages from the Event Log area."""
    if txt_event_log is not None:
        txt_event_log.configure(state="normal")
        txt_event_log.delete("1.0", tk.END)
        txt_event_log.configure(state="disabled")
        add_log("Event log cleared.", "INFO")


topology_state = {
    "primary": "OFFLINE",
    "backup": "STANDBY",
    "active": "PRIMARY"
}


def draw_topology(primary_status=None, backup_status=None, active=None):
    """
    Draws the live network topology diagram on the Canvas:
    Client node on the left, Primary and Backup server nodes on the right,
    with dynamic color-coded links showing active routing and failures.
    """
    global topology_state
    if canvas_topo is None:
        return

    if primary_status is not None:
        topology_state["primary"] = primary_status
    if backup_status is not None:
        topology_state["backup"] = backup_status
    if active is not None:
        topology_state["active"] = active

    p_status = topology_state["primary"]
    b_status = topology_state["backup"]
    act = topology_state["active"]

    canvas_topo.delete("all")
    w = canvas_topo.winfo_width() or 860
    h = canvas_topo.winfo_height() or 140

    # Coordinates
    client_x, client_y = 90, h // 2
    prim_x, prim_y = w - 110, 38
    back_x, back_y = w - 110, h - 38

    # Link colors and styles
    link_prim_color = "#334155"  # Slate inactive
    link_prim_width = 2
    link_prim_dash = (4, 4)

    link_back_color = "#334155"
    link_back_width = 2
    link_back_dash = (4, 4)

    if p_status == "ONLINE" and act == "PRIMARY":
        link_prim_color = "#10b981"  # Emerald active
        link_prim_width = 3
        link_prim_dash = ()
    elif p_status in ("OFFLINE", "TIMEOUT"):
        link_prim_color = "#ef4444"  # Red failed
        link_prim_width = 3
        link_prim_dash = (3, 3)

    if b_status == "ONLINE" and act == "BACKUP":
        link_back_color = "#10b981"  # Emerald active
        link_back_width = 3
        link_back_dash = ()
    elif b_status == "STANDBY":
        link_back_color = "#38bdf8"  # Cyan standby
        link_back_width = 2
        link_back_dash = (6, 4)

    # Draw Link Lines
    canvas_topo.create_line(client_x + 35, client_y, prim_x - 45, prim_y, fill=link_prim_color, width=link_prim_width, dash=link_prim_dash)
    canvas_topo.create_line(client_x + 35, client_y, back_x - 45, back_y, fill=link_back_color, width=link_back_width, dash=link_back_dash)

    def draw_node(x, y, label, sublabel, color, border_color):
        # Card body
        canvas_topo.create_rectangle(x - 55, y - 24, x + 55, y + 24, fill=color, outline=border_color, width=2)
        canvas_topo.create_text(x, y - 7, text=label, fill="#ffffff", font=("Segoe UI", 9, "bold"))
        canvas_topo.create_text(x, y + 9, text=sublabel, fill="#94a3b8", font=("Segoe UI", 8))

    # Draw Client Node
    draw_node(client_x, client_y, "CLIENT", "NetFailover App", "#1e293b", "#38bdf8")

    # Draw Primary Server Node
    prim_bg = "#064e3b" if p_status == "ONLINE" else "#450a0a"
    prim_border = "#10b981" if p_status == "ONLINE" else "#ef4444"
    draw_node(prim_x, prim_y, f"PRIMARY :{SERVER_PORT}", f"[{p_status}]", prim_bg, prim_border)

    # Draw Backup Server Node
    if b_status == "ONLINE" and act == "BACKUP":
        back_bg = "#064e3b"
        back_border = "#10b981"
    else:
        back_bg = "#0c4a6e"
        back_border = "#38bdf8"
    draw_node(back_x, back_y, f"BACKUP :{BACKUP_SERVER_PORT}", f"[{b_status}]", back_bg, back_border)


def update_missed_blocks(missed_count):
    """Updates the 3-step missed heartbeat visual indicator blocks."""
    blocks = [box_missed_1, box_missed_2, box_missed_3]
    for i, b in enumerate(blocks, start=1):
        if b is None:
            continue
        if i <= missed_count:
            if missed_count >= 3:
                b.config(bg="#ef4444", fg="#ffffff")  # Red threshold reached
            else:
                b.config(bg="#f59e0b", fg="#ffffff")  # Amber warning
        else:
            b.config(bg="#1e293b", fg="#64748b")     # Grey idle


def on_client_event(event_type, data):
    """Thread-safe event dispatcher that marshals networking events to the GUI thread."""
    if root is not None:
        root.after(0, lambda: handle_gui_event(event_type, data))


def handle_gui_event(event_type, data):
    """Updates widgets, counters, topology, and logs on the main Tkinter thread."""
    global stats

    if event_type == "PRIMARY_CONNECTED":
        lbl_primary_pill.config(text="ONLINE", bg="#065f46", fg="#34d399")
        lbl_backup_pill.config(text="STANDBY", bg="#0c4a6e", fg="#38bdf8")
        lbl_active_pill.config(text="PRIMARY SERVER", bg="#1e3a8a", fg="#60a5fa")

        lbl_hb_status.config(text="ACTIVE HEARTBEAT", fg="#34d399")
        update_missed_blocks(0)
        lbl_det_val.config(text="0.00 s")
        lbl_switch_val.config(text="0.00 ms")

        draw_topology("ONLINE", "STANDBY", "PRIMARY")
        add_log(f"Connected to Primary Server at {data.get('ip')}:{data.get('port')}.", "SUCCESS")
        btn_start.config(state="disabled")
        btn_stop.config(state="normal")

    elif event_type == "HEARTBEAT_PING":
        stats["pings_sent"] += 1
        lbl_stat_pings.config(text=str(stats["pings_sent"]))
        add_log(f"PING probe -> {data.get('active_server')}", "PING")

    elif event_type == "HEARTBEAT_PONG":
        stats["pongs_received"] += 1
        lbl_stat_pongs.config(text=str(stats["pongs_received"]))
        rtt = data.get("response_time", 0.0)
        lbl_rtt_val.config(text=f"{rtt:.2f} ms")
        update_missed_blocks(0)
        lbl_hb_status.config(text=f"CONNECTED ({data.get('active_server')})", fg="#34d399")
        add_log(f"PONG received from {data.get('active_server')} (RTT: {rtt:.2f} ms)", "SUCCESS")

    elif event_type == "HEARTBEAT_MISSED":
        missed = data.get("missed_count", 0)
        update_missed_blocks(missed)
        active = data.get("active_server", "PRIMARY")
        lbl_hb_status.config(text=f"PROBE TIMEOUT ({missed}/3)", fg="#f59e0b")
        add_log(f"Heartbeat probe {missed}/3 timed out from {active} server!", "WARN")

    elif event_type == "FAILURE_DETECTED":
        det_time = data.get("detection_time", 0.0)
        lbl_primary_pill.config(text="OFFLINE", bg="#7f1d1d", fg="#f87171")
        lbl_det_val.config(text=f"{det_time:.2f} s")
        lbl_hb_status.config(text="PRIMARY FAILED", fg="#ef4444")
        draw_topology("OFFLINE", "STANDBY", "PRIMARY")
        add_log(f"FAULT DETECTED: Primary server failed! (Detection time: {det_time:.2f} s)", "FAIL")

    elif event_type == "FAILOVER_STARTED":
        lbl_hb_status.config(text="FAILOVER IN PROGRESS...", fg="#f59e0b")
        add_log(f"Initiating automatic socket failover to Backup ({BACKUP_SERVER_IP}:{BACKUP_SERVER_PORT})...", "FAILOVER")

    elif event_type == "BACKUP_CONNECTED":
        lbl_backup_pill.config(text="ONLINE (ACTIVE)", bg="#065f46", fg="#34d399")

    elif event_type == "FAILOVER_COMPLETED":
        stats["total_failovers"] += 1
        lbl_stat_failovers.config(text=str(stats["total_failovers"]))

        det_time = data.get("detection_time", 0.0)
        dur = data.get("failover_duration", 0.0)

        lbl_primary_pill.config(text="OFFLINE", bg="#7f1d1d", fg="#f87171")
        lbl_backup_pill.config(text="ONLINE", bg="#065f46", fg="#34d399")
        lbl_active_pill.config(text="BACKUP SERVER", bg="#581c87", fg="#c084fc")

        lbl_hb_status.config(text="CONNECTED (Backup Active)", fg="#34d399")
        update_missed_blocks(0)
        lbl_det_val.config(text=f"{det_time:.2f} s")
        lbl_switch_val.config(text=f"{dur:.2f} ms")

        draw_topology("OFFLINE", "ONLINE", "BACKUP")
        add_log(f"FAILOVER COMPLETED: Switched to Backup Server at {data.get('ip')}:{data.get('port')}.", "FAILOVER")
        add_log(f"Reconnection TCP handshake finished in {dur:.2f} ms.", "SUCCESS")

    elif event_type == "CONNECTION_FAILED":
        msg = data.get("message", "Connection failed.")
        lbl_hb_status.config(text="DISCONNECTED", fg="#ef4444")
        draw_topology("OFFLINE", "OFFLINE", "NONE")
        add_log(f"Connection error: {msg}", "FAIL")
        btn_start.config(state="normal")
        btn_stop.config(state="disabled")

    elif event_type == "DISCONNECTED":
        lbl_hb_status.config(text="STANDBY / STOPPED", fg="#94a3b8")
        draw_topology("OFFLINE", "STANDBY", "NONE")
        add_log("Monitoring stopped and client disconnected.", "INFO")
        btn_start.config(state="normal")
        btn_stop.config(state="disabled")


def start_monitoring():
    """Connects to Primary Server and starts heartbeats in background thread."""
    global client
    if client and client.is_connected:
        return

    btn_start.config(state="disabled")
    btn_stop.config(state="normal")
    add_log("Connecting to Primary Server...", "INFO")

    def connect_worker():
        global client
        client = NetFailoverClient(event_callback=on_client_event)
        success = client.connect()
        if success:
            client.start_heartbeat()
        else:
            def on_fail():
                btn_start.config(state="normal")
                btn_stop.config(state="disabled")
            root.after(0, on_fail)

    threading.Thread(target=connect_worker, daemon=True).start()


def stop_monitoring():
    """Disconnects client cleanly and stops heartbeat worker."""
    global client
    btn_start.config(state="normal")
    btn_stop.config(state="disabled")

    def disconnect_worker():
        global client
        if client:
            client.disconnect()
            client = None

    threading.Thread(target=disconnect_worker, daemon=True).start()


def send_gui_command(command_text):
    """Sends interactive command through active socket without blocking GUI."""
    global client
    if not client or not client.is_connected:
        add_log("Cannot send: Client is not connected to any server.", "FAIL")
        return

    cmd = command_text.strip()
    if not cmd:
        return

    def command_worker():
        add_log(f"TX -> '{cmd}' to {client.active_server}", "CMD")
        response = client.send_command(cmd)
        if response:
            root.after(0, lambda: add_log(f"RX <- {response}", "SUCCESS"))
        else:
            root.after(0, lambda: add_log(f"RX <- No response from {client.active_server}!", "FAIL"))

    threading.Thread(target=command_worker, daemon=True).start()


def trigger_simulated_crash():
    """Simulates primary server failure by instructing primary server to crash."""
    global client
    if not client or not client.is_connected:
        add_log("Cannot simulate crash: Client is not connected to any server.", "FAIL")
        return
    if client.active_server != "PRIMARY":
        add_log("Primary Server is already OFFLINE.", "WARN")
        return

    add_log("Triggering simulated crash of Primary Server...", "WARN")
    send_gui_command("CRASH")


def on_send_message():
    """Handles sending text from the message entry box."""
    global entry_message
    if entry_message:
        text = entry_message.get().strip()
        if text:
            send_gui_command(f"MESSAGE {text}")


def on_window_close():
    """Ensures clean socket teardown on exit."""
    global client
    if client:
        try:
            client.disconnect()
        except Exception:
            pass
    if root:
        root.destroy()


def create_dashboard():
    """Constructs the high-tech NOC Tkinter dashboard."""
    global root, canvas_topo
    global lbl_active_pill, lbl_primary_pill, lbl_backup_pill
    global lbl_rtt_val, lbl_det_val, lbl_switch_val, lbl_hb_status
    global box_missed_1, box_missed_2, box_missed_3
    global lbl_stat_pings, lbl_stat_pongs, lbl_stat_failovers
    global txt_event_log, btn_start, btn_stop, entry_message

    root = tk.Tk()
    root.title("NetFailover NOC - Computer Networks Fault Detection & Failover")
    root.geometry("980x720")
    root.minsize(920, 640)
    root.protocol("WM_DELETE_WINDOW", on_window_close)

    # Dark NOC Palette
    bg_dark = "#0b1120"
    card_bg = "#1e293b"
    border_color = "#334155"
    text_primary = "#f8fafc"
    text_secondary = "#94a3b8"

    root.configure(bg=bg_dark)

    main_frame = tk.Frame(root, bg=bg_dark, padx=16, pady=12)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 1. TOP HEADER & TITLE
    header = tk.Frame(main_frame, bg=card_bg, padx=16, pady=12, highlightthickness=1, highlightbackground=border_color)
    header.pack(fill=tk.X, pady=(0, 10))

    title_box = tk.Frame(header, bg=card_bg)
    title_box.pack(side=tk.LEFT)

    tk.Label(
        title_box,
        text="NETFAILOVER NOC MONITOR",
        font=("Segoe UI", 14, "bold"),
        fg="#38bdf8",
        bg=card_bg
    ).pack(anchor="w")

    tk.Label(
        title_box,
        text="Network Fault Detection & Automatic Server Failover System • TCP Socket Layer",
        font=("Segoe UI", 9),
        fg=text_secondary,
        bg=card_bg
    ).pack(anchor="w")

    # Header Active Pill
    active_frame = tk.Frame(header, bg=card_bg)
    active_frame.pack(side=tk.RIGHT)
    tk.Label(active_frame, text="ROUTED NODE:", font=("Segoe UI", 8, "bold"), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT, padx=6)
    lbl_active_pill = tk.Label(active_frame, text="STANDBY", font=("Segoe UI", 9, "bold"), bg="#334155", fg="#cbd5e1", padx=10, pady=3)
    lbl_active_pill.pack(side=tk.LEFT)

    # 2. TOPOLOGY DIAGRAM CANVAS
    topo_card = tk.LabelFrame(
        main_frame,
        text="  Network Topology & Real-Time Flow  ",
        font=("Segoe UI", 9, "bold"),
        fg="#38bdf8",
        bg=card_bg,
        padx=8,
        pady=4,
        bd=1,
        relief="solid"
    )
    topo_card.pack(fill=tk.X, pady=(0, 10))

    canvas_topo = tk.Canvas(topo_card, height=105, bg="#0f172a", highlightthickness=0)
    canvas_topo.pack(fill=tk.X, expand=True)
    canvas_topo.bind("<Configure>", lambda e: draw_topology())

    # 3. METRICS GRID (Cards A, B, C)
    grid_frame = tk.Frame(main_frame, bg=bg_dark)
    grid_frame.pack(fill=tk.X, pady=(0, 10))
    grid_frame.columnconfigure(0, weight=1)
    grid_frame.columnconfigure(1, weight=1)
    grid_frame.columnconfigure(2, weight=1)

    def make_section(parent, title, col):
        frame = tk.LabelFrame(
            parent,
            text=f"  {title}  ",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg=card_bg,
            padx=12,
            pady=8,
            bd=1,
            relief="solid"
        )
        frame.grid(row=0, column=col, sticky="nsew", padx=4)
        return frame

    # CARD 1: SERVERS HEALTH
    c1 = make_section(grid_frame, "1. Node Connectivity", 0)

    # Primary Row
    r1 = tk.Frame(c1, bg=card_bg)
    r1.pack(fill=tk.X, pady=3)
    tk.Label(r1, text="Primary (:5000):", font=("Segoe UI", 9), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_primary_pill = tk.Label(r1, text="OFFLINE", font=("Segoe UI", 8, "bold"), bg="#334155", fg="#94a3b8", padx=8, pady=1)
    lbl_primary_pill.pack(side=tk.RIGHT)

    # Backup Row
    r2 = tk.Frame(c1, bg=card_bg)
    r2.pack(fill=tk.X, pady=3)
    tk.Label(r2, text="Backup (:5001):", font=("Segoe UI", 9), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_backup_pill = tk.Label(r2, text="STANDBY", font=("Segoe UI", 8, "bold"), bg="#0c4a6e", fg="#38bdf8", padx=8, pady=1)
    lbl_backup_pill.pack(side=tk.RIGHT)

    # CARD 2: HEARTBEAT TELEMETRY
    c2 = make_section(grid_frame, "2. Heartbeat Telemetry", 1)

    # Heartbeat Status
    r3 = tk.Frame(c2, bg=card_bg)
    r3.pack(fill=tk.X, pady=2)
    tk.Label(r3, text="Status:", font=("Segoe UI", 9), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_hb_status = tk.Label(r3, text="DISCONNECTED", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg=card_bg)
    lbl_hb_status.pack(side=tk.RIGHT)

    # RTT Latency
    r4 = tk.Frame(c2, bg=card_bg)
    r4.pack(fill=tk.X, pady=2)
    tk.Label(r4, text="Round-Trip Time (RTT):", font=("Segoe UI", 9), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_rtt_val = tk.Label(r4, text="0.00 ms", font=("Segoe UI", 9, "bold"), fg="#34d399", bg=card_bg)
    lbl_rtt_val.pack(side=tk.RIGHT)

    # Missed Blocks
    r5 = tk.Frame(c2, bg=card_bg)
    r5.pack(fill=tk.X, pady=2)
    tk.Label(r5, text="Missed Probes:", font=("Segoe UI", 9), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    box_missed_3 = tk.Label(r5, text=" 3 ", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#64748b", relief="solid", bd=1)
    box_missed_3.pack(side=tk.RIGHT, padx=1)
    box_missed_2 = tk.Label(r5, text=" 2 ", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#64748b", relief="solid", bd=1)
    box_missed_2.pack(side=tk.RIGHT, padx=1)
    box_missed_1 = tk.Label(r5, text=" 1 ", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#64748b", relief="solid", bd=1)
    box_missed_1.pack(side=tk.RIGHT, padx=1)

    # CARD 3: FAILOVER BENCHMARKS
    c3 = make_section(grid_frame, "3. Failover Metrics", 2)

    # Detection Time
    r6 = tk.Frame(c3, bg=card_bg)
    r6.pack(fill=tk.X, pady=3)
    tk.Label(r6, text="Fault Detection Time:", font=("Segoe UI", 9), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_det_val = tk.Label(r6, text="0.00 s", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg=card_bg)
    lbl_det_val.pack(side=tk.RIGHT)

    # Switchover Handshake
    r7 = tk.Frame(c3, bg=card_bg)
    r7.pack(fill=tk.X, pady=3)
    tk.Label(r7, text="Reconnection Handshake:", font=("Segoe UI", 9), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_switch_val = tk.Label(r7, text="0.00 ms", font=("Segoe UI", 9, "bold"), fg="#c084fc", bg=card_bg)
    lbl_switch_val.pack(side=tk.RIGHT)

    # 4. CONTROL ACTION BAR & COMMAND PANEL
    actions_card = tk.LabelFrame(
        main_frame,
        text="  Interactive Network Controls & Testing  ",
        font=("Segoe UI", 9, "bold"),
        fg="#38bdf8",
        bg=card_bg,
        padx=10,
        pady=8,
        bd=1,
        relief="solid"
    )
    actions_card.pack(fill=tk.X, pady=(0, 10))

    # Controls Row
    btn_start = tk.Button(
        actions_card,
        text="▶ START MONITORING",
        font=("Segoe UI", 9, "bold"),
        bg="#059669",
        fg="#ffffff",
        activebackground="#047857",
        activeforeground="#ffffff",
        relief="flat",
        padx=10,
        pady=4,
        cursor="hand2",
        command=start_monitoring
    )
    btn_start.pack(side=tk.LEFT, padx=(0, 6))

    btn_stop = tk.Button(
        actions_card,
        text="⏹ STOP",
        font=("Segoe UI", 9, "bold"),
        bg="#dc2626",
        fg="#ffffff",
        activebackground="#b91c1c",
        activeforeground="#ffffff",
        relief="flat",
        padx=10,
        pady=4,
        cursor="hand2",
        state="disabled",
        command=stop_monitoring
    )
    btn_stop.pack(side=tk.LEFT, padx=(0, 6))

    btn_crash = tk.Button(
        actions_card,
        text="💥 KILL PRIMARY (TEST FAILOVER)",
        font=("Segoe UI", 9, "bold"),
        bg="#b91c1c",
        fg="#ffffff",
        activebackground="#991b1b",
        activeforeground="#ffffff",
        relief="flat",
        padx=10,
        pady=4,
        cursor="hand2",
        command=trigger_simulated_crash
    )
    btn_crash.pack(side=tk.LEFT, padx=(0, 14))

    # Separator
    tk.Label(actions_card, text="|", fg="#475569", bg=card_bg).pack(side=tk.LEFT, padx=(0, 10))

    # Test Commands
    tk.Button(
        actions_card,
        text="STATUS",
        font=("Segoe UI", 8, "bold"),
        bg="#0284c7",
        fg="#ffffff",
        relief="flat",
        padx=8,
        pady=4,
        cursor="hand2",
        command=lambda: send_gui_command("STATUS")
    ).pack(side=tk.LEFT, padx=(0, 4))

    tk.Button(
        actions_card,
        text="TIME",
        font=("Segoe UI", 8, "bold"),
        bg="#0284c7",
        fg="#ffffff",
        relief="flat",
        padx=8,
        pady=4,
        cursor="hand2",
        command=lambda: send_gui_command("TIME")
    ).pack(side=tk.LEFT, padx=(0, 10))

    # Message input
    tk.Label(actions_card, text="Payload:", font=("Segoe UI", 8), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT, padx=(0, 4))
    entry_message = tk.Entry(actions_card, font=("Segoe UI", 9), bg="#0f172a", fg="#f8fafc", insertbackground="#ffffff", relief="solid", bd=1, width=22)
    entry_message.pack(side=tk.LEFT, padx=(0, 6))
    entry_message.insert(0, "Test Packet")

    tk.Button(
        actions_card,
        text="SEND",
        font=("Segoe UI", 8, "bold"),
        bg="#7c3aed",
        fg="#ffffff",
        relief="flat",
        padx=8,
        pady=4,
        cursor="hand2",
        command=on_send_message
    ).pack(side=tk.LEFT)

    entry_message.bind("<Return>", lambda e: on_send_message())

    # Clear Log Button
    tk.Button(
        actions_card,
        text="CLEAR LOG",
        font=("Segoe UI", 8),
        bg="#334155",
        fg="#cbd5e1",
        relief="flat",
        padx=8,
        pady=4,
        cursor="hand2",
        command=clear_log
    ).pack(side=tk.RIGHT)

    # 5. REAL-TIME EVENT LOG
    log_card = tk.LabelFrame(
        main_frame,
        text="  Real-Time Socket Event Log  ",
        font=("Segoe UI", 9, "bold"),
        fg="#38bdf8",
        bg=card_bg,
        padx=8,
        pady=6,
        bd=1,
        relief="solid"
    )
    log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    txt_event_log = scrolledtext.ScrolledText(
        log_card,
        wrap=tk.WORD,
        font=("Consolas", 9),
        bg="#090d16",
        fg="#e2e8f0",
        insertbackground="#38bdf8",
        bd=0,
        padx=8,
        pady=8
    )
    txt_event_log.pack(fill=tk.BOTH, expand=True)

    # Syntax Highlighting Tags
    txt_event_log.tag_config("INFO", foreground="#94a3b8")
    txt_event_log.tag_config("PING", foreground="#38bdf8")
    txt_event_log.tag_config("SUCCESS", foreground="#34d399")
    txt_event_log.tag_config("WARN", foreground="#fbbf24")
    txt_event_log.tag_config("FAIL", foreground="#f87171")
    txt_event_log.tag_config("FAILOVER", foreground="#c084fc")
    txt_event_log.tag_config("CMD", foreground="#67e8f9")

    # 6. BOTTOM TELEMETRY STATUS BAR
    bar = tk.Frame(main_frame, bg=card_bg, padx=12, pady=4, highlightthickness=1, highlightbackground=border_color)
    bar.pack(fill=tk.X)

    tk.Label(bar, text="Pings Sent:", font=("Segoe UI", 8), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_stat_pings = tk.Label(bar, text="0", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg=card_bg)
    lbl_stat_pings.pack(side=tk.LEFT, padx=(2, 16))

    tk.Label(bar, text="Pongs Received:", font=("Segoe UI", 8), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_stat_pongs = tk.Label(bar, text="0", font=("Segoe UI", 8, "bold"), fg="#34d399", bg=card_bg)
    lbl_stat_pongs.pack(side=tk.LEFT, padx=(2, 16))

    tk.Label(bar, text="Failover Count:", font=("Segoe UI", 8), fg=text_secondary, bg=card_bg).pack(side=tk.LEFT)
    lbl_stat_failovers = tk.Label(bar, text="0", font=("Segoe UI", 8, "bold"), fg="#c084fc", bg=card_bg)
    lbl_stat_failovers.pack(side=tk.LEFT, padx=(2, 16))

    tk.Label(bar, text="Protocol: TCP (SOCK_STREAM) | Interval: 2.0s | Max Miss: 3", font=("Segoe UI", 8), fg="#64748b", bg=card_bg).pack(side=tk.RIGHT)

    # Initial Log Messages
    add_log("NetFailover High-Availability NOC Dashboard initialized.", "INFO")
    add_log(f"Primary Server target : {SERVER_IP}:{SERVER_PORT}", "INFO")
    add_log(f"Backup Server target  : {BACKUP_SERVER_IP}:{BACKUP_SERVER_PORT}", "INFO")
    add_log("Click '▶ START MONITORING' to initiate TCP handshake and heartbeat loop.", "INFO")

    draw_topology()
    return root


if __name__ == "__main__":
    app = create_dashboard()
    app.mainloop()