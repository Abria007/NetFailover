"""
NetFailover - GUI Dashboard
Computer Networks Fault Detection & Automatic Failover Simulation

This module provides a Tkinter-based dashboard for monitoring and demonstrating
the NetFailover system:
- Connection Status (Primary & Backup servers)
- Heartbeat Monitor (Status, latency, missed heartbeat counter)
- Failover Information (Active server, detection time, failover status)
- Event Log (Timestamped system events)
- Interactive Demonstration controls
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

# Global references for dashboard widgets and state
root = None
lbl_primary_status = None
lbl_backup_status = None
lbl_active_server = None
lbl_heartbeat_status = None
lbl_response_time = None
lbl_missed_count = None
lbl_failover_status = None
lbl_detection_time = None
canvas_primary_dot = None
canvas_backup_dot = None
txt_event_log = None

# Monitoring state flag
is_monitoring = False
demo_job = None

def get_current_timestamp():
    """Returns formatted current timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def add_log(message):
    """
    Appends a timestamped message to the scrolling Event Log area.
    """
    if txt_event_log is not None:
        timestamp = get_current_timestamp()
        log_entry = f"[{timestamp}] {message}\n"
        txt_event_log.configure(state="normal")
        txt_event_log.insert(tk.END, log_entry)
        txt_event_log.see(tk.END)
        txt_event_log.configure(state="disabled")

def clear_log():
    """
    Clears all messages from the Event Log area.
    """
    if txt_event_log is not None:
        txt_event_log.configure(state="normal")
        txt_event_log.delete("1.0", tk.END)
        txt_event_log.configure(state="disabled")
        add_log("Event log cleared.")

def draw_status_dot(canvas, color):
    """Draws a clean colored status indicator circle on a Tkinter Canvas."""
    canvas.delete("all")
    canvas.create_oval(3, 3, 15, 15, fill=color, outline=color)

def update_primary_status(status):
    """
    Updates the Primary Server status label and visual indicator.
    Accepts: 'ONLINE', 'OFFLINE', 'TIMEOUT'
    """
    global lbl_primary_status, canvas_primary_dot
    color_map = {
        "ONLINE": "#2e7d32",   # Green
        "OFFLINE": "#d32f2f",  # Red
        "TIMEOUT": "#ed6c02"   # Orange
    }
    color = color_map.get(status, "#757575")
    if lbl_primary_status:
        lbl_primary_status.config(text=status, foreground=color)
    if canvas_primary_dot:
        draw_status_dot(canvas_primary_dot, color)

def update_backup_status(status):
    """
    Updates the Backup Server status label and visual indicator.
    Accepts: 'STANDBY', 'ONLINE', 'OFFLINE'
    """
    global lbl_backup_status, canvas_backup_dot
    color_map = {
        "ONLINE": "#2e7d32",   # Green (Active)
        "STANDBY": "#0288d1",  # Blue (Ready in standby)
        "OFFLINE": "#d32f2f"   # Red
    }
    color = color_map.get(status, "#757575")
    if lbl_backup_status:
        lbl_backup_status.config(text=status, foreground=color)
    if canvas_backup_dot:
        draw_status_dot(canvas_backup_dot, color)

def update_active_server(server_name):
    """
    Updates the Active Server label display.
    Accepts: 'PRIMARY' or 'BACKUP'
    """
    global lbl_active_server
    color = "#1565c0" if server_name == "PRIMARY" else "#6a1b9a"
    if lbl_active_server:
        lbl_active_server.config(text=server_name, foreground=color)

def simulate_normal():
    """
    Demonstration Mode: Simulates normal healthy operation.
    - Primary Server = ONLINE
    - Backup Server  = STANDBY
    - Active Server  = PRIMARY
    - Heartbeat      = CONNECTED
    - Failover       = NOT REQUIRED
    """
    update_primary_status("ONLINE")
    update_backup_status("STANDBY")
    update_active_server("PRIMARY")

    lbl_heartbeat_status.config(text="CONNECTED", foreground="#2e7d32")
    lbl_response_time.config(text="1.15 ms")
    lbl_missed_count.config(text="0 / 3", foreground="#2e7d32")

    lbl_failover_status.config(text="NOT REQUIRED", foreground="#2e7d32")
    lbl_detection_time.config(text="0.00 s")

    add_log("[DEMO] State set to NORMAL: Primary server ONLINE, Backup server STANDBY.")

def simulate_failover():
    """
    Demonstration Mode: Simulates primary failure and automatic failover.
    - Primary Server = OFFLINE
    - Backup Server  = ONLINE
    - Active Server  = BACKUP
    - Heartbeat      = CONNECTED (to Backup)
    - Failover       = COMPLETED
    """
    update_primary_status("OFFLINE")
    update_backup_status("ONLINE")
    update_active_server("BACKUP")

    lbl_heartbeat_status.config(text="CONNECTED (to Backup)", foreground="#2e7d32")
    lbl_response_time.config(text="1.28 ms")
    lbl_missed_count.config(text="0 / 3", foreground="#2e7d32")

    lbl_failover_status.config(text="COMPLETED (Switched to Backup)", foreground="#6a1b9a")
    lbl_detection_time.config(text="4.02 s")

    add_log("[DEMO] Simulated failure: Primary heartbeat timed out (3 missed).")
    add_log("[DEMO] Automatic failover triggered! Active server switched to BACKUP (127.0.0.1:5001).")

def start_monitoring():
    """Starts simulated monitoring loop for demonstration."""
    global is_monitoring, demo_job
    if is_monitoring:
        return
    is_monitoring = True
    add_log("[MONITOR] Heartbeat monitoring started (Interval: 2.0s).")

    def heartbeat_tick():
        global demo_job
        if not is_monitoring:
            return
        # Subtle simulation log
        active = lbl_active_server.cget("text")
        add_log(f"[HEARTBEAT] PING -> {active} | PONG received (Response time: 1.20 ms)")
        demo_job = root.after(2000, heartbeat_tick)

    demo_job = root.after(2000, heartbeat_tick)

def stop_monitoring():
    """Stops simulated monitoring loop."""
    global is_monitoring, demo_job
    if not is_monitoring:
        return
    is_monitoring = False
    if demo_job:
        root.after_cancel(demo_job)
        demo_job = None
    add_log("[MONITOR] Heartbeat monitoring stopped.")

def create_dashboard():
    """
    Constructs the main dashboard window, layout, and widgets using Tkinter.
    """
    global root
    global lbl_primary_status, lbl_backup_status, lbl_active_server
    global lbl_heartbeat_status, lbl_response_time, lbl_missed_count
    global lbl_failover_status, lbl_detection_time
    global canvas_primary_dot, canvas_backup_dot, txt_event_log

    root = tk.Tk()
    root.title("NetFailover - Network Fault Detection & Automatic Failover")
    root.geometry("900x600")
    root.minsize(850, 550)

    # Style configuration
    style = ttk.Style()
    style.theme_use("clam")

    # Background color configuration
    bg_main = "#f4f6f9"
    card_bg = "#ffffff"
    root.configure(bg=bg_main)

    # Main Container Frame
    main_frame = tk.Frame(root, bg=bg_main, padx=16, pady=12)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # ==========================================
    # HEADER SECTION
    # ==========================================
    header_frame = tk.Frame(main_frame, bg="#1a237e", padx=16, pady=12)
    header_frame.pack(fill=tk.X, pady=(0, 12))

    lbl_title = tk.Label(
        header_frame,
        text="NetFailover - Network Fault Detection & Automatic Failover",
        font=("Segoe UI", 16, "bold"),
        fg="#ffffff",
        bg="#1a237e"
    )
    lbl_title.pack(anchor="w")

    lbl_subtitle = tk.Label(
        header_frame,
        text="Computer Networks Laboratory Project • Socket Programming & High Availability Simulation",
        font=("Segoe UI", 9),
        fg="#c5cae9",
        bg="#1a237e"
    )
    lbl_subtitle.pack(anchor="w")

    # ==========================================
    # CARDS GRID (A, B, C)
    # ==========================================
    cards_frame = tk.Frame(main_frame, bg=bg_main)
    cards_frame.pack(fill=tk.X, pady=(0, 10))
    cards_frame.columnconfigure(0, weight=1)
    cards_frame.columnconfigure(1, weight=1)
    cards_frame.columnconfigure(2, weight=1)

    # Helper function to create clean card frames
    def make_card(parent, title_text, col):
        card = tk.LabelFrame(
            parent,
            text=f"  {title_text}  ",
            font=("Segoe UI", 10, "bold"),
            fg="#1a237e",
            bg=card_bg,
            padx=12,
            pady=10,
            relief="solid",
            bd=1
        )
        card.grid(row=0, column=col, sticky="nsew", padx=6)
        return card

    # --- CARD A: CONNECTION STATUS ---
    card_a = make_card(cards_frame, "A. Connection Status", 0)

    # Primary Row
    row_prim = tk.Frame(card_a, bg=card_bg)
    row_prim.pack(fill=tk.X, pady=3)
    tk.Label(row_prim, text="Primary Server (5000):", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    lbl_primary_status = tk.Label(row_prim, text="ONLINE", font=("Segoe UI", 9, "bold"), fg="#2e7d32", bg=card_bg)
    lbl_primary_status.pack(side=tk.RIGHT)
    canvas_primary_dot = tk.Canvas(row_prim, width=18, height=18, bg=card_bg, highlightthickness=0)
    canvas_primary_dot.pack(side=tk.RIGHT, padx=4)
    draw_status_dot(canvas_primary_dot, "#2e7d32")

    # Backup Row
    row_back = tk.Frame(card_a, bg=card_bg)
    row_back.pack(fill=tk.X, pady=3)
    tk.Label(row_back, text="Backup Server (5001):", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    lbl_backup_status = tk.Label(row_back, text="STANDBY", font=("Segoe UI", 9, "bold"), fg="#0288d1", bg=card_bg)
    lbl_backup_status.pack(side=tk.RIGHT)
    canvas_backup_dot = tk.Canvas(row_back, width=18, height=18, bg=card_bg, highlightthickness=0)
    canvas_backup_dot.pack(side=tk.RIGHT, padx=4)
    draw_status_dot(canvas_backup_dot, "#0288d1")

    # Active Server Row
    row_active = tk.Frame(card_a, bg=card_bg)
    row_active.pack(fill=tk.X, pady=3)
    tk.Label(row_active, text="Current Active Server:", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    lbl_active_server = tk.Label(row_active, text="PRIMARY", font=("Segoe UI", 9, "bold"), fg="#1565c0", bg=card_bg)
    lbl_active_server.pack(side=tk.RIGHT)

    # --- CARD B: HEARTBEAT MONITOR ---
    card_b = make_card(cards_frame, "B. Heartbeat Monitor", 1)

    # Heartbeat Status
    row_hb_status = tk.Frame(card_b, bg=card_bg)
    row_hb_status.pack(fill=tk.X, pady=3)
    tk.Label(row_hb_status, text="Heartbeat Status:", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    lbl_heartbeat_status = tk.Label(row_hb_status, text="CONNECTED", font=("Segoe UI", 9, "bold"), fg="#2e7d32", bg=card_bg)
    lbl_heartbeat_status.pack(side=tk.RIGHT)

    # Response Time
    row_rtt = tk.Frame(card_b, bg=card_bg)
    row_rtt.pack(fill=tk.X, pady=3)
    tk.Label(row_rtt, text="Response Time (RTT):", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    lbl_response_time = tk.Label(row_rtt, text="1.15 ms", font=("Segoe UI", 9, "bold"), fg="#37474f", bg=card_bg)
    lbl_response_time.pack(side=tk.RIGHT)

    # Missed Heartbeat Count
    row_missed = tk.Frame(card_b, bg=card_bg)
    row_missed.pack(fill=tk.X, pady=3)
    tk.Label(row_missed, text="Missed Heartbeats:", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    lbl_missed_count = tk.Label(row_missed, text="0 / 3", font=("Segoe UI", 9, "bold"), fg="#2e7d32", bg=card_bg)
    lbl_missed_count.pack(side=tk.RIGHT)

    # --- CARD C: FAILOVER INFORMATION ---
    card_c = make_card(cards_frame, "C. Failover Information", 2)

    # Detection Time
    row_det_time = tk.Frame(card_c, bg=card_bg)
    row_det_time.pack(fill=tk.X, pady=3)
    tk.Label(row_det_time, text="Failure Detection Time:", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    lbl_detection_time = tk.Label(row_det_time, text="0.00 s", font=("Segoe UI", 9, "bold"), fg="#37474f", bg=card_bg)
    lbl_detection_time.pack(side=tk.RIGHT)

    # Failover Status
    row_failover = tk.Frame(card_c, bg=card_bg)
    row_failover.pack(fill=tk.X, pady=3)
    tk.Label(row_failover, text="Failover Status:", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    lbl_failover_status = tk.Label(row_failover, text="NOT REQUIRED", font=("Segoe UI", 9, "bold"), fg="#2e7d32", bg=card_bg)
    lbl_failover_status.pack(side=tk.RIGHT)

    # Protocol summary
    row_proto = tk.Frame(card_c, bg=card_bg)
    row_proto.pack(fill=tk.X, pady=3)
    tk.Label(row_proto, text="Failover Trigger:", font=("Segoe UI", 9), bg=card_bg).pack(side=tk.LEFT)
    tk.Label(row_proto, text="3 Missed PONGs", font=("Segoe UI", 9), fg="#616161", bg=card_bg).pack(side=tk.RIGHT)

    # ==========================================
    # ACTION & DEMO BUTTONS BAR
    # ==========================================
    btn_bar = tk.Frame(main_frame, bg=bg_main)
    btn_bar.pack(fill=tk.X, pady=(0, 10))

    btn_start = tk.Button(
        btn_bar,
        text="▶ START MONITORING",
        font=("Segoe UI", 9, "bold"),
        bg="#2e7d32",
        fg="#ffffff",
        activebackground="#1b5e20",
        activeforeground="#ffffff",
        padx=12,
        pady=5,
        relief="flat",
        cursor="hand2",
        command=start_monitoring
    )
    btn_start.pack(side=tk.LEFT, padx=(0, 6))

    btn_stop = tk.Button(
        btn_bar,
        text="⏹ STOP MONITORING",
        font=("Segoe UI", 9, "bold"),
        bg="#c62828",
        fg="#ffffff",
        activebackground="#b71c1c",
        activeforeground="#ffffff",
        padx=12,
        pady=5,
        relief="flat",
        cursor="hand2",
        command=stop_monitoring
    )
    btn_stop.pack(side=tk.LEFT, padx=(0, 12))

    # Demo Simulation Buttons
    btn_sim_normal = tk.Button(
        btn_bar,
        text="✔ SIMULATE NORMAL",
        font=("Segoe UI", 9),
        bg="#e0e0e0",
        fg="#212121",
        padx=10,
        pady=5,
        relief="groove",
        cursor="hand2",
        command=simulate_normal
    )
    btn_sim_normal.pack(side=tk.LEFT, padx=(0, 6))

    btn_sim_failover = tk.Button(
        btn_bar,
        text="⚡ SIMULATE FAILOVER",
        font=("Segoe UI", 9),
        bg="#fff3e0",
        fg="#e65100",
        padx=10,
        pady=5,
        relief="groove",
        cursor="hand2",
        command=simulate_failover
    )
    btn_sim_failover.pack(side=tk.LEFT, padx=(0, 6))

    btn_clear = tk.Button(
        btn_bar,
        text="🗑 CLEAR LOG",
        font=("Segoe UI", 9),
        bg="#eeeeee",
        fg="#424242",
        padx=10,
        pady=5,
        relief="groove",
        cursor="hand2",
        command=clear_log
    )
    btn_clear.pack(side=tk.RIGHT)

    # ==========================================
    # CARD D: EVENT LOG
    # ==========================================
    log_card = tk.LabelFrame(
        main_frame,
        text="  D. Event Log  ",
        font=("Segoe UI", 10, "bold"),
        fg="#1a237e",
        bg=card_bg,
        padx=8,
        pady=8,
        relief="solid",
        bd=1
    )
    log_card.pack(fill=tk.BOTH, expand=True)

    txt_event_log = scrolledtext.ScrolledText(
        log_card,
        wrap=tk.WORD,
        font=("Consolas", 9),
        bg="#1e1e1e",
        fg="#d4d4d4",
        insertbackground="#ffffff",
        bd=0,
        padx=8,
        pady=8
    )
    txt_event_log.pack(fill=tk.BOTH, expand=True)

    # Initial boot log entries
    add_log("NetFailover Dashboard initialized.")
    add_log("Primary Server configured at 127.0.0.1:5000 (ONLINE).")
    add_log("Backup Server configured at 127.0.0.1:5001 (STANDBY).")
    add_log("Heartbeat mechanism ready: PING/PONG interval = 2s, timeout = 3s, threshold = 3 misses.")

    return root

if __name__ == "__main__":
    app = create_dashboard()
    app.mainloop()
