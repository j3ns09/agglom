import threading
import netifaces
import socket
import time

from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import choice


DEFAULT_UDP_PORT = 15733


class Server:
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
                            sock.send(f"[{name}] - {str_data}".encode())
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
        print(f"New connection from address {address}")
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
        print(f"Listening on {address}")

        self.start_broadcast()

        # Continuously accept clients
        try:
            while self.running:
                self.client_join()
        except OSError as e:
            print(f"Error: {e}")

    def stop(self):
        self.running = False
        print("Disconnecting all clients...")
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
        print("Room closed.")


class Client:
    DISCOVERY_INTERVAL = 8

    def __init__(self, name: str):
        self.name: str = name
        self.prompt_session: PromptSession = PromptSession()
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running: bool = True

    def discover_rooms(self, timeout=DISCOVERY_INTERVAL):
        """Listen for UDP broadcasts for `timeout` seconds, return list of (ip, port)"""
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind(("", DEFAULT_UDP_PORT))
        udp.settimeout(timeout)
        rooms = {}
        start = time.time()
        while time.time() - start < timeout:
            try:
                data, addr = udp.recvfrom(1024)
                msg = data.decode()
                if msg.startswith("ROOM_HOST:"):
                    _, ip, port_str, name = msg.split(":")
                    port = int(port_str)
                    rooms[name] = (ip, port)
            except socket.timeout:
                break
            except Exception:
                continue
        return rooms

    def join_room(self, ip: str, port: int):
        self.socket.connect((ip, port))
        print("Connected to room at", (ip, port))
        self.socket.send(f"_NAME={self.name}".encode())

        threading.Thread(target=self.receive_loop, daemon=True).start()

    def send_loop(self):
        with patch_stdout():
            while self.running:
                try:
                    message: str = self.prompt_session.prompt("[Vous] >>> ")
                    if message.lower() in ("exit", "quit"):
                        self.running = False
                        break
                    self.socket.send(message.encode())
                except (EOFError, KeyboardInterrupt):
                    self.running = False
                    break

    def receive_loop(self):
        while self.running:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                message = data.decode(errors="ignore")
                print(f"{message}")
            except Exception as e:
                print(f"\nErreur: {e}")
                break

    def run(self):
        result: str = choice(
            message="Voulez-vous créer ou rejoindre une salle ? :",
            options=[("host", "Créer une salle"), ("client", "Rejoindre une salle")],
            default="client",
        )

        if result == "host":
            name = prompt("Quel nom donner à la salle ? : ")
            host = Server(name)
            threading.Thread(target=host.start, daemon=True).start()

            time.sleep(0.5)
            with host.lock:
                self.join_room("127.0.0.1", host.tcp_address[1])

        else:
            rooms: set = self.discover_rooms()
            if not rooms:
                print("No rooms found.")
                return
            print("Rooms discovered:")

            result: str = choice(
                message="Veuillez choisir la salle :",
                options=[(addr, name) for name, addr in rooms.items()],
            )

            self.join_room(*result)

        self.send_loop()

    def disconnect(self):
        self.socket.close()


def main():
    name = input("Enter your name: ")
    client = Client(name)
    client.run()


if __name__ == "__main__":
    main()
