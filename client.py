"""
NetFailover - Client Networking Engine & CLI
Computer Networks Fault Detection & Automatic Failover System

Implements the NetFailoverClient class with:
- TCP connection management
- Thread-safe background heartbeat probing (PING/PONG)
- Round-trip time (RTT) latency measurement
- Missed heartbeat tracking (threshold = 3)
- Automatic failover reconnection to Backup Server
- Detection time and failover duration measurement
- Event notification callback mechanism for UI integration
- Standalone CLI interactive loop
"""

import socket
import threading
import time

# Import configuration with safe fallback
try:
    from config import (
        SERVER_IP,
        PRIMARY_PORT,
        BACKUP_PORT,
        HEARTBEAT_INTERVAL,
        SOCKET_TIMEOUT,
        MAX_MISSED_HEARTBEATS,
        BUFFER_SIZE,
    )
    SERVER_PORT = PRIMARY_PORT
    BACKUP_SERVER_IP = SERVER_IP
    BACKUP_SERVER_PORT = BACKUP_PORT
except ImportError:
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 5000
    BACKUP_SERVER_IP = "127.0.0.1"
    BACKUP_SERVER_PORT = 5001
    HEARTBEAT_INTERVAL = 2
    SOCKET_TIMEOUT = 3.0
    MAX_MISSED_HEARTBEATS = 3
    BUFFER_SIZE = 1024


def display_connection_status(conn):
    """Displays a formatted status banner showing active server connection info."""
    if isinstance(conn, dict):
        server_name = conn.get("server", conn.get("active_server", "PRIMARY"))
        ip = conn.get("ip", SERVER_IP)
        port = conn.get("port", SERVER_PORT)
        status = "ONLINE" if conn.get("alive", True) else "OFFLINE"
    else:
        server_name = getattr(conn, "active_server", "PRIMARY")
        ip = getattr(conn, "active_ip", SERVER_IP)
        port = getattr(conn, "active_port", SERVER_PORT)
        status = "ONLINE" if getattr(conn, "is_connected", True) else "OFFLINE"

    print("\n================================================")
    print("           NETFAILOVER CLIENT STATUS            ")
    print("================================================")
    print(f"Active Server : {server_name}")
    print(f"Server Target : {ip}:{port}")
    print(f"Status        : {status}")
    print("================================================\n")


class NetFailoverClient:
    """
    Reusable client manager for the NetFailover system.
    Handles Primary connection, Backup failover, periodic heartbeat probing,
    timeout detection, and event notifications.
    """

    def __init__(
        self,
        primary_ip=SERVER_IP,
        primary_port=SERVER_PORT,
        backup_ip=BACKUP_SERVER_IP,
        backup_port=BACKUP_SERVER_PORT,
        heartbeat_interval=HEARTBEAT_INTERVAL,
        socket_timeout=SOCKET_TIMEOUT,
        max_missed_heartbeats=MAX_MISSED_HEARTBEATS,
        event_callback=None
    ):
        self.primary_ip = primary_ip
        self.primary_port = primary_port
        self.backup_ip = backup_ip
        self.backup_port = backup_port
        self.heartbeat_interval = heartbeat_interval
        self.socket_timeout = socket_timeout
        self.max_missed_heartbeats = max_missed_heartbeats
        self.event_callback = event_callback

        # Sockets and synchronization
        self.socket = None
        self.socket_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.heartbeat_thread = None

        # State tracking
        self.active_server = "PRIMARY"
        self.active_ip = self.primary_ip
        self.active_port = self.primary_port
        self.is_connected = False

        # Metrics
        self.missed_heartbeats = 0
        self.first_failure_time = None
        self.last_response_time = 0.0
        self.last_detection_time = 0.0
        self.failover_duration = 0.0

    def set_callback(self, callback):
        """Registers a callback function to receive networking events."""
        self.event_callback = callback

    def _notify(self, event_type, **kwargs):
        """Dispatches an event dictionary to the registered callback."""
        if self.event_callback:
            event_data = {
                "active_server": self.active_server,
                "ip": self.active_ip,
                "port": self.active_port,
                "missed_count": self.missed_heartbeats,
                "response_time": self.last_response_time,
                "detection_time": self.last_detection_time,
                "failover_duration": self.failover_duration,
            }
            event_data.update(kwargs)
            try:
                self.event_callback(event_type, event_data)
            except Exception as e:
                print(f"[CALLBACK ERROR] Error in event callback: {e}")

    def connect(self):
        """
        Connects initially to the Primary Server.
        Returns True if successful, False otherwise.
        """
        self.stop_event.clear()
        with self.socket_lock:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.socket_timeout)
                self.socket.connect((self.primary_ip, self.primary_port))

                self.active_server = "PRIMARY"
                self.active_ip = self.primary_ip
                self.active_port = self.primary_port
                self.is_connected = True
                self.missed_heartbeats = 0
                self.first_failure_time = None

                self._notify(
                    "PRIMARY_CONNECTED",
                    ip=self.primary_ip,
                    port=self.primary_port
                )
                return True

            except Exception as e:
                self.is_connected = False
                if self.socket:
                    try:
                        self.socket.close()
                    except Exception:
                        pass
                    self.socket = None

                self._notify(
                    "CONNECTION_FAILED",
                    message=f"Could not connect to Primary Server at {self.primary_ip}:{self.primary_port} ({e})"
                )
                return False

    def start_heartbeat(self):
        """Starts the background heartbeat worker thread."""
        if not self.is_connected or (self.heartbeat_thread and self.heartbeat_thread.is_alive()):
            return

        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            daemon=True
        )
        self.heartbeat_thread.start()

    def _heartbeat_worker(self):
        """
        Background worker that sends periodic PING heartbeats, measures response times,
        and triggers automatic failover if Primary Server fails.
        """
        while not self.stop_event.is_set():
            if self.stop_event.wait(self.heartbeat_interval):
                break

            with self.socket_lock:
                if not self.is_connected or self.socket is None:
                    break

                probe_start = time.time()
                current_target = self.active_server

                try:
                    self._notify("HEARTBEAT_PING", active_server=current_target)
                    self.socket.sendall("PING".encode("utf-8"))

                    response = self.socket.recv(BUFFER_SIZE).decode("utf-8").strip()
                    elapsed_ms = (time.time() - probe_start) * 1000
                    self.last_response_time = elapsed_ms

                    if response == "PONG":
                        self.missed_heartbeats = 0
                        self.first_failure_time = None
                        self._notify(
                            "HEARTBEAT_PONG",
                            active_server=current_target,
                            response_time=elapsed_ms
                        )
                    else:
                        self.missed_heartbeats += 1
                        if self.first_failure_time is None:
                            self.first_failure_time = probe_start
                        self._notify(
                            "HEARTBEAT_MISSED",
                            active_server=current_target,
                            missed_count=self.missed_heartbeats,
                            error=f"Unexpected reply: {response}"
                        )

                except socket.timeout:
                    self.missed_heartbeats += 1
                    if self.first_failure_time is None:
                        self.first_failure_time = probe_start
                    self._notify(
                        "HEARTBEAT_MISSED",
                        active_server=current_target,
                        missed_count=self.missed_heartbeats,
                        error="Socket timeout (no response within 3s)"
                    )

                except Exception as e:
                    if not self.stop_event.is_set():
                        self.missed_heartbeats += 1
                        if self.first_failure_time is None:
                            self.first_failure_time = probe_start
                        self._notify(
                            "HEARTBEAT_MISSED",
                            active_server=current_target,
                            missed_count=self.missed_heartbeats,
                            error=str(e)
                        )

                # Check if failure threshold reached
                if self.missed_heartbeats >= self.max_missed_heartbeats:
                    detection_time = time.time() - self.first_failure_time
                    self.last_detection_time = detection_time

                    self._notify(
                        "FAILURE_DETECTED",
                        failed_server=current_target,
                        detection_time=detection_time
                    )

                    if self.active_server == "PRIMARY":
                        failover_start = time.time()
                        self._notify("FAILOVER_STARTED")

                        # 1. Close failed Primary connection
                        try:
                            self.socket.close()
                        except Exception:
                            pass

                        # 2. Attempt connection to Backup Server
                        try:
                            backup_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            backup_socket.settimeout(self.socket_timeout)
                            backup_socket.connect((self.backup_ip, self.backup_port))

                            self.failover_duration = (time.time() - failover_start) * 1000

                            # 3. Update connection state and active server
                            self.socket = backup_socket
                            self.active_server = "BACKUP"
                            self.active_ip = self.backup_ip
                            self.active_port = self.backup_port

                            # 4. Reset failure metrics
                            self.missed_heartbeats = 0
                            self.first_failure_time = None

                            self._notify(
                                "BACKUP_CONNECTED",
                                ip=self.backup_ip,
                                port=self.backup_port
                            )
                            self._notify(
                                "FAILOVER_COMPLETED",
                                active_server="BACKUP",
                                ip=self.backup_ip,
                                port=self.backup_port,
                                detection_time=detection_time,
                                failover_duration=self.failover_duration
                            )

                        except Exception as e:
                            self.is_connected = False
                            self.stop_event.set()
                            self._notify(
                                "CONNECTION_FAILED",
                                message=f"Could not connect to Backup Server at {self.backup_ip}:{self.backup_port} ({e})"
                            )
                            break
                    else:
                        # Backup Server also failed
                        self.is_connected = False
                        self.stop_event.set()
                        self._notify(
                            "DISCONNECTED",
                            message="Backup Server unreachable."
                        )
                        break

    def send_command(self, command):
        """
        Sends an interactive command to the currently active server.
        Returns the server's reply string, or None if transmission fails.
        """
        with self.socket_lock:
            if not self.is_connected or self.socket is None:
                return None

            try:
                self.socket.sendall(command.encode("utf-8"))

                if command.upper() == "EXIT":
                    return "Exiting session."

                response = self.socket.recv(BUFFER_SIZE).decode("utf-8").strip()
                if not response:
                    return None
                return response

            except Exception:
                return None

    def disconnect(self):
        """Cleanly stops heartbeat monitoring and closes the active socket."""
        self.stop_event.set()
        with self.socket_lock:
            self.is_connected = False
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None

        if self.heartbeat_thread and threading.current_thread() != self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=1.0)
            self.heartbeat_thread = None

        self._notify("DISCONNECTED")


def start_client():
    """
    Command-line interface (CLI) for running the client interactively.
    Invoked when running: python client.py
    """
    def cli_event_handler(event_type, data):
        if event_type == "PRIMARY_CONNECTED":
            print(f"[CONNECTED] Successfully connected to server at {data['ip']}:{data['port']}")
            display_connection_status(data)
            print("Available commands: STATUS | TIME | MESSAGE <text> | EXIT\n")
        elif event_type == "HEARTBEAT_PING":
            print(f"\n[HEARTBEAT] PING -> {data['active_server']}")
        elif event_type == "HEARTBEAT_PONG":
            print(f"[HEARTBEAT] PONG <- {data['active_server']} (Response time: {data['response_time']:.2f} ms)")
        elif event_type == "HEARTBEAT_MISSED":
            print(f"[HEARTBEAT] Timeout: No response from {data['active_server']} ({data['missed_count']}/{MAX_MISSED_HEARTBEATS} missed).")
        elif event_type == "FAILURE_DETECTED":
            print(f"\n[FAILURE DETECTED] Primary server is not responding.")
            print(f"[FAILURE DETECTED] Approximate failure detection time: {data['detection_time']:.2f} seconds.")
        elif event_type == "FAILOVER_STARTED":
            print("[FAILOVER] Attempting connection to Backup Server...")
        elif event_type == "FAILOVER_COMPLETED":
            print(f"[FAILOVER] Connected to Backup Server at {data['ip']}:{data['port']}")
            print(f"[FAILOVER] Reconnection handshake took: {data.get('failover_duration', 0.0):.2f} ms")
            print("[FAILOVER] Client successfully switched to Backup Server.")
            display_connection_status(data)
        elif event_type == "CONNECTION_FAILED":
            print(f"[ERROR] {data.get('message', 'Connection failed.')}")

    client = NetFailoverClient(event_callback=cli_event_handler)

    try:
        success = client.connect()
        if not success:
            return

        client.start_heartbeat()

        while client.is_connected:
            try:
                command = input("Enter command: ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not command:
                continue

            if command.upper() == "EXIT":
                print("[EXIT] Exiting client session...")
                client.send_command("EXIT")
                break

            response = client.send_command(command)
            if response is None:
                if not client.is_connected:
                    print("[DISCONNECTED] Server closed the connection.")
                    break
                print(f"[ERROR] Communication error with {client.active_server} server.")
            else:
                print(f"[RECEIVED] Server response: {response}")

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

    finally:
        client.disconnect()
        print("[CLOSED] Socket connection closed.")


if __name__ == "__main__":
    start_client()