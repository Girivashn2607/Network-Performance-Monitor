# Cisco Packet Tracer - Network Performance Monitor Lab Guide

Complete step-by-step guide for monitoring and analyzing network performance inside **Cisco Packet Tracer 9.0.1**.

---

## 1. Topology & Architecture Overview

```
 [NMS / Syslog Server]
    (192.168.10.10)
          |
   [SW1-HQ-Switch] (192.168.10.2)
          | G0/0
   [R1-HQ-Gateway] (192.168.10.1)
          |
          | WAN (10.0.0.0/30) - IP SLA RTT Probing, NetFlow, QoS
          |
   [R2-Branch-Gateway] (10.0.0.2)
          | G0/0
   [SW2-Branch-Switch] (192.168.20.2)
          |
    [Branch-Host-PC]
    (192.168.20.100)
```

### IP Addressing Table

| Device | Interface | IP Address | Subnet Mask | Default Gateway | Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R1-HQ-Gateway** | G0/0 (LAN) | `192.168.10.1` | `255.255.255.0` | N/A | HQ Core Gateway / SNMP Agent / IP SLA Sender |
| **R1-HQ-Gateway** | G0/1 (WAN) | `10.0.0.1` | `255.255.255.252` | N/A | WAN Uplink / NetFlow Exporter / QoS |
| **R2-Branch-Gateway** | G0/1 (WAN) | `10.0.0.2` | `255.255.255.252` | N/A | Branch Gateway / SLA Responder |
| **R2-Branch-Gateway** | G0/0 (LAN) | `192.168.20.1` | `255.255.255.0` | N/A | Branch LAN Gateway |
| **SW1-HQ-Switch** | VLAN 1 | `192.168.10.2` | `255.255.255.0` | `192.168.10.1` | HQ Layer 2 Switch / SNMP Agent |
| **NMS-Server** | FastEth 0 | `192.168.10.10` | `255.255.255.0` | `192.168.10.1` | NMS Station (Syslog, NetFlow, SNMP MIB Browser) |
| **Admin-PC** | FastEth 0 | `192.168.10.50` | `255.255.255.0` | `192.168.10.1` | Admin Workstation (MIB Browser) |
| **Branch-PC** | FastEth 0 | `192.168.20.100` | `255.255.255.0` | `192.168.20.1` | End-Host (Traffic Generator) |

---

## 2. Quick Launch: Ready-to-Run Lab Files

This demo includes four pre-built labs in `packet_tracer_demo/`:

1. **`SNMP_Performance_Monitor.pkt`**: Router & Switch SNMP monitoring with MIB browser queries.
2. **`NetFlow_Traffic_Monitor.pkt`**: Traditional NetFlow monitoring, top-talkers, and flow cache export.
3. **`Flexible_NetFlow_Monitor.pkt`**: Next-gen Flexible NetFlow (FNF) flow record monitoring.
4. **`QoS_Congestion_Monitor.pkt`**: QoS bandwidth allocation, priority queuing, and drop counters.

### Launching Labs:
Run the launcher script:
```bash
python open_cpt_lab.py
```
Or double-click any `.pkt` file directly inside the `packet_tracer_demo/` folder.

---

## 3. Monitoring Capabilities & Verification Walkthrough

### A. SNMP Network Monitoring (MIB Browser)
1. Open `SNMP_Performance_Monitor.pkt` or configure R1 using [`HQ_Router_R1.ios`](file:///c:/Users/ssgir/OneDrive/Desktop/Projects/Computer%20Networks/packet_tracer_demo/configs/HQ_Router_R1.ios).
2. Click on **Admin-PC** or **NMS-Server** -> Open **Desktop** tab -> Click **MIB Browser**.
3. In MIB Browser:
   - **Address**: `192.168.10.1`
   - **Read Community**: `public`
   - **Write Community**: `private`
   - **SNMP Version**: `v2c`
4. Expand the MIB tree:
   - Navigate: `iso(1) -> org(3) -> dod(6) -> internet(1) -> mgmt(2) -> mib-2(1)`
   - **System info**: Select `system -> sysDescr` -> Click **Go** (Returns Cisco IOS version).
   - **Interface Traffic Counters**:
     - Navigate to `interfaces -> ifTable -> ifEntry -> ifInOctets`.
     - Click **Go** or **Get Table** to view received bytes on all interfaces in real time.
     - Navigate to `ifOutOctets` to view transmitted bytes.
     - Navigate to `ifOperStatus` to check operational status (`1 = UP`, `2 = DOWN`).

---

### B. Cisco IP SLA Latency & RTT Probing
R1 continuously probes R2 over the WAN link every 5 seconds to track Round Trip Time (RTT) and latency degradation.

1. Open CLI on **R1-HQ-Gateway**.
2. Run SLA Summary:
   ```cisco
   show ip sla summary
   ```
   *Output shows operation ID `1`, type `icmp-echo`, target `10.0.0.2`, state `Active`, and latest RTT.*
3. Run detailed SLA performance metrics:
   ```cisco
   show ip sla statistics 1
   ```
   *Shows:*
   - **RTT**: Latest RTT (e.g., `4 ms`), Min RTT, Max RTT, Average RTT.
   - **Packet Loss / Success**: Number of successful probes vs timeouts/failures.

---

### C. NetFlow Traffic Flow & Top-Talkers
1. Generate test traffic:
   - On **Branch-PC**, open Command Prompt:
     ```cmd
     ping -t 192.168.10.10
     ```
   - Open Web Browser on **Branch-PC** and navigate to `http://192.168.10.10`.
2. Inspect Flow Cache on **R1-HQ-Gateway**:
   ```cisco
   show ip cache flow
   ```
   *Output displays:*
   - Protocol (ICMP, TCP, UDP), Source IP/Port, Destination IP/Port.
   - Packets and bytes per flow.
   - Active flow exports sent to NMS Collector (`192.168.10.10:2055`).

---

### D. Syslog Centralized Event & Performance Alerts
1. On **NMS-Server**, open **Services** tab -> Click **SYSLOG** -> Ensure service is **On**.
2. Simulate link degradation/flap on **R1-HQ-Gateway**:
   ```cisco
   configure terminal
   interface GigabitEthernet0/1
   shutdown
   ```
3. Observe **NMS-Server SYSLOG window**:
   - Immediate alert arrives: `%LINK-5-CHANGED: Interface GigabitEthernet0/1, changed state to administratively down`.
   - SNMP linkdown trap logged.
4. Restore link:
   ```cisco
   no shutdown
   ```
   - `%LINK-5-CHANGED: Interface GigabitEthernet0/1, changed state to up`.

---

### E. Quality of Service (QoS) Queue & Drops
1. Run QoS verification on **R1-HQ-Gateway**:
   ```cisco
   show policy-map interface GigabitEthernet0/1
   ```
2. Inspect:
   - **Class-map CRITICAL-TRAFFIC**: Matches ICMP / SNMP with priority bandwidth.
   - **Class-map class-default**: Best-effort traffic.
   - **Packets matched, bytes matched, and drop counts**.

---

### F. Packet Tracer Simulation Mode (Visual PDU Analysis)
1. In bottom-right corner of Packet Tracer, click **Simulation** (Shift + S).
2. Click **Show All/None**, then click **Edit Filters**.
3. Check only:
   - **SNMP**
   - **ICMP**
   - **Syslog**
4. Send an SNMP query from Admin-PC or trigger an IP SLA probe.
5. Click **Capture / Forward** to watch packets hop from device to device.
6. Click any packet envelope on the wire to open **PDU Information** showing:
   - OSI Layers (Layer 3 IP headers, Layer 4 UDP port 161/162/514, Layer 7 SNMP/Syslog payload).

