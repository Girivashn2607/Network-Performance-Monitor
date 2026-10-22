"""
Terminal Network Performance Monitor (CLI/TUI) using Rich.
Runs a live dashboard in the terminal.
"""

import sys
import time
import argparse
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from network_collector import NetworkCollector
from traffic_generator import TrafficGenerator


def format_bytes(b: float) -> str:
    """Format bytes into readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(b) < 1024.0:
            return f"{b:6.2f} {unit}"
        b /= 1024.0
    return f"{b:6.2f} PB"


def format_rate(bytes_sec: float) -> str:
    """Format throughput rate."""
    kbps = (bytes_sec * 8) / 1000.0
    mbps = kbps / 1000.0
    kbs = bytes_sec / 1024.0
    if mbps >= 1.0:
        return f"{mbps:6.2f} Mbps ({kbs:6.1f} KB/s)"
    return f"{kbps:6.2f} Kbps ({kbs:6.1f} KB/s)"


def latency_style(ms: float) -> str:
    if ms < 0:
        return "[bold red]FAIL[/bold red]"
    if ms < 35:
        return f"[bold green]{ms:5.1f} ms[/bold green]"
    if ms < 90:
        return f"[bold yellow]{ms:5.1f} ms[/bold yellow]"
    return f"[bold red]{ms:5.1f} ms[/bold red]"


def build_dashboard(data: dict, traffic_active: bool) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=1),
    )
    layout["left"].split_column(
        Layout(name="bandwidth", ratio=1),
        Layout(name="latency", ratio=1),
    )
    layout["right"].split_column(
        Layout(name="sockets", ratio=1),
        Layout(name="interfaces", ratio=1),
    )

    # Header
    sys_info = data.get("system", {})
    cpu = sys_info.get("cpu_percent", 0.0)
    mem = sys_info.get("memory_percent", 0.0)
    traffic_status = "[bold green]ON[/bold green]" if traffic_active else "[dim]OFF[/dim]"
    header_text = Text.from_markup(
        f"[bold cyan]NETWORK PERFORMANCE MONITOR[/bold cyan]  |  "
        f"Time: [white]{data['timestamp']}[/white]  |  "
        f"CPU: [cyan]{cpu:.1f}%[/cyan]  |  "
        f"RAM: [magenta]{mem:.1f}%[/magenta]  |  "
        f"Traffic Simulator: {traffic_status}"
    )
    layout["header"].update(Panel(header_text, style="blue"))

    # Bandwidth Panel
    bw = data["bandwidth"]
    totals = data["totals"]
    pkts = data["packets"]
    bw_table = Table(box=None, expand=True)
    bw_table.add_column("Metric", style="bold cyan")
    bw_table.add_column("Current Rate", justify="right")
    bw_table.add_column("Total Transferred", justify="right")

    bw_table.add_row(
        "Download (RX)",
        f"[green]{format_rate(bw['download_bytes_sec'])}[/green]",
        format_bytes(totals["bytes_recv"]),
    )
    bw_table.add_row(
        "Upload (TX)",
        f"[blue]{format_rate(bw['upload_bytes_sec'])}[/blue]",
        format_bytes(totals["bytes_sent"]),
    )
    bw_table.add_row(
        "Packets RX",
        f"[green]{pkts['recv_rate']:6.0f} pkt/s[/green]",
        f"{totals['packets_recv']:,} pkts",
    )
    bw_table.add_row(
        "Packets TX",
        f"[blue]{pkts['sent_rate']:6.0f} pkt/s[/blue]",
        f"{totals['packets_sent']:,} pkts",
    )
    bw_table.add_row(
        "Errors / Drops",
        f"Err: {pkts['errin_total'] + pkts['errout_total']}",
        f"Drop: {pkts['dropin_total'] + pkts['dropout_total']}",
    )
    layout["bandwidth"].update(Panel(bw_table, title="[bold]Bandwidth & Throughput[/bold]", border_style="cyan"))

    # Latency Panel
    lat_table = Table(box=None, expand=True)
    lat_table.add_column("Target Host", style="bold white")
    lat_table.add_column("Probe Type", justify="center")
    lat_table.add_column("RTT Latency", justify="right")
    for tgt, rtt in data.get("latencies_ms", {}).items():
        desc = "Google DNS" if "8.8.8.8" in tgt else "Cloudflare" if "1.1.1.1" in tgt else "Target"
        lat_table.add_row(f"{tgt} ({desc})", "TCP:53", latency_style(rtt))

    layout["latency"].update(Panel(lat_table, title="[bold]Network Latency (RTT)[/bold]", border_style="green"))

    # Sockets Panel
    sock_info = data.get("sockets", {})
    by_st = sock_info.get("by_status", {})
    sock_table = Table(box=None, expand=True)
    sock_table.add_column("State", style="bold")
    sock_table.add_column("Count", justify="right")
    for st, count in sorted(by_st.items(), key=lambda x: -x[1])[:6]:
        color = "green" if st == "ESTABLISHED" else "yellow" if st == "LISTEN" else "white"
        sock_table.add_row(f"[{color}]{st}[/{color}]", str(count))
    sock_table.add_row("[bold]TOTAL[/bold]", f"[bold cyan]{sock_info.get('total', 0)}[/bold cyan]")
    layout["sockets"].update(Panel(sock_table, title="[bold]Active Socket Connections[/bold]", border_style="yellow"))

    # Interfaces Panel
    if_table = Table(box=None, expand=True)
    if_table.add_column("Interface", style="bold")
    if_table.add_column("Status")
    if_table.add_column("IPv4")
    if_table.add_column("RX / TX", justify="right")
    for nic in data.get("interfaces", []):
        if not nic["is_up"] and nic["ipv4"] == "-":
            continue
        status_str = "[green]UP[/green]" if nic["is_up"] else "[red]DOWN[/red]"
        io_str = f"{format_bytes(nic['bytes_recv'])} / {format_bytes(nic['bytes_sent'])}"
        if_table.add_row(nic["name"][:16], status_str, nic["ipv4"], io_str)

    layout["interfaces"].update(Panel(if_table, title="[bold]Network Interfaces (NIC)[/bold]", border_style="magenta"))

    # Footer
    footer_text = Text.from_markup(
        "[dim]Press [bold white]Ctrl+C[/bold white] to exit. Web Dashboard runs at: "
        "[bold cyan]http://127.0.0.1:8000[/bold cyan][/dim]"
    )
    layout["footer"].update(Panel(footer_text, style="grey37"))

    return layout


def main():
    parser = argparse.ArgumentParser(description="Terminal Network Performance Monitor")
    parser.add_argument("--simulate-traffic", action="store_true", help="Start traffic simulator")
    parser.add_argument("--interval", type=float, default=1.0, help="Refresh interval in seconds")
    args = parser.parse_args()

    collector = NetworkCollector()
    traffic = TrafficGenerator()

    if args.simulate_traffic:
        traffic.start()

    console = Console()
    try:
        with Live(console=console, screen=True, refresh_per_second=4) as live:
            while True:
                data = collector.collect()
                dashboard = build_dashboard(data, traffic.is_running)
                live.update(dashboard)
                time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        traffic.stop()
        collector.stop()
        print("\nMonitor stopped.")


if __name__ == "__main__":
    main()

