"""
Network metrics collector module.
Gathers real-time bandwidth, interface stats, socket states, and latency.
"""

import time
import socket
import threading
from collections import deque
import psutil


class NetworkCollector:
    def __init__(self, history_len: int = 60, ping_targets: list[str] | None = None):
        self.history_len = history_len
        self.ping_targets = ping_targets or ["8.8.8.8", "1.1.1.1"]
        self.lock = threading.Lock()

        # IO counters previous state
        self._prev_io = psutil.net_io_counters()
        self._prev_time = time.time()

        # Rolling history
        self.history = {
            "timestamps": deque(maxlen=history_len),
            "bytes_recv_rate": deque(maxlen=history_len),  # B/s
            "bytes_sent_rate": deque(maxlen=history_len),  # B/s
            "packets_recv_rate": deque(maxlen=history_len),  # pkts/s
            "packets_sent_rate": deque(maxlen=history_len),  # pkts/s
            "latencies": {tgt: deque(maxlen=history_len) for tgt in self.ping_targets},
        }

        # Latest ping latency cache
        self.latest_latency = {tgt: 0.0 for tgt in self.ping_targets}

        # Start background latency checker thread
        self._running = True
        self._latency_thread = threading.Thread(target=self._latency_worker, daemon=True)
        self._latency_thread.start()

    def _measure_tcp_rtt(self, host: str, port: int = 53, timeout: float = 1.0) -> float:
        """Measure TCP connect RTT in milliseconds without requiring root/admin raw sockets."""
        t0 = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            rtt = (time.perf_counter() - t0) * 1000.0
            return round(rtt, 2)
        except Exception:
            return -1.0  # Unreachable or timed out
        finally:
            sock.close()

    def _latency_worker(self):
        """Worker measuring latency periodically."""
        while self._running:
            for tgt in self.ping_targets:
                rtt = self._measure_tcp_rtt(tgt, port=53, timeout=1.0)
                with self.lock:
                    self.latest_latency[tgt] = rtt
            time.sleep(1.0)

    def get_interface_stats(self) -> list[dict]:
        """Fetch per-interface network status and stats."""
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        io_per_nic = psutil.net_io_counters(pernic=True)

        interfaces = []
        for name, if_stat in stats.items():
            ipv4 = "-"
            ipv6 = "-"
            mac = "-"
            if name in addrs:
                for addr in addrs[name]:
                    if addr.family == socket.AF_INET:
                        ipv4 = addr.address
                    elif addr.family == socket.AF_INET6:
                        ipv6 = addr.address.split("%")[0]
                    elif hasattr(psutil, "AF_LINK") and addr.family == psutil.AF_LINK:
                        mac = addr.address

            nic_io = io_per_nic.get(name)
            interfaces.append({
                "name": name,
                "is_up": if_stat.isup,
                "speed_mbps": if_stat.speed,
                "mtu": if_stat.mtu,
                "ipv4": ipv4,
                "ipv6": ipv6,
                "mac": mac,
                "bytes_sent": nic_io.bytes_sent if nic_io else 0,
                "bytes_recv": nic_io.bytes_recv if nic_io else 0,
                "packets_sent": nic_io.packets_sent if nic_io else 0,
                "packets_recv": nic_io.packets_recv if nic_io else 0,
                "errin": nic_io.errin if nic_io else 0,
                "errout": nic_io.errout if nic_io else 0,
                "dropin": nic_io.dropin if nic_io else 0,
                "dropout": nic_io.dropout if nic_io else 0,
            })
        return interfaces

    def get_socket_summary(self) -> dict:
        """Count connection states (ESTABLISHED, LISTEN, etc.)."""
        states = {}
        total = 0
        try:
            conns = psutil.net_connections(kind="inet")
            for c in conns:
                st = c.status if c.status else "UNKNOWN"
                states[st] = states.get(st, 0) + 1
                total += 1
        except Exception:
            states["ERROR"] = 1
        return {"total": total, "by_status": states}

    def collect(self) -> dict:
        """Collect snapshot of network rates and append to history."""
        curr_time = time.time()
        curr_io = psutil.net_io_counters()

        dt = curr_time - self._prev_time
        if dt <= 0:
            dt = 1e-6

        # Rates (per second)
        bytes_recv_rate = max(0.0, (curr_io.bytes_recv - self._prev_io.bytes_recv) / dt)
        bytes_sent_rate = max(0.0, (curr_io.bytes_sent - self._prev_io.bytes_sent) / dt)
        pkts_recv_rate = max(0.0, (curr_io.packets_recv - self._prev_io.packets_recv) / dt)
        pkts_sent_rate = max(0.0, (curr_io.packets_sent - self._prev_io.packets_sent) / dt)

        self._prev_io = curr_io
        self._prev_time = curr_time

        timestamp_str = time.strftime("%H:%M:%S", time.localtime(curr_time))

        with self.lock:
            self.history["timestamps"].append(timestamp_str)
            self.history["bytes_recv_rate"].append(bytes_recv_rate)
            self.history["bytes_sent_rate"].append(bytes_sent_rate)
            self.history["packets_recv_rate"].append(pkts_recv_rate)
            self.history["packets_sent_rate"].append(pkts_sent_rate)

            for tgt in self.ping_targets:
                self.history["latencies"][tgt].append(self.latest_latency[tgt])

            current_latencies = dict(self.latest_latency)

        interfaces = self.get_interface_stats()
        sockets = self.get_socket_summary()

        return {
            "timestamp": timestamp_str,
            "bandwidth": {
                "download_bytes_sec": bytes_recv_rate,
                "upload_bytes_sec": bytes_sent_rate,
                "download_kbps": (bytes_recv_rate * 8) / 1000.0,
                "upload_kbps": (bytes_sent_rate * 8) / 1000.0,
                "download_mbps": (bytes_recv_rate * 8) / 1_000_000.0,
                "upload_mbps": (bytes_sent_rate * 8) / 1_000_000.0,
                "download_kbytes_sec": bytes_recv_rate / 1024.0,
                "upload_kbytes_sec": bytes_sent_rate / 1024.0,
            },
            "packets": {
                "recv_rate": pkts_recv_rate,
                "sent_rate": pkts_sent_rate,
                "errin_total": curr_io.errin,
                "errout_total": curr_io.errout,
                "dropin_total": curr_io.dropin,
                "dropout_total": curr_io.dropout,
            },
            "totals": {
                "bytes_recv": curr_io.bytes_recv,
                "bytes_sent": curr_io.bytes_sent,
                "packets_recv": curr_io.packets_recv,
                "packets_sent": curr_io.packets_sent,
            },
            "latencies_ms": current_latencies,
            "sockets": sockets,
            "interfaces": interfaces,
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
            },
        }

    def get_history(self) -> dict:
        """Return history as plain lists for charting."""
        with self.lock:
            return {
                "timestamps": list(self.history["timestamps"]),
                "download_kbps": [
                    round((b * 8) / 1000.0, 2)
                    for b in self.history["bytes_recv_rate"]
                ],
                "upload_kbps": [
                    round((b * 8) / 1000.0, 2)
                    for b in self.history["bytes_sent_rate"]
                ],
                "packets_recv": list(self.history["packets_recv_rate"]),
                "packets_sent": list(self.history["packets_sent_rate"]),
                "latencies": {
                    tgt: list(self.history["latencies"][tgt])
                    for tgt in self.ping_targets
                },
            }

    def stop(self):
        self._running = False

