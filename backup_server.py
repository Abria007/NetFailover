import socket
from datetime import datetime

# Backup Server host and port configuration
HOST = "127.0.0.1"
PORT = 5001

def start_backup_server():
    # 1. Socket Creation: Create an IPv4 (AF_INET), TCP (SOCK_STREAM) socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Enable port reuse so the server can be restarted immediately without waiting for timeout
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # 2. Bind: Associate the socket with the IP address and port number 5001
        server_socket.bind((HOST, PORT))

        # 3. Listen: Put the socket into listening mode to queue incoming connection requests
        server_socket.listen(1)
        print(f"[BACKUP SERVER] Listening on {HOST}:{PORT}...")

        # 4. Accept: Wait for an incoming client connection (blocks until a client connects)
        client_socket, client_address = server_socket.accept()
        print(f"[CONNECTED] Client connected from {client_address}")

        # Loop to process multiple commands from the connected client
        while True:
            # 5. Recv: Receive data from the client (up to 1024 bytes at a time)
            data = client_socket.recv(1024).decode("utf-8").strip()

            # If the client closes the connection or sends empty data
            if not data:
                print(f"[DISCONNECTED] Client {client_address} closed connection.")
                break

            print(f"[RECEIVED] Command from client: {data}")

            # Process supported commands
            if data == "PING":
                response = "PONG"
            elif data == "STATUS":
                response = "Backup Server is ONLINE"
            elif data == "TIME":
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                response = f"Current Server Time: {current_time}"
            elif data.startswith("MESSAGE "):
                # Extract the text after 'MESSAGE '
                message_text = data[8:]
                response = f"Received message: {message_text}"
            elif data == "EXIT":
                print(f"[EXIT] Client {client_address} sent EXIT. Closing connection.")
                break
            else:
                response = f"Unknown command: '{data}'. Supported commands: STATUS, TIME, MESSAGE <text>, PING, EXIT"

            # 6. Sendall: Send the response bytes back to the client
            client_socket.sendall(response.encode("utf-8"))

        # Close the connection with this specific client
        client_socket.close()
        print(f"[CLOSED] Connection with {client_address} closed.")

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

    finally:
        # Close the listening server socket
        server_socket.close()
        print("[STOPPED] Backup server shut down.")

if __name__ == "__main__":
    start_backup_server()
