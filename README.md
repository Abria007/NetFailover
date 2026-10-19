# NetFailover 🔄
**Network Fault Detection & Automatic Server Failover System**  
*Computer Networks Academic Project*

---

## 📌 Project Overview
NetFailover is a client-server Computer Networks system that detects when a primary server crashes or becomes unreachable and automatically switches the client to a backup standby server without restarting the client application.

The project demonstrates:
- **Reliable TCP socket communication** (`socket.AF_INET`, `socket.SOCK_STREAM`)
- **Heartbeat & Keepalive protocol** (`PING` / `PONG`)
- **Failure detection** using consecutive timeout counters (Threshold = 3)
- **Automatic failover** and transparent socket reconnection
- **Real-time NOC Tkinter GUI dashboard** with live network topology and telemetry
- **Latency (RTT), failure detection time, and failover switch duration measurement**

---

## ⚙️ System Architecture

```mermaid
flowchart TD
    subgraph Normal Operation
        Client[Client / NOC Dashboard] -->|1. TCP Connect| Primary[Primary Server :5000]
        Client -->|2. Periodic PING Heartbeat 2s| Primary
        Primary -.->|PONG Response| Client
    end

    subgraph Failure & Failover
        Primary -.->|💥 Crash / Process Killed| Missed[Missed Heartbeat Counter: 1, 2, 3]
        Missed --> Timeout[Timeout Threshold Reached ~6s]
        Timeout -->|3. Automatic Failover| Backup[Backup Server :5001]
        Client -->|4. Resume Communication & Requests| Backup
    end