import socket
import threading
import time

# Server connection configuration
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000

# Heartbeat & Fault Detection configuration
HEARTBEAT_INTERVAL = 2       # Send PING every 2 seconds
SOCKET_TIMEOUT = 3.0         # Timeout in seconds for socket operations
MAX_MISSED_HEARTBEATS = 3    # Number of consecutive missed heartbeats to declare failure

def heartbeat_worker(client_socket, socket_lock, stop_event):
    """
    Background worker that sends periodic PING heartbeats to the server,
    measures round-trip response time, and detects server failure after
    3 consecutive missed heartbeats.
    """
    missed_heartbeats = 0
    first_failure_time = None

    while not stop_event.is_set():
        # Wait for the next heartbeat interval or until stopped
        if stop_event.wait(HEARTBEAT_INTERVAL):
            break

        # Acquire lock to ensure heartbeat and user commands do not interleave on the socket
        with socket_lock:
            probe_start = time.time()
            try:
                print("\n[HEARTBEAT] PING")
                client_socket.sendall("PING".encode("utf-8"))

                # Wait for server response (up to SOCKET_TIMEOUT)
                response = client_socket.recv(1024).decode("utf-8").strip()
                elapsed_ms = (time.time() - probe_start) * 1000

                if response == "PONG":
                    print(f"[HEARTBEAT] PONG (Response time: {elapsed_ms:.2f} ms)")
                    # Reset failure counter and timer upon a successful heartbeat
                    missed_heartbeats = 0
                    first_failure_time = None
                else:
                    print(f"[HEARTBEAT] Unexpected response: {response}")
                    missed_heartbeats += 1
                    if first_failure_time is None:
                        first_failure_time = probe_start

            except socket.timeout:
                missed_heartbeats += 1
                if first_failure_time is None:
                    first_failure_time = probe_start
                print(f"[HEARTBEAT] Timeout: No response received ({missed_heartbeats}/{MAX_MISSED_HEARTBEATS} missed).")

            except Exception as e:
                if not stop_event.is_set():
                    missed_heartbeats += 1
                    if first_failure_time is None:
                        first_failure_time = probe_start
                    print(f"[HEARTBEAT] Connection error ({missed_heartbeats}/{MAX_MISSED_HEARTBEATS} missed): {e}")

        # Declare failure only after 3 consecutive missed heartbeats
        if missed_heartbeats >= MAX_MISSED_HEARTBEATS:
            detection_time = time.time() - first_failure_time
            print("\n[FAILURE DETECTED] Primary server is not responding.")
            print(f"[FAILURE DETECTED] Approximate failure detection time: {detection_time:.2f} seconds.")
            break

def start_client():
    # 1. Create a TCP/IP socket (AF_INET = IPv4, SOCK_STREAM = TCP)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Set socket timeout for detecting unresponsive server / missed heartbeats
    client_socket.settimeout(SOCKET_TIMEOUT)

    # Lock and Event for thread-safe socket access and graceful shutdown
    socket_lock = threading.Lock()
    stop_event = threading.Event()

    try:
        # 2. Connect to the server using its IP address and port number
        client_socket.connect((SERVER_IP, SERVER_PORT))
        print(f"[CONNECTED] Successfully connected to server at {SERVER_IP}:{SERVER_PORT}")
        print("Available commands: STATUS | TIME | MESSAGE <text> | EXIT")

        # 3. Start background heartbeat thread (daemon=True so it terminates on program exit)
        heartbeat_thread = threading.Thread(
            target=heartbeat_worker,
            args=(client_socket, socket_lock, stop_event),
            daemon=True
        )
        heartbeat_thread.start()

        # 4. Interactive loop to accept and send user commands
        while True:
            command = input("Enter command: ").strip()

            # Ignore empty input and prompt again
            if not command:
                continue

            with socket_lock:
                # Send the entered command to the server
                client_socket.sendall(command.encode("utf-8"))

                # If user enters EXIT, break the loop to close the session
                if command.upper() == "EXIT":
                    print("[EXIT] Exiting client session...")
                    break

                # Receive the server's reply (buffer size of 1024 bytes)
                response = client_socket.recv(1024).decode("utf-8").strip()
                if not response:
                    print("[DISCONNECTED] Server closed the connection.")
                    break

                print(f"[RECEIVED] Server response: {response}")

    except socket.timeout:
        print("[ERROR] Connection timed out waiting for server response.")
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

    finally:
        # 5. Stop the heartbeat worker and clean up the socket connection
        stop_event.set()
        client_socket.close()
        print("[CLOSED] Socket connection closed.")

if __name__ == "__main__":
    start_client()
