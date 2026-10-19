"""
NetFailover - Central Configuration Module
Defines network endpoints, heartbeat intervals, and failure detection parameters.
"""

# Server Network Configuration
SERVER_IP = "127.0.0.1"
PRIMARY_PORT = 5000
BACKUP_PORT = 5001

# Heartbeat & Fault Detection Configuration
HEARTBEAT_INTERVAL = 2       # Interval between PING probes (seconds)
SOCKET_TIMEOUT = 3.0         # Socket operation timeout (seconds)
MAX_MISSED_HEARTBEATS = 3    # Consecutive missed heartbeats before declaring failure

# Buffer Configuration
BUFFER_SIZE = 1024           # Socket transmission buffer size in bytes