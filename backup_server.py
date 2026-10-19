"""
NetFailover - Backup Server
Computer Networks Fault Detection & Automatic Failover System

Runs on TCP port 5001 in STANDBY mode during normal operation.
Becomes ACTIVE when client failover is triggered after Primary failure.
"""

import socket
from datetime import datetime

# Import configuration with safe fallback
try:
    from config import SERVER_IP, BACKUP_PORT, BUFFER_SIZE
    HOST = SERVER_IP
    PORT = BACKUP_PORT
except ImportError:
    HOST = "127.0.0.1"
    PORT = 5001
    BUFFER_SIZE = 1024


def start_backup_server():
    """Starts the Backup Server socket listener."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print("==================================================")
        print("            NETFAILOVER BACKUP SERVER             ")
        print("==================================================")
        print(f"[*] Backup Server listening on {HOST}:{PORT}")
        print("[*] Status: STANDBY (Ready to accept failover traffic)")
        print("==================================================\n")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"\n[FAILOVER CONNECTED] Client connected from {client_address}")
                print("[ACTIVE] Backup Server is now actively serving the client.")

                while True:
                    data = client_socket.recv(BUFFER_SIZE).decode("utf-8").strip()

                    if not data:
                        print(f"[DISCONNECTED] Client {client_address} closed connection.")
                        break

                    print(f"[RECEIVED] Command from client: {data}")

                    if data == "PING":
                        response = "PONG"
                    elif data == "STATUS":
                        response = "Backup Server is ONLINE (Active Failover Node)"
                    elif data == "TIME":
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        response = f"Current Backup Server Time: {current_time}"
                    elif data.startswith("MESSAGE "):
                        message_text = data[8:]
                        response = f"Received message on Backup: {message_text}"
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
        print("\n[STOPPED] Backup server stopped by user (Ctrl+C).")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    finally:
        server_socket.close()
        print("[STOPPED] Backup server listening socket closed.")


if __name__ == "__main__":
    start_backup_server()