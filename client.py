import socket

# Server connection configuration
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000

def start_client():
    # 1. Create a TCP/IP socket (AF_INET = IPv4, SOCK_STREAM = TCP)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # 2. Connect to the server using its IP address and port number
        client_socket.connect((SERVER_IP, SERVER_PORT))
        print(f"[CONNECTED] Successfully connected to server at {SERVER_IP}:{SERVER_PORT}")

        # 3. Prepare and send the message (encoded from string to bytes)
        message = "HELLO"
        print(f"[SENDING] Sending message: {message}")
        client_socket.sendall(message.encode("utf-8"))

        # 4. Receive the server's reply (buffer size of 1024 bytes)
        response = client_socket.recv(1024).decode("utf-8")
        print(f"[RECEIVED] Server response: {response}")

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

    finally:
        # 5. Clean up and close the socket connection
        client_socket.close()
        print("[CLOSED] Socket connection closed.")

if __name__ == "__main__":
    start_client()
