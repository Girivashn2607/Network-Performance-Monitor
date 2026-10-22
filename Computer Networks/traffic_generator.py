"""
Simulated traffic generator for testing and demonstrating network monitor.
Generates local loopback UDP/TCP packets or external requests on demand.
"""

import time
import socket
import threading


class TrafficGenerator:
    def __init__(self, port: int = 49152):
        self.port = port
        self.is_running = False
        self._threads = []
        self._server_sock = None

    def _udp_receiver(self):
        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._server_sock.bind(("127.0.0.1", self.port))
            self._server_sock.settimeout(0.5)
            while self.is_running:
                try:
                    _, _ = self._server_sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except Exception:
                    break
        except Exception:
            pass
        finally:
            if self._server_sock:
                try:
                    self._server_sock.close()
                except Exception:
                    pass

    def _udp_sender(self, payload_kb: int = 16, delay_sec: float = 0.001):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = b"X" * (payload_kb * 1024)
        while self.is_running:
            try:
                sock.sendto(payload, ("127.0.0.1", self.port))
                time.sleep(delay_sec)
            except Exception:
                time.sleep(0.01)
        sock.close()

    def start(self, num_senders: int = 2, payload_kb: int = 16, delay_sec: float = 0.001):
        """Start generating simulated traffic."""
        if self.is_running:
            return
        self.is_running = True

        recv_t = threading.Thread(target=self._udp_receiver, daemon=True)
        recv_t.start()
        self._threads.append(recv_t)

        time.sleep(0.05)  # Let receiver bind

        for _ in range(num_senders):
            send_t = threading.Thread(
                target=self._udp_sender,
                args=(payload_kb, delay_sec),
                daemon=True,
            )
            send_t.start()
            self._threads.append(send_t)

    def stop(self):
        """Stop generating traffic."""
        self.is_running = False
        self._threads.clear()


if __name__ == "__main__":
    print("Testing Traffic Generator for 3 seconds...")
    gen = TrafficGenerator()
    gen.start()
    time.sleep(3)
    gen.stop()
    print("Traffic Generator stopped.")

