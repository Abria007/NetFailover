import socket
import threading
import time

# Server connection configuration
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000

# Heartbeat configuration
HEARTBEAT_INTERVAL = 2    # Send PING every 2 seconds
SOCKET_TIMEOUT = 3.0      # Timeout in seconds for socket operations

def heartbeat_worker(client_socket, socket_lock, stop_event):
    """
    Background worker that sends periodic PING heartbeats to the server
    and measures the round-trip response time.
    """
    while not stop_event.is_set():
        # Wait for the next heartbeat interval or until stopped
        if stop_event.wait(HEARTBEAT_INTERVAL):
            break

        # Acquire lock to ensure heartbeat and user commands do not interleave on the socket
        with socket_lock:
            try:
                print("\n[HEARTBEAT] PING")
                start_time = time.time()
                client_socket.sendall("PING".encode("utf-8"))

                # Wait for server response (up to SOCKET_TIMEOUT)
                response = client_socket.recv(1024).decode("utf-8").strip()
                elapsed_ms = (time.time() - start_time) * 1000

                if response == "PONG":
                    print(f"[HEARTBEAT] PONG (Response time: {elapsed_ms:.2f} ms)")
                else:
                    print(f"[HEARTBEAT] Unexpected response: {response}")

            except socket.timeout:
                print("[HEARTBEAT] Timeout: No PONG response received from server within 3 seconds.")
            except Exception as e:
                if not stop_event.is_set():
                    print(f"[HEARTBEAT] Connection error: {e}")
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
