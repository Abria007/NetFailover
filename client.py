import socket
import threading
import time

# Primary Server connection configuration
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000

# Backup Server connection configuration
BACKUP_SERVER_IP = "127.0.0.1"
BACKUP_SERVER_PORT = 5001

# Heartbeat & Fault Detection configuration
HEARTBEAT_INTERVAL = 2       # Send PING every 2 seconds
SOCKET_TIMEOUT = 3.0         # Timeout in seconds for socket operations
MAX_MISSED_HEARTBEATS = 3    # Consecutive missed heartbeats before declaring failure

def heartbeat_worker(conn, socket_lock, stop_event):
    """
    Background worker that sends periodic PING heartbeats to the active server,
    measures round-trip response time, and triggers automatic failover to the
    Backup Server after 3 consecutive missed heartbeats from the Primary Server.
    """
    missed_heartbeats = 0
    first_failure_time = None

    while not stop_event.is_set():
        # Wait for the next heartbeat interval or until stopped
        if stop_event.wait(HEARTBEAT_INTERVAL):
            break

        # Acquire lock so heartbeat and user commands do not collide on the socket
        with socket_lock:
            if not conn["alive"] or conn["socket"] is None:
                break

            current_server = conn["server"]
            current_socket = conn["socket"]
            probe_start = time.time()

            try:
                print(f"\n[HEARTBEAT] PING -> {current_server}")
                current_socket.sendall("PING".encode("utf-8"))

                # Wait for server response (up to SOCKET_TIMEOUT)
                response = current_socket.recv(1024).decode("utf-8").strip()
                elapsed_ms = (time.time() - probe_start) * 1000

                if response == "PONG":
                    print(f"[HEARTBEAT] PONG <- {current_server} (Response time: {elapsed_ms:.2f} ms)")
                    # Reset failure counter and timer upon a successful heartbeat
                    missed_heartbeats = 0
                    first_failure_time = None
                else:
                    print(f"[HEARTBEAT] Unexpected response from {current_server}: {response}")
                    missed_heartbeats += 1
                    if first_failure_time is None:
                        first_failure_time = probe_start

            except socket.timeout:
                missed_heartbeats += 1
                if first_failure_time is None:
                    first_failure_time = probe_start
                print(f"[HEARTBEAT] Timeout: No response from {current_server} ({missed_heartbeats}/{MAX_MISSED_HEARTBEATS} missed).")

            except Exception as e:
                if not stop_event.is_set():
                    missed_heartbeats += 1
                    if first_failure_time is None:
                        first_failure_time = probe_start
                    print(f"[HEARTBEAT] Connection error from {current_server} ({missed_heartbeats}/{MAX_MISSED_HEARTBEATS} missed): {e}")

            # Trigger automatic failover after 3 consecutive missed heartbeats
            if missed_heartbeats >= MAX_MISSED_HEARTBEATS:
                detection_time = time.time() - first_failure_time
                print("\n[FAILURE DETECTED] Primary server is not responding.")
                print(f"[FAILURE DETECTED] Approximate failure detection time: {detection_time:.2f} seconds.")

                if current_server == "PRIMARY":
                    print("[FAILOVER] Attempting connection to Backup Server...")
                    # 1. Close failed Primary connection
                    try:
                        current_socket.close()
                    except Exception:
                        pass

                    # 2. Attempt connection to Backup Server
                    try:
                        backup_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        backup_socket.settimeout(SOCKET_TIMEOUT)
                        backup_socket.connect((BACKUP_SERVER_IP, BACKUP_SERVER_PORT))

                        # 3. Update connection state and active server
                        conn["socket"] = backup_socket
                        conn["server"] = "BACKUP"

                        # 4. Reset heartbeat metrics for the Backup Server
                        missed_heartbeats = 0
                        first_failure_time = None

                        print(f"[FAILOVER] Connected to Backup Server at {BACKUP_SERVER_IP}:{BACKUP_SERVER_PORT}")
                        print("[FAILOVER] Client successfully switched to Backup Server.")

                    except Exception as e:
                        print(f"[FAILOVER] Could not connect to Backup Server at {BACKUP_SERVER_IP}:{BACKUP_SERVER_PORT} ({e}).")
                        conn["alive"] = False
                        stop_event.set()
                        break
                else:
                    # If Backup Server also fails, stop heartbeat loop
                    print(f"[ERROR] Backup server is not responding.")
                    break

def start_client():
    # 1. Create a TCP/IP socket (AF_INET = IPv4, SOCK_STREAM = TCP)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(SOCKET_TIMEOUT)

    # Thread synchronization primitives
    socket_lock = threading.Lock()
    stop_event = threading.Event()

    # Shared connection state
    conn = {
        "socket": client_socket,
        "server": "PRIMARY",
        "alive": True
    }

    try:
        # 2. Connect initially to the Primary Server
        client_socket.connect((SERVER_IP, SERVER_PORT))
        print(f"[CONNECTED] Successfully connected to server at {SERVER_IP}:{SERVER_PORT}")
        print("Available commands: STATUS | TIME | MESSAGE <text> | EXIT")

        # 3. Start background heartbeat thread
        heartbeat_thread = threading.Thread(
            target=heartbeat_worker,
            args=(conn, socket_lock, stop_event),
            daemon=True
        )
        heartbeat_thread.start()

        # 4. Interactive loop to accept and send user commands
        while not stop_event.is_set():
            try:
                command = input("Enter command: ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            # Ignore empty input and prompt again
            if not command:
                continue

            with socket_lock:
                if not conn["alive"] or conn["socket"] is None:
                    print("[ERROR] No active server connection available.")
                    break

                active_socket = conn["socket"]
                active_server = conn["server"]

                try:
                    # Send the entered command to the active server
                    active_socket.sendall(command.encode("utf-8"))

                    # If user enters EXIT, break the loop to close session
                    if command.upper() == "EXIT":
                        print("[EXIT] Exiting client session...")
                        break

                    # Receive response from active server (buffer size 1024 bytes)
                    response = active_socket.recv(1024).decode("utf-8").strip()
                    if not response:
                        print(f"[DISCONNECTED] {active_server} server closed the connection.")
                        break

                    print(f"[RECEIVED] Server response: {response}")

                except socket.timeout:
                    print(f"[ERROR] Connection timed out waiting for response from {active_server} server.")
                except Exception as e:
                    print(f"[ERROR] Communication error with {active_server} server: {e}")

    except socket.timeout:
        print("[ERROR] Connection timed out while connecting to Primary Server.")
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

    finally:
        # 5. Clean up background thread and close whichever socket is active
        stop_event.set()
        with socket_lock:
            conn["alive"] = False
            if conn["socket"]:
                try:
                    conn["socket"].close()
                except Exception:
                    pass
        print("[CLOSED] Socket connection closed.")

if __name__ == "__main__":
    start_client()
