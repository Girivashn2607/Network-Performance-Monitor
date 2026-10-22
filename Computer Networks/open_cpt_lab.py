"""
Launcher script for Cisco Packet Tracer Network Performance Monitoring labs.
Detects Packet Tracer 9.0.1 installation and opens selected lab file.
"""

import os
import sys
import subprocess
from pathlib import Path

LABS = {
    "1": ("SNMP_Performance_Monitor.pkt", "SNMP Router & Switch Monitoring Lab"),
    "2": ("NetFlow_Traffic_Monitor.pkt", "Traditional NetFlow Traffic & Top-Talkers Lab"),
    "3": ("Flexible_NetFlow_Monitor.pkt", "Flexible NetFlow (FNF) Flow Monitoring Lab"),
    "4": ("QoS_Congestion_Monitor.pkt", "QoS Queuing, Drops & Congestion Lab"),
}

PT_PATHS = [
    r"C:\Program Files\Cisco Packet Tracer 9.0.1\bin\PacketTracer.exe",
    r"C:\Program Files\Cisco Packet Tracer 8.2.2\bin\PacketTracer.exe",
    r"C:\Program Files\Cisco Packet Tracer 8.2.1\bin\PacketTracer.exe",
    r"C:\Program Files\Cisco Packet Tracer 8.2.0\bin\PacketTracer.exe",
    r"C:\Program Files\Cisco Packet Tracer 8.0\bin\PacketTracer.exe",
    r"C:\Program Files\Cisco Packet Tracer 7.3.1\bin\PacketTracer.exe",
    r"C:\Program Files (x86)\Cisco Packet Tracer 9.0.1\bin\PacketTracer.exe",
]


def find_packet_tracer():
    for path in PT_PATHS:
        if os.path.exists(path):
            return path
    return None


def main():
    pt_exe = find_packet_tracer()
    if not pt_exe:
        print("[!] Cisco Packet Tracer executable not found in standard paths.")
        sys.exit(1)

    print(f"[*] Found Cisco Packet Tracer at: {pt_exe}\n")
    print("Available Network Performance Monitor Labs:")
    for key, (filename, desc) in LABS.items():
        print(f"  [{key}] {desc} ({filename})")

    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("\nUsage: python open_cpt_lab.py [1|2|3|4]")
        sys.exit(0)

    choice = sys.argv[1] if len(sys.argv) > 1 else input("\nEnter lab number (1-4, default=1): ").strip() or "1"

    if choice not in LABS:
        print(f"[!] Invalid selection: {choice}")
        sys.exit(1)

    filename, desc = LABS[choice]
    lab_path = Path(__file__).resolve().parent / "packet_tracer_demo" / filename

    if not lab_path.exists():
        print(f"[!] Lab file not found: {lab_path}")
        sys.exit(1)

    print(f"[*] Launching {desc}...")
    subprocess.Popen([pt_exe, str(lab_path)])
    print("[+] Packet Tracer launched successfully!")


if __name__ == "__main__":
    main()
