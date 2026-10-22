# Network Performance Monitor Demo

Real-time network performance monitoring tool for computer networks education and diagnostics.

## Features

- **Live Bandwidth & Throughput Tracking**:
  - Real-time download/upload speeds in Mbps and KB/s.
  - Cumulative sent and received bytes.
- **Latency & RTT Probing**:
  - Continuous round-trip time measurements to Google DNS (`8.8.8.8`) and Cloudflare (`1.1.1.1`).
- **Packet Activity & Health**:
  - Ingress and egress packets per second.
  - Drop and error counters.
- **Socket Connection States**:
  - Breakdown of active connections (`ESTABLISHED`, `LISTEN`, `TIME_WAIT`, `CLOSE_WAIT`).
- **Network Interface Details (NIC)**:
  - Adapter name, operational status (UP/DOWN), IPv4 address, MAC address, link speed, and data metrics.
- **Dual Visual Interfaces**:
  1. **Web Dashboard**: Modern dark-mode UI with live Chart.js graphs powered by WebSockets.
  2. **Terminal TUI**: Real-time interactive command-line interface powered by `rich`.
- **Built-in Traffic Simulator**:
  - Synthesize network load with one click or flag to observe dynamic metric fluctuations.

---

## Project Structure

```
Computer Networks/
├── app.py                # FastAPI web server with WebSocket streaming (port 8000)
├── monitor_cli.py        # Terminal TUI dashboard
├── network_collector.py  # Network statistics collector (psutil, latency probing)
├── traffic_generator.py  # Network traffic load generator
├── open_cpt_lab.py       # Cisco Packet Tracer lab launcher
├── packet_tracer_demo/   # Cisco Packet Tracer Network Performance Monitoring labs
│   ├── SNMP_Performance_Monitor.pkt    # SNMP Router & Switch monitoring
│   ├── NetFlow_Traffic_Monitor.pkt     # NetFlow traffic flow & top talkers
│   ├── Flexible_NetFlow_Monitor.pkt    # Flexible NetFlow (FNF)
│   ├── QoS_Congestion_Monitor.pkt      # QoS queuing, bandwidth & drops
│   ├── LAB_GUIDE.md                    # Complete lab walkthrough & commands
│   └── configs/                        # Cisco IOS configurations (R1, R2, SW1)
├── static/
│   ├── index.html        # Web dashboard layout
│   ├── style.css         # Dark theme styling
│   └── app.js            # WebSocket client and dynamic charts
└── README.md             # Documentation
```

---

## Cisco Packet Tracer Demo

Pre-configured Cisco Packet Tracer 9.0.1 labs for hardware-level network performance monitoring:

- **SNMP MIB Querying**: Live polling of `ifInOctets`, `ifOutOctets`, and `ifOperStatus` using NMS MIB Browser.
- **Cisco IP SLA**: Synthetic ICMP echo latency and RTT probes measuring delay and packet loss across WAN.
- **NetFlow Flow Export**: Flow-cache inspection (`show ip cache flow`) and export to port 2055.
- **Syslog Alerts**: Real-time logging of interface flaps, link states, and threshold alerts.
- **QoS Monitoring**: Inspect queue depth and dropped packets using `show policy-map interface`.

### Launch Packet Tracer Labs
```bash
python open_cpt_lab.py
```
Or open [`packet_tracer_demo/LAB_GUIDE.md`](file:///c:/Users/ssgir/OneDrive/Desktop/Projects/Computer%20Networks/packet_tracer_demo/LAB_GUIDE.md) for step-by-step instructions.

---

## How to Run

### Option 1: Web Dashboard (Recommended)

1. Start the server:
   ```bash
   python app.py
   ```
2. Open your browser:
   ```
   http://127.0.0.1:8000
   ```
3. Click **"Simulate Traffic"** in the top bar to test live network load spikes.

---

### Option 2: Terminal Monitor (TUI)

1. Run the terminal dashboard:
   ```bash
   python monitor_cli.py
   ```
2. Run with built-in traffic generation enabled:
   ```bash
   python monitor_cli.py --simulate-traffic
   ```
3. Press `Ctrl + C` to stop.

