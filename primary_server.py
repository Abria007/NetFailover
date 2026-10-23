"""
NetFailover - Primary Server
Computer Networks Fault Detection & Automatic Failover System

Listens on TCP port 5000, responds to heartbeat probes (PING -> PONG),
and provides basic network services (STATUS, TIME, MESSAGE).
"""

import socket
from datetime import datetime

# Import configuration with safe fallback
try:
    from config import SERVER_IP, PRIMARY_PORT, BUFFER_SIZE
    HOST = SERVER_IP
    PORT = PRIMARY_PORT
except ImportError:
    HOST = "127.0.0.1"
    PORT = 5000
    BUFFER_SIZE = 1024


def start_primary_server():
    """Starts the Primary Server socket listener."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print("==================================================")
        print("           NETFAILOVER PRIMARY SERVER             ")
        print("==================================================")
        print(f"[*] Primary Server listening on {HOST}:{PORT}")
        print("[*] Press Ctrl+C in this terminal to simulate Primary Server failure.")
        print("==================================================\n")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"[CONNECTED] Client connected from {client_address}")

                while True:
                    data = client_socket.recv(BUFFER_SIZE).decode("utf-8").strip()

                    if not data:
                        print(f"[DISCONNECTED] Client {client_address} closed connection.")
                        break

                    print(f"[RECEIVED] Command from client: {data}")

                    if data == "PING":
                        response = "PONG"
                    elif data == "STATUS":
                        response = "Primary Server is ONLINE"
                    elif data == "TIME":
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        response = f"Current Server Time: {current_time}"
                    elif data.startswith("MESSAGE "):
                        message_text = data[8:]
                        response = f"Received message: {message_text}"
                    elif data in ("CRASH", "KILL"):
                        print(f"\n[SIMULATED CRASH] Crash requested by client {client_address}! Shutting down Primary Server...")
                        try:
                            client_socket.close()
                        except Exception:
                            pass
                        try:
                            server_socket.close()
                        except Exception:
                            pass
                        import os
                        os._exit(0)
                    elif data == "EXIT":
                        print(f"[EXIT] Client {client_address} sent EXIT.")
                        break
                    else:
                        response = f"Unknown command: '{data}'. Supported: STATUS, TIME, MESSAGE <text>, PING, EXIT"

                    client_socket.sendall(response.encode("utf-8"))

                client_socket.close()
                print(f"[CLOSED] Session with {client_address} closed.\n")

            except socket.error as e:
                print(f"[INFO] Socket connection reset or closed: {e}")

    except KeyboardInterrupt:
        print("\n[SIMULATED FAILURE] Primary server stopped by user (Ctrl+C).")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    finally:
        server_socket.close()
        print("[STOPPED] Primary server listening socket closed.")


if __name__ == "__main__":
    start_primary_server()