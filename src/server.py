import threading
import netifaces
import socket
import time

from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

DEFAULT_UDP_PORT = 15733


class Server:
    PROMPT_STYLE = Style.from_dict(
        {
            "prompt-name": "#808080 bold",
            "good": "#00ff00 bold",
            "new": "#F9F1A5 bold",
            "bad": "#ff0000",
            "others": "#7592F9 bold",
        }
    )

    BROADCAST_INTERVAL: int = 5

    def __init__(self, name: str):
        self.name: str = name

        self.tcp_socket: socket.socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )
        self.udp_socket: socket.socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        )
        self.tcp_address: tuple(str, int) | None = None
        self.ip: str | None = None

        self.clients: dict[int, socket.socket] = {}
        self.client_count: int = 0
        self.lock = threading.Lock()

        self.running = True

    def _add_client(self, s: socket.socket, address: tuple[str, int]):
        with self.lock:
            self.clients[hash(address)] = s
            self.client_count += 1

    def _remove_client(self, address: tuple[str, int]):
        with self.lock:
            del self.clients[hash(address)]

    def _get_client(self, address: tuple[str, int]):
        with self.lock:
            return self.clients[hash(address)]

    def _get_address(self):
        return self.tcp_socket.getsockname()

    def _get_all_interfaces(self):
        results = {}
        for iface in netifaces.interfaces():
            try:
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET not in addrs:
                    continue
                ipv4_info = addrs[netifaces.AF_INET][0]
                ip = ipv4_info.get("addr")
                netmask = ipv4_info.get("netmask")
                broadcast = ipv4_info.get("broadcast")

                if ip is None or ip.startswith("127.") or ip.startswith("169.254."):
                    continue

                if broadcast is None:
                    continue

                results[iface] = {}
                results[iface]["ip"] = ip
                results[iface]["netmask"] = netmask
                results[iface]["broadcast"] = broadcast
            except Exception:
                continue
        return results

    def listen_client(self, s: socket.socket, address: tuple[str, int]):
        try:
            data = s.recv(1024)
            if not data:
                return
            name = data.decode(errors="ignore")
            if name.startswith("_NAME="):
                name = name[6:].strip()
            else:
                name = f"Anonymous #{self.client_count}"

            while True:
                data = s.recv(1024)
                if not data:
                    break

                str_data = data.decode()
                with self.lock:
                    for sock in self.clients.values():
                        if sock is not s:
                            sock.send(f"{name}:{str_data}".encode())
        finally:
            with self.lock:
                self._remove_client(address)
            s.close()

    def start_broadcast(self):
        self.udp_socket.bind(("", DEFAULT_UDP_PORT))
        for iface, data in self._get_all_interfaces().items():
            threading.Thread(
                target=self.broadcast_loop, args=(data["broadcast"],), daemon=True
            ).start()

    def broadcast_loop(self, broadcast_address: str):
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = f"ROOM_HOST:{self.ip}:{self.tcp_address[1]}:{self.name}"

        while self.running:
            self.udp_socket.sendto(msg.encode(), (broadcast_address, DEFAULT_UDP_PORT))
            time.sleep(Server.BROADCAST_INTERVAL)

    def on_client_join(self, s: socket.socket, address: tuple[str, int]):
        print_formatted_text(
            HTML(f"<new>New connection from address {address}</new>"),
            style=Server.PROMPT_STYLE,
        )
        self._add_client(s, address)
        self.listen_client(s, address)

    def client_join(self):
        client_socket, address = self.tcp_socket.accept()
        new_client_thread = threading.Thread(
            target=self.on_client_join, args=(client_socket, address), daemon=True
        )
        new_client_thread.start()

    def start(self):
        ts: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ts.connect(("8.8.8.8", 80))
        self.ip = ts.getsockname()[0]
        ts.close()

        self.tcp_socket.bind(("", 0))
        address = self.tcp_socket.getsockname()

        self.tcp_address = address
        self.tcp_socket.listen()
        print_formatted_text(
            HTML(f"<new>Listening on {address}</new>"), style=Server.PROMPT_STYLE
        )

        self.start_broadcast()

        # Continuously accept clients
        try:
            while self.running:
                self.client_join()
        except OSError as e:
            print(f"Error: {e}")

    def stop(self):
        self.running = False
        print_formatted_text(
            HTML("<bad>Disconnecting all clients...</bad>"), style=Server.PROMPT_STYLE
        )
        with self.lock:
            for sock in self.clients.values():
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                except Exception:
                    pass
            self.clients.clear()
        self.tcp_socket.close()
        self.udp_socket.close()
        print_formatted_text(HTML("<bad>Room closed.</bad>"), style=Server.PROMPT_STYLE)
